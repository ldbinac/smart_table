"""
脚本执行沙箱服务
在受限环境中执行用户自定义的 Python 脚本

通过子进程隔离调用独立 runner（python_runner.py），
主进程不直接 exec 用户代码，确保故障隔离与超时可控。
"""
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

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
                    'error': f'不支持的脚本语言: {language}（仅支持 python）',
                    'result': None,
                    'branch': None,
                    'stdout': '',
                }
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                'status': 'error',
                'error': f'脚本执行超时（{timeout}秒）',
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
                        'error': '脚本输出超过 1MB 限制',
                        'result': None,
                        'branch': None,
                        'duration_ms': duration_ms,
                        'stdout': (result.get('stdout') or '')[:MAX_STDOUT_LENGTH],
                    }
            except (TypeError, ValueError) as e:
                return {
                    'status': 'error',
                    'error': f'脚本输出无法 JSON 序列化: {e}',
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
        payload = json.dumps(
            {
                'script_source': script_source,
                'input': input_data,
                'context': context,
            },
            ensure_ascii=True,
            default=str,
        )
        proc = subprocess.run(
            [sys.executable, str(runner_path)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            cwd=str(runner_dir),
        )
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
                'error': '脚本 runner 输出解析失败',
                'result': None,
                'branch': None,
                'stdout': stdout,
            }

        if not isinstance(result, dict):
            return {
                'status': 'error',
                'error': '脚本 runner 输出格式异常',
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
