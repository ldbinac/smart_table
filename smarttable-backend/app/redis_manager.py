"""
Redis 进程生命周期管理器
负责在应用启动时自动启动 Redis 服务，退出时自动清理

功能：
- 自动检测 Redis 可执行文件位置（支持 PyInstaller 打包和开发环境）
- 管理 Redis 子进程的启动、停止、重启
- 检测 Redis 是否就绪并可接受连接
- 支持自定义端口和绑定地址
- 提供上下文管理器接口（with 语句）
- 处理异常情况（端口冲突、进程崩溃等）
"""

import os
import sys
import subprocess
import time
import atexit
import platform
import signal


class RedisManager:
    """
    Redis 服务器进程管理器
    
    用法示例:
        manager = RedisManager(port=6379)
        if manager.start():
            print("Redis 已启动")
            # ... 应用逻辑 ...
            manager.stop()
        
        # 或使用上下文管理器
        with RedisManager(port=6379) as manager:
            if manager.is_running():
                # 使用 Redis
                pass
    """

    def __init__(self, port=6379, host='localhost'):
        """
        初始化 Redis 管理器
        
        Args:
            port: Redis 监听端口（默认 6379）
            host: Redis 绑定地址（默认 localhost）
        """
        self.port = port
        self.host = host
        self.redis_process = None
        self._executable_path = self._detect_redis_path()
        self._startup_timeout = 10  # 启动超时时间（秒）
        self._stop_timeout = 5      # 停止超时时间（秒）

    def _detect_redis_path(self):
        """
        检测 Redis 可执行文件的路径
        
        搜索顺序:
        1. 相对于主程序目录的上一级（打包后的典型结构）
        2. 主程序同目录
        3. 系统 PATH 中的 redis-server
        
        Returns:
            str or None: 找到的可执行文件路径，未找到返回 None
        """
        system = platform.system()
        script_dir = self._get_script_directory()

        if system == 'Windows':
            executable_name = 'redis-server.exe'
            candidates = [
                os.path.join(script_dir, '..', executable_name),
                os.path.join(script_dir, executable_name),
                executable_name,
            ]
        else:
            executable_name = 'redis-server'
            candidates = [
                os.path.join(script_dir, '..', executable_name),
                os.path.join(script_dir, executable_name),
                f'./{executable_name}',
                '/usr/bin/redis-server',
                '/usr/local/bin/redis-server',
            ]

        for candidate in candidates:
            candidate = os.path.abspath(candidate)
            if os.path.isfile(candidate):
                # Windows 不需要执行权限检查，Linux/Mac 需要
                if system == 'Windows' or os.access(candidate, os.X_OK):
                    print(f'[Redis] Found executable: {candidate}')
                    return candidate

        print('[Redis] Warning: No Redis executable found in expected locations')
        print('[Redis] Searched paths:')
        for candidate in candidates[:4]:  # 只显示前几个关键路径
            print(f'  - {candidate}')
        return None

    def _get_script_directory(self):
        """获取当前脚本/程序所在目录（兼容 PyInstaller 打包）"""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def start(self):
        """
        启动 Redis 服务器进程
        
        Returns:
            bool: 是否成功启动（True=成功, False=失败）
        """
        if not self._executable_path:
            print(f'[Redis] ✗ Cannot start: executable not found on port {self.port}')
            return False

        if self.is_running():
            print(f'[Redis] Already running on {self.host}:{self.port} (PID: {self.redis_process.pid})')
            return True

        print(f'[Redis] Starting Redis on {self.host}:{self.port}...')

        try:
            work_dir = os.path.dirname(os.path.abspath(self._executable_path))
            
            # 构建启动命令参数
            cmd = [
                self._executable_path,
                '--port', str(self.port),
                '--bind', self.host,
                '--loglevel', 'warning',
                '--maxclients', '100',          # 限制最大客户端数
                '--timeout', '300',             # 客户端空闲超时
                '--tcp-backlog', '511',         # TCP 连接队列长度
                '--save', '',                   # 禁用持久化（开发/测试环境）
                '--appendonly', 'no',           # 禁用 AOF
            ]

            # Windows 不支持 daemonize 参数
            if platform.system() != 'Windows':
                cmd.extend(['--daemonize', 'yes'])

            # 启动进程
            creation_flags = 0
            if platform.system() == 'Windows':
                creation_flags = subprocess.CREATE_NO_WINDOW

            self.redis_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                cwd=work_dir,
                creation_flags=creation_flags
            )

            # 等待 Redis 就绪
            if self._wait_for_ready():
                print(f'[Redis] ✓ Started successfully (PID: {self.redis_process.pid})')
                atexit.register(self.stop)
                return True
            else:
                print(f'[Redis] ✗ Failed to start within {self._startup_timeout}s')
                self._cleanup_zombie_process()
                return False

        except FileNotFoundError as e:
            print(f'[Redis] ✗ Executable not found: {e}')
            return False
        except PermissionError as e:
            print(f'[Redis] ✗ Permission denied: {e}')
            return False
        except Exception as e:
            print(f'[Redis] ✗ Error starting: {type(e).__name__}: {e}')
            return False

    def _wait_for_ready(self):
        """
        等待 Redis 服务就绪
        
        通过尝试连接来检测 Redis 是否可以接受请求
        
        Returns:
            bool: 是否在超时时间内就绪
        """
        max_retries = int(self._startup_timeout / 0.5)  # 每 0.5 秒检查一次
        
        for i in range(max_retries):
            # 先检查进程是否还在运行
            if self.redis_process.poll() is not None:
                # 进程已退出，读取错误信息
                stderr_output = ''
                if self.redis_process.stderr:
                    stderr_output = self.redis_process.stderr.read().decode('utf-8', errors='ignore')
                if stderr_output:
                    print(f'[Redis] Process exited with error: {stderr_output[:200]}')
                return False
            
            # 尝试连接
            if self._check_connection():
                return True
            
            time.sleep(0.5)

        return False

    def stop(self, timeout=None):
        """
        停止 Redis 服务器进程
        
        Args:
            timeout: 停止超时时间（秒），默认使用实例配置
        """
        if not self.redis_process:
            return

        if not self.is_running():
            print('[Redis] Not running')
            self.redis_process = None
            return

        timeout = timeout or self._stop_timeout
        pid = self.redis_process.pid
        print(f'[Redis] Stopping (PID: {pid})...')

        try:
            # 第一步：优雅终止（SIGTERM）
            self.redis_process.terminate()

            # 等待进程退出
            try:
                self.redis_process.wait(timeout=timeout)
                print(f'[Redis] ✓ Stopped gracefully (PID: {pid})')
            except subprocess.TimeoutExpired:
                # 第二步：强制杀死（SIGKILL/SIGTERM）
                print(f'[Redis] Force killing (PID: {pid})...')
                self.redis_process.kill()
                
                try:
                    self.redis_process.wait(timeout=2)
                    print(f'[Redis] ✓ Killed forcefully (PID: {pid})')
                except subprocess.TimeoutExpired:
                    print(f'[Redis] ⚠️ Failed to kill process (PID: {pid}), may be zombie')

        except OSError as e:
            # 进程可能已经不存在
            if e.errno == 3:  # No such process (Windows) or ESRCH (Linux)
                print(f'[Redis] Process already exited (PID: {pid})')
            else:
                print(f'[Redis] ✗ Error stopping: {e}')

        except Exception as e:
            print(f'[Redis] ✗ Unexpected error: {type(e).__name__}: {e}')

        finally:
            self.redis_process = None

    def restart(self):
        """重启 Redis 服务"""
        print(f'[Redis] Restarting...')
        self.stop()
        time.sleep(1)  # 等待端口释放
        return self.start()

    def is_running(self):
        """
        检查 Redis 是否正在运行
        
        Returns:
            bool: 是否在运行且可接受连接
        """
        if not self.redis_process:
            return False

        # 检查进程是否存活
        poll_result = self.redis_process.poll()
        if poll_result is not None:
            # 进程已结束
            if poll_result != 0:
                print(f'[Redis] Process exited unexpectedly with code {poll_result}')
            self.redis_process = None
            return False

        # 尝试连接验证服务可用性
        return self._check_connection()

    def _check_connection(self):
        """
        检查 Redis 连接是否可用
        
        Returns:
            bool: 是否可以成功连接并执行 PING 命令
        """
        try:
            import redis
            client = redis.Redis(
                host=self.host,
                port=self.port,
                socket_connect_timeout=1,
                socket_timeout=1,
                decode_responses=True
            )
            result = client.ping()
            return result is True
        except ImportError:
            # redis 包未安装，仅检查端口是否开放
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            try:
                result = sock.connect_ex((self.host, self.port))
                return result == 0
            finally:
                sock.close()
        except Exception:
            return False

    def _cleanup_zombie_process(self):
        """清理可能存在的僵尸进程"""
        if self.redis_process and self.redis_process.poll() is None:
            try:
                self.redis_process.kill()
                self.redis_process.wait(timeout=2)
            except Exception:
                pass
            finally:
                self.redis_process = None

    def get_status(self):
        """
        获取 Redis 服务状态信息
        
        Returns:
            dict: 包含状态信息的字典
        """
        status = {
            'configured': self._executable_path is not None,
            'running': self.is_running(),
            'port': self.port,
            'host': self.host,
            'executable': self._executable_path or 'Not found',
            'pid': self.redis_process.pid if self.redis_process and self.redis_process.poll() is None else None,
        }

        if status['running']:
            try:
                import redis
                client = redis.Redis(host=self.host, port=self.port, socket_timeout=2)
                info = client.info()
                status.update({
                    'version': info.get('redis_version', 'Unknown'),
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory_human': info.get('used_memory_human', 'Unknown'),
                    'uptime_in_seconds': info.get('uptime_in_seconds', 0),
                })
            except Exception as e:
                status['error'] = str(e)

        return status

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()
        return False  # 不抑制异常

    def __repr__(self):
        status = "Running" if self.is_running() else "Stopped"
        return f'<RedisManager {self.host}:{self.port} ({status})>'


# 全局单例（可选，用于应用级访问）
_global_manager = None


def get_global_redis_manager(port=6379, host='localhost'):
    """
    获取全局 Redis 管理器实例
    
    Args:
        port: Redis 端口
        host: Redis 地址
        
    Returns:
        RedisManager: 全局实例
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = RedisManager(port=port, host=host)
    return _global_manager


def cleanup_global_manager():
    """清理全局 Redis 管理器"""
    global _global_manager
    if _global_manager:
        _global_manager.stop()
        _global_manager = None
