"""
泛微 E10 OAuth2 单点登录配置。

所有配置均通过环境变量或 Flask ``app.config`` 注入，不修改上游 ``app/config.py``。
``app.config`` 优先于环境变量，方便测试与运行时覆盖。
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Iterable, Optional, Tuple
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

_TRUE_VALUES = {'1', 'true', 'yes', 'on', 'y'}
_FALSE_VALUES = {'0', 'false', 'no', 'off', 'n', ''}


def as_bool(value: object, default: bool = False) -> bool:
    """把环境变量/配置值解析为布尔值。"""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    return default


def as_int(value: object, default: int) -> int:
    """把环境变量/配置值解析为整数，非法值回退到默认值。"""
    if value is None or str(value).strip() == '':
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def as_csv(value: object) -> Tuple[str, ...]:
    """把逗号分隔字符串/列表解析为去重后的元组。"""
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set)):
        items: Iterable[str] = (str(item) for item in value)
    else:
        items = str(value).split(',')
    result = []
    seen = set()
    for item in items:
        text = item.strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _get(app, key: str, default: Optional[str] = None) -> Optional[str]:
    """读取配置：app.config 优先，其次环境变量，最后默认值。"""
    value = app.config.get(key)
    if value is None or (isinstance(value, str) and value.strip() == ''):
        value = os.environ.get(key, default)
    return value


@dataclass
class E10Config:
    """E10 OAuth2 集成配置。"""

    # 开关与凭据
    enabled: bool = False
    base_url: str = ''
    client_id: str = ''
    client_secret: str = ''

    # 地址
    redirect_uri: str = ''
    public_base_url: str = ''
    frontend_base_url: str = ''

    # 端点路径（不同 E10 版本如路径不同，可通过环境变量覆盖）
    authorize_path: str = '/papi/sso/oauth2.0/authorize'
    token_path: str = '/papi/sso/oauth2.0/accessToken'
    profile_path: str = '/papi/sso/oauth2.0/profile'
    logout_path: str = '/sp/integration/oauth2.0/logout'

    # 请求行为
    token_param_style: str = 'auto'  # auto / query / form
    profile_param_style: str = 'query'  # query / form
    scope: str = ''
    send_state: bool = True
    timeout: int = 15
    verify_ssl: bool = True
    ca_bundle: str = ''

    # 账号映射 / 自动开通
    id_field: str = 'loginId'
    email_domain: str = ''
    email_template: str = ''
    email_fallback_template: str = ''
    auto_create_users: bool = True
    default_role: str = 'editor'
    admin_ids: Tuple[str, ...] = field(default_factory=tuple)
    match_by_email: bool = True
    sync_profile: bool = True

    # 登录页 / 登出
    password_login_enabled: bool = True
    enforce_sso: bool = False
    logout_with_e10: bool = True
    logout_service: str = ''

    # 生命周期
    auto_create_schema: bool = True
    state_ttl: int = 600
    ticket_ttl: int = 120
    state_cookie_name: str = 'e10_oauth_state'
    binding_cookie_name: str = 'e10_login_binding'
    cookie_secure: str = 'auto'  # auto / true / false
    cookie_samesite: str = 'Lax'  # Lax / Strict / None（iframe 嵌入时可能需要 None + HTTPS）

    @property
    def ready(self) -> bool:
        """必填项是否齐全。"""
        return bool(self.base_url and self.client_id and self.client_secret)

    @property
    def missing(self) -> Tuple[str, ...]:
        """返回缺失的必填配置项名称。"""
        missing = []
        if not self.base_url:
            missing.append('E10_BASE_URL')
        if not self.client_id:
            missing.append('E10_CLIENT_ID')
        if not self.client_secret:
            missing.append('E10_CLIENT_SECRET')
        return tuple(missing)

    def resolve_callback_url(self, request=None) -> str:
        """
        解析 OAuth2 回调地址。

        优先级：E10_REDIRECT_URI > E10_PUBLIC_BASE_URL + 固定路径 > 当前请求根地址。
        注意：E10 要求 redirect_uri 不能包含 ``#`` 路由，因此这里始终指向后端。
        """
        if self.redirect_uri:
            # 必须与 E10 应用登记的回调地址完全一致，不做任何路径归一化
            return self.redirect_uri
        base = (self.public_base_url or '').rstrip('/')
        if not base and request is not None:
            base = request.url_root.rstrip('/')
        return f'{base}/api/integrations/e10/callback' if base else ''

    def resolve_frontend_base(self, request=None) -> str:
        """解析前端首页地址（用于登录完成后跳转）。"""
        if self.frontend_base_url:
            return self.frontend_base_url.rstrip('/')
        if self.public_base_url:
            return self.public_base_url.rstrip('/')
        if self.redirect_uri:
            parts = urlsplit(self.redirect_uri)
            if parts.scheme and parts.netloc:
                prefix = parts.path or ''
                suffix = '/api/integrations/e10/callback'
                if prefix.endswith(suffix):
                    prefix = prefix[:-len(suffix)]
                return f'{parts.scheme}://{parts.netloc}{prefix}'.rstrip('/')
        if request is not None:
            return request.url_root.rstrip('/')
        return ''

    def should_use_secure_cookie(self, request=None) -> bool:
        """决定 OAuth state Cookie 是否加 Secure 标记。"""
        mode = (self.cookie_secure or 'auto').strip().lower()
        if mode in _TRUE_VALUES:
            return True
        if mode in _FALSE_VALUES and mode != 'auto':
            return False
        if request is None:
            return False
        forwarded = (request.headers.get('X-Forwarded-Proto') or '').split(',')[0].strip()
        return request.is_secure or forwarded == 'https'

    @classmethod
    def from_app(cls, app) -> 'E10Config':
        """从 Flask 应用配置 + 环境变量构建配置对象。"""
        cfg = cls(
            enabled=as_bool(_get(app, 'E10_SSO_ENABLED', 'false')),
            base_url=(_get(app, 'E10_BASE_URL', '') or '').strip().rstrip('/'),
            client_id=(_get(app, 'E10_CLIENT_ID', '') or '').strip(),
            client_secret=(_get(app, 'E10_CLIENT_SECRET', '') or '').strip(),
            redirect_uri=(_get(app, 'E10_REDIRECT_URI', '') or '').strip(),
            public_base_url=(_get(app, 'E10_PUBLIC_BASE_URL', '') or '').strip().rstrip('/'),
            frontend_base_url=(_get(app, 'E10_FRONTEND_BASE_URL', '') or '').strip().rstrip('/'),
            authorize_path=(_get(app, 'E10_AUTHORIZE_PATH', '/papi/sso/oauth2.0/authorize') or '').strip(),
            token_path=(_get(app, 'E10_TOKEN_PATH', '/papi/sso/oauth2.0/accessToken') or '').strip(),
            profile_path=(_get(app, 'E10_PROFILE_PATH', '/papi/sso/oauth2.0/profile') or '').strip(),
            logout_path=(_get(app, 'E10_LOGOUT_PATH', '/sp/integration/oauth2.0/logout') or '').strip(),
            token_param_style=(_get(app, 'E10_TOKEN_PARAM_STYLE', 'auto') or 'auto').strip().lower(),
            profile_param_style=(_get(app, 'E10_PROFILE_PARAM_STYLE', 'query') or 'query').strip().lower(),
            scope=(_get(app, 'E10_SCOPE', '') or '').strip(),
            send_state=as_bool(_get(app, 'E10_SEND_STATE', 'true'), True),
            timeout=as_int(_get(app, 'E10_TIMEOUT', '15'), 15),
            verify_ssl=as_bool(_get(app, 'E10_VERIFY_SSL', 'true'), True),
            ca_bundle=(_get(app, 'E10_CA_BUNDLE', '') or '').strip(),
            id_field=(_get(app, 'E10_ID_FIELD', 'loginId') or 'loginId').strip(),
            email_domain=(_get(app, 'E10_EMAIL_DOMAIN', '') or '').strip().lstrip('@'),
            email_template=(_get(app, 'E10_EMAIL_TEMPLATE', '') or '').strip(),
            email_fallback_template=(_get(app, 'E10_EMAIL_FALLBACK_TEMPLATE', '') or '').strip(),
            auto_create_users=as_bool(_get(app, 'E10_AUTO_CREATE_USERS', 'true'), True),
            default_role=(_get(app, 'E10_DEFAULT_ROLE', 'editor') or 'editor').strip(),
            admin_ids=as_csv(_get(app, 'E10_ADMIN_IDS', '')),
            match_by_email=as_bool(_get(app, 'E10_MATCH_BY_EMAIL', 'true'), True),
            sync_profile=as_bool(_get(app, 'E10_SYNC_PROFILE', 'true'), True),
            password_login_enabled=as_bool(_get(app, 'E10_PASSWORD_LOGIN_ENABLED', 'true'), True),
            enforce_sso=as_bool(_get(app, 'E10_ENFORCE_SSO', 'false'), False),
            logout_with_e10=as_bool(_get(app, 'E10_LOGOUT_WITH_E10', 'true'), True),
            logout_service=(_get(app, 'E10_LOGOUT_SERVICE', '') or '').strip(),
            auto_create_schema=as_bool(_get(app, 'E10_AUTO_CREATE_SCHEMA', 'true'), True),
            state_ttl=as_int(_get(app, 'E10_STATE_TTL', '600'), 600),
            ticket_ttl=as_int(_get(app, 'E10_TICKET_TTL', '120'), 120),
            state_cookie_name=(_get(app, 'E10_STATE_COOKIE_NAME', 'e10_oauth_state') or 'e10_oauth_state').strip(),
            binding_cookie_name=(_get(app, 'E10_BINDING_COOKIE_NAME', 'e10_login_binding') or 'e10_login_binding').strip(),
            cookie_secure=(_get(app, 'E10_COOKIE_SECURE', 'auto') or 'auto').strip().lower(),
            cookie_samesite=(_get(app, 'E10_COOKIE_SAMESITE', 'Lax') or 'Lax').strip(),
        )

        # 归一化：路径必须以 / 开头；参数风格只允许白名单值
        for attr in ('authorize_path', 'token_path', 'profile_path', 'logout_path'):
            value = getattr(cfg, attr)
            if value and not value.startswith('/'):
                setattr(cfg, attr, '/' + value)
        if cfg.token_param_style not in ('auto', 'query', 'form'):
            logger.warning('[E10] 非法的 E10_TOKEN_PARAM_STYLE=%r，回退到 auto', cfg.token_param_style)
            cfg.token_param_style = 'auto'
        if cfg.profile_param_style not in ('query', 'form', 'auto'):
            logger.warning('[E10] 非法的 E10_PROFILE_PARAM_STYLE=%r，回退到 query', cfg.profile_param_style)
            cfg.profile_param_style = 'query'
        samesite = (cfg.cookie_samesite or 'lax').strip().lower()
        if samesite not in ('lax', 'strict', 'none'):
            logger.warning('[E10] 非法的 E10_COOKIE_SAMESITE=%r，回退到 Lax', cfg.cookie_samesite)
            samesite = 'lax'
        cfg.cookie_samesite = samesite.capitalize()
        if cfg.cookie_samesite == 'None':
            logger.info(
                '[E10] E10_COOKIE_SAMESITE=None 需要 HTTPS 且 Secure Cookie；'
                '仅在 SmartTable 被嵌入 E10 门户 iframe 时使用'
            )
        if cfg.timeout <= 0:
            cfg.timeout = 15
        if cfg.state_ttl <= 0:
            cfg.state_ttl = 600
        if cfg.ticket_ttl <= 0:
            cfg.ticket_ttl = 120

        if cfg.enabled and not cfg.ready:
            logger.warning(
                '[E10] E10_SSO_ENABLED=true 但缺少必填配置：%s。'
                '登录按钮将保持隐藏，直到配置完整。',
                ', '.join(cfg.missing) or 'unknown',
            )
        if cfg.enabled and cfg.ready and not (cfg.redirect_uri or cfg.public_base_url):
            logger.warning(
                '[E10] 未配置 E10_REDIRECT_URI / E10_PUBLIC_BASE_URL，将根据当前请求推导回调地址。'
                '生产环境（尤其反向代理）请显式配置，避免 http/https 或 Host 不一致导致 80013/1005 错误。'
            )
        if cfg.redirect_uri and not cfg.redirect_uri.rstrip('/').endswith(
            '/api/integrations/e10/callback'
        ):
            logger.warning(
                '[E10] E10_REDIRECT_URI=%s 与内置回调路径 '
                '/api/integrations/e10/callback 不一致，请确认 E10 应用登记地址与路由匹配。',
                cfg.redirect_uri,
            )
        return cfg
