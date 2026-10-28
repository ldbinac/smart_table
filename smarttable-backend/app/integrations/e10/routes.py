"""
泛微 E10 OAuth2 单点登录路由。

端点（默认挂载在 ``/api/integrations/e10``）：
- GET  /config    前端读取开关与登录地址
- GET  /login     跳转到 E10 授权页
- GET  /callback  E10 回调（必须与 E10 注册的回调地址完全一致，且不能带 #）
- POST /exchange  前端用一次性票据换取 SmartTable JWT
- GET  /logout    注销 E10 会话并回到登录页
"""
from __future__ import annotations

import hmac
import logging
import secrets
from urllib.parse import urlencode

from flask import Blueprint, current_app, make_response, redirect, request, url_for

from app.utils.response import error_response, success_response

from .client import E10Client, E10OAuthError
from .config import E10Config
from .i18n import t
from .service import (
    E10UserService,
    build_frontend_target,
    consume_ticket,
    create_state,
    create_ticket,
    issue_login_payload,
    sanitize_redirect,
    verify_state,
)

logger = logging.getLogger(__name__)

e10_bp = Blueprint('e10_sso', __name__)
e10_bp.strict_slashes = False

_COOKIE_PATH = '/api/integrations/e10'


def _cookie_path() -> str:
    """兼容应用挂载在子路径（SCRIPT_NAME）下的部署。"""
    script_root = (request.script_root or '').rstrip('/')
    return f'{script_root}{_COOKIE_PATH}'


def _cfg() -> E10Config:
    cfg = current_app.extensions.get('e10_integration')
    if not isinstance(cfg, E10Config):
        cfg = E10Config.from_app(current_app)
        current_app.extensions['e10_integration'] = cfg
    return cfg


def _is_ready(cfg: E10Config) -> bool:
    return bool(cfg.enabled and cfg.ready)


def _clear_state_cookie(response, cfg: E10Config) -> None:
    response.delete_cookie(
        cfg.state_cookie_name,
        path=_cookie_path(),
        secure=cfg.should_use_secure_cookie(request),
        httponly=True,
        samesite=cfg.cookie_samesite,
    )


def _redirect_to_frontend(cfg: E10Config, path: str) -> str:
    base = cfg.resolve_frontend_base(request)
    return build_frontend_target(base, path)


def _error_redirect(cfg: E10Config, reason: str, upstream_code: str | None = None):
    """把错误带回前端回调页，由前端显示本地化提示。"""
    target = _redirect_to_frontend(cfg, '/e10-callback')
    if not target:
        return error_response(
            t('e10_internal_error'), code=503, error=reason
        )
    params = {'error': reason}
    if upstream_code:
        params['e10_code'] = upstream_code
    response = redirect(f'{target}?{urlencode(params)}')
    _clear_state_cookie(response, cfg)
    response.headers['Cache-Control'] = 'no-store'
    return response


def _not_ready_response(cfg: E10Config, *, as_redirect: bool):
    if not cfg.enabled:
        reason = 'e10_disabled'
        message = t('e10_sso_not_enabled')
        status = 404
    else:
        reason = 'e10_misconfigured'
        message = t('e10_sso_misconfigured')
        status = 503
    if as_redirect:
        return _error_redirect(cfg, reason)
    return error_response(message, code=status, error=reason)


@e10_bp.route('/config', methods=['GET'])
def get_config():
    """前端读取 E10 SSO 开关；不返回任何密钥。"""
    cfg = _cfg()
    ready = _is_ready(cfg)
    return success_response(
        data={
            'enabled': ready,
            'ready': cfg.ready,
            'provider_name': 'Weaver E10',
            'login_url': url_for('e10_sso.login') if ready else None,
            'logout_url': url_for('e10_sso.logout'),
            'logout_with_e10': bool(cfg.logout_with_e10),
            'password_login_enabled': bool(cfg.password_login_enabled),
            'auto_create_users': bool(cfg.auto_create_users),
        },
        message='fetch_success',
    )


