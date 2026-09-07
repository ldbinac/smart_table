"""
插件脚本执行服务
负责脚本插件的子进程编排：启动 plugin_runner.py 子进程、解析 stdio 协议帧、
以触发者身份代理执行受限表格 API（双层校验：manifest 权限 + 用户 RBAC）、
超时/并发限制与 RunLog 落库。

安全与隔离：
- 代理执行在 Flask app context 中进行，按触发者身份校验 Base 权限
- 插件 manifest 权限点逐方法校验（deny by default）
- 子进程超时（manifest 可声明，封顶 300s）杀进程
- 并发子进程上限（超过 CPU 核数时拒绝）
- 连续失败 N 次自动将插件置为 error 状态
"""
import json
import logging
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from flask import current_app

from app.extensions import db
from app.models.base import MemberRole
from app.models.plugin import (
    Plugin, PluginRunLog, PluginStatus, RunStatus,
)
from app.models.table import Table
from app.models.field import Field
from app.models.record import Record
from app.services.permission_service import PermissionService
from app.services.plugin_service import PluginService

log = logging.getLogger(__name__)

# ---- 限制常量（与 script_execution_service 保持一致风格）----
DEFAULT_TIMEOUT = 30
MAX_TIMEOUT = 300
MAX_CONCURRENT_RUNS = max(4, (os.cpu_count() or 4))
MAX_LOG_OUTPUT = 20000        # 运行日志截断长度
MAX_TRACEBACK = 8000          # traceback 截断长度
AUTO_ERROR_FAILURE_THRESHOLD = 5   # 连续失败 N 次自动置 error
MAX_RPC_CALLS_PER_RUN = 10000      # 单次运行代理调用上限（防失控脚本）

_RUN_SEMAPHORE = threading.Semaphore(MAX_CONCURRENT_RUNS)
_ACTIVE_RUNS = 0
_ACTIVE_RUNS_LOCK = threading.Lock()

_RUNNER_PATH = Path(__file__).resolve().parent.parent / 'script_runner' / 'plugin_runner.py'


def _err(code: str, message: str) -> Dict[str, Any]:
    return {'code': code, 'message': message}


