"""
统一响应格式模块
提供标准化的 API 响应格式
"""
from typing import Any, Optional, Dict, List
from flask import jsonify, Response

from app.i18n import translate


def success_response(
    data: Any = None,
    message: str = 'operation_success',
    code: int = 200,
    meta: Optional[Dict] = None
) -> Response:
    """
    成功响应
    
    Args:
        data: 响应数据
        message: 成功消息（i18n key 或原始文本，自动翻译）
        code: HTTP 状态码
        meta: 元数据（如分页信息等）
        
    Returns:
        Flask Response 对象
    """
    # 翻译 message：若 message 是 i18n key 则翻译，否则原样返回
    translated_message = translate(message)
    
    response = {
        'success': True,
        'message': translated_message,
        'data': data
    }
    
    if meta is not None:
        response['meta'] = meta
    
    return jsonify(response), code


def error_response(
    message: str = 'operation_failed',
    code: int = 400,
    error: Optional[str] = None,
    details: Optional[List[Dict]] = None,
    request_id: Optional[str] = None
) -> Response:
    """
    错误响应
    
    Args:
        message: 错误消息（i18n key 或原始文本，自动翻译）
        code: HTTP 状态码
        error: 错误代码
        details: 详细错误信息列表
        request_id: 请求追踪ID
        
    Returns:
        Flask Response 对象
    """
    # 翻译 message：若 message 是 i18n key 则翻译，否则原样返回
    translated_message = translate(message)
    
    response = {
        'success': False,
        'message': translated_message
    }
    
    if error is not None:
        response['error'] = error
    
    if details is not None:
        response['details'] = details
    
    if request_id is not None:
        response['request_id'] = request_id
    
    return jsonify(response), code


def created_response(
    data: Any = None,
    message: str = 'resource_created',
    code: int = 201
) -> Response:
    """
    创建资源成功响应（201）

    Args:
        data: 响应数据
        message: 成功消息（i18n key 或原始文本，自动翻译）
        code: HTTP 状态码

    Returns:
        Flask Response 对象
    """
    return success_response(data=data, message=message, code=code)


def conflict_response(message: str = 'conflict') -> Response:
    """
    资源冲突响应（409）

    Args:
        message: 错误消息（i18n key 或原始文本，自动翻译）

    Returns:
        Flask Response 对象
    """
    return error_response(message=message, code=409, error='conflict')


def server_error_response(message: str = 'server_error') -> Response:
    """
    服务器错误响应（500）

    Args:
        message: 错误消息（i18n key 或原始文本，自动翻译）

    Returns:
        Flask Response 对象
    """
    return error_response(message=message, code=500, error='server_error')


def paginated_response(
    items: List[Any],
    total: int,
    page: int,
    per_page: int,
    message: str = 'fetch_success'
) -> Response:
    """
    分页响应
    
    Args:
        items: 当前页数据列表
        total: 总记录数
        page: 当前页码
        per_page: 每页数量
        message: 成功消息（i18n key 或原始文本，自动翻译）
        
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
            'message': translate(messages[0] if isinstance(messages, list) else messages)
        }
        for field, messages in errors.items()
    ]
    
    return error_response(
        message='validation_error',
        code=422,
        error='validation_error',
        details=details
    )


def not_found_response(resource: str = 'resource_not_found') -> Response:
    """
    资源未找到响应
    
    Args:
        resource: 资源名称或 i18n key
        
    Returns:
        Flask Response 对象
    """
    return error_response(
        message=resource,
        code=404,
        error='not_found'
    )


def unauthorized_response(message: str = 'unauthorized_access') -> Response:
    """
    未授权响应
    
    Args:
        message: 错误消息（i18n key 或原始文本，自动翻译）
        
    Returns:
        Flask Response 对象
    """
    return error_response(
        message=message,
        code=401,
        error='unauthorized'
    )


def forbidden_response(message: str = 'forbidden') -> Response:
    """
    禁止访问响应

    Args:
        message: 错误消息（i18n key 或原始文本，自动翻译）

    Returns:
        Flask Response 对象
    """
    return error_response(
        message=message,
        code=403,
        error='forbidden'
    )


def bad_request_response(message: str = 'param_error') -> Response:
    """
    错误请求响应

    Args:
        message: 错误消息（i18n key 或原始文本，自动翻译）

    Returns:
        Flask Response 对象
    """
    return error_response(
        message=message,
        code=400,
        error='bad_request'
    )