@e10_bp.route('/login', methods=['GET'])
def login():
    """生成 state 并 302 到 E10 授权地址。"""
    cfg = _cfg()
    if not _is_ready(cfg):
        return _not_ready_response(cfg, as_redirect=True)

    redirect_target = sanitize_redirect(request.args.get('redirect'))
    callback_url = cfg.resolve_callback_url(request)
    if not callback_url:
        logger.error('[E10] 无法解析 callback 地址，请配置 E10_REDIRECT_URI 或 E10_PUBLIC_BASE_URL')
        return _error_redirect(cfg, 'e10_misconfigured')

    try:
        state = create_state(redirect_target, cfg.state_ttl)
    except Exception:
        logger.exception('[E10] 生成 OAuth state 失败')
        return _error_redirect(cfg, 'e10_misconfigured')

    client = E10Client(cfg)
    authorize_url = client.build_authorize_url(state, redirect_uri=callback_url)
    response = make_response(redirect(authorize_url, code=302))
    response.set_cookie(
        cfg.state_cookie_name,
        state,
        max_age=cfg.state_ttl,
        httponly=True,
        samesite=cfg.cookie_samesite,
        secure=cfg.should_use_secure_cookie(request),
        path=_cookie_path(),
    )
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@e10_bp.route('/callback', methods=['GET'])
def callback():
    """接收 E10 回调，换取用户信息并签发一次性登录票据。"""
    cfg = _cfg()
    if not _is_ready(cfg):
        return _not_ready_response(cfg, as_redirect=True)

    if request.args.get('error'):
        logger.warning('[E10] E10 授权页返回 error=%s', request.args.get('error'))
        return _error_redirect(cfg, 'e10_authorization_denied')

    code = (request.args.get('code') or '').strip()
    if not code:
        return _error_redirect(cfg, 'e10_code_missing')

    cookie_state = request.cookies.get(cfg.state_cookie_name) or ''
    query_state = (request.args.get('state') or '').strip()
    if not cookie_state:
        logger.warning('[E10] 回调缺少 state Cookie（可能被浏览器/代理丢弃）')
        return _error_redirect(cfg, 'e10_state_missing')
    if query_state and not hmac.compare_digest(query_state, cookie_state):
        logger.warning('[E10] 回调 state 与 Cookie 不一致')
        return _error_redirect(cfg, 'e10_state_mismatch')

    try:
        state_payload, state_error = verify_state(cookie_state, cfg.state_ttl)
    except Exception:
        logger.exception('[E10] 校验 OAuth state 失败')
        return _error_redirect(cfg, 'e10_misconfigured')

    if state_error:
        reason = 'e10_state_expired' if state_error == 'expired' else 'e10_state_invalid'
        return _error_redirect(cfg, reason)
    redirect_target = sanitize_redirect((state_payload or {}).get('r'))
    callback_url = cfg.resolve_callback_url(request)
    if not callback_url:
        logger.error('[E10] 回调时无法解析 callback 地址')
        return _error_redirect(cfg, 'e10_misconfigured')

    client = E10Client(cfg)
    try:
        token = client.exchange_code(code, redirect_uri=callback_url)
        profile = client.fetch_profile(token.access_token)
        user, user_error = E10UserService.resolve_user(profile, cfg)
        if user_error:
            logger.warning(
                '[E10] 用户映射失败: reason=%s, e10_id=%s',
                user_error,
                profile.id,
            )
            return _error_redirect(cfg, user_error)
        binding = secrets.token_urlsafe(24)
        ticket = create_ticket(
            user,
            redirect_target,
            cfg.ticket_ttl,
            binding=binding,
        )
        logger.info('[E10] SSO 登录成功: user_id=%s, e10_id=%s', user.id, profile.id)
    except E10OAuthError as exc:
        logger.warning('[E10] OAuth2 调用失败: %s', exc)
        return _error_redirect(cfg, exc.public_reason, exc.upstream_code)
    except Exception:
        logger.exception('[E10] 回调处理发生未预期异常')
        return _error_redirect(cfg, 'e10_internal_error')

    target = _redirect_to_frontend(cfg, '/e10-callback')
    if not target:
        logger.error('[E10] 无法解析前端地址，请配置 E10_FRONTEND_BASE_URL')
        return _error_redirect(cfg, 'e10_misconfigured')

    response = redirect(f'{target}?{urlencode({"ticket": ticket})}')
    _clear_state_cookie(response, cfg)
    response.set_cookie(
        cfg.binding_cookie_name,
        binding,
        max_age=cfg.ticket_ttl,
        httponly=True,
        samesite=cfg.cookie_samesite,
        secure=cfg.should_use_secure_cookie(request),
        path=_cookie_path(),
    )
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@e10_bp.route('/exchange', methods=['POST'])
def exchange():
    """用一次性票据换取 SmartTable JWT。"""
    cfg = _cfg()
    if not _is_ready(cfg):
        return _not_ready_response(cfg, as_redirect=False)

    data = request.get_json(silent=True) or {}
    ticket = data.get('ticket') or request.form.get('ticket')
    binding = request.cookies.get(cfg.binding_cookie_name) or ''
    result, error = consume_ticket(ticket, cfg.ticket_ttl, binding)
    if error or result is None:
        status = 401 if error in (
            'e10_ticket_missing',
            'e10_ticket_invalid',
            'e10_ticket_used',
        ) else 403
        return error_response(t(error or 'e10_ticket_invalid'), code=status, error=error)

    payload = issue_login_payload(result['user'])
    payload['redirect'] = result['redirect']
    # 不立即删除 binding Cookie：保留到 ticket TTL 结束，
    # 这样同一浏览器重放时能返回更准确的 e10_ticket_used（而不是 invalid）。
    return success_response(data=payload, message='login_success')


@e10_bp.route('/logout', methods=['GET'])
def logout():
    """注销 E10 会话（若启用），然后回到前端登录页。"""
    cfg = _cfg()
    if not _is_ready(cfg):
        return redirect(_redirect_to_frontend(cfg, '/login') or '/')

    if not cfg.logout_with_e10:
        return redirect(_redirect_to_frontend(cfg, '/login') or '/')

    redirect_path = sanitize_redirect(request.args.get('redirect'), '/login')
    service_url = cfg.logout_service or _redirect_to_frontend(cfg, redirect_path)
    if not service_url:
        return redirect('/')

    logout_url = E10Client(cfg).build_logout_url(service_url)
    response = redirect(logout_url)
    _clear_state_cookie(response, cfg)
    response.headers['Cache-Control'] = 'no-store'
    return response
