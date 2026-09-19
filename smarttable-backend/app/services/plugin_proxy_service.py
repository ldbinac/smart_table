"""
插件第三方后端代理服务

前端插件经宿主代理访问第三方服务，规避 iframe（opaque origin）的 CORS/CSP 限制。
安全边界：
- 目标域名必须落在插件 manifest 的 permissions.network 白名单内（精确或子域匹配）
- SSRF 防护：仅允许 http/https，解析 DNS 后拒绝内网/保留/环回等地址段
- 请求头过滤：禁止透传 Host/Cookie/Authorization 等宿主凭证或受控头
- 上限保护：超时（PROXY_TIMEOUT）、响应体大小（MAX_RESPONSE_BYTES）、每插件速率限制
"""
import base64
import ipaddress
import socket
import threading
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests

# ---- 代理限制常量 ----
PROXY_TIMEOUT = 15                      # 单次代理请求超时（秒）
MAX_RESPONSE_BYTES = 5 * 1024 * 1024   # 响应体上限 5MB
ALLOWED_SCHEMES = {"http", "https"}
# 禁止插件经代理透传的受控/凭证头（避免泄露宿主或冒充身份）
_FORBIDDEN_HEADERS = {
    "host", "cookie", "authorization", "proxy-authorization",
    "x-forwarded-for", "x-forwarded-host", "x-real-ip", "referer", "origin",
    "content-length",
}
# 每插件速率限制（滑动窗口）
_RATE_LIMIT_MAX = 60
_RATE_LIMIT_WINDOW = 60
_rate_lock = threading.Lock()
_RATE_BUCKETS: dict = {}


class ProxyError(Exception):
    """代理失败（error_code + message + http_status）

    message 为 i18n key（含 {占位符}），由路由层 translate() 结合 params
    渲染为当前语言文本。
    """

    def __init__(self, error_code: str, message: str, http_status: int = 400,
                 params: Optional[Dict[str, Any]] = None):
        super().__init__(f"{error_code}: {message}")
        self.error_code = error_code
        self.message = message
        self.http_status = http_status
        self.params = params or {}


def _check_rate_limit(plugin_id: str) -> None:
    now = time.time()
    with _rate_lock:
        ts = _RATE_BUCKETS.get(plugin_id, [])
        ts = [t for t in ts if now - t < _RATE_LIMIT_WINDOW]
        if len(ts) >= _RATE_LIMIT_MAX:
            raise ProxyError(
                "RATE_LIMITED", "plugin_proxy_rate_limited", 429,
                {"plugin_id": plugin_id, "limit": _RATE_LIMIT_MAX,
                 "window": int(_RATE_LIMIT_WINDOW)})
        ts.append(now)
        _RATE_BUCKETS[plugin_id] = ts


def _is_allowed_host(host: str, whitelist) -> bool:
    """精确或子域匹配白名单（host 已是小写）"""
    for entry in (whitelist or []):
        e = str(entry).lower().strip()
        if not e:
            continue
        if host == e or host.endswith("." + e):
            return True
    return False


def _is_restricted_addr(host: str) -> bool:
    """DNS 解析后判断是否落在内网/保留/环回等受限地址段（false=安全）"""
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        # 解析失败一律视为不安全，阻断
        return True
    for info in infos:
        raw = info[4][0].split("%")[0]
        try:
            addr = ipaddress.ip_address(raw)
        except ValueError:
            return True
        if (addr.is_private or addr.is_loopback or addr.is_link_local
                or addr.is_reserved or addr.is_multicast or addr.is_unspecified):
            return True
    return False


def proxy(plugin_id: str, manifest: dict, url: str, method: str = "GET",
          headers: dict = None, body=None) -> dict:
    """执行一次受控第三方代理

    Returns:
        {status, headers, body, body_encoding}
    Raises:
        ProxyError: 校验/转发失败
    """
    _check_rate_limit(plugin_id)

    parsed = urlparse(url or "")
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ProxyError("INVALID_URL", "plugin_proxy_invalid_scheme",
                         params={"scheme": parsed.scheme})
    host = (parsed.hostname or "").lower()
    if not host:
        raise ProxyError("INVALID_URL", "plugin_proxy_missing_host")

    whitelist = (manifest.get("permissions") or {}).get("network") or []
    if not whitelist:
        raise ProxyError("PERMISSION_DENIED",
                         "plugin_proxy_network_not_declared")
    if not _is_allowed_host(host, whitelist):
        raise ProxyError("PERMISSION_DENIED", "plugin_proxy_host_not_allowed",
                         params={"host": host})

    # SSRF 防护：解析目标地址，拒绝受限网段
    if _is_restricted_addr(host):
        raise ProxyError("SSRF_BLOCKED", "plugin_proxy_ssrf_blocked",
                         params={"host": host})

    # 过滤受控/凭证头
    filtered = {}
    for k, v in (headers or {}).items():
        if str(k).lower() in _FORBIDDEN_HEADERS:
            continue
        filtered[k] = v

    method = (method or "GET").upper()
    try:
        resp = requests.request(
            method, url, headers=filtered, data=body,
            timeout=PROXY_TIMEOUT, stream=True, allow_redirects=False)
    except requests.exceptions.Timeout:
        raise ProxyError("UPSTREAM_TIMEOUT", "plugin_proxy_upstream_timeout", 504)
    except requests.exceptions.RequestException as e:
        raise ProxyError("UPSTREAM_ERROR", "plugin_proxy_upstream_error", 502,
                         params={"error": f"{type(e).__name__}: {e}"})

    # 响应体大小上限（流式读取，超限即断开）
    chunks = []
    total = 0
    truncated = False
    for chunk in resp.iter_content(8192):
        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            truncated = True
            resp.close()
            break

    raw = b"".join(chunks)
    content_type = resp.headers.get("content-type", "")
    is_text = any(t in content_type.lower() for t in
                  ("text/", "json", "xml", "javascript", "application/x-www-form"))
    if is_text:
        try:
            body_out = raw.decode("utf-8")
            body_encoding = "text"
        except UnicodeDecodeError:
            body_out = base64.b64encode(raw).decode("ascii")
            body_encoding = "base64"
    else:
        body_out = base64.b64encode(raw).decode("ascii")
        body_encoding = "base64"

    # 响应头仅透传安全子集，避免泄露内部头
    safe_headers = {}
    for k, v in resp.headers.items():
        kl = k.lower()
        if kl in ("content-type", "content-length", "cache-control",
                  "etag", "last-modified", "content-disposition"):
            safe_headers[k] = v

    if truncated:
        raise ProxyError("RESPONSE_TOO_LARGE", "plugin_proxy_response_too_large",
                         502, params={"limit": MAX_RESPONSE_BYTES})

    return {
        "status": resp.status_code,
        "headers": safe_headers,
        "body": body_out,
        "body_encoding": body_encoding,
    }
