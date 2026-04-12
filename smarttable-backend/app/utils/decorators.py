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
                return unauthorized_response('用户不存在')

            if not user.is_active():
                current_app.logger.error(f'[JWT] User inactive: {user_id}')
                return unauthorized_response('用户账号已被禁用')

            g.current_user = user
            g.current_user_id = user_id

            return fn(*args, **kwargs)

        except Exception as e:
            from flask import current_app
            error_type = type(e).__name__
            error_msg = str(e)
            # 根据异常类型返回更具体的错误信息
            if 'No such table' in error_msg or 'OperationalError' in error_type:
                current_app.logger.error(f'[JWT] 数据库表不存在，请运行数据库迁移：{error_msg}', exc_info=True)
                return error_response('服务配置错误，请联系管理员', code=500)
            elif 'Signature verification' in error_msg or 'Signature' in error_msg:
                current_app.logger.error(f'[JWT] Token 签名验证失败：{error_msg}')
                return unauthorized_response('无效的认证令牌')
            elif 'ExpiredSignature' in error_msg:
                current_app.logger.error(f'[JWT] Token 已过期：{error_msg}')
                return unauthorized_response('认证令牌已过期，请重新登录')
            else:
                current_app.logger.error(f'[JWT] JWT 验证失败 [{error_type}]：{error_msg}', exc_info=True)
                return unauthorized_response('无效的认证令牌')

    return wrapper


# 兼容别名：避免与 flask_jwt_extended.jwt_required 命名冲突
# 新代码应使用 @authenticate，旧代码的 @jwt_required 仍可正常工作
jwt_required = authenticate


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
                return unauthorized_response('请先登录')
            
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
                return forbidden_response('权限不足，无法执行此操作')
            
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
            return unauthorized_response('请先登录')
        
        # 检查是否为管理员
        current_user_role = g.current_user.role
        current_role_value = current_user_role.value if hasattr(current_user_role, 'value') else current_user_role
        
        allowed_roles = ['admin', 'workspace_admin']
        if current_role_value not in allowed_roles:
            return forbidden_response('权限不足，无法执行此操作')
        
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
                return unauthorized_response('请先登录')
            
            # 管理员直接通过
            if g.current_user.is_admin():
                return fn(*args, **kwargs)
            
            # 获取资源所有者 ID
            owner_id = get_owner_id(*args, **kwargs)
            
            # 检查是否为所有者
            if str(g.current_user.id) != str(owner_id):
                return forbidden_response('只有资源所有者可以执行此操作')
            
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
                    message='请求内容必须是 JSON 格式',
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
                    message=f'缺少必需字段: {", ".join(missing_fields)}',
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
                        message=f'登录尝试次数过多，请 {minutes} 分 {seconds} 秒后再试',
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
                    message=f'登录尝试次数过多，账户已锁定 {minutes} 分钟',
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
