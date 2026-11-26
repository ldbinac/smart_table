# Auto-split skeleton

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

from ._auth import authenticate, jwt_required, app_session_required, form_share_or_jwt, role_required, admin_required, owner_or_admin_required, open_api_auth_required, require_open_scope
from ._ratelimit import rate_limit, record_login_attempt, clear_login_attempts, api_rate_limit, upload_rate_limit, query_rate_limit, write_rate_limit, open_api_rate_limit
from ._logger import operation_log
from ._utils import _login_attempts, get_client_ip, get_user_agent, capture_request_info, validate_json
