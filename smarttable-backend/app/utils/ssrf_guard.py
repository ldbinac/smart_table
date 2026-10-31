"""
SSRF 防护工具

为所有"目标 URL 由用户/租户配置"的服务端出站请求提供统一防护：
- 协议白名单（仅 http/https）
- DNS 解析后拒绝内网/保留/环回/链路本地/组播等受限地址段

使用方：
- app.services.webhook_service（Webhook 投递）
- app.services.plugin_proxy_service（插件第三方代理）

安全边界说明：
- 本校验与实际发起请求之间存在 DNS 重绑定窗口（TOCTOU），
  与插件代理保持同等防护水平；若需彻底消除，需在连接层固定已校验 IP。
"""
import ipaddress
import socket
from urllib.parse import urlparse

# 允许的协议白名单
ALLOWED_SCHEMES = frozenset({'http', 'https'})


class SSRFBlockedError(Exception):
    """目标 URL 被 SSRF 防护策略拒绝（协议非法/缺主机/解析到受限网段）"""


def is_restricted_addr(host: str) -> bool:
    """DNS 解析后判断是否落在内网/保留/环回等受限地址段（True=受限）

    getaddrinfo 会将 IPv6 字面量、十六进制/短格式 IPv4 等统一归一化，
    因此字面量形式的内网地址同样会被拦截。
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        # 解析失败一律视为不安全，阻断
        return True
    for info in infos:
        raw = info[4][0].split('%')[0]
        try:
            addr = ipaddress.ip_address(raw)
        except ValueError:
            return True
        if (addr.is_private or addr.is_loopback or addr.is_link_local
                or addr.is_reserved or addr.is_multicast or addr.is_unspecified):
            return True
    return False


def validate_public_http_url(url: str) -> None:
    """校验出站 HTTP(S) URL 的 SSRF 安全性，不通过抛 SSRFBlockedError

    覆盖：协议白名单、主机存在性、DNS 解析后受限网段（含 IPv4/IPv6
    字面量、十六进制与短格式 IP）。
    """
    parsed = urlparse(url or '')
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        scheme = parsed.scheme or '(空)'
        raise SSRFBlockedError(f"不支持的协议: '{scheme}'，仅允许 http/https")

    host = (parsed.hostname or '').lower()
    if not host:
        raise SSRFBlockedError('URL 缺少主机名')

    if is_restricted_addr(host):
        raise SSRFBlockedError(
            f'目标主机解析到内网/受限地址段，已拦截: {host}')
