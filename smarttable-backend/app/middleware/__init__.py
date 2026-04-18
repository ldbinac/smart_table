"""
Flask 中间件模块
"""
from .security_headers import init_security_headers

__all__ = ['init_security_headers']
