#!/usr/bin/env python3
import argparse
import asyncio
import json
import math
import subprocess
import sys
from pathlib import Path

from pymobiledevice3 import usbmux
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.amfi import AmfiService


ROOT = Path(__file__).resolve().parent
CLI = ROOT / ".venv/bin/pymobiledevice3"
PENDING = ROOT / ".pending-restore.json"


async def usb_devices():
    return [device for device in await usbmux.list_devices() if device.is_usb]


async def device_status():
    devices = await usb_devices()
    if not devices:
        raise RuntimeError("没有检测到 USB iPhone。请连接数据线、解锁并确认信任此电脑。")
    if len(devices) != 1:
        raise RuntimeError(f"检测到 {len(devices)} 台 USB iPhone，请只保留目标设备。")
    device = devices[0]
    lockdown = await create_using_usbmux(
        serial=device.serial, connection_type="USB", autopair=True
    )
    try:
        developer_mode = await lockdown.get_developer_mode_status()
        values = lockdown.all_values
        return {
            "serial": device.serial,
            "label": f"{values.get('DeviceName', 'iPhone')} · {values.get('ProductType', '未知机型')}",
            "ios": lockdown.product_version,
            "build": values.get("BuildVersion", "未知"),
            "developer_mode": bool(developer_mode),
        }
    finally:
        await lockdown.close()


async def reveal_developer_mode():
    devices = await usb_devices()
    if len(devices) != 1:
        raise RuntimeError(f"请连接并解锁一台 USB iPhone；当前发现 {len(devices)} 台。")
    lockdown = await create_using_usbmux(serial=devices[0].serial, connection_type="USB", autopair=True)
    try:
        if await lockdown.get_developer_mode_status():
            return "开发者模式已开启。"
        await AmfiService(lockdown).reveal_developer_mode_option_in_ui()
        return "已请求显示开发者模式选项。请在 iPhone 设置 → 隐私与安全中开启，并按提示重启和确认。"
    finally:
        await lockdown.close()


def run_location_command(action, *coordinates):
    command = [
        sys.executable,
        "-c",
        "import runpy,sys; from pymobiledevice3.cli.cli_common import OSUTILS; "
        "OSUTILS.wait_return=lambda: None; sys.argv=['pymobiledevice3',*sys.argv[1:]]; "
        "runpy.run_module('pymobiledevice3',run_name='__main__')",
        "developer",
        "dvt",
        "simulate-location",
        action,
        "--userspace",
    ]
    if coordinates:
        command.append("--")
        command.extend(str(value) for value in coordinates)
    # The CLI normally waits for a signal after set; the wrapper skips only
    # that wait after the device-facing call completes.
    result = subprocess.run(command, text=True, capture_output=True, timeout=240)
    if result.returncode:
        message = (result.stderr or result.stdout or "定位指令失败").strip()
        raise RuntimeError(message)
    return (result.stdout or "指令已完成").strip()


def parse_coordinate(value, minimum, maximum, name):
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"{name}必须是数字") from exc
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"{name}范围应为 {minimum} 到 {maximum}")
    return number


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("status")
    subparsers.add_parser("reveal")
    set_parser = subparsers.add_parser("set")
    set_parser.add_argument("latitude")
    set_parser.add_argument("longitude")
    subparsers.add_parser("clear")
    args = parser.parse_args()

    if args.action == "reveal":
        print(asyncio.run(reveal_developer_mode()))
        return

    info = asyncio.run(device_status())
    if not info["developer_mode"]:
        raise RuntimeError("开发者模式未开启，请在 iPhone 设置 → 隐私与安全中开启并重启确认。")

    if args.action == "status":
        pending = "；定位待恢复" if PENDING.exists() else ""
        print(f"已连接：{info['label']} · iOS {info['ios']} ({info['build']}){pending}")
        return

    if args.action == "set":
        latitude = parse_coordinate(args.latitude, -90, 90, "纬度")
        longitude = parse_coordinate(args.longitude, -180, 180, "经度")
        PENDING.write_text(
            json.dumps(
                {
                    "device": "…" + info["serial"][-6:],
                    "latitude": latitude,
                    "longitude": longitude,
                },
                ensure_ascii=False,
            )
        )
        run_location_command("set", latitude, longitude)
        print(f"模拟坐标已发送：{latitude:.6f}, {longitude:.6f}\n请在 iPhone 地图点击定位箭头确认。")
        return

    run_location_command("clear")
    PENDING.unlink(missing_ok=True)
    print("恢复真实定位指令已发送。请在 iPhone 地图点击定位箭头确认。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
