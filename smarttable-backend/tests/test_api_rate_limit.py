"""
针对 api_rate_limit 限流逻辑的单元测试。
重点验证：剩余等待时间被钳制在窗口内（不会出现数千秒的误封），
以及陈旧的 first_request 时间戳不会导致 remaining_time 被放大。
"""
import time
import sys
import os
import types

import pytest


# ---------------------------------------------------------------------------
# 构造一个轻量的测试环境，避免依赖 Flask/JWT/cache 全局对象
# ---------------------------------------------------------------------------
class _FakeCache:
    """内存缓存，模拟 Flask-Caching 的 get/set/delete。"""

    def __init__(self):
        self._store = {}

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value, timeout=None):
        self._store[key] = value

    def delete(self, key):
        self._store.pop(key, None)


def _make_module(fake_cache):
    """动态构造 decorators 模块，注入 fake cache 与最小依赖。"""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "test_decorators_mod",
        os.path.join(os.path.dirname(__file__), "..", "app", "utils", "decorators.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    # 注入依赖桩
    fake_flask = types.ModuleType("flask")
    fake_flask.request = types.SimpleNamespace(
        headers=types.SimpleNamespace(get=lambda *a, **k: None),
        remote_addr="127.0.0.1",
        view_args={},
        args={},
        is_json=False,
        get_json=lambda *a, **k: None,
        form={},
    )
    fake_flask.g = types.SimpleNamespace()
    fake_jwt = types.ModuleType("flask_jwt_extended")
    fake_jwt.verify_jwt_in_request = lambda *a, **k: None
    fake_jwt.get_jwt_identity = lambda *a, **k: None
    fake_jwt.get_jwt = lambda *a, **k: {}

    fake_ext = types.ModuleType("app.extensions")
    fake_ext.cache = fake_cache
    fake_resp = types.ModuleType("app.utils.response")
    fake_resp.error_response = lambda message, code=400, error=None, **kw: {
        "error_message": message,
        "code": code,
        "error": error,
    }
    fake_resp.forbidden_response = lambda *a, **k: {}
    fake_resp.unauthorized_response = lambda *a, **k: {}

    sys.modules["flask"] = fake_flask
    sys.modules["flask_jwt_extended"] = fake_jwt
    sys.modules["app.extensions"] = fake_ext
    sys.modules["app.utils.response"] = fake_resp

    # 提供简单的 app.utils / app.models 桩，防止 import 失败
    for name in ("app.utils", "app.models", "app.models.user", "app.models.log"):
        sys.modules.setdefault(name, types.ModuleType(name))

    spec.loader.exec_module(mod)
    return mod


def _call_limited(fn, times, fake_cache):
    """连续调用被装饰的 fn times 次，返回最后一次响应。"""
    last = None
    for _ in range(times):
        last = fn()
    return last


def test_remaining_time_clamped_within_window():
    """超过额度后，返回的剩余时间不应超过 window。"""
    fake_cache = _FakeCache()
    mod = _make_module(fake_cache)
    calls = {"n": 0}

    @mod.api_rate_limit(max_requests=5, window=60, key_prefix="test", by_user=False, by_ip=False)
    def view():
        calls["n"] += 1
        return {"ok": True}

    # 第 6 次应被限流（max_requests=5）
    resp = _call_limited(view, 6, fake_cache)
    assert resp is not None
    assert resp["code"] == 429
    # 提示信息中的等待时间不应超出 window(60)
    msg = resp["error_message"]
    import re
    total_secs = 0
    m_min = re.search(r"(\d+)\s*分", msg)
    m_sec = re.search(r"(\d+)\s*秒", msg)
    if m_min:
        total_secs += int(m_min.group(1)) * 60
    if m_sec:
        total_secs += int(m_sec.group(1))
    assert total_secs > 0, f"无法从提示中提取等待时间: {msg}"
    assert total_secs <= 60, f"剩余时间 {total_secs} 超出窗口 60 秒"


def test_stale_first_request_does_not_amplify_remaining():
    """陈旧的 first_request（来自很久以前）不应把剩余时间放大成数千秒。"""
    fake_cache = _FakeCache()
    mod = _make_module(fake_cache)
    key = "rate_limit:test:ip:127.0.0.1"
    # 注入一个 first_request 来自未来（3384 秒后，模拟缓存/时钟异常导致
    # 的时间戳错乱）、count 已接近上限的陈旧记录。
    # 旧逻辑的 remaining = window - (now - first_request) 会被放大成数千秒。
    fake_cache.set(key, {"count": 5, "first_request": time.time() + 3384}, timeout=60)

    @mod.api_rate_limit(max_requests=5, window=60, key_prefix="test", by_user=False, by_ip=True)
    def view():
        return {"ok": True}

    resp = view()  # 第 6 次：count 5->6 > 5 触发限流
    assert resp["code"] == 429
    import re
    msg = resp["error_message"]
    # 提示可能是"请 N 秒后再试"或"请 M 分 S 秒后再试"，统一换算成秒
    total_secs = 0
    m_min = re.search(r"(\d+)\s*分", msg)
    m_sec = re.search(r"(\d+)\s*秒", msg)
    if m_min:
        total_secs += int(m_min.group(1)) * 60
    if m_sec:
        total_secs += int(m_sec.group(1))
    assert total_secs > 0, f"无法从提示中提取等待时间: {msg}"
    assert total_secs <= 60, f"陈旧时间戳导致剩余时间被放大到 {total_secs} 秒"


def test_normal_requests_not_blocked():
    """未超过额度时，请求应正常通过。"""
    fake_cache = _FakeCache()
    mod = _make_module(fake_cache)
    count = {"n": 0}

    @mod.api_rate_limit(max_requests=100, window=60, key_prefix="test", by_user=False, by_ip=False)
    def view():
        count["n"] += 1
        return {"ok": True}

    for _ in range(50):
        assert view() == {"ok": True}
    assert count["n"] == 50


if __name__ == "__main__":
    test_remaining_time_clamped_within_window()
    test_stale_first_request_does_not_amplify_remaining()
    test_normal_requests_not_blocked()
    print("all passed")
