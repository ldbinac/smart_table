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
#
# 注意：eventlet 默认 patch os/threading/time/select/socket 等所有模块。
# SQLite (C 扩展) + eventlet monkey_patch 存在兼容性问题：
#   1. eventlet 替换 os.path 后，SQLite 打开已存在的 .db/-wal/-shm 辅助文件
#      时可能触发 "unable to open database file"
#   2. eventlet 替换 time 后，SQLite busy_timeout 的 retry loop 被 greenlet
#      调度干扰，锁等待超时抛 "database is locked"
#   3. eventlet 替换 threading.local 后，SQLAlchemy QueuePool 的 per-thread
#      连接隔离失效，连接池状态错乱
# 解决：patch 时排除 os / time / thread 三个模块（eventlet 的 thread 参数同时控制 thread + threading + Queue），
# 保留 socket / select / ssl 让 WebSocket 和 eventlet.wsgi.server 正常工作即可。
eventlet.monkey_patch(os=False, time=False, thread=False)
# 显式导入 eventlet.wsgi，monkey_patch 不会自动加载此子模块
import eventlet.wsgi

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