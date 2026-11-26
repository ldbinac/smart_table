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
