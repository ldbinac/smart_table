"""
装饰器模块
提供认证、权限检查、速率限制、操作日志等装饰器
"""
import json
import time
from functools import wraps
from typing import Callable, List, Optional, Union, Any, Dict

from flask import request, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt

from app.i18n import translate
from app.extensions import cache
from app.utils.response import forbidden_response, unauthorized_response, error_response


# 登录失败记录存储（内存存储，生产环境建议使用 Redis）

def authenticate(fn: Callable) -> Callable:
    """
    统一认证装饰器
    优先验证系统 JWT；若 JWT 缺失或无效，则尝试验证应用级会话 Token。
    应用级会话验证通过后，将当前用户设置到 g.current_user，并标记 g.is_app_session=True，
    使得所有现有数据接口（/bases/*、/tables/*、/records/* 等）在应用独立运行时模式下可直接使用。

    Args:
        fn: 被装饰的函数

    Returns:
        装饰后的函数
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from uuid import UUID
        from app.models.user import User
        try:
            from app.services.application_auth_service import ApplicationAuthService
        except ImportError:
            ApplicationAuthService = None
        from flask import current_app
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

        auth_header = request.headers.get('Authorization')
        current_app.logger.info(
            f'[Auth] Request method: {request.method}, Path: {request.path}'
        )
        current_app.logger.info(
            f'[Auth] Authorization header: {auth_header[:50]}...'
            if auth_header and len(auth_header) > 50
            else f'[Auth] Authorization header: {auth_header}'
        )

        jwt_authenticated = False
        try:
            # 1) 优先尝试系统 JWT 认证（仅当存在 Authorization: Bearer 时）
            if auth_header and auth_header.startswith('Bearer '):
                try:
                    verify_jwt_in_request()
                    user_id = get_jwt_identity()
                    uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id
                    user = User.query.filter_by(id=uuid_id).first()
                    if not user:
                        current_app.logger.error(f'[Auth] JWT user not found: {user_id}')
                        return unauthorized_response('用户不存在')
                    if not user.is_active():
                        current_app.logger.error(f'[Auth] JWT user inactive: {user_id}')
                        return unauthorized_response('用户账号已被禁用')

                    g.current_user = user
                    g.current_user_id = user_id
                    g.user_id = user_id  # 兼容性别名
                    jwt_authenticated = True
                    current_app.logger.info(f'[Auth] JWT authenticated: {user_id}')
                except Exception as e:
                    # JWT 验证失败时继续尝试应用级会话，不要立即返回 401
                    current_app.logger.info(
                        f'[Auth] JWT validation failed, will try app session: {str(e)}'
                    )

            # 2) JWT 未通过时，尝试应用级会话 Token
            if not jwt_authenticated:
                session_token = ApplicationAuthService.extract_session_token_from_header()
                if not session_token:
                    current_app.logger.error('[Auth] 缺少认证令牌')
                    return unauthorized_response('缺少认证令牌')

                session_info, error = ApplicationAuthService.validate_application_session(
                    session_token
                )
                if error:
                    current_app.logger.error(f'[Auth] 应用级会话验证失败：{error}')
                    return unauthorized_response(error)

                user_id = session_info.get('user', {}).get('id')
                if not user_id:
                    return unauthorized_response('无效的会话信息')

                uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id
                user = User.query.filter_by(id=uuid_id).first()
                if not user:
                    current_app.logger.error(f'[JWT] User not found: {user_id}')
                    return unauthorized_response('user_does_not_exist')

                if not user.is_active():
                    current_app.logger.error(f'[JWT] User inactive: {user_id}')
                    return unauthorized_response('user_account_disabled')

                g.current_user = user
                g.current_user_id = user_id
                g.user_id = user_id  # 兼容性别名
                g.is_app_session = True
                g.app_session = session_info
                current_app.logger.info(f'[Auth] App session authenticated: {user_id}')
        except Exception as e:
            from flask import current_app
            error_type = type(e).__name__
            error_msg = str(e)
            # 根据异常类型返回更具体的错误信息
            if 'No such table' in error_msg or 'OperationalError' in error_type:
                current_app.logger.error(f'[JWT] 数据库表不存在，请运行数据库迁移：{error_msg}', exc_info=True)
                return error_response('service_configuration_error_contact_administrator', code=500)
            elif 'Signature verification' in error_msg or 'Signature' in error_msg:
                current_app.logger.error(f'[JWT] Token 签名验证失败：{error_msg}')
                return unauthorized_response('invalid_authentication_token')
            elif 'ExpiredSignature' in error_msg:
                current_app.logger.error(f'[JWT] Token 已过期：{error_msg}')
                return unauthorized_response('authentication_token_expired_log_again')
            else:
                current_app.logger.error(f'[JWT] JWT 验证失败 [{error_type}]：{error_msg}', exc_info=True)
                return unauthorized_response('invalid_authentication_token')

        # 视图函数在 try/except 块之外执行，
        # 避免视图函数中的非 JWT 相关异常被错误地当作 401 返回
        return fn(*args, **kwargs)

    return wrapper

jwt_required = authenticate

def app_session_required(fn: Callable) -> Callable:
    """
    应用级会话认证装饰器
    验证请求头中的 Application-Token（或 Authorization Bearer），
    并将当前应用会话信息设置到 g.app_session 和 g.current_user_id。

    与系统 JWT 认证完全隔离，用于 /application/:appId/runtime 等独立运行时端点。
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            from app.services.application_auth_service import ApplicationAuthService
        except ImportError:
            ApplicationAuthService = None

        session_token = ApplicationAuthService.extract_session_token_from_header()
        if not session_token:
            return unauthorized_response('missing_app_session_token')

        session_info, error = ApplicationAuthService.validate_application_session(session_token)
        if error:
            return unauthorized_response(error)

        # 将会话信息写入请求上下文，供视图函数使用
        g.app_session = session_info
        g.current_user_id = session_info.get('user', {}).get('id') if session_info.get('user') else None

        return fn(*args, **kwargs)

    return wrapper

