"""
错误处理器模块
集中处理应用中的各种错误
"""
import traceback
from flask import Flask, request, g
from werkzeug.exceptions import (
    BadRequest,
    Unauthorized,
    Forbidden,
    NotFound,
    MethodNotAllowed,
    InternalServerError,
    HTTPException
)
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError as MarshmallowValidationError

from app.utils.response import error_response


def _log_error_with_context(app, error, error_code=None):
    """
    记录包含完整上下文的错误日志
    
    Args:
        app: Flask 应用实例
        error: 异常对象
        error_code: 错误代码（可选）
    """
    # 获取请求 ID
    request_id = getattr(g, 'request_id', None)
    
    # 获取用户 ID（如果已认证）
    user_id = None
    try:
        from flask_jwt_extended import get_jwt_identity
        user_id = get_jwt_identity()
    except Exception:
        pass
    
    # 获取请求信息
    request_info = {
        'method': request.method,
        'path': request.path,
        'remote_addr': request.remote_addr,
        'user_agent': request.user_agent.string if request.user_agent else None
    }
    
    # 构建日志消息
    log_msg = f"[{request_id}] Request: {request_info['method']} {request_info['path']}"
    if user_id:
        log_msg += f" | User: {user_id}"
    log_msg += f" | Error: {type(error).__name__}: {str(error)}"
    
    # 记录错误（包含堆栈）
    app.logger.error(log_msg)
    app.logger.error(f"[{request_id}] Stack trace:\n{traceback.format_exc()}")
    
    return request_id


