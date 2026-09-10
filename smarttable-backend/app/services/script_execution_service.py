"""
脚本执行沙箱服务
在受限环境中执行用户自定义的 Python 脚本

通过子进程隔离调用独立 runner（python_runner.py），
主进程不直接 exec 用户代码，确保故障隔离与超时可控。
"""
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict
from app.i18n import translate

# 结果最大体积 1MB
MAX_RESULT_SIZE = 1024 * 1024
# stdout 截断长度
MAX_STDOUT_LENGTH = 5000
# 默认超时（秒）
DEFAULT_TIMEOUT = 30
# 超时上下限（秒）
MIN_TIMEOUT = 1
MAX_TIMEOUT = 300

log = logging.getLogger(__name__)


def resolve_python_executable() -> str:
    """解析用于执行 runner 脚本的 Python 解释器路径。

    不能简单使用 sys.executable：在 PyInstaller 单文件打包模式下，
    sys.executable 指向生成的 EXE（如 SmartTable.exe），它本身不是
    Python 解释器，用它去启动 .py 脚本会在 Windows 上触发
    NotADirectoryError: [WinError 267]（目录名称无效）。

    解析优先级：
    1. 当前进程是常规 python 解释器（sys.executable 指向 python*.exe）→ 直接使用；
    2. PATH 中的 python / python3（打包环境通常已安装 Python）；
    3. 回退到 sys.executable（保底，便于暴露真实错误）。
    """
    exe = sys.executable or ''
    exe_name = os.path.basename(exe).lower()
    # 常规 CPython 解释器：python.exe / python3.exe / python3.11.exe 等
    if 'python' in exe_name and exe_name.endswith('.exe'):
        return exe
    # 在 PATH 中探测独立的 Python 解释器
    for candidate in ('python', 'python3'):
        found = shutil.which(candidate)
        if found:
            return found
    # 保底：仍用 sys.executable，让错误信息暴露真实路径
    return exe


