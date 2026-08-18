"""
第三方应用接入路由

- 公开令牌端点：POST /api/oauth/token（Client Credentials 模式）
- 管理员应用管理：/api/oauth/apps 下的 CRUD、密钥重置、令牌查看与撤销、审计日志

开放 API（数据访问）位于 routes/open_api.py，前缀 /api/open/v1。
"""
import uuid
from typing import Optional

from flask import Blueprint, request, jsonify, g

from app.utils.decorators import (
    authenticate,
    admin_required,
    api_rate_limit,
    operation_log,
)
from app.utils.response import (
    success_response,
    created_response,
    error_response,
    validation_error_response,
    not_found_response,
    unauthorized_response,
    forbidden_response,
)
from app.services.oauth_app_service import OAuthAppService
from app.models.base import Base
from app.i18n import translate as _

oauth_bp = Blueprint('oauth', __name__, url_prefix='/api/oauth')


# =========================================================================
# 公开令牌端点（无需用户登录）
# =========================================================================
@oauth_bp.route('/token', methods=['POST'])
@api_rate_limit(max_requests=60, window=60, key_prefix='oauth_token', by_ip=True)
def token():
    """
    OAuth2 令牌端点（Client Credentials 模式）

    请求（表单或 JSON）：
        grant_type = client_credentials（必填）
        client_id  = <应用 client_id>
        client_secret = <应用 client_secret>
        scope      = <可选，空格分隔，需为应用授予 scope 的子集>

    支持 Basic Auth（Authorization: Basic base64(client_id:client_secret））。

    成功响应（OAuth2 标准）：
        {
          "access_token": "<JWT>",
          "token_type": "Bearer",
          "expires_in": 7200,
          "scope": "record:read record:write"
        }
    """
    grant_type = (
        request.form.get('grant_type')
        or (request.json.get('grant_type') if request.is_json else None)
    )
    if grant_type != 'client_credentials':
        _audit_token_fail(None, 'unsupported_grant_type', '非 client_credentials grant')
        return _oauth_error('unsupported_grant_type', _('oauth_unsupported_grant'), 400)

    client_id, client_secret = _extract_client_credentials()
    if not client_id or not client_secret:
        _audit_token_fail(None, 'invalid_client', '缺少 client_id 或 client_secret')
        return _oauth_error('invalid_client', _('oauth_invalid_client'), 401)

    app = OAuthAppService.verify_secret(client_id, client_secret)
    if app is None:
        _audit_token_fail(client_id, 'invalid_client', '密钥校验失败')
        return _oauth_error('invalid_client', _('oauth_invalid_client'), 401)

    if not app.is_active:
        _audit_token_fail(client_id, 'invalid_client', '应用已停用')
        return _oauth_error('invalid_client', _('oauth_inactive_app'), 401)

    scope_param = (
        request.form.get('scope')
        or (request.json.get('scope') if request.is_json else None)
        or ''
    )
    requested_scopes = scope_param.split() if scope_param else None

    # 校验请求的 scope 是否超出授予范围
    if requested_scopes:
        granted = set(app.scopes.split()) if app.scopes else set()
        if not set(requested_scopes).issubset(granted):
            _audit_token_fail(client_id, 'invalid_scope', f'scope 越权: {" ".join(requested_scopes)}')
            return _oauth_error('invalid_scope', _('oauth_invalid_scope'), 403)

    access_token, token_record = OAuthAppService.issue_token(app, requested_scopes)
    expires_in = int((token_record.expires_at - token_record.created_at).total_seconds())

    return jsonify({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': expires_in,
        'scope': token_record.scope,
        'request_id': getattr(request, 'request_id', None),
    }), 200


def _extract_client_credentials():
    """从 Basic Auth 或 请求体 提取 client_id / client_secret"""
    client_id = None
    client_secret = None

    auth = request.authorization
    if auth and auth.type == 'basic':
        client_id = auth.username
        client_secret = auth.password
    else:
        if request.is_json:
            client_id = request.json.get('client_id')
            client_secret = request.json.get('client_secret')
        else:
            client_id = request.form.get('client_id')
            client_secret = request.form.get('client_secret')
    return client_id, client_secret


