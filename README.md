# 行迹实验室 RouteLab

在 Mac 上通过 USB 连接 iPhone，在本地地图选点并发送模拟坐标。此项目需要本机 Python 服务和 iPhone 开发者模式；GitHub Pages 不能直接连接 USB 设备。

## 安装和启动

需要 macOS、Python 3、支持数据传输的 USB 线和网络连接。地图使用 Leaflet 与 OpenStreetMap，加载需要联网。以下命令在项目目录的终端中运行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python map_server.py
```

程序会打开本机网页；保持终端运行。安装依赖可能需要一定时间。本版本基于本机的 Python 3.14 和 pymobiledevice3 11.49.4 开发，其他系统、设备和版本的兼容性尚需实测。

## 使用

1. 用 USB 连接并解锁 iPhone，按手机提示信任电脑并开启开发者模式。页面上的“显示开发者模式”只请求显示系统选项，开启、重启及确认需要在手机上完成。
2. 在地图点击选点，或填写 WGS-84 纬度和经度，检查坐标后选择“设置为手机定位”。
3. 在 iPhone 苹果地图点击定位箭头，观察蓝点是否移动。命令发送成功不等于手机上的位置已验证。
4. 结束后点击“恢复真实定位”，并在苹果地图确认蓝点回到实际位置。

本工具只发送模拟坐标，不会产生步数；第三方 App 是否采纳定位或记录运动数据未获保证。一次只连接一台 iPhone。若连接失败或设备断开，请检查页面错误并重新连接。

## 隐私和依赖

本机生成的 `.pending-restore.json` 可能包含坐标和设备标识的一部分，已被 `.gitignore` 排除，请勿提交。`.venv` 等本机文件也不应上传。

本项目依赖 [pymobiledevice3](https://github.com/doronz88/pymobiledevice3)（GPL-3.0-or-later）及其依赖，使用前请查阅各组件许可证。本仓库的项目代码和徽标暂未声明开放许可。
