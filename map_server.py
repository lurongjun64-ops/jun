#!/usr/bin/env python3
import json
import secrets
import subprocess
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
TOOL = ROOT / "location_tool.py"
HTML = ROOT / "static/map.html"
PYTHON = ROOT / ".venv/bin/python"
TOKEN = secrets.token_urlsafe(32)


def run_tool(*arguments):
    result = subprocess.run(
        [str(PYTHON), str(TOOL), *map(str, arguments)],
        text=True,
        capture_output=True,
        timeout=260,
    )
    text = (result.stdout if result.returncode == 0 else result.stderr) or "操作没有返回结果"
    return result.returncode == 0, text.strip()


class Handler(BaseHTTPRequestHandler):
    server_version = "RouteLabMap/1.0"

    def log_message(self, format, *args):
        return

    def _headers(self, status, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://unpkg.com; "
            "img-src 'self' data: https://*.tile.openstreetmap.org; "
            "connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
        self.end_headers()

    def _json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode()
        self._headers(status, "application/json; charset=utf-8")
        self.wfile.write(data)

    def _authorized(self):
        host = self.headers.get("Host", "")
        expected = f"127.0.0.1:{self.server.server_port}"
        origin = self.headers.get("Origin")
        return (
            host == expected
            and (not origin or origin == f"http://{expected}")
            and secrets.compare_digest(self.headers.get("X-Location-Token", ""), TOKEN)
        )

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            page = HTML.read_text().replace("__TOKEN__", TOKEN).encode()
            self._headers(200, "text/html; charset=utf-8")
            self.wfile.write(page)
            return
        if path == "/jun-logo.png":
            self._headers(200, "image/png")
            self.wfile.write((ROOT / "static/jun-logo.png").read_bytes())
            return
        if path == "/api/status":
            if not self._authorized():
                self._json(403, {"ok": False, "message": "会话验证失败"})
                return
            ok, message = run_tool("status")
            self._json(200 if ok else 503, {"ok": ok, "message": message})
            return
        self._json(404, {"ok": False, "message": "未找到"})

    def do_POST(self):
        path = urlparse(self.path).path
        if not self._authorized():
            self._json(403, {"ok": False, "message": "会话验证失败"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 4096:
                raise ValueError("请求过大")
            payload = json.loads(self.rfile.read(length) or b"{}")
            if path == "/api/set":
                ok, message = run_tool("set", payload.get("latitude"), payload.get("longitude"))
            elif path == "/api/clear":
                ok, message = run_tool("clear")
            elif path == "/api/reveal":
                ok, message = run_tool("reveal")
            elif path == "/api/shutdown":
                self._json(200, {"ok": True, "message": "地图服务已关闭"})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            else:
                self._json(404, {"ok": False, "message": "未找到"})
                return
            self._json(200 if ok else 503, {"ok": ok, "message": message})
        except Exception as exc:
            self._json(400, {"ok": False, "message": f"{type(exc).__name__}: {exc}"})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(url, flush=True)
    threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