def _oauth_error(error_code: str, description: str, status: int):
    """返回 OAuth2 标准错误响应"""
    return jsonify({
        'error': error_code,
        'error_description': description,
        'request_id': getattr(request, 'request_id', None),
    }), status


def _audit_token_fail(client_id: Optional[str], error_code: str, detail: str):
    """记录令牌签发失败审计（仅当能定位到应用时才有意义；client_id 为空则跳过）"""
    if not client_id:
        return
    try:
        app = OAuthAppService.get_app_by_client_id(client_id)
        if app is None:
            return
        OAuthAppService.write_audit(
            app_id=str(app.id),
            action='token_fail',
            detail=f'{error_code}: {detail}',
            ip=request.remote_addr,
        )
    except Exception:
        pass


# =========================================================================
# 第三方应用管理（管理员）
# =========================================================================
@oauth_bp.route('/apps', methods=['GET'])
@authenticate
@admin_required
def list_apps():
    """列出第三方应用（管理员可见全部）"""
    apps = OAuthAppService.list_apps()
    # 批量查询授权 Base 名称映射，避免 N+1
    all_ids = {str(bid) for a in apps for bid in (a.allowed_bases or [])}
    base_names: dict = {}
    if all_ids:
        bases = Base.query.filter(Base.id.in_(all_ids)).all()
        base_names = {str(b.id): b.name for b in bases}
    return success_response(
        data=[a.to_dict(base_names=base_names) for a in apps],
        message='fetch_success'
    )


@oauth_bp.route('/bases', methods=['GET'])
@authenticate
@admin_required
def list_all_bases():
    """列出全部 Base（供应用授权范围多选使用，仅返回 id / name / owner 摘要）"""
    bases = Base.query.order_by(Base.created_at.desc()).all()
    data = [
        {
            'id': str(b.id),
            'name': getattr(b, 'name', None),
            'owner_id': str(b.owner_id) if b.owner_id else None,
        }
        for b in bases
    ]
    return success_response(data=data, message='fetch_success')


@oauth_bp.route('/apps', methods=['POST'])
@authenticate
@admin_required
@api_rate_limit(max_requests=20, window=60, key_prefix='oauth_app_create', by_user=True, by_ip=True)
@operation_log(action='create', entity_type='oauth_app', capture_new_value=False)
def create_app():
    """创建第三方应用"""
    data = request.get_json(silent=True) or {}
    app_name = (data.get('app_name') or '').strip()
    if not app_name:
        return validation_error_response(
            errors={'app_name': [_('oauth_app_name_required')]}
        )

    allowed_bases = data.get('allowed_bases') or []
    scopes = data.get('scopes') or []
    callback_url = data.get('callback_url')
    is_active = data.get('is_active', True)

    valid_bases = _validate_bases(allowed_bases)

    app, plain_secret = OAuthAppService.create_app(
        owner_id=g.current_user_id,
        app_name=app_name,
        allowed_bases=[str(b) for b in valid_bases],
        scopes=scopes,
        callback_url=callback_url,
        is_active=bool(is_active),
    )
    return created_response(
        data=app.to_dict(include_secret=True),
        message='oauth_app_created'
    )


@oauth_bp.route('/apps/<app_id>', methods=['GET'])
@authenticate
@admin_required
def get_app(app_id):
    """获取应用详情"""
    app = OAuthAppService.get_app(app_id)
    if app is None:
        return not_found_response(resource='oauth_app_not_found')
    return success_response(data=app.to_dict(), message='fetch_success')