class ScriptExecutionService:
    """脚本执行沙箱服务"""

    @staticmethod
    def execute(
        language: str,
        script_source: str,
        input_data: Any,
        context: Dict[str, Any],
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Dict[str, Any]:
        """执行脚本

        Args:
            language: 脚本语言（仅支持 'python'）
            script_source: 脚本源代码
            input_data: 上游节点输出（JSON 可序列化值）
            context: 工作流上下文 {trigger, record, instance, workflow, loop}
            timeout: 超时秒数（1-300）

        Returns:
            {status: 'success'|'error', result, branch, error, duration_ms, stdout}
        """
        start_time = time.time()
        # 限制超时范围
        try:
            timeout = max(MIN_TIMEOUT, min(MAX_TIMEOUT, int(timeout)))
        except (TypeError, ValueError):
            timeout = DEFAULT_TIMEOUT

        try:
            if language == 'python':
                result = ScriptExecutionService._execute_python(
                    script_source, input_data, context, timeout
                )
            else:
                result = {
                    'status': 'error',
                    'error': translate('unsupported_script_language', language),
                    'result': None,
                    'branch': None,
                    'stdout': '',
                }
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                'status': 'error',
                'error': translate('script_execution_timeout', timeout),
                'result': None,
                'branch': None,
                'duration_ms': duration_ms,
                'stdout': '',
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log.exception('[ScriptExecutionService] 脚本执行异常')
            return {
                'status': 'error',
                'error': f'{type(e).__name__}: {e}',
                'result': None,
                'branch': None,
                'duration_ms': duration_ms,
                'stdout': '',
            }

        duration_ms = int((time.time() - start_time) * 1000)
        result['duration_ms'] = duration_ms

        # 结果体积校验（仅对成功结果校验）
        if result.get('status') == 'success' and result.get('result') is not None:
            try:
                serialized = json.dumps(result['result'], ensure_ascii=True, default=str)
                if len(serialized.encode('utf-8')) > MAX_RESULT_SIZE:
                    return {
                        'status': 'error',
                        'error': 'script_output_exceeds_mb_limit',
                        'result': None,
                        'branch': None,
                        'duration_ms': duration_ms,
                        'stdout': (result.get('stdout') or '')[:MAX_STDOUT_LENGTH],
                    }
            except (TypeError, ValueError) as e:
                return {
                    'status': 'error',
                    'error': translate('script_output_not_json_serializable', e),
                    'result': None,
                    'branch': None,
                    'duration_ms': duration_ms,
                    'stdout': (result.get('stdout') or '')[:MAX_STDOUT_LENGTH],
                }

        # stdout 截断
        stdout = result.get('stdout') or ''
        if len(stdout) > MAX_STDOUT_LENGTH:
            stdout = stdout[:MAX_STDOUT_LENGTH]
        result['stdout'] = stdout

        # 统一缺失字段
        result.setdefault('result', None)
        result.setdefault('branch', None)
        result.setdefault('error', None)
        result.setdefault('stdout', '')

        return result

    @staticmethod
    def _execute_python(
        script_source: str,
        input_data: Any,
        context: Dict[str, Any],
        timeout: int,
    ) -> Dict[str, Any]:
        """通过子进程调用 python_runner.py 执行 Python 脚本"""
        runner_path = Path(__file__).parent.parent / 'script_runner' / 'python_runner.py'
        runner_dir = runner_path.parent
        python_exe = resolve_python_executable()
        payload = json.dumps(
            {
                'script_source': script_source,
                'input': input_data,
                'context': context,
            },
            ensure_ascii=True,
            default=str,
        )
        try:
            proc = subprocess.run(
                [python_exe, str(runner_path)],
                input=payload,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                cwd=str(runner_dir),
            )
        except FileNotFoundError as e:
            return {
                'status': 'error',
                'error': (
                    f'找不到可用的 Python 解释器（已探测 sys.executable={sys.executable!r}，'
                    f'PATH 中 python/python3 均不可用）。脚本节点需要在已安装 Python 的环境中运行。'
                ),
                'result': None,
                'branch': None,
                'stdout': '',
            }
        return ScriptExecutionService._parse_runner_output(
            proc.stdout, proc.stderr, proc.returncode
        )

    @staticmethod
    def _parse_runner_output(
        stdout: str, stderr: str, returncode: int
    ) -> Dict[str, Any]:
        """解析 runner 子进程输出：取 stdout 最后一行 JSON 作为结果，其余作为 stdout 字段"""
        stdout = stdout or ''
        stderr = stderr or ''
        lines = [ln for ln in stdout.splitlines() if ln.strip()]

        if not lines:
            err = stderr.strip() or f'脚本 runner 无输出（退出码 {returncode}）'
            return {
                'status': 'error',
                'error': err,
                'result': None,
                'branch': None,
                'stdout': '',
            }

        try:
            result = json.loads(lines[-1])
        except json.JSONDecodeError:
            return {
                'status': 'error',
                'error': 'failed_parse_script_runner_output',
                'result': None,
                'branch': None,
                'stdout': stdout,
            }

        if not isinstance(result, dict):
            return {
                'status': 'error',
                'error': 'script_runner_output_format_abnormal',
                'result': None,
                'branch': None,
                'stdout': stdout,
            }

        # stdout 字段：用户脚本输出（除最终结果行外）+ stderr
        user_output = '\n'.join(lines[:-1]) if len(lines) > 1 else ''
        if stderr.strip():
            user_output = (user_output + '\n' + stderr) if user_output else stderr
        result['stdout'] = user_output

        # 若 runner 未返回 status，根据 returncode 兜底
        if 'status' not in result and returncode != 0:
            result['status'] = 'error'
            result['error'] = result.get('error') or f'脚本 runner 异常退出（退出码 {returncode}）'

        return result