class APIError(Exception):
    """
    API 错误基类
    
    属性:
        message: 错误消息
        code: HTTP 状态码
        error: 错误代码
        details: 详细错误信息
    """
    
    def __init__(
        self,
        message: str = '操作失败',
        code: int = 400,
        error: str = None,
        details: list = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.error = error or 'api_error'
        self.details = details or []


class ValidationError(APIError):
    """数据验证错误"""
    
    def __init__(self, message: str = '数据验证失败', details: list = None):
        super().__init__(
            message=message,
            code=422,
            error='validation_error',
            details=details
        )


class ResourceNotFoundError(APIError):
    """资源未找到错误"""
    
    def __init__(self, resource: str = '资源'):
        super().__init__(
            message=f'{resource}不存在',
            code=404,
            error='not_found'
        )


class PermissionDeniedError(APIError):
    """权限不足错误"""
    
    def __init__(self, message: str = '权限不足'):
        super().__init__(
            message=message,
            code=403,
            error='permission_denied'
        )


class ConflictError(APIError):
    """资源冲突错误"""
    
    def __init__(self, message: str = '资源冲突'):
        super().__init__(
            message=message,
            code=409,
            error='conflict'
        )


def register_handlers(app: Flask) -> None:
    """
    注册所有错误处理器到 Flask 应用
    
    Args:
        app: Flask 应用实例
    """
    
    # 400 - 错误请求
    @app.errorhandler(BadRequest)
    def handle_bad_request(error):
        """处理错误请求"""
        request_id = getattr(g, 'request_id', None)
        app.logger.warning(f"[{request_id}] Bad request: {str(error)}")
        return error_response(
            message='请求格式错误',
            code=400,
            error='bad_request',
            request_id=request_id
        )
    
    # 401 - 未授权
    @app.errorhandler(Unauthorized)
    def handle_unauthorized(error):
        """处理未授权请求"""
        request_id = getattr(g, 'request_id', None)
        return error_response(
            message='请先登录',
            code=401,
            error='unauthorized',
            request_id=request_id
        )
    
    # 403 - 禁止访问
    @app.errorhandler(Forbidden)
    def handle_forbidden(error):
        """处理禁止访问请求"""
        request_id = getattr(g, 'request_id', None)
        return error_response(
            message='权限不足',
            code=403,
            error='forbidden',
            request_id=request_id
        )
    
    # 404 - 未找到
    @app.errorhandler(NotFound)
    def handle_not_found(error):
        """处理资源未找到"""
        request_id = getattr(g, 'request_id', None)
        if request.path.startswith('/api/'):
            return error_response(
                message='请求的资源不存在',
                code=404,
                error='not_found',
                request_id=request_id
            )
        # 非 API 路由返回 HTML 404
        return error
    
    # 405 - 方法不允许
    @app.errorhandler(MethodNotAllowed)
    def handle_method_not_allowed(error):
        """处理方法不允许"""
        request_id = getattr(g, 'request_id', None)
        return error_response(
            message=f'不支持的请求方法: {request.method}',
            code=405,
            error='method_not_allowed',
            request_id=request_id
        )
    
    # 422 - 验证错误（Marshmallow）
    @app.errorhandler(MarshmallowValidationError)
    def handle_validation_error(error):
        """处理数据验证错误"""
        request_id = getattr(g, 'request_id', None)
        details = [
            {'field': field, 'message': msgs[0] if isinstance(msgs, list) else msgs}
            for field, msgs in error.messages.items()
        ]
        return error_response(
            message='数据验证失败',
            code=422,
            error='validation_error',
            details=details,
            request_id=request_id
        )
    
    # 自定义 API 错误
    @app.errorhandler(APIError)
    def handle_api_error(error):
        """处理自定义 API 错误"""
        request_id = getattr(g, 'request_id', None)
        app.logger.warning(f"[{request_id}] API Error: {error.error} - {error.message}")
        return error_response(
            message=error.message,
            code=error.code,
            error=error.error,
            details=error.details if error.details else None,
            request_id=request_id
        )
    
    # 数据库完整性错误
    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        """处理数据库完整性错误"""
        request_id = _log_error_with_context(app, error)
        # 解析常见的完整性错误
        error_str = str(error.orig).lower()
        
        if 'unique' in error_str or 'duplicate' in error_str:
            return error_response(
                message='数据已存在，请勿重复添加',
                code=409,
                error='duplicate_entry',
                request_id=request_id
            )
        elif 'foreign key' in error_str:
            return error_response(
                message='关联的数据不存在',
                code=400,
                error='foreign_key_constraint',
                request_id=request_id
            )
        elif 'not null' in error_str:
            return error_response(
                message='必填字段不能为空',
                code=400,
                error='not_null_constraint',
                request_id=request_id
            )
        else:
            return error_response(
                message='数据操作失败',
                code=400,
                error='integrity_error',
                request_id=request_id
            )
    
    # 数据库错误
    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error):
        """处理数据库错误"""
        request_id = _log_error_with_context(app, error, 'DATABASE_ERROR')
        return error_response(
            message='数据库操作失败，请稍后重试',
            code=500,
            error='database_error',
            request_id=request_id
        )
    
    # 500 - 服务器内部错误
    @app.errorhandler(InternalServerError)
    @app.errorhandler(Exception)
    def handle_internal_error(error):
        """处理服务器内部错误"""
        # 记录完整错误日志
        request_id = _log_error_with_context(app, error)
        
        # 如果是 HTTP 异常，使用其状态码
        if isinstance(error, HTTPException):
            return error_response(
                message=error.description or '服务器错误',
                code=error.code,
                error='http_error',
                request_id=request_id
            )
        
        # 生产环境不暴露详细错误信息
        if not app.debug:
            return error_response(
                message='服务器内部错误，请稍后重试',
                code=500,
                error='internal_server_error',
                request_id=request_id
            )
        
        # 开发环境返回详细错误
        return error_response(
            message=str(error),
            code=500,
            error='internal_server_error',
            request_id=request_id
        )


def handle_404_error(resource_name: str = '资源') -> tuple:
    """
    生成 404 错误响应的快捷方法
    
    Args:
        resource_name: 资源名称
        
    Returns:
        错误响应元组
    """
    request_id = getattr(g, 'request_id', None)
    return error_response(
        message=f'{resource_name}不存在',
        code=404,
        error='not_found',
        request_id=request_id
    )


def handle_409_error(message: str = '资源冲突') -> tuple:
    """
    生成 409 冲突错误响应的快捷方法
    
    Args:
        message: 错误消息
        
    Returns:
        错误响应元组
    """
    request_id = getattr(g, 'request_id', None)
    return error_response(
        message=message,
        code=409,
        error='conflict',
        request_id=request_id
    )
