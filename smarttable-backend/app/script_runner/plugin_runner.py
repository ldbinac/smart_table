"""
插件脚本沙箱 runner（双向 stdio 协议版）

与 python_runner.py 的区别：
- python_runner.py：单向（stdin 一次性 payload → exec → stdout 一次性结果），用于工作流脚本节点
- plugin_runner.py：双向协议，脚本运行期间可通过受限 base/table 代理对象回调宿主执行表格操作

协议（stdout 每行一个 JSON 帧，与用户 print 输出分离）：
  脚本 → 宿主: {"__rpc__": "call", "id": "c1", "method": "...", "params": {...}}
  宿主 → 脚本: {"__rpc__": "result", "id": "c1", "ok": true, "result": {...}}
               {"__rpc__": "result", "id": "c1", "ok": false, "error": {"code", "message"}}
  脚本 → 宿主: {"__rpc__": "log", "message": "..."}        # print 自动捕获
  脚本 → 宿主: {"__rpc__": "done", "status": "success", "result": ...}
               {"__rpc__": "done", "status": "error", "error": "...", "traceback": "..."}

业务失败约定：done 为 success 但 result 为 dict 且含非空 error 字段时，
宿主将该次运行按 failed 处理（error_summary 取该 error 值）。

安全说明：受限 builtins + 模块白名单是"受控执行"而非强沙箱，
配合宿主侧子进程隔离/超时/并发限制使用，生产环境建议低权限 OS 用户运行。
"""
import builtins
import json
import sys
import traceback

# 白名单模块（无网络、无文件系统、无系统访问能力）
ALLOWED_MODULES = {
    'json', 're', 'math', 'datetime', 'decimal', 'collections',
    'itertools', 'hashlib', 'base64', 'uuid', 'statistics',
}

# 危险内建函数（从受限 builtins 中移除）
DANGEROUS_BUILTINS = {
    'open', 'exec', 'eval', '__import__', 'compile', 'globals',
    'locals', 'vars', 'input', 'breakpoint', 'exit', 'quit',
}

_REAL_IMPORT = builtins.__import__


def safe_import(name, *args, **kwargs):
    """仅允许导入白名单模块"""
    if name.split('.')[0] not in ALLOWED_MODULES:
        raise ImportError(
            f"模块 '{name}' 被禁止导入，仅允许: {sorted(ALLOWED_MODULES)}"
        )
    return _REAL_IMPORT(name, *args, **kwargs)


def make_restricted_builtins():
    """构建受限的 __builtins__"""
    safe = {}
    for name in dir(builtins):
        if name in DANGEROUS_BUILTINS:
            continue
        safe[name] = getattr(builtins, name)
    safe['__import__'] = safe_import
    return safe


# ==================== 协议通道 ====================

def _send_frame(frame):
    """向宿主输出一个协议帧（协议通道，非用户输出）"""
    sys.__stdout__.write(json.dumps(frame, ensure_ascii=True, default=str) + '\n')
    sys.__stdout__.flush()


def _read_frame():
    """从宿主读取一行 JSON 帧（阻塞）"""
    line = sys.__stdin__.readline()
    if not line:
        raise EOFError('host closed stdin')
    return json.loads(line)


class _PrintCapture:
    """捕获用户脚本的 print 输出，包装为 log 帧（协议帧分离）"""

    def write(self, text):
        if text.strip():
            _send_frame({'__rpc__': 'log', 'message': str(text).rstrip('\n')})

    def flush(self):
        pass


# ==================== 受限代理对象 ====================

class _RpcError(Exception):
    def __init__(self, code, message):
        super().__init__(f'{code}: {message}')
        self.code = code
        self.message = message


