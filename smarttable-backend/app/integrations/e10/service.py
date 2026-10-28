"""
E10 OAuth2 业务逻辑：state / 一次性票据 / 用户映射与自动开通。
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlsplit
from uuid import UUID

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.extensions import cache, db
from app.models.user import User, UserRole, UserStatus
from app.services.auth_service import AuthService

from .client import E10Profile
from .config import E10Config
from .models import E10Identity

logger = logging.getLogger(__name__)

_STATE_SALT = 'smarttable.e10.oauth.state.v1'
_TICKET_SALT = 'smarttable.e10.oauth.ticket.v1'

_MEMORY_TICKETS: Dict[str, Tuple[float, str]] = {}
_MEMORY_TICKETS_LOCK = threading.Lock()

_SCHEMA_READY = False
_SCHEMA_LOCK = threading.Lock()

# 允许通过 E10_DEFAULT_ROLE 自动开通的角色；管理角色只能通过 E10_ADMIN_IDS 显式指定
_AUTO_PROVISION_ROLES = {
    UserRole.VIEWER,
    UserRole.COMMENTER,
    UserRole.EDITOR,
}


# E10 自定义属性别名（键名大小写/命名风格可能因版本而异）
_ATTRIBUTE_ALIASES = {
    'job_num': ('job_num', 'jobNum', 'jobnum', 'job_number', 'jobNo'),
    'username': ('username', 'user_name', 'userName', 'name', 'displayName', 'fullName', 'cn', 'nickName'),
    'mobile': ('mobile', 'phone', 'phone_number', 'phoneNumber'),
    'email': ('email', 'mail', 'emailAddress', 'email_address'),
    'avatar': ('avatar', 'avatarUrl', 'avatar_url', 'photo', 'headImage'),
}


def _attr_value(attributes: Any, *names: str) -> Any:
    """大小写不敏感地读取 E10 attributes 中的值。"""
    if not isinstance(attributes, dict):
        return None
    lowered = {str(key).strip().lower(): value for key, value in attributes.items()}
    for name in names:
        value = lowered.get(name.strip().lower())
        if value is not None and str(value).strip() != '':
            return value
    return None


def _template_values(profile: E10Profile, cfg: E10Config) -> Dict[str, str]:
    """构造邮箱模板变量：{id}、{job_num}、{username}、{mobile}、{domain} 等。"""
    attributes = profile.attributes or {}
    values: Dict[str, str] = {
        'id': str(profile.id or ''),
        'login_id': str(profile.id or ''),
        'loginId': str(profile.id or ''),
        'domain': cfg.email_domain or '',
    }
    for canonical, aliases in _ATTRIBUTE_ALIASES.items():
        value = _attr_value(attributes, *aliases)
        if value is not None:
            values[canonical] = str(value).strip()
    # 保留原始属性键，便于直接使用 {job_num} / {jobNum} 等写法
    for key, value in attributes.items():
        if value is None:
            continue
        text = str(value).strip()
        values[str(key)] = text
        values[str(key).lower()] = text
    return values


def _render_template(template: str, values: Dict[str, str]) -> str:
    """替换 ``{key}`` 占位符；未知占位符替换为空字符串（随后邮箱校验会失败）。"""
    return re.sub(
        r'\{([A-Za-z0-9_]+)\}',
        lambda match: values.get(match.group(1), ''),
        template,
    )


# ----------------------------------------------------------------------
# URL / redirect 安全处理
# ----------------------------------------------------------------------
def sanitize_redirect(value: Any, default: str = '/') -> str:
    """
    只允许站内绝对路径，防止开放重定向。

    - 必须以单个 ``/`` 开头；
    - 拒绝 ``//host``、反斜杠、控制字符、``#`` fragment；
    - 限制长度。
    """
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    if len(text) > 2048:
        return default
    if not text.startswith('/') or text.startswith('//'):
        return default
    if '\\' in text or '#' in text:
        return default
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in text):
        return default
    parts = urlsplit(text)
    if parts.scheme or parts.netloc:
        return default
    return text


def build_frontend_target(base_url: str, route: str = '/') -> str:
    """把站内路由拼接到前端 hash 路由地址上。"""
    base = (base_url or '').rstrip('/')
    route = sanitize_redirect(route)
    if not base:
        return ''
    if route.startswith('/#'):
        return f'{base}{route}'
    return f'{base}/#{route}'


# ----------------------------------------------------------------------
# 签名 state / 一次性票据
# ----------------------------------------------------------------------
def _serializer(salt: str) -> URLSafeTimedSerializer:
    secret = current_app.config.get('SECRET_KEY')
    if not secret:
        raise RuntimeError('SECRET_KEY is required to sign E10 SSO state/ticket')
    return URLSafeTimedSerializer(
        secret,
        salt=salt,
        signer_kwargs={'digest_method': hashlib.sha256},
    )


def create_state(redirect: str, ttl: int) -> str:
    """生成带签名的 OAuth state（同时写入 HttpOnly Cookie 做双检）。"""
    payload = {
        'r': sanitize_redirect(redirect),
        'n': secrets.token_urlsafe(24),
    }
    return _serializer(_STATE_SALT).dumps(payload)


def verify_state(token: str, ttl: int) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """校验 state 签名与有效期，返回 (payload, error)。"""
    if not token:
        return None, 'invalid'
    try:
        payload = _serializer(_STATE_SALT).loads(token, max_age=ttl)
    except SignatureExpired:
        return None, 'expired'
    except BadSignature:
        return None, 'invalid'
    except Exception as exc:  # pragma: no cover - 防御性兜底
        logger.warning('[E10] 校验 state 失败: %s', exc)
        return None, 'invalid'
    if not isinstance(payload, dict):
        return None, 'invalid'
    return payload, None


def _ticket_cache_key(nonce: str) -> str:
    return f'e10:ticket:{nonce}'


def _store_ticket_nonce(nonce: str, user_id: str, ttl: int) -> None:
    try:
        cache.set(_ticket_cache_key(nonce), str(user_id), timeout=ttl)
        return
    except Exception as exc:
        logger.warning(
            '[E10] Redis 不可用，一次性票据退化为单进程内存存储（多进程部署请确保 Redis 可用）: %s',
            exc,
        )
    now = time.time()
    with _MEMORY_TICKETS_LOCK:
        for key in [k for k, (expires, _) in _MEMORY_TICKETS.items() if expires < now]:
            _MEMORY_TICKETS.pop(key, None)
        _MEMORY_TICKETS[nonce] = (now + ttl, str(user_id))


def _consume_ticket_nonce(nonce: str, user_id: str) -> bool:
    try:
        stored = cache.get(_ticket_cache_key(nonce))
        if stored is not None:
            cache.delete(_ticket_cache_key(nonce))
            return str(stored) == str(user_id)
    except Exception as exc:
        logger.warning('[E10] 读取/删除一次性票据失败，尝试内存存储: %s', exc)

    with _MEMORY_TICKETS_LOCK:
        entry = _MEMORY_TICKETS.pop(nonce, None)
    if entry and entry[0] >= time.time():
        return entry[1] == str(user_id)
    return False


def create_ticket(user: User, redirect: str, ttl: int, binding: str) -> str:
    """生成短时、一次性登录票据，避免把 JWT 暴露在浏览器地址栏。

    ``binding`` 会同时写入 HttpOnly Cookie，确保票据只能在发起回调的浏览器中兑换，
    防止攻击者把自己的 ticket 链接发给受害者造成登录 CSRF。
    """
    nonce = secrets.token_urlsafe(24)
    _store_ticket_nonce(nonce, str(user.id), ttl)
    payload = {
        'u': str(user.id),
        'r': sanitize_redirect(redirect),
        'n': nonce,
        'b': binding,
    }
    return _serializer(_TICKET_SALT).dumps(payload)


def consume_ticket(
    ticket: str,
    ttl: int,
    binding: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """校验并消费登录票据，返回 (result, error)。"""
    if not ticket:
        return None, 'e10_ticket_missing'
    try:
        payload = _serializer(_TICKET_SALT).loads(ticket, max_age=ttl)
    except SignatureExpired:
        return None, 'e10_ticket_invalid'
    except BadSignature:
        return None, 'e10_ticket_invalid'
    except Exception as exc:  # pragma: no cover - 防御性兜底
        logger.warning('[E10] 校验登录票据失败: %s', exc)
        return None, 'e10_ticket_invalid'

    if not isinstance(payload, dict):
        return None, 'e10_ticket_invalid'
    user_id = payload.get('u')
    nonce = payload.get('n')
    ticket_binding = payload.get('b')
    if not user_id or not nonce or not ticket_binding:
        return None, 'e10_ticket_invalid'

    # 绑定校验必须在消费 nonce 之前：错误的浏览器不能把合法票据“烧掉”
    if not binding or not hmac.compare_digest(str(ticket_binding), str(binding)):
        logger.warning('[E10] 登录票据绑定 Cookie 不匹配（可能是在不同浏览器打开回调链接）')
        return None, 'e10_ticket_invalid'

    if not _consume_ticket_nonce(str(nonce), str(user_id)):
        return None, 'e10_ticket_used'

    try:
        user_uuid = UUID(str(user_id))
    except (TypeError, ValueError):
        return None, 'e10_ticket_invalid'

    user = db.session.get(User, user_uuid)
    if user is None:
        return None, 'e10_user_not_provisioned'
    if not user.is_active():
        return None, 'e10_account_disabled'

    return {
        'user': user,
        'redirect': sanitize_redirect(payload.get('r')),
    }, None


# ----------------------------------------------------------------------
# 用户映射 / 自动开通
# ----------------------------------------------------------------------
class E10UserService:
    """把 E10 人员标识映射为 SmartTable User。"""

    @staticmethod
    def ensure_schema() -> None:
        """按需创建 E10 身份映射表（进程内只检查一次）。"""
        global _SCHEMA_READY
        if _SCHEMA_READY:
            return
        with _SCHEMA_LOCK:
            if _SCHEMA_READY:
                return
            E10Identity.ensure_schema()
            _SCHEMA_READY = True

    # ------------------------------------------------------------------
    # 字段解析
    # ------------------------------------------------------------------
    @staticmethod
    def resolve_email(profile: E10Profile, cfg: E10Config) -> Tuple[Optional[str], Optional[str]]:
        """
        解析 SmartTable 用户邮箱。

        优先级：
        1. E10 ``attributes`` 中的 email / mail（若 E10 返回）；
        2. ``profile.id`` 本身是邮箱（账号映射规则 = 电子邮箱）；
        3. ``E10_EMAIL_TEMPLATE``，支持 ``{id}``、``{job_num}``、``{username}``、
           ``{mobile}``、``{domain}`` 等占位符；
        4. ``E10_EMAIL_FALLBACK_TEMPLATE``；
        5. ``E10_EMAIL_DOMAIN``，等价于 ``{id}@<domain>``。

        对于「人员 id + 工号/手机号」这类映射，推荐：
        ``E10_EMAIL_TEMPLATE={job_num}@e10.local``
        ``E10_EMAIL_FALLBACK_TEMPLATE={id}@e10.local``
        """
        attributes = profile.attributes or {}
        value = _attr_value(attributes, *_ATTRIBUTE_ALIASES['email'])
        if value is not None:
            email = str(value).strip().lower()
            if E10UserService._is_valid_email(email):
                return email, None

        raw = (profile.id or '').strip()
        if not raw:
            return None, 'e10_email_not_configured'

        # E10 账号映射规则选择「电子邮箱」时，id 本身就是邮箱
        if '@' in raw:
            email = raw.lower()
            if E10UserService._is_valid_email(email):
                return email, None
            return None, 'e10_email_not_configured'

        templates = []
        if cfg.email_template.strip():
            templates.append(cfg.email_template.strip())
        if cfg.email_fallback_template.strip():
            templates.append(cfg.email_fallback_template.strip())
        if cfg.email_domain:
            templates.append('{id}@' + cfg.email_domain)
        if not templates:
            return None, 'e10_email_not_configured'

        values = _template_values(profile, cfg)
        for template in templates:
            email = _render_template(template, values).strip().lower()
            if E10UserService._is_valid_email(email):
                return email, None
        return None, 'e10_email_not_configured'

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        if not email or len(email) > 255 or ' ' in email:
            return False
        local, sep, domain = email.rpartition('@')
        return bool(sep and local and domain)

    @staticmethod
    def resolve_name(profile: E10Profile) -> Tuple[str, bool]:
        """
        解析显示名，返回 (name, 是否为 E10 明确返回的姓名)。

        优先使用 E10 自定义属性 ``username``（本环境已确认该字段为姓名）。
        若没有明确姓名，则回退到 id，但调用方不应拿这个回退值去覆盖已有用户的显示名。
        """
        value = _attr_value(profile.attributes or {}, *_ATTRIBUTE_ALIASES['username'])
        if value is not None:
            return str(value).strip()[:100], True
        return (profile.id or 'E10 User')[:100], False

    @staticmethod
    def resolve_avatar(profile: E10Profile) -> Optional[str]:
        value = _attr_value(profile.attributes or {}, *_ATTRIBUTE_ALIASES['avatar'])
        if value is not None:
            return str(value).strip()
        return None

    @staticmethod
    def _is_admin(profile: E10Profile, cfg: E10Config) -> bool:
        """管理员白名单支持 E10 人员 id，也支持工号（便于配置）。"""
        if not cfg.admin_ids:
            return False
        candidates = {str(profile.id)}
        job_num = _attr_value(profile.attributes or {}, *_ATTRIBUTE_ALIASES['job_num'])
        if job_num is not None:
            candidates.add(str(job_num).strip())
        return bool(candidates.intersection(cfg.admin_ids))

    @staticmethod
    def _role_for(profile: E10Profile, cfg: E10Config) -> UserRole:
        if E10UserService._is_admin(profile, cfg):
            return UserRole.ADMIN
        try:
            role = UserRole(cfg.default_role)
        except (TypeError, ValueError):
            logger.warning('[E10] 非法的 E10_DEFAULT_ROLE=%r，回退到 editor', cfg.default_role)
            return UserRole.EDITOR
        if role not in _AUTO_PROVISION_ROLES:
            logger.warning(
                '[E10] E10_DEFAULT_ROLE=%r 不允许用于自动开通，回退到 editor；'
                '管理员请使用 E10_ADMIN_IDS 显式指定',
                cfg.default_role,
            )
            return UserRole.EDITOR
        return role

    # ------------------------------------------------------------------
    # 用户解析
    # ------------------------------------------------------------------
    @classmethod
    def resolve_user(
        cls,
        profile: E10Profile,
        cfg: E10Config,
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        根据 E10 profile 查找/创建 SmartTable 用户。

        匹配顺序：
        1. ``e10_sso_identities`` 已绑定记录；
        2. 邮箱相同的既有 SmartTable 用户（E10_MATCH_BY_EMAIL，默认开启）；
        3. 自动开通新用户（E10_AUTO_CREATE_USERS，默认开启）。
        """
        cls.ensure_schema()

        identity = E10Identity.query.filter_by(e10_user_id=profile.id).first()
        user: Optional[User] = None
        if identity is not None:
            user = db.session.get(User, identity.user_id)
            if user is None:
                # 上游用户已被删除，清理失效绑定后重新映射
                db.session.delete(identity)
                db.session.commit()
                identity = None

        if user is None and cfg.match_by_email:
            email, email_error = cls.resolve_email(profile, cfg)
            if email_error:
                return None, email_error
            user = User.query.filter(func.lower(User.email) == email.lower()).first()

        if user is None:
            if not cfg.auto_create_users:
                return None, 'e10_user_not_provisioned'
            email, email_error = cls.resolve_email(profile, cfg)
            if email_error:
                return None, email_error
            user, create_error = cls._create_user(profile, cfg, email)
            if create_error:
                return None, create_error

        if user is None:
            return None, 'e10_user_not_provisioned'
        if not user.is_active():
            return None, 'e10_account_disabled'

        if identity is None:
            identity = E10Identity.query.filter_by(e10_user_id=profile.id).first()
        if identity is None:
            identity = E10Identity(
                e10_user_id=profile.id,
                user_id=user.id,
                e10_name=cls.resolve_name(profile)[0],
                attributes=profile.attributes or {},
            )
            db.session.add(identity)
            try:
                db.session.flush()
            except IntegrityError:
                # 并发首登：另一个请求已经完成绑定，回读即可
                db.session.rollback()
                identity = E10Identity.query.filter_by(e10_user_id=profile.id).first()
                if identity is None:
                    logger.exception('[E10] 绑定 E10 身份失败（并发冲突且回读为空）')
                    return None, 'e10_identity_binding_failed'

        now = datetime.now(timezone.utc)
        name, name_is_explicit = cls.resolve_name(profile)
        avatar = cls.resolve_avatar(profile)

        identity.e10_name = name
        identity.attributes = profile.attributes or {}
        identity.last_login_at = now

        if cfg.sync_profile:
            # 只有 E10 明确返回姓名时才同步，避免用登录名覆盖已有显示名
            if name_is_explicit and user.name != name:
                user.name = name
            if avatar and user.avatar != avatar:
                user.avatar = avatar

        # E10_ADMIN_IDS 是显式白名单：每次登录确保其为 admin（不会自动降级）
        if cls._is_admin(profile, cfg) and user.role != UserRole.ADMIN:
            user.role = UserRole.ADMIN

        user.last_login_at = now
        db.session.commit()
        return user, None

    @classmethod
    def _create_user(
        cls,
        profile: E10Profile,
        cfg: E10Config,
        email: str,
    ) -> Tuple[Optional[User], Optional[str]]:
        user = User(
            email=email,
            # E10 SSO 用户不需要本地密码；写入不可猜测的随机值
            password=secrets.token_urlsafe(32),
            name=cls.resolve_name(profile)[0],
            role=cls._role_for(profile, cfg),
            status=UserStatus.ACTIVE,
            email_verified=True,
        )
        avatar = cls.resolve_avatar(profile)
        if avatar:
            user.avatar = avatar

        db.session.add(user)
        try:
            db.session.flush()
        except IntegrityError:
            # 并发首登或邮箱已被其他请求创建
            db.session.rollback()
            existing = User.query.filter(func.lower(User.email) == email.lower()).first()
            if existing is None:
                logger.exception('[E10] 自动开通用户失败: email=%s', email)
                return None, 'e10_user_create_failed'
            return existing, None
        return user, None


def issue_login_payload(user: User) -> Dict[str, Any]:
    """签发 SmartTable JWT，返回与 /api/auth/login 一致的结构。"""
    tokens = AuthService.generate_tokens(str(user.id))
    return {
        'user': user.to_dict(include_email=True),
        'tokens': tokens,
    }
