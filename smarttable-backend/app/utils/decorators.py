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
_login_attempts = {}


def get_client_ip() -> str:
    """
    获取客户端 IP 地址
    支持代理服务器（X-Forwarded-For, X-Real-IP 等）
    
    Returns:
        客户端 IP 地址字符串
    """
    # 检查 X-Forwarded-For 头（代理服务器常用）
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        # X-Forwarded-For 可能包含多个 IP，取第一个（客户端真实 IP）
        ip = x_forwarded_for.split(',')[0].strip()
        if ip:
            return ip
    
    # 检查 X-Real-IP 头（Nginx 常用）
    x_real_ip = request.headers.get('X-Real-IP')
    if x_real_ip:
        return x_real_ip.strip()
    
    # 检查 Forwarded 头（RFC 7239 标准）
    forwarded = request.headers.get('Forwarded')
    if forwarded:
        # 解析 Forwarded: for=192.0.2.60;proto=http;by=203.0.113.43
        for part in forwarded.split(';'):
            if part.strip().startswith('for='):
                ip = part.split('=')[1].strip().strip('"[]')
                if ip:
                    return ip
    
    # 最后使用 remote_addr
    return request.remote_addr or 'unknown'


def get_user_agent() -> Optional[str]:
    """
    获取客户端 User-Agent 信息
    
    Returns:
        User-Agent 字符串，如果不存在则返回 None
    """
    return request.headers.get('User-Agent')


def capture_request_info() -> Dict[str, Any]:
    """
    捕获请求中的相关信息
    用于记录操作日志时的 old_value 和 new_value
    
    Returns:
        包含请求信息的字典：
        - method: 请求方法
        - path: 请求路径
        - query_params: 查询参数
        - json_data: JSON 请求体
        - form_data: 表单数据
        - view_args: 路由参数
    """
    info = {
        'method': request.method,
        'path': request.path,
        'query_params': dict(request.args),
        'view_args': dict(request.view_args) if request.view_args else {},
    }
    
    # 获取 JSON 数据
    if request.is_json:
        try:
            info['json_data'] = request.get_json(silent=True) or {}
        except Exception:
            info['json_data'] = {}
    
    # 获取表单数据
    if request.form:
        info['form_data'] = dict(request.form)
    
    return info


