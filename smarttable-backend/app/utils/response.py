"""
统一响应格式模块
提供标准化的 API 响应格式
"""
from typing import Any, Optional, Dict, List
from flask import jsonify, Response


def success_response(
    data: Any = None,
    message: str = '操作成功',
    code: int = 200,
    meta: Optional[Dict] = None
) -> Response:
    """
    成功响应
    
    Args:
        data: 响应数据
        message: 成功消息
        code: HTTP 状态码
        meta: 元数据（如分页信息等）
        
    Returns:
        Flask Response 对象
    """
    response = {
        'success': True,
        'message': message,
        'data': data
    }
    
    if meta is not None:
        response['meta'] = meta
    
    return jsonify(response), code


def error_response(
    message: str = '操作失败',
    code: int = 400,
    error: Optional[str] = None,
    details: Optional[List[Dict]] = None
) -> Response:
    """
    错误响应
    
    Args:
        message: 错误消息
        code: HTTP 状态码
        error: 错误代码
        details: 详细错误信息列表
        
    Returns:
        Flask Response 对象
    """
    response = {
        'success': False,
        'message': message
    }
    
    if error is not None:
        response['error'] = error
    
    if details is not None:
        response['details'] = details
    
    return jsonify(response), code


def paginated_response(
    items: List[Any],
    total: int,
    page: int,
    per_page: int,
    message: str = '获取成功'
) -> Response:
    """
    分页响应
    
    Args:
        items: 当前页数据列表
        total: 总记录数
        page: 当前页码
        per_page: 每页数量
        message: 成功消息
        
    Returns:
        Flask Response 对象
    """
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    meta = {
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    }
    
    return success_response(
        data=items,
        message=message,
        meta=meta
    )


def validation_error_response(errors: Dict[str, List[str]]) -> Response:
    """
    验证错误响应
    
    Args:
        errors: 字段错误信息字典
        
    Returns:
        Flask Response 对象
    """
    details = [
        {
            'field': field,
            'message': messages[0] if isinstance(messages, list) else messages
        }
        for field, messages in errors.items()
    ]
    
    return error_response(
        message='数据验证失败',
        code=422,
        error='validation_error',
        details=details
    )


def not_found_response(resource: str = '资源') -> Response:
    """
    资源未找到响应
    
    Args:
        resource: 资源名称
        
    Returns:
        Flask Response 对象
    """
    return error_response(
        message=f'{resource}不存在',
        code=404,
        error='not_found'
    )


def unauthorized_response(message: str = '未授权访问') -> Response:
    """
    未授权响应
    
    Args:
        message: 错误消息
        
    Returns:
        Flask Response 对象
    """
    return error_response(
        message=message,
        code=401,
        error='unauthorized'
    )


def forbidden_response(message: str = '权限不足') -> Response:
    """
    禁止访问响应
    
    Args:
        message: 错误消息
        
    Returns:
        Flask Response 对象
    """
    return error_response(
        message=message,
        code=403,
        error='forbidden'
    )
