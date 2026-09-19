"""插件第三方代理服务测试：白名单 / SSRF 防护 / 转发"""
import pytest

from app.services import plugin_proxy_service as proxy_svc


def test_whitelist_subdomain_match():
    assert proxy_svc._is_allowed_host("a.api.example.com", ["api.example.com"]) is True
    assert proxy_svc._is_allowed_host("api.example.com", ["api.example.com"]) is True
    assert proxy_svc._is_allowed_host("evil.com", ["api.example.com"]) is False


def test_restricted_addr_loopback():
    # IP 字面量解析无网络依赖
    assert proxy_svc._is_restricted_addr("127.0.0.1") is True
    assert proxy_svc._is_restricted_addr("10.0.0.1") is True
    assert proxy_svc._is_restricted_addr("169.254.0.1") is True
    assert proxy_svc._is_restricted_addr("8.8.8.8") is False


def test_proxy_denies_unlisted_host(monkeypatch):
    called = {"v": False}

    def fake_request(*a, **k):
        called["v"] = True
        raise AssertionError("should not forward")

    monkeypatch.setattr(proxy_svc.requests, "request", fake_request)
    manifest = {"permissions": {"network": ["api.example.com"]}}
    with pytest.raises(proxy_svc.ProxyError) as ei:
        proxy_svc.proxy("p1", manifest, "https://evil.com/x", "GET")
    assert ei.value.error_code == "PERMISSION_DENIED"
    assert called["v"] is False


def test_proxy_blocks_ssrf(monkeypatch):
    def fake_request(*a, **k):
        raise AssertionError("should not forward")

    monkeypatch.setattr(proxy_svc.requests, "request", fake_request)
    manifest = {"permissions": {"network": ["127.0.0.1"]}}
    with pytest.raises(proxy_svc.ProxyError) as ei:
        proxy_svc.proxy("p1", manifest, "http://127.0.0.1:8080/admin", "GET")
    assert ei.value.error_code == "SSRF_BLOCKED"


class _FakeResp:
    def __init__(self, status, headers, chunks):
        self.status_code = status
        self.headers = headers
        self._chunks = chunks

    def iter_content(self, n):
        for c in self._chunks:
            yield c


def test_proxy_forwards_and_returns_text(monkeypatch):
    def fake_request(method, url, **k):
        assert method == "GET"
        return _FakeResp(200, {"content-type": "application/json"}, [b'{"ok":', b'true}'])

    monkeypatch.setattr(proxy_svc.requests, "request", fake_request)
    # 隔离真实 DNS，专注验证转发与响应解析逻辑
    monkeypatch.setattr(proxy_svc, "_is_restricted_addr", lambda host: False)
    manifest = {"permissions": {"network": ["api.example.com"]}}
    result = proxy_svc.proxy("p1", manifest, "https://api.example.com/v1/x", "GET")
    assert result["status"] == 200
    assert result["body"] == '{"ok":true}'
    assert result["body_encoding"] == "text"


def test_proxy_rejects_non_http_scheme(monkeypatch):
    manifest = {"permissions": {"network": ["api.example.com"]}}
    with pytest.raises(proxy_svc.ProxyError) as ei:
        proxy_svc.proxy("p1", manifest, "ftp://api.example.com/x", "GET")
    assert ei.value.error_code == "INVALID_URL"