def authenticate(fn: Callable) -> Callable:
    """
    JWT 认证装饰器
    验证请求中的 JWT 令牌，并将当前用户设置到 g.current_user

    Args:
        fn: 被装饰的函数

    Returns:
        装饰后的函数
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            from uuid import UUID
            from app.models.user import User
            from flask import current_app

            # 检查 Authorization 头
            auth_header = request.headers.get('Authorization')
            current_app.logger.info(f'[JWT] Request method: {request.method}, Path: {request.path}')
            current_app.logger.info(f'[JWT] Authorization header: {auth_header[:50]}...' if auth_header and len(auth_header) > 50 else f'[JWT] Authorization header: {auth_header}')
            
            # 验证 JWT token
            verify_jwt_in_request()
            
            # 获取 token payload
            from flask_jwt_extended import get_jwt
            
            user_id = get_jwt_identity()
            current_app.logger.info(f'[JWT] User ID: {user_id}')

            # 将字符串 ID 转换为 UUID 对象
            uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id

            # 使用 filter_by 而不是 get，避免 SQLAlchemy 2.0 的兼容性问题
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


# 兼容别名：避免与 flask_jwt_extended.jwt_required 命名冲突
# 新代码应使用 @authenticate，旧代码的 @jwt_required 仍可正常工作
jwt_required = authenticate


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
                    from app.models.base import MemberRole
                    if not TableService.check_permission(str(table_id), user_id, MemberRole.VIEWER):
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


def operation_log(
    action: str,
    entity_type: str,
    entity_id_field: Optional[str] = None,
    capture_old_value: bool = False,
    capture_new_value: bool = True
) -> Callable:
    """
    操作日志装饰器
    自动记录管理员操作日志，包括用户 ID、操作类型、实体信息、IP 地址等
    
    使用示例:
        @admin_bp.route('/users/<user_id>', methods=['PUT'])
        @jwt_required
        @admin_required
        @operation_log(
            action='update',
            entity_type='user',
            entity_id_field='user_id',
            capture_old_value=True,
            capture_new_value=True
        )
        def update_user(user_id):
            # 视图函数代码
            return success_response(data=user_info)
    
    Args:
        action: 操作类型 (create, update, delete, suspend, activate 等)
        entity_type: 实体类型 (user, config, table, field 等)
        entity_id_field: 从路由参数或请求数据中获取 entity_id 的字段名
                        如果为 None，则尝试从 view_args 中获取
        capture_old_value: 是否捕获旧值（需要在 g 中预先设置 old_value）
        capture_new_value: 是否捕获新值（从视图函数的返回值中提取）
    
    Returns:
        装饰器函数
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from flask import current_app
            from app.models.log import OperationLog, AdminActionType, EntityType
            from uuid import UUID
            
            # 执行视图函数
            response = fn(*args, **kwargs)
            
            try:
                # 获取当前用户 ID
                user_id = g.get('current_user_id')
                if not user_id:
                    current_app.logger.warning('operation_log: 未找到当前用户 ID')
                    return response
                
                # 获取 entity_id
                entity_id = None
                if entity_id_field:
                    # 优先从路由参数获取
                    if entity_id_field in kwargs:
                        entity_id = kwargs[entity_id_field]
                    # 其次从 view_args 获取
                    elif request.view_args and entity_id_field in request.view_args:
                        entity_id = request.view_args[entity_id_field]
                    # 最后从请求数据获取
                    elif request.is_json:
                        data = request.get_json(silent=True)
                        if data and entity_id_field in data:
                            entity_id = data[entity_id_field]
                else:
                    # 尝试从 view_args 中获取常见的 ID 字段
                    for id_field in ['user_id', 'id', 'table_id', 'field_id', 'record_id']:
                        if request.view_args and id_field in request.view_args:
                            entity_id = request.view_args[id_field]
                            break
                
                # 获取旧值
                old_value = None
                if capture_old_value and hasattr(g, 'old_value'):
                    old_value = g.old_value
                
                # 获取新值
                new_value = None
                if capture_new_value and response:
                    try:
                        # 尝试从响应中获取 data 字段
                        if hasattr(response, 'get_json'):
                            response_data = response.get_json(silent=True)
                            if response_data and 'data' in response_data:
                                new_value = response_data['data']
                        elif isinstance(response, dict) and 'data' in response:
                            new_value = response['data']
                    except Exception:
                        pass
                
                # 获取 IP 地址和 User-Agent
                ip_address = get_client_ip()
                user_agent = get_user_agent()
                
                # 创建操作日志记录
                OperationLog.log(
                    user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=UUID(entity_id) if entity_id and isinstance(entity_id, str) else entity_id,
                    old_value=old_value,
                    new_value=new_value,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # 提交数据库会话
                from app.extensions import db
                db.session.commit()
                
                current_app.logger.info(
                    f'操作日志已记录：user_id={user_id}, action={action}, '
                    f'entity_type={entity_type}, entity_id={entity_id}'
                )
                
            except Exception as e:
                # 记录日志失败不影响主流程
                from app.extensions import db
                db.session.rollback()
                current_app.logger.error(f'记录操作日志失败：{str(e)}', exc_info=True)
            
            return response
        
        return wrapper
    return decorator


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


def validate_json(*required_fields: str) -> Callable:
    """
    JSON 数据验证装饰器
    检查请求是否包含 JSON 数据以及必需的字段
    
    Args:
        required_fields: 必需的字段名列表
        
    Returns:
        装饰器函数
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # 检查 Content-Type
            if not request.is_json:
                return error_response(
                    message='request_content_json_format',
                    code=415,
                    error='invalid_content_type'
                )
            
            data = request.get_json()
            
            # 检查必需字段
            missing_fields = [
                field for field in required_fields 
                if field not in data or data[field] is None
            ]
            
            if missing_fields:
                return error_response(
                    message=translate('missing_required_fields', ', '.join(missing_fields)),
                    code=400,
                    error='missing_required_fields'
                )
            
            return fn(*args, **kwargs)
        
        return wrapper
    return decorator


def rate_limit(max_attempts: int = 5, window: int = 900) -> Callable:
    """
    登录速率限制装饰器
    限制单位时间内的登录尝试次数，防止暴力破解
    
    Args:
        max_attempts: 最大尝试次数（默认 5 次）
        window: 时间窗口（秒，默认 15 分钟 = 900 秒）
        
    Returns:
        装饰器函数
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # 获取客户端标识（优先使用邮箱，其次使用 IP 地址）
            data = request.get_json() or {}
            identifier = data.get('email', '').lower().strip()
            
            if not identifier:
                # 如果没有邮箱，使用 IP 地址
                identifier = request.remote_addr or 'unknown'
            
            # 构建缓存键
            cache_key = f"login_attempts:{identifier}"
            lockout_key = f"login_lockout:{identifier}"
            
            # 检查是否处于锁定状态
            lockout_until = cache.get(lockout_key)
            if lockout_until:
                remaining_time = int(lockout_until - time.time())
                if remaining_time > 0:
                    minutes = remaining_time // 60
                    seconds = remaining_time % 60
                    return error_response(
                        message=translate('login_attempts_exceeded', minutes, seconds),
                        code=429,
                        error='too_many_requests'
                    )
                else:
                    # 锁定已过期，清除记录
                    cache.delete(lockout_key)
                    cache.delete(cache_key)
            
            # 获取当前尝试记录
            attempts = cache.get(cache_key) or {'count': 0, 'first_attempt': time.time()}
            
            # 检查时间窗口是否过期
            if time.time() - attempts['first_attempt'] > window:
                # 重置计数
                attempts = {'count': 0, 'first_attempt': time.time()}
            
            # 检查是否超过最大尝试次数
            if attempts['count'] >= max_attempts:
                # 设置锁定
                lockout_until = time.time() + window
                cache.set(lockout_key, lockout_until, timeout=window)
                minutes = window // 60
                return error_response(
                    message=translate('login_attempts_locked', minutes),
                    code=429,
                    error='too_many_requests'
                )
            
            # 将尝试记录存储到请求上下文，供视图函数更新
            g.login_attempts = attempts
            g.login_cache_key = cache_key
            g.login_lockout_key = lockout_key
            g.login_window = window
            g.max_attempts = max_attempts
            
            return fn(*args, **kwargs)
        
        return wrapper
    return decorator


def record_login_attempt(success: bool = False):
    """
    记录登录尝试结果
    在登录视图函数中调用此函数来记录成功或失败
    
    Args:
        success: 登录是否成功
    """
    if not hasattr(g, 'login_attempts'):
        return
    
    attempts = g.login_attempts
    cache_key = g.login_cache_key
    window = g.login_window
    
    if success:
        # 登录成功，清除尝试记录
        cache.delete(cache_key)
        if hasattr(g, 'login_lockout_key'):
            cache.delete(g.login_lockout_key)
    else:
        # 登录失败，增加计数
        attempts['count'] += 1
        cache.set(cache_key, attempts, timeout=window)


def clear_login_attempts(identifier: str):
    """
    清除指定标识的登录尝试记录
    
    Args:
        identifier: 用户邮箱或 IP 地址
    """
    cache_key = f"login_attempts:{identifier}"
    lockout_key = f"login_lockout:{identifier}"
    cache.delete(cache_key)
    cache.delete(lockout_key)


def api_rate_limit(
    max_requests: int = 100,
    window: int = 60,
    key_prefix: str = 'api',
    by_user: bool = True,
    by_ip: bool = True
) -> Callable:
    """
    通用 API 速率限制装饰器
    
    限制单位时间内的 API 请求次数，防止滥用和 DoS 攻击
    
    Args:
        max_requests: 最大请求数（默认 100 次）
        window: 时间窗口（秒，默认 60 秒）
        key_prefix: 缓存键前缀（用于区分不同类型的 API）
        by_user: 是否按用户限制（默认 True）
        by_ip: 是否按 IP 限制（默认 True）
        
    Returns:
        装饰器函数
        
    使用示例:
        @api_rate_limit(max_requests=50, window=60, key_prefix='query')
        def get_records():
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            identifiers = []
            
            # 按用户限制
            if by_user:
                try:
                    verify_jwt_in_request(optional=True)
                    user_id = get_jwt_identity()
                    if user_id:
                        identifiers.append(f"user:{user_id}")
                except:
                    pass
            
            # 按 IP 限制
            if by_ip:
                client_ip = get_client_ip()
                identifiers.append(f"ip:{client_ip}")
            
            # 如果没有任何标识符，使用 IP
            if not identifiers:
                identifiers.append(f"ip:{get_client_ip()}")
            
            current_time = time.time()
            # 收集各维度超限时需要等待的剩余时间，取最长（最严格）的提示给用户
            exceeded = False
            max_remaining = 0
            
            # 检查所有限制
            for identifier in identifiers:
                cache_key = f"rate_limit:{key_prefix}:{identifier}"
                
                # 获取当前请求计数
                request_data = cache.get(cache_key)
                
                if request_data is None:
                    # 首次请求
                    request_data = {
                        'count': 1,
                        'first_request': current_time
                    }
                    cache.set(cache_key, request_data, timeout=window)
                    continue
                
                first_request = request_data.get('first_request', current_time)
                # 防御：first_request 异常（时钟回拨/缓存跨进程时间戳错乱/反序列化异常）
                # 会导致 remaining 被放大成巨大值（如数千秒）。统一钳制到 [now - window, now]。
                if not isinstance(first_request, (int, float)) or first_request > current_time:
                    first_request = current_time
                elif current_time - first_request > window:
                    # 窗口已过期，重置计数
                    first_request = current_time
                    request_data['count'] = 0
                
                # 增加计数
                request_data['count'] = request_data.get('count', 0) + 1

                # 检查是否超过限制
                if request_data['count'] > max_requests:
                    exceeded = True
                    # 超限时立即把窗口起点重置为当前时间（滑动惩罚），
                    # 避免窗口从很久以前的第一次请求起算，导致剩余时间被拉长到数十分钟。
                    first_request = current_time
                    request_data['first_request'] = first_request
                    request_data['count'] = 0
                    # 剩余等待时间钳制在 [0, window]，避免返回过长（如数千秒）
                    remaining_time = int(window - (current_time - first_request))
                    remaining_time = max(0, min(window, remaining_time))
                    max_remaining = max(max_remaining, remaining_time)
                else:
                    request_data['first_request'] = first_request
                
                # 更新缓存（无论是否超限都更新，保证窗口结束自动清除）
                cache.set(cache_key, request_data, timeout=window)
            
            if exceeded:
                if max_remaining >= 60:
                    minutes = max_remaining // 60
                    seconds = max_remaining % 60
                    wait_text = f'{minutes} 分 {seconds} 秒' if seconds else f'{minutes} 分钟'
                else:
                    wait_text = f'{max_remaining} 秒'
                return error_response(
                    message=translate('request_too_frequent', wait_text),
                    code=429,
                    error='too_many_requests'
                )
            
            return fn(*args, **kwargs)
        
        return wrapper
    return decorator


def upload_rate_limit(
    max_uploads: int = 30,
    window: int = 300
) -> Callable:
    """
    文件上传速率限制装饰器
    
    限制单位时间内的文件上传次数，防止存储滥用
    
    Args:
        max_uploads: 最大上传次数（默认 30 次/5 分钟）
        window: 时间窗口（秒，默认 5 分钟 = 300 秒）
        
    Returns:
        装饰器函数
    """
    return api_rate_limit(
        max_requests=max_uploads,
        window=window,
        key_prefix='upload',
        by_user=True,
        by_ip=True
    )


def query_rate_limit(
    max_queries: int = 200,
    window: int = 60
) -> Callable:
    """
    数据查询速率限制装饰器
    
    限制单位时间内的数据查询次数，防止数据库过载
    
    Args:
        max_queries: 最大查询次数（默认 200 次/分钟）
        window: 时间窗口（秒，默认 60 秒）
        
    Returns:
        装饰器函数
    """
    return api_rate_limit(
        max_requests=max_queries,
        window=window,
        key_prefix='query',
        by_user=True,
        by_ip=True
    )


def write_rate_limit(
    max_writes: int = 100,
    window: int = 60
) -> Callable:
    """
    数据写入速率限制装饰器
    
    限制单位时间内的数据写入次数，防止恶意写入
    
    Args:
        max_writes: 最大写入次数（默认 100 次/分钟）
        window: 时间窗口（秒，默认 60 秒）
        
    Returns:
        装饰器函数
    """
    return api_rate_limit(
        max_requests=max_writes,
        window=window,
        key_prefix='write',
        by_user=True,
        by_ip=True
    )


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


def open_api_rate_limit(
    max_requests: int = 600,
    window: int = 60
) -> Callable:
    """
    开放 API 速率限制装饰器

    与用户 API 限流隔离：以应用身份（jwt identity = app_id）为维度，
    key_prefix='open'，防止第三方应用耗尽用户配额。

    使用示例：
        @open_api_bp.route('/records', methods=['GET'])
        @open_api_auth_required
        @open_api_rate_limit(max_requests=300, window=60)
        def list_records():
            ...
    """
    return api_rate_limit(
        max_requests=max_requests,
        window=window,
        key_prefix='open',
        by_user=True,
        by_ip=False
    )