class _BaseProxy:
    """受限 base 代理：方法调用经 stdio 协议帧由宿主执行并鉴权

    宿主侧按触发者身份做双层校验（插件 manifest 权限 + 用户 RBAC）。
    """

    def _call(self, method, params=None):
        call_id = f'c{self._seq}'
        self._seq += 1
        _send_frame({'__rpc__': 'call', 'id': call_id,
                     'method': method, 'params': params or {}})
        resp = _read_frame()
        if resp.get('id') != call_id:
            raise _RpcError('PROTOCOL_ERROR', f'response id mismatch: {resp.get("id")}')
        if resp.get('ok'):
            return resp.get('result')
        err = resp.get('error') or {}
        raise _RpcError(err.get('code', 'INTERNAL_ERROR'),
                        err.get('message', 'unknown rpc error'))

    # ---- 每个代理实例独立的调用序号 ----
    _seq = 1

    # ---- 表结构 ----
    def list_tables(self):
        """列出当前 Base 的所有表 [{id, name, description}]"""
        return self._call('base.list_tables')

    def get_fields(self, table_id):
        """获取表字段列表 [{id, name, type}]"""
        return self._call('base.get_fields', {'table_id': str(table_id)})

    # ---- 记录 ----
    def list_records(self, table_id, page=1, per_page=100):
        """分页获取记录 {items: [{id, values}], total}"""
        return self._call('base.list_records', {
            'table_id': str(table_id), 'page': page, 'per_page': per_page})

    def get_record(self, record_id):
        """获取单条记录 {id, values}"""
        return self._call('base.get_record', {'record_id': str(record_id)})

    def create_record(self, table_id, values):
        """创建记录 {id}"""
        return self._call('base.create_record', {
            'table_id': str(table_id), 'values': values})

    def update_record(self, record_id, values):
        """更新记录字段 {id}"""
        return self._call('base.update_record', {
            'record_id': str(record_id), 'values': values})

    def delete_record(self, record_id):
        """删除记录 {deleted: true}"""
        return self._call('base.delete_record', {'record_id': str(record_id)})

    # ---- 配置与日志 ----
    def get_config(self):
        """获取插件在当前 Base 的生效配置（base 深合并 global）"""
        return self._call('base.get_config')

    def log(self, message):
        """输出日志（同 print，进运行日志）"""
        _send_frame({'__rpc__': 'log', 'message': str(message)})


# ==================== 主流程 ====================

def run():
    # 注意：宿主写完 init payload 后不会关闭 stdin（后续还要回写 RPC 结果），
    # 因此必须按行读取（协议约定 init 为单行 JSON），不能用 json.load（会读到 EOF 而永久阻塞）
    payload = json.loads(sys.__stdin__.readline())
    script_source = payload['script_source']
    context = payload.get('context') or {}
    config = payload.get('config') or {}

    result_holder = {'result': None, 'has_result': False}

    def set_result(value):
        result_holder['result'] = value
        result_holder['has_result'] = True

    base = _BaseProxy()

    restricted_globals = {
        '__builtins__': make_restricted_builtins(),
        'base': base,
        'context': context,
        'config': config,
        'set_result': set_result,
        'result': None,
    }

    # 捕获 print：写入用户 stdout 会污染协议通道，统一转为 log 帧
    sys.stdout = _PrintCapture()

    try:
        exec(compile(script_source, '<plugin_script>', 'exec'), restricted_globals)
        if not result_holder['has_result'] and restricted_globals.get('result') is not None:
            result_holder['result'] = restricted_globals['result']
            result_holder['has_result'] = True
        _send_frame({
            '__rpc__': 'done',
            'status': 'success',
            'result': result_holder['result'],
        })
    except _RpcError as e:
        # 宿主拒绝的调用（权限/不存在等）作为脚本错误返回
        _send_frame({
            '__rpc__': 'done',
            'status': 'error',
            'error': f'{e.code}: {e.message}',
            'traceback': '',
        })
    except Exception as e:
        _send_frame({
            '__rpc__': 'done',
            'status': 'error',
            'error': f'{type(e).__name__}: {e}',
            'traceback': traceback.format_exc(),
        })


if __name__ == '__main__':
    run()