def form_share_or_jwt(table_param: str = 'table_id', require_role: Optional[List[str]] = None) -> Callable:
    """
    JWT 或表单分享 token 双通道认证装饰器。

    - 已登录用户：走原有权限校验（require_role 走全局角色校验，否则走表格 VIEWER 权限校验）。
    - 匿名用户：必须携带有效且未过期的表单分享 token，且该 token 允许访问目标表
      （表单所在表或同 base 表），用于匿名分享表单的只读接口（字段、可关联记录等）。
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            table_id = kwargs.get(table_param) or (request.view_args or {}).get(table_param)
            user_id = None
            try:
                verify_jwt_in_request(optional=True)
                identity = get_jwt_identity()
                if identity:
                    user_id = str(identity)
                    from app.models.user import User
                    from uuid import UUID
                    try:
                        g.current_user = User.query.filter_by(id=UUID(user_id)).first()
                        g.current_user_id = user_id
                    except Exception:
                        g.current_user = None
            except Exception:
                user_id = None
                g.current_user = None

            if user_id:
                if require_role:
                    from app.models.user import UserRole
                    if not getattr(g, 'current_user', None):
                        return unauthorized_response('log_first')
                    allowed = []
                    for r in require_role:
                        try:
                            allowed.append(UserRole(r).value)
                        except ValueError:
                            allowed.append(r)
                    cur = g.current_user.role
                    cur_val = cur.value if hasattr(cur, 'value') else cur
                    if cur_val not in allowed:
                        return forbidden_response('insufficient_permissions_perform_operation')
                else:
                    from app.services.table_service import TableService
                    from app.services.table_share_service import TableShareService
                    from app.models.base import MemberRole
                    # Base 成员按原有逻辑校验；纯表分享用户命中该表的分享角色时放行（仅限被授权的表）
                    if not TableService.check_permission(str(table_id), user_id, MemberRole.VIEWER) \
                            and TableShareService.get_members_role(str(table_id), user_id) is None:
                        return forbidden_response('no_permission_access_table_2')
                return fn(*args, **kwargs)

            # 匿名：需有效分享 token 且允许访问该表
            share_token = request.args.get('share_token')
            if not share_token:
                return unauthorized_response('authentication_required')
            from app.services.form_share_service import FormShareService
            ok, err = FormShareService.verify_share_access_to_table(share_token, str(table_id))
            if not ok:
                return unauthorized_response(err or 'invalid_form_share_token')
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def role_required(roles) -> Callable:
    """
    角色权限检查装饰器
    检查当前用户是否具有指定角色
    
    Args:
        roles: 允许的角色或角色列表（可以是字符串或 UserRole 枚举）
        
    Returns:
        装饰器函数
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from app.models.user import UserRole
            
            if not hasattr(g, 'current_user') or g.current_user is None:
                return unauthorized_response('log_first')
            
            # 标准化角色列表（支持字符串和 UserRole 枚举）
            if isinstance(roles, list):
                allowed_roles = []
                for r in roles:
                    if isinstance(r, str):
                        # 如果是字符串，尝试转换为 UserRole 枚举
                        try:
                            allowed_roles.append(UserRole(r))
                        except ValueError:
                            # 如果转换失败，直接使用字符串
                            allowed_roles.append(r)
                    else:
                        allowed_roles.append(r)
            else:
                # 单个角色
                if isinstance(roles, str):
                    try:
                        allowed_roles = [UserRole(roles)]
                    except ValueError:
                        allowed_roles = [roles]
                else:
                    allowed_roles = [roles]
            
            # 获取允许的角色值列表
            allowed_role_values = []
            for r in allowed_roles:
                if hasattr(r, 'value'):
                    allowed_role_values.append(r.value)
                else:
                    allowed_role_values.append(r)
            
            # 检查用户角色
            current_user_role = g.current_user.role
            current_role_value = current_user_role.value if hasattr(current_user_role, 'value') else current_user_role
            
            if current_role_value not in allowed_role_values:
                return forbidden_response('insufficient_permissions_perform_operation')
            
            return fn(*args, **kwargs)
        
        return wrapper
    return decorator

