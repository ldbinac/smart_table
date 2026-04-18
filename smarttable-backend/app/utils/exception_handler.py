"""
异常处理工具模块
提供统一的异常处理机制，确保敏感信息不泄露给客户端
"""
import logging
from typing import Tuple, Optional, Any, Dict
from flask import current_app

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """服务层错误基类"""
    
    def __init__(self, message: str, internal_message: Optional[str] = None):
        self.message = message
        self.internal_message = internal_message or message
        super().__init__(self.message)


def handle_service_exception(
    error: Exception,
    operation: str = '操作',
    log_context: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    统一处理服务层异常
    
    Args:
        error: 捕获的异常
        operation: 操作名称（用于日志和错误消息）
        log_context: 额外的日志上下文信息
        
    Returns:
        Tuple[bool, str]: (成功标志, 错误消息)
    """
    context_str = f" | 上下文: {log_context}" if log_context else ""
    
    if isinstance(error, ServiceError):
        logger.error(f'[{operation}] {error.internal_message}{context_str}')
        return False, error.message
    
    internal_error = str(error)
    logger.error(f'[{operation}] 内部错误: {internal_error}{context_str}')
    
    return False, f'{operation}失败，请稍后重试'


def handle_service_exception_dict(
    error: Exception,
    operation: str = '操作',
    log_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    统一处理服务层异常（返回字典格式）
    
    Args:
        error: 捕获的异常
        operation: 操作名称（用于日志和错误消息）
        log_context: 额外的日志上下文信息
        
    Returns:
        Dict[str, Any]: 包含 success 和 error 字段的字典
    """
    context_str = f" | 上下文: {log_context}" if log_context else ""
    
    if isinstance(error, ServiceError):
        logger.error(f'[{operation}] {error.internal_message}{context_str}')
        return {'success': False, 'error': error.message}
    
    internal_error = str(error)
    logger.error(f'[{operation}] 内部错误: {internal_error}{context_str}')
    
    return {'success': False, 'error': f'{operation}失败，请稍后重试'}


def safe_error_message(error: Exception, default_message: str = '操作失败，请稍后重试') -> str:
    """
    获取安全的错误消息（不包含内部细节）
    
    Args:
        error: 捕获的异常
        default_message: 默认错误消息
        
    Returns:
        str: 可安全返回给客户端的错误消息
    """
    if isinstance(error, ServiceError):
        return error.message
    
    return default_message


def log_exception(error: Exception, operation: str, context: Optional[Dict[str, Any]] = None) -> None:
    """
    记录异常详情到日志（不返回给客户端）
    
    Args:
        error: 捕获的异常
        operation: 操作名称
        context: 额外的上下文信息
    """
    context_str = f" | 上下文: {context}" if context else ""
    internal_error = str(error)
    logger.error(f'[{operation}] 内部错误: {internal_error}{context_str}')
    
    if hasattr(current_app, 'logger'):
        current_app.logger.exception(f'[{operation}] 异常详情')
