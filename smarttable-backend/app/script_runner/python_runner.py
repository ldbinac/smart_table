"""
Python 脚本沙箱 runner
从 stdin 读取 {script_source, input, context}，执行用户脚本，输出 {status, result, branch, error, traceback} 到 stdout

被 ScriptExecutionService 通过子进程调用，与主进程隔离执行用户代码。
"""
import builtins
import json
import sys
import traceback

# 白名单模块（仅允许导入这些标准库模块）
ALLOWED_MODULES = {
    'json', 're', 'math', 'datetime', 'decimal', 'collections',
    'itertools', 'hashlib', 'base64', 'uuid', 'statistics',
}

# 危险内建函数（从受限 builtins 中移除）
DANGEROUS_BUILTINS = {
    'open', 'exec', 'eval', '__import__', 'compile', 'globals',
    'locals', 'vars', 'input', 'breakpoint', 'exit', 'quit',
}

# 保存原始 __import__（在替换 builtins 前捕获，供 safe_import 调用）
_REAL_IMPORT = builtins.__import__


def safe_import(name, *args, **kwargs):
    """仅允许导入白名单模块，其余抛出 ImportError"""
    if name not in ALLOWED_MODULES:
        raise ImportError(
            f"模块 '{name}' 被禁止导入，仅允许: {sorted(ALLOWED_MODULES)}"
        )
    return _REAL_IMPORT(name, *args, **kwargs)


def make_restricted_builtins():
    """构建受限的 __builtins__，移除危险函数并以 safe_import 替换 __import__"""
    safe = {}
    for name in dir(builtins):
        if name in DANGEROUS_BUILTINS:
            continue
        safe[name] = getattr(builtins, name)
    safe['__import__'] = safe_import
    return safe


def run():
    """从 stdin 读取 payload，执行用户脚本，输出结果 JSON 到 stdout"""
    payload = json.load(sys.stdin)
    script_source = payload['script_source']
    input_data = payload.get('input')
    context = payload.get('context') or {}

    result_holder = {'result': None, 'branch': None, 'has_result': False}

    def set_result(value):
        result_holder['result'] = value
        result_holder['has_result'] = True

    def set_branch(label):
        result_holder['branch'] = label

    # 构建受限 globals：用户脚本无法访问真实 builtins
    restricted_globals = {
        '__builtins__': make_restricted_builtins(),
        'input': input_data,
        'context': context,
        'set_result': set_result,
        'set_branch': set_branch,
        'result': None,
    }

    try:
        exec(compile(script_source, '<user_script>', 'exec'), restricted_globals)
        # 若未调用 set_result 但定义了 result 变量
        if not result_holder['has_result'] and restricted_globals.get('result') is not None:
            result_holder['result'] = restricted_globals['result']
            result_holder['has_result'] = True
        print(json.dumps({
            'status': 'success',
            'result': result_holder['result'],
            'branch': result_holder['branch'],
        }, ensure_ascii=True, default=str))
    except Exception as e:
        print(json.dumps({
            'status': 'error',
            'error': f'{type(e).__name__}: {e}',
            'traceback': traceback.format_exc(),
        }, ensure_ascii=True, default=str))


if __name__ == '__main__':
    run()
