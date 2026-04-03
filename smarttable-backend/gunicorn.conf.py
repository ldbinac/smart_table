"""
Gunicorn 配置文件
生产环境 WSGI HTTP 服务器配置
"""
import multiprocessing
import os

# 服务器绑定
bind = "0.0.0.0:5000"

# 工作进程数
# 建议: 2-4 x $(NUM_CORES)
workers = multiprocessing.cpu_count() * 2 + 1

# 工作进程类型
worker_class = "sync"

# 每个工作进程的线程数
threads = 4

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
forwarded_allow_ips = "*"

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
