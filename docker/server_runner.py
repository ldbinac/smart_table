#!/usr/bin/env python
"""
SmartTable Eventlet WSGI Server
统一使用 eventlet.wsgi.server，不再依赖 Gunicorn。
eventlet 原生支持 HTTP + WebSocket 混合流量。

当 REALTIME_ENABLED=True 时，app.wsgi_app 已被 SocketIO middleware 包装，
会自动拦截 /socket.io/ 进行 WebSocket 升级。
当 REALTIME_ENABLED=False 时，app.wsgi_app 是 Flask 原生 WSGI app，
处理普通 HTTP 请求。两种模式下 eventlet.wsgi.server 均能正确处理。
"""
import eventlet
# monkey_patch 必须在导入应用之前执行，确保所有标准库模块被正确替换
eventlet.monkey_patch()

import os
import sys
# 将项目根目录添加到 sys.path，确保 run.py 可被导入
# 脚本在 /app/docker/server_runner.py，项目根目录是 /app
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from run import app

host = os.environ.get('FLASK_HOST', '0.0.0.0')
port = int(os.environ.get('FLASK_PORT', 5000))

print(f'[Runner] Starting Eventlet WSGI server on {host}:{port}...')

try:
    eventlet.wsgi.server(
        eventlet.listen((host, port)),
        app,
        log_output=True,
        max_size=8096,  # 最大并发连接数
        debug=False,
    )
except (KeyboardInterrupt, SystemExit):
    print('[Runner] Server stopped gracefully')
except Exception as e:
    print(f'[Runner] Server error: {e}')
    raise