def admin_required(fn: Callable) -> Callable:
    """
    管理员权限装饰器
    快捷方式，仅允许管理员访问
    同时记录管理员访问日志
    
    Args:
        fn: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from flask import current_app
        from app.models.log import OperationLog, AdminActionType
        from uuid import UUID
        
        # 先执行角色检查
        from app.models.user import UserRole
        
        if not hasattr(g, 'current_user') or g.current_user is None:
            return unauthorized_response('log_first')
        
        # 检查是否为管理员
        current_user_role = g.current_user.role
        current_role_value = current_user_role.value if hasattr(current_user_role, 'value') else current_user_role
        
        allowed_roles = ['admin', 'workspace_admin']
        if current_role_value not in allowed_roles:
            return forbidden_response('insufficient_permissions_perform_operation')
        
        # 记录管理员访问日志（仅记录访问，不记录具体操作）
        try:
            user_id = g.get('current_user_id')
            if user_id:
                OperationLog.log(
                    user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
                    action=AdminActionType.LOGIN.value,  # 使用 LOGIN 表示访问
                    entity_type='system',
                    entity_id=None,
                    ip_address=get_client_ip(),
                    user_agent=get_user_agent()
                )
                from app.extensions import db
                db.session.commit()
        except Exception as e:
            from app.extensions import db
            db.session.rollback()
            current_app.logger.error(f'记录管理员访问日志失败：{str(e)}')
        
        return fn(*args, **kwargs)
    
    return wrapper

def owner_or_admin_required(get_owner_id: Callable) -> Callable:
    """
    所有者或管理员权限装饰器
    检查当前用户是否是资源所有者或管理员
    
    Args:
        get_owner_id: 获取资源所有者 ID 的函数
        
    Returns:
        装饰器函数
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # 确保已经通过 JWT 认证
            if not hasattr(g, 'current_user') or g.current_user is None:
                return unauthorized_response('log_first')
            
            # 管理员直接通过
            if g.current_user.is_admin():
                return fn(*args, **kwargs)
            
            # 获取资源所有者 ID
            owner_id = get_owner_id(*args, **kwargs)
            
            # 检查是否为所有者
            if str(g.current_user.id) != str(owner_id):
                return forbidden_response('resource_owner_perform_operation')
            
            return fn(*args, **kwargs)
        
        return wrapper
    return decorator

def open_api_auth_required(fn: Callable) -> Callable:
    """
    开放 API（第三方应用）认证装饰器

    校验 OAuth2 客户端凭证签发的 JWT（携带 app_id / scope / client_id），
    加载 OAuthApp 并校验 `is_active`，在 g 上设置：
        - g.oauth_app: OAuthApp 实例
        - g.oauth_app_id: 应用 id（str）
        - g.oauth_scopes: scope 列表（list[str]）
        - g.is_service_account: True

    注意：该装饰器不依赖 g.current_user（用户认证），仅用于应用身份。
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from flask import current_app
        from app.models.oauth_app import OAuthApp

        try:
            verify_jwt_in_request()
            claims = get_jwt()
        except Exception as e:
            current_app.logger.error(f'[OpenAPI] JWT 验证失败：{str(e)}')
            return unauthorized_response('invalid_access_token')

        app_id = claims.get('app_id') or claims.get('sub')
        if not app_id:
            return unauthorized_response('token_missing_application_identity_information')

        if claims.get('token_type') != 'app':
            # 仅接受开放 API 签发（应用身份）的令牌，拒绝用户令牌
            return forbidden_response('token_not_applicable_open_api')

        try:
            from uuid import UUID
            app = OAuthApp.query.get(UUID(str(app_id)))
        except (ValueError, TypeError):
            app = None

        if app is None:
            return unauthorized_response('application_does_not_exist_been_deleted')
        if not app.is_active:
            return forbidden_response('application_been_disabled')

        # 同步令牌中的 scope 与库中授予的 scope
        token_scopes = (claims.get('scope') or '').split()
        granted_scopes = app.scopes.split() if app.scopes else []
        effective_scopes = [s for s in token_scopes if s in granted_scopes]

        g.oauth_app = app
        g.oauth_app_id = str(app.id)
        g.oauth_scopes = effective_scopes
        g.is_service_account = True

        return fn(*args, **kwargs)

    return wrapper

def require_open_scope(*required_scopes: str) -> Callable:
    """
    开放 API scope 校验装饰器

    校验 g.oauth_scopes 是否包含所需的全部 scope，否则返回 403。
    必须在 @open_api_auth_required 之后使用。

    使用示例：
        @open_api_bp.route('/records', methods=['POST'])
        @open_api_auth_required
        @require_open_scope('record:write')
        def create_record():
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            scopes = getattr(g, 'oauth_scopes', None) or []
            missing = [s for s in required_scopes if s not in scopes]
            if missing:
                return forbidden_response(
                    translate('missing_required_scope', ', '.join(missing))
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator
