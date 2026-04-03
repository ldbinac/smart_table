"""
错误处理器模块
集中处理应用中的各种错误
"""
from flask import Flask, request
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
        return error_response(
            message='请求格式错误',
            code=400,
            error='bad_request'
        )
    
    # 401 - 未授权
    @app.errorhandler(Unauthorized)
    def handle_unauthorized(error):
        """处理未授权请求"""
        return error_response(
            message='请先登录',
            code=401,
            error='unauthorized'
        )
    
    # 403 - 禁止访问
    @app.errorhandler(Forbidden)
    def handle_forbidden(error):
        """处理禁止访问请求"""
        return error_response(
            message='权限不足',
            code=403,
            error='forbidden'
        )
    
    # 404 - 未找到
    @app.errorhandler(NotFound)
    def handle_not_found(error):
        """处理资源未找到"""
        if request.path.startswith('/api/'):
            return error_response(
                message='请求的资源不存在',
                code=404,
                error='not_found'
            )
        # 非 API 路由返回 HTML 404
        return error
    
    # 405 - 方法不允许
    @app.errorhandler(MethodNotAllowed)
    def handle_method_not_allowed(error):
        """处理方法不允许"""
        return error_response(
            message=f'不支持的请求方法: {request.method}',
            code=405,
            error='method_not_allowed'
        )
    
    # 422 - 验证错误（Marshmallow）
    @app.errorhandler(MarshmallowValidationError)
    def handle_validation_error(error):
        """处理数据验证错误"""
        details = [
            {'field': field, 'message': msgs[0] if isinstance(msgs, list) else msgs}
            for field, msgs in error.messages.items()
        ]
        return error_response(
            message='数据验证失败',
            code=422,
            error='validation_error',
            details=details
        )
    
    # 自定义 API 错误
    @app.errorhandler(APIError)
    def handle_api_error(error):
        """处理自定义 API 错误"""
        return error_response(
            message=error.message,
            code=error.code,
            error=error.error,
            details=error.details if error.details else None
        )
    
    # 数据库完整性错误
    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        """处理数据库完整性错误"""
        # 解析常见的完整性错误
        error_str = str(error.orig).lower()
        
        if 'unique' in error_str or 'duplicate' in error_str:
            return error_response(
                message='数据已存在，请勿重复添加',
                code=409,
                error='duplicate_entry'
            )
        elif 'foreign key' in error_str:
            return error_response(
                message='关联的数据不存在',
                code=400,
                error='foreign_key_constraint'
            )
        elif 'not null' in error_str:
            return error_response(
                message='必填字段不能为空',
                code=400,
                error='not_null_constraint'
            )
        else:
            return error_response(
                message='数据操作失败',
                code=400,
                error='integrity_error'
            )
    
    # 数据库错误
    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error):
        """处理数据库错误"""
        app.logger.error(f'Database error: {str(error)}')
        return error_response(
            message='数据库操作失败，请稍后重试',
            code=500,
            error='database_error'
        )
    
    # 500 - 服务器内部错误
    @app.errorhandler(InternalServerError)
    @app.errorhandler(Exception)
    def handle_internal_error(error):
        """处理服务器内部错误"""
        # 记录错误日志
        app.logger.exception('Internal server error')
        
        # 如果是 HTTP 异常，使用其状态码
        if isinstance(error, HTTPException):
            return error_response(
                message=error.description or '服务器错误',
                code=error.code,
                error='http_error'
            )
        
        # 生产环境不暴露详细错误信息
        if not app.debug:
            return error_response(
                message='服务器内部错误，请稍后重试',
                code=500,
                error='internal_server_error'
            )
        
        # 开发环境返回详细错误
        return error_response(
            message=str(error),
            code=500,
            error='internal_server_error'
        )


def handle_404_error(resource_name: str = '资源') -> tuple:
    """
    生成 404 错误响应的快捷方法
    
    Args:
        resource_name: 资源名称
        
    Returns:
        错误响应元组
    """
    return error_response(
        message=f'{resource_name}不存在',
        code=404,
        error='not_found'
    )


def handle_409_error(message: str = '资源冲突') -> tuple:
    """
    生成 409 冲突错误响应的快捷方法
    
    Args:
        message: 错误消息
        
    Returns:
        错误响应元组
    """
    return error_response(
        message=message,
        code=409,
        error='conflict'
    )