@oauth_bp.route('/apps/<app_id>', methods=['PUT'])
@authenticate
@admin_required
@api_rate_limit(max_requests=30, window=60, key_prefix='oauth_app_update', by_user=True, by_ip=True)
@operation_log(action='update', entity_type='oauth_app', entity_id_field='app_id')
def update_app(app_id):
    """更新应用配置"""
    app = OAuthAppService.get_app(app_id)
    if app is None:
        return not_found_response(resource='oauth_app_not_found')

    data = request.get_json(silent=True) or {}
    allowed_bases = data.get('allowed_bases')
    if allowed_bases is not None:
        allowed_bases = [str(b) for b in _validate_bases(allowed_bases)]

    updated = OAuthAppService.update_app(
        app_id=app_id,
        app_name=data.get('app_name'),
        callback_url=data.get('callback_url'),
        allowed_bases=allowed_bases,
        scopes=data.get('scopes'),
        is_active=data.get('is_active'),
    )
    return success_response(
        data=updated.to_dict(),
        message='oauth_app_updated'
    )


@oauth_bp.route('/apps/<app_id>', methods=['DELETE'])
@authenticate
@admin_required
@operation_log(action='delete', entity_type='oauth_app', entity_id_field='app_id')
def delete_app(app_id):
    """删除应用（级联撤销令牌）"""
    ok = OAuthAppService.delete_app(app_id)
    if not ok:
        return not_found_response(resource='oauth_app_not_found')
    return success_response(message='oauth_app_deleted')


@oauth_bp.route('/apps/<app_id>/reset-secret', methods=['POST'])
@authenticate
@admin_required
@api_rate_limit(max_requests=10, window=60, key_prefix='oauth_secret_reset', by_user=True, by_ip=True)
@operation_log(action='reset_secret', entity_type='oauth_app', entity_id_field='app_id', capture_new_value=False)
def reset_secret(app_id):
    """重置 client_secret（旧密钥立即失效）"""
    result = OAuthAppService.reset_secret(app_id)
    if result is None:
        return not_found_response(resource='oauth_app_not_found')
    app, plain_secret = result
    return success_response(
        data=app.to_dict(include_secret=True),
        message='oauth_secret_reset'
    )


@oauth_bp.route('/apps/<app_id>/tokens', methods=['GET'])
@authenticate
@admin_required
def list_app_tokens(app_id):
    """查看应用已颁发的令牌（不含明文）"""
    app = OAuthAppService.get_app(app_id)
    if app is None:
        return not_found_response(resource='oauth_app_not_found')
    tokens = OAuthAppService.list_app_tokens(app_id, include_revoked=True)
    return success_response(
        data=[t.to_dict() for t in tokens],
        message='fetch_success'
    )


@oauth_bp.route('/apps/<app_id>/tokens/revoke', methods=['POST'])
@authenticate
@admin_required
@operation_log(action='revoke_tokens', entity_type='oauth_app', entity_id_field='app_id')
def revoke_app_tokens(app_id):
    """撤销应用令牌：指定 jti 撤销单个，否则撤销全部未过期令牌"""
    app = OAuthAppService.get_app(app_id)
    if app is None:
        return not_found_response(resource='oauth_app_not_found')

    data = request.get_json(silent=True) or {}
    jti = data.get('jti')
    if jti:
        ok = OAuthAppService.revoke_token_by_jti(jti)
        if not ok:
            return not_found_response(resource='oauth_token_revoked')
        return success_response(message='oauth_token_revoked')
    else:
        count = OAuthAppService.revoke_all_app_tokens(app_id)
        return success_response(
            data={'revoked': count},
            message='oauth_token_revoked'
        )


@oauth_bp.route('/apps/<app_id>/audit', methods=['GET'])
@authenticate
@admin_required
def app_audit(app_id):
    """查看应用审计日志"""
    app = OAuthAppService.get_app(app_id)
    if app is None:
        return not_found_response(resource='oauth_app_not_found')
    logs = OAuthAppService.list_audit_logs(app_id=app_id, limit=200)
    return success_response(
        data=[log.to_dict() for log in logs],
        message='fetch_success'
    )


def _validate_bases(base_ids):
    """校验 base_ids 是否真实存在，返回有效的 Base id 列表"""
    valid = []
    for bid in base_ids:
        try:
            b = Base.query.get(uuid.UUID(str(bid)))
        except (ValueError, TypeError):
            b = None
        if b is not None:
            valid.append(str(bid))
    return valid
