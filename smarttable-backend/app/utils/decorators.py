"""
装饰器模块
提供认证、权限检查、速率限制等装饰器
"""
import time
from functools import wraps
from typing import Callable, List, Optional, Union

from flask import request, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt

from app.extensions import cache
from app.utils.response import forbidden_response, unauthorized_response, error_response


# 登录失败记录存储（内存存储，生产环境建议使用 Redis）
_login_attempts = {}


def jwt_required(fn: Callable) -> Callable:
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
            current_app.logger.info(f'[JWT] Authorization header: {auth_header[:20] if auth_header else None}...')
            
            # 验证 JWT token
            verify_jwt_in_request()
            
            # 获取 token payload
            from flask_jwt_extended import get_jwt
            jwt_payload = get_jwt()
            current_app.logger.info(f'[JWT] Token payload: {jwt_payload}')
            
            user_id = get_jwt_identity()
            current_app.logger.info(f'[JWT] User ID: {user_id}')

            # 将字符串 ID 转换为 UUID 对象
            uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id

            # 使用 filter_by 而不是 get，避免 SQLAlchemy 2.0 的兼容性问题
            user = User.query.filter_by(id=uuid_id).first()
            current_app.logger.info(f'[JWT] User found: {user.email if user else None}')

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
            current_app.logger.error(f'[JWT] JWT 验证失败：{str(e)}', exc_info=True)
            return unauthorized_response(f'无效的认证令牌：{str(e)}')

    return wrapper


def role_required(roles):
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
    
    Args:
        fn: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    from app.models.user import UserRole
    return role_required([UserRole.ADMIN, UserRole.WORKSPACE_ADMIN])(fn)


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
