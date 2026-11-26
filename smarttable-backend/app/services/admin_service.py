# Auto-split skeleton

"""
管理员服务模块
处理管理员用户管理系统的所有业务逻辑，包括用户管理、操作日志、系统配置等功能
"""
import csv
import io
import json
import logging
import secrets
import smtplib
import ssl
import string
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Optional, Tuple, Dict, Any, List
from uuid import UUID

from sqlalchemy import or_, and_

from app.extensions import db
try:
    from app.utils.crypto import decrypt_secret, encrypt_secret
except ImportError:
    decrypt_secret = None
    encrypt_secret = None
from app.models.user import User, UserRole, UserStatus
from app.models.log import OperationLog, AdminActionType, EntityType
from app.models.config import SystemConfig
from app.services.email_config_service import EmailConfigService
from app.services.email_sender_service import EmailSenderService
from app.services.notification_service import NotificationService
from app.services.security_config_service import SecurityConfigService
from app.services.config_cache_service import ConfigCacheService
from app.i18n import translate

logger = logging.getLogger(__name__)

from .admin_service_group01 import AdminServiceGroup01Mixin
from .admin_service_group02 import AdminServiceGroup02Mixin

class AdminService(AdminServiceGroup01Mixin, AdminServiceGroup02Mixin):
    """AdminService — 主类，方法在 mixin 中"""
    
    """
    管理员服务类
    提供用户管理、操作日志记录、系统配置管理等所有管理员相关功能
    """
    


# === 反向注入：把主类注入到所有 group mixin 模块 ===
# PyArmor 加密后模块加载顺序不确定，mixin 里硬编码引用主类会 NameError
from app.services._inject import inject_main_class
inject_main_class(AdminService, 'admin_service_group01', 'admin_service_group02')