class PluginScriptService:
    """脚本插件执行编排服务"""

    @classmethod
    def run(cls, plugin: Plugin, base_id: str, user_id: str) -> Dict[str, Any]:
        """同步运行脚本插件（由 REST run 接口调用，处于请求上下文中）

        Returns:
            {status, duration_ms, result, output, run_log_id}
        """
        global _ACTIVE_RUNS
        manifest = plugin.manifest or {}
        timeout = cls._resolve_timeout(manifest)

        # 并发上限检查
        with _ACTIVE_RUNS_LOCK:
            if _ACTIVE_RUNS >= MAX_CONCURRENT_RUNS:
                return {
                    'status': 'failed',
                    'error': 'TOO_MANY_CONCURRENT_RUNS',
                    'output': '',
                }
            _ACTIVE_RUNS += 1

        run_log = PluginRunLog(
            plugin_id=plugin.id, base_id=base_id,
            status=RunStatus.RUNNING, triggered_by=user_id)

        started = time.time()
        try:
            _RUN_SEMAPHORE.acquire()
            script_source = cls._read_entry_source(plugin)
            config = PluginService.get_effective_config(plugin.id, base_id)

            result = cls._execute(
                script_source=script_source,
                base_id=base_id,
                user_id=user_id,
                plugin=plugin,
                config=config,
                timeout=timeout,
            )
        except Exception as e:
            log.exception('[PluginScriptService] 脚本执行编排异常 %s', plugin.id)
            result = {
                'status': 'failed',
                'error': f'{type(e).__name__}: {e}',
                'output': '',
                'result': None,
            }
        finally:
            _RUN_SEMAPHORE.release()
            with _ACTIVE_RUNS_LOCK:
                _ACTIVE_RUNS -= 1

        duration_ms = int((time.time() - started) * 1000)

        # 业务结果约定：脚本正常结束（沙箱 success）但返回结果为 dict 且携带
        # 非空 error 字段时，视为"业务失败"——避免"沙箱执行成功但插件结果
        # 自报有错"被整体标记为完全成功而误导用户
        if result.get('status') == 'success':
            payload = result.get('result')
            if isinstance(payload, dict):
                biz_err = payload.get('error')
                if biz_err:
                    result['status'] = 'failed'
                    result['error'] = (
                        biz_err if isinstance(biz_err, str) else str(biz_err))

        status = result.get('status')

        run_log.status = RunStatus.TIMEOUT if status == 'timeout' else (
            RunStatus.SUCCESS if status == 'success' else RunStatus.FAILED)
        run_log.duration_ms = duration_ms
        run_log.output = (result.get('output') or '')[:MAX_LOG_OUTPUT]
        run_log.result = result.get('result')
        run_log.error_summary = (result.get('error') or '')[:500]
        run_log.traceback_text = (result.get('traceback') or '')[:MAX_TRACEBACK]
        db.session.add(run_log)
        db.session.commit()

        # 连续失败自动置 error
        if status != 'success':
            cls._maybe_auto_error(plugin)

        return {
            'status': status,
            'duration_ms': duration_ms,
            'result': result.get('result'),
            'output': run_log.output,
            'error': result.get('error'),
            'run_log_id': str(run_log.id),
            'base_id': str(base_id),
        }

    # ==================== 子进程与协议循环 ====================

    @classmethod
    def _execute(cls, script_source: str, base_id: str, user_id: str,
                 plugin: Plugin, config: Dict, timeout: int) -> Dict[str, Any]:
        """启动子进程并处理协议帧循环（读线程 + 队列 + 截止时间）"""
        # 强制子进程 stdio 使用 UTF-8：否则中文 Windows 上子进程会用本地编码(GBK)
        # 解码宿主写入的 UTF-8 init payload，多字节序列会吞并引号/破坏 JSON 结构，
        # 且脚本内的中文输出/回显也会乱码（已复现验证）
        child_env = os.environ.copy()
        child_env['PYTHONIOENCODING'] = 'utf-8'
        proc = subprocess.Popen(
            [sys.executable, str(_RUNNER_PATH)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            cwd=str(_RUNNER_PATH.parent),
            env=child_env,
        )

        init_payload = json.dumps({
            'script_source': script_source,
            'context': {
                'plugin_id': plugin.id,
                'base_id': base_id,
            },
            'config': config,
        }, ensure_ascii=False)

        frames: "queue.Queue[Optional[Dict]]" = queue.Queue()
        reader_error: Dict[str, str] = {}

        def _reader():
            try:
                for line in proc.stdout:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        frames.put(json.loads(line))
                    except json.JSONDecodeError:
                        # 非协议行（不应出现，runner 已捕获 print）忽略
                        continue
            except Exception as e:  # noqa: BLE001
                reader_error['error'] = str(e)
            finally:
                frames.put(None)  # EOF 哨兵

        reader = threading.Thread(target=_reader, daemon=True)
        reader.start()

        try:
            proc.stdin.write(init_payload + '\n')
            proc.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            proc.kill()
            return {'status': 'failed', 'error': f'sandbox init failed: {e}',
                    'output': '', 'result': None}

        deadline = time.time() + timeout
        output_lines = []
        rpc_calls = 0
        final: Optional[Dict] = None

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                proc.kill()
                return {'status': 'timeout',
                        'error': f'script timed out after {timeout}s',
                        'output': '\n'.join(output_lines)[:MAX_LOG_OUTPUT],
                        'result': None}
            try:
                frame = frames.get(timeout=min(remaining, 1.0))
            except queue.Empty:
                # 检查子进程是否已死
                if proc.poll() is not None and frames.empty():
                    break
                continue

            if frame is None:
                break

            kind = frame.get('__rpc__')
            if kind == 'log':
                output_lines.append(str(frame.get('message', '')))
            elif kind == 'call':
                rpc_calls += 1
                if rpc_calls > MAX_RPC_CALLS_PER_RUN:
                    resp = _err('RATE_LIMITED',
                                'too many rpc calls in one run')
                else:
                    resp = cls._handle_call(frame, plugin, base_id, user_id)
                try:
                    proc.stdin.write(json.dumps({
                        '__rpc__': 'result',
                        'id': frame.get('id'),
                        'ok': resp.get('ok', False),
                        **({'result': resp['result']} if resp.get('ok') else
                           {'error': resp.get('error') or _err('INTERNAL_ERROR', '')}),
                    }, ensure_ascii=False, default=str) + '\n')
                    proc.stdin.flush()
                except (BrokenPipeError, OSError):
                    break
            elif kind == 'done':
                final = frame
                break
            else:
                log.warning('[PluginScriptService] 未知协议帧: %s', kind)

        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

        if final is None:
            stderr = ''
            try:
                stderr = (proc.stderr.read() or '')[:MAX_LOG_OUTPUT]
            except Exception:  # noqa: BLE001
                pass
            return {'status': 'failed',
                    'error': 'sandbox exited without done frame',
                    'output': '\n'.join(
                        filter(None, ['\n'.join(output_lines), stderr])
                    )[:MAX_LOG_OUTPUT],
                    'result': None}

        output = '\n'.join(output_lines)[:MAX_LOG_OUTPUT]
        if final.get('status') == 'success':
            return {'status': 'success', 'result': final.get('result'),
                    'output': output}
        return {'status': 'failed', 'error': final.get('error', 'unknown'),
                'traceback': final.get('traceback', ''),
                'output': output, 'result': None}

    # ==================== 代理调用处理（触发者身份） ====================

    @classmethod
    def _handle_call(cls, frame: Dict, plugin: Plugin,
                     base_id: str, user_id: str) -> Dict[str, Any]:
        """处理来自脚本的代理调用：manifest 权限 + 用户 RBAC 双层校验"""
        method = frame.get('method', '')
        params = frame.get('params') or {}

        # 方法与所需权限映射（deny by default）
        method_perms = {
            'base.list_tables': ('tables', 'read', MemberRole.VIEWER),
            'base.get_fields': ('tables', 'read', MemberRole.VIEWER),
            'base.list_records': ('records', 'read', MemberRole.VIEWER),
            'base.get_record': ('records', 'read', MemberRole.VIEWER),
            'base.create_record': ('records', 'write', MemberRole.EDITOR),
            'base.update_record': ('records', 'write', MemberRole.EDITOR),
            'base.delete_record': ('records', 'write', MemberRole.EDITOR),
            'base.get_config': (None, None, MemberRole.VIEWER),  # config 隐含授予
        }
        if method not in method_perms:
            return {'ok': False, 'error': _err(
                'PERMISSION_DENIED', f'unknown method: {method}')}

        perm_key, perm_level, min_role = method_perms[method]

        # 1) 插件 manifest 权限校验
        if perm_key is not None:
            declared = ((plugin.manifest or {}).get('permissions') or {}).get(perm_key)
            if declared is None:
                return {'ok': False, 'error': _err(
                    'PERMISSION_DENIED',
                    f'plugin did not declare permission: {perm_key}')}
            if perm_level == 'write' and declared not in ('write',):
                return {'ok': False, 'error': _err(
                    'PERMISSION_DENIED',
                    f'plugin permission {perm_key}={declared} insufficient for write')}

        # 2) 触发者身份的 Base RBAC 校验（代理在 app context 中执行）
        with current_app.app_context():
            if not PermissionService.check_permission(
                    str(base_id), str(user_id), min_role):
                return {'ok': False, 'error': _err(
                    'PERMISSION_DENIED',
                    f'triggering user lacks role {min_role.value} on base')}

            try:
                result = cls._dispatch(method, params, base_id, user_id, plugin)
                db.session.commit()
                return {'ok': True, 'result': result}
            except ValueError as e:
                db.session.rollback()
                return {'ok': False, 'error': _err('VALIDATION_ERROR', str(e))}
            except LookupError as e:
                db.session.rollback()
                return {'ok': False, 'error': _err('NOT_FOUND', str(e))}
            except Exception as e:  # noqa: BLE001
                db.session.rollback()
                log.exception('[PluginScriptService] 代理调用失败 %s', method)
                return {'ok': False, 'error': _err(
                    'INTERNAL_ERROR', f'{type(e).__name__}: {e}')}

    @classmethod
    def _dispatch(cls, method: str, params: Dict, base_id: str,
                  user_id: str, plugin: Plugin) -> Any:
        """实际执行表格操作（在 app context 内，已通过双层校验）"""
        if method == 'base.list_tables':
            tables = Table.query.filter_by(
                base_id=base_id).order_by(Table.order).all()
            return [{'id': str(t.id), 'name': t.name,
                     'description': t.description} for t in tables]

        if method == 'base.get_fields':
            table_id = cls._require_table(params, base_id)
            fields = Field.query.filter_by(table_id=table_id).all()
            return [{'id': str(f.id), 'name': f.name, 'type': f.type}
                    for f in fields]

        if method == 'base.list_records':
            table_id = cls._require_table(params, base_id)
            page = max(1, int(params.get('page', 1)))
            per_page = min(500, max(1, int(params.get('per_page', 100))))
            query = Record.query.filter_by(table_id=table_id, is_deleted=False)
            total = query.count()
            records = (query.order_by(Record.created_at)
                       .offset((page - 1) * per_page).limit(per_page).all())
            return {
                'items': [{'id': str(r.id), 'values': r.values or {}} for r in records],
                'total': total, 'page': page, 'per_page': per_page,
            }

        if method == 'base.get_record':
            record = cls._require_record(params, base_id)
            return {'id': str(record.id), 'values': record.values or {}}

        if method == 'base.create_record':
            table_id = cls._require_table(params, base_id)
            values = params.get('values')
            if not isinstance(values, dict):
                raise ValueError('values must be an object')
            record = Record(table_id=table_id, values=values,
                            created_by=user_id, updated_by=user_id)
            db.session.add(record)
            db.session.flush()
            cls._record_audit_note(plugin, record.id, 'create')
            return {'id': str(record.id)}

        if method == 'base.update_record':
            record = cls._require_record(params, base_id)
            values = params.get('values')
            if not isinstance(values, dict):
                raise ValueError('values must be an object')
            merged = dict(record.values or {})
            merged.update(values)
            record.values = merged
            record.updated_by = user_id
            db.session.add(record)
            cls._record_audit_note(plugin, record.id, 'update')
            return {'id': str(record.id)}

        if method == 'base.delete_record':
            record = cls._require_record(params, base_id)
            record.is_deleted = True
            record.updated_by = user_id
            db.session.add(record)
            cls._record_audit_note(plugin, record.id, 'delete')
            return {'deleted': True}

        if method == 'base.get_config':
            return PluginService.get_effective_config(plugin.id, base_id)

        raise LookupError(f'unknown method: {method}')

    # ==================== 辅助 ====================

    @classmethod
    def _require_table(cls, params: Dict, base_id: str):
        """校验 table_id 属于当前 Base（防止跨 Base 越权访问）"""
        table_id = params.get('table_id')
        if not table_id:
            raise ValueError('table_id is required')
        table = db.session.get(Table, table_id)
        if table is None or str(table.base_id) != str(base_id):
            raise LookupError(f'table not found in base: {table_id}')
        return table.id

    @classmethod
    def _require_record(cls, params: Dict, base_id: str) -> Record:
        record_id = params.get('record_id')
        if not record_id:
            raise ValueError('record_id is required')
        record = db.session.get(Record, record_id)
        if record is None or record.is_deleted:
            raise LookupError(f'record not found: {record_id}')
        table = db.session.get(Table, record.table_id)
        if table is None or str(table.base_id) != str(base_id):
            raise LookupError(f'record not found in base: {record_id}')
        return record

    @classmethod
    def _record_audit_note(cls, plugin: Plugin, record_id, action: str):
        """审计归因：插件操作附加 via_plugin 标记（写日志，轻量实现）"""
        log.info('[PluginScriptService] 插件数据变更 via_plugin=%s action=%s '
                 'record=%s', plugin.id, action, record_id)

    @classmethod
    def _read_entry_source(cls, plugin: Plugin) -> str:
        entry = (plugin.manifest or {}).get('entry', '')
        from app.models.plugin import PluginVersion
        version = PluginVersion.query.filter_by(
            plugin_id=plugin.id, version=plugin.current_version).first()
        if version is None:
            raise FileNotFoundError(
                f'plugin version not found: {plugin.id}@{plugin.current_version}')
        # 相对路径按后端根目录锚定解析，与进程 CWD 无关
        entry_path = PluginService.resolve_package_path(
            version.package_path) / entry
        if not entry_path.is_file():
            raise FileNotFoundError(f'plugin entry missing: {entry_path}')
        return entry_path.read_text(encoding='utf-8')

    @classmethod
    def _resolve_timeout(cls, manifest: Dict) -> int:
        try:
            t = int((manifest.get('script') or {}).get('timeout', DEFAULT_TIMEOUT))
        except (TypeError, ValueError):
            t = DEFAULT_TIMEOUT
        return max(1, min(MAX_TIMEOUT, t))

    @classmethod
    def _maybe_auto_error(cls, plugin: Plugin):
        """连续失败 N 次自动置 error"""
        try:
            recent = (PluginRunLog.query
                      .filter_by(plugin_id=plugin.id)
                      .order_by(PluginRunLog.created_at.desc())
                      .limit(AUTO_ERROR_FAILURE_THRESHOLD)
                      .all())
            if (len(recent) == AUTO_ERROR_FAILURE_THRESHOLD
                    and all(r.status != RunStatus.SUCCESS for r in recent)
                    and plugin.status == PluginStatus.ENABLED):
                plugin.status = PluginStatus.ERROR
                db.session.commit()
                log.warning('[PluginScriptService] 插件 %s 连续失败 %d 次，'
                            '已自动置为 error', plugin.id,
                            AUTO_ERROR_FAILURE_THRESHOLD)
        except Exception:  # noqa: BLE001
            db.session.rollback()
            log.exception('[PluginScriptService] 自动置 error 失败')
