"""
Gunicorn 配置文件
生产环境 WSGI HTTP 服务器配置
"""
import multiprocessing
import os

# 服务器绑定
bind = "0.0.0.0:5000"

# 工作进程数
# eventlet 模式下建议单 worker（协程并发），多 worker 需要额外的消息队列支持
# gthread 模式下可以根据 CPU 核心数调整
if os.environ.get('ENABLE_REALTIME', '').lower() == 'true':
    workers = 1
else:
    workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))

# 工作进程类型
# 根据 ENABLE_REALTIME 环境变量动态选择 worker 类型
# Flask-SocketIO 需要 eventlet worker，使用 sync 会导致 WebSocket 异常
# 未启用实时协作时使用 gthread worker，性能更好
_worker_class = "eventlet" if os.environ.get('ENABLE_REALTIME', '').lower() == 'true' else "gthread"
worker_class = _worker_class

# 每个工作进程的线程数
# eventlet 模式下使用协程，不需要多线程
# gthread 模式下使用多线程
threads = 1 if os.environ.get('ENABLE_REALTIME', '').lower() == 'true' else int(os.environ.get('GUNICORN_THREADS', 4))

# 工作进程超时时间（秒）
timeout = 120

# 保持连接时间（秒）
keepalive = 5

# 最大等待连接数
backlog = 2048

# 工作进程名称
proc_name = "smarttable"

# 是否守护进程模式
daemon = False

# 进程PID文件
pidfile = "/tmp/gunicorn.pid"

# 日志配置
accesslog = "-"  # 输出到stdout
errorlog = "-"   # 输出到stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 是否使用虚拟主机
# 仅信任本地反向代理的 X-Forwarded-For 头，防止 IP 伪造
forwarded_allow_ips = "127.0.0.1"

# 安全限制
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# 预加载应用
preload_app = True

# 工作进程重启前的最大请求数
max_requests = 10000
max_requests_jitter = 1000

# 优雅重启超时时间
graceful_timeout = 30


def on_starting(server):
    """服务器启动时调用"""
    pass


def on_reload(server):
    """重新加载配置时调用"""
    pass


def when_ready(server):
    """服务器就绪时调用"""
    pass


def worker_int(worker):
    """工作进程接收到 SIGINT 或 SIGQUIT 时调用"""
    pass


def worker_abort(worker):
    """工作进程接收到 SIGABRT 时调用"""
    pass
