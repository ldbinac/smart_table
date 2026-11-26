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
from app.utils.decorators._utils import get_client_ip


# 登录失败记录存储（内存存储，生产环境建议使用 Redis）

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
            # 获取客户端标识（优先使用 email/username，其次 IP 地址）
            # 注意：对 GET / check-* 等不带 JSON body 的请求，必须加 silent=True
            # 否则 request.get_json() 会因 Content-Type 不匹配抛 415 UnsupportedMediaType
            data = request.get_json(silent=True) or {}
            identifier = (
                data.get('email', '')
                or data.get('username', '')
            ).lower().strip()
            
            client_ip = request.remote_addr or 'unknown'
            
            # 双重锁定策略：同时基于 identifier（用户名/邮箱）和 IP 地址限速
            # - identifier 维度：同一账号被连续尝试时锁定该账号
            # - IP 维度：同一 IP 短时间尝试大量不同账号时锁定该 IP
            # 两者独立计数，任一达到上限都会拒绝
            identifiers = []
            if identifier:
                identifiers.append(('id', identifier))
            identifiers.append(('ip', client_ip))
            
            lockout_triggered = False
            lockout_message = None
            
            # 检查所有标识是否处于锁定状态
            for key_type, ident in identifiers:
                lockout_key = f"login_lockout:{key_type}:{ident}"
                lockout_until = cache.get(lockout_key)
                if lockout_until:
                    remaining_time = int(lockout_until - time.time())
                    if remaining_time > 0:
                        minutes = remaining_time // 60
                        seconds = remaining_time % 60
                        lockout_triggered = True
                        lockout_message = translate('login_attempts_exceeded', minutes, seconds)
                    else:
                        cache.delete(lockout_key)
                        cache.delete(f"login_attempts:{key_type}:{ident}")
            
            if lockout_triggered:
                return error_response(
                    message=lockout_message,
                    code=429,
                    error='too_many_requests'
                )
            
            # 检查所有标识的尝试计数，任一超上限则锁定
            for key_type, ident in identifiers:
                cache_key = f"login_attempts:{key_type}:{ident}"
                attempts = cache.get(cache_key) or {'count': 0, 'first_attempt': time.time()}
                
                # 检查时间窗口是否过期
                if time.time() - attempts['first_attempt'] > window:
                    attempts = {'count': 0, 'first_attempt': time.time()}
                
                if attempts['count'] >= max_attempts:
                    lockout_key = f"login_lockout:{key_type}:{ident}"
                    lockout_until = time.time() + window
                    cache.set(lockout_key, lockout_until, timeout=window)
                    minutes = window // 60
                    return error_response(
                        message=translate('login_attempts_locked', minutes),
                        code=429,
                        error='too_many_requests'
                    )
            
            # 将两个标识都存储到请求上下文，供 record_login_attempt 统一更新
            g.login_attempt_keys = [
                (f"login_attempts:{kt}:{ident}", f"login_lockout:{kt}:{ident}")
                for kt, ident in identifiers
            ]
            g.login_window = window
            
            return fn(*args, **kwargs)
        
        return wrapper
    return decorator

def record_login_attempt(success: bool = False):
    """
    记录登录尝试结果（成功清除计数，失败 +1）
    同时更新 identifier 和 IP 两个维度的计数
    
    Args:
        success: 登录是否成功
    """
    if not hasattr(g, 'login_attempt_keys'):
        return
    
    window = getattr(g, 'login_window', 900)
    
    for cache_key, lockout_key in g.login_attempt_keys:
        if success:
            # 登录成功，清除尝试记录和锁定
            cache.delete(cache_key)
            cache.delete(lockout_key)
        else:
            # 登录失败，增加计数
            attempts = cache.get(cache_key) or {'count': 0, 'first_attempt': time.time()}
            
            # 检查时间窗口是否过期
            if time.time() - attempts['first_attempt'] > window:
                attempts = {'count': 0, 'first_attempt': time.time()}
            
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
