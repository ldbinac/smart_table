"""
ScriptExecutionService 单元测试
测试 Python / TypeScript 脚本沙箱：受限 builtins、白名单模块、超时、输出体积限制。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.script_execution_service import ScriptExecutionService


class TestPythonSandbox:
    def test_basic_set_result(self):
        r = ScriptExecutionService.execute('python', 'set_result({"processed": True, "count": len(input) if isinstance(input, list) else 1})', [1, 2, 3], {}, timeout=5)
        assert r['status'] == 'success'
        assert r['result'] == {'processed': True, 'count': 3}

    def test_result_variable_fallback(self):
        # 未调用 set_result 但赋值 result 变量
        r = ScriptExecutionService.execute('python', 'result = 42', None, {}, timeout=5)
        assert r['status'] == 'success'
        assert r['result'] == 42

    def test_set_branch(self):
        r = ScriptExecutionService.execute('python', 'set_result(1)\nset_branch("high")', None, {}, timeout=5)
        assert r['status'] == 'success'
        assert r['branch'] == 'high'

    def test_dangerous_open_blocked(self):
        r = ScriptExecutionService.execute('python', 'open("x.txt","w")', None, {}, timeout=5)
        assert r['status'] == 'error'
        assert 'open' in r['error'] or 'NameError' in r['error']

    def test_dangerous_exec_blocked(self):
        r = ScriptExecutionService.execute('python', 'exec("import os")', None, {}, timeout=5)
        assert r['status'] == 'error'

    def test_dangerous_import_os_blocked(self):
        r = ScriptExecutionService.execute('python', 'import os', None, {}, timeout=5)
        assert r['status'] == 'error'
        assert 'os' in r['error'] or 'ImportError' in r['error']

    def test_whitelist_module_json(self):
        r = ScriptExecutionService.execute('python', 'import json\nset_result(json.loads(\'{"a":1}\'))', None, {}, timeout=5)
        assert r['status'] == 'success'
        assert r['result'] == {'a': 1}

    def test_whitelist_module_math(self):
        r = ScriptExecutionService.execute('python', 'import math\nset_result(math.ceil(1.2))', None, {}, timeout=5)
        assert r['status'] == 'success'
        assert r['result'] == 2

    def test_timeout(self):
        r = ScriptExecutionService.execute('python', 'while True:\n    pass', None, {}, timeout=2)
        assert r['status'] == 'error'
        assert '超时' in r['error']

    def test_oversized_output(self):
        # 构造 >1MB 结果
        r = ScriptExecutionService.execute('python', 'set_result({"x": "a" * 2000000})', None, {}, timeout=10)
        assert r['status'] == 'error'
        assert '1MB' in r['error'] or '超过' in r['error']

    def test_unsupported_language(self):
        r = ScriptExecutionService.execute('typescript', 'setResult(1)', None, {}, timeout=10)
        assert r['status'] == 'error'
        assert 'python' in r['error']
