# Auto-split skeleton

"""
基础数据服务模块
处理 Base（工作区/数据库）的 CRUD 操作和成员管理
"""
from typing import List, Optional, Dict, Any
import uuid

# 用于区分"未传递 role_id"和"明确将 role_id 设为 None"
_UNSET = object()
import threading
from datetime import datetime, timezone

from flask import current_app
from sqlalchemy import or_

from app.extensions import db
from app.models.base import Base, BaseMember, MemberRole
from app.models.base_share import BaseShare, SharePermission
from app.models.user import User
from app.models.table import Table
from app.models.field import Field
from app.models.record import Record
from app.models.view import View
from app.models.dashboard import Dashboard
from app.utils.constants import ROLE_LEVELS
from app.services.email_config_service import EmailConfigService
from app.services.email_sender_service import EmailSenderService
from app.services.notification_service import NotificationService

from .base_service_group01 import BaseServiceGroup01Mixin
from .base_service_group02 import BaseServiceGroup02Mixin
from .base_service_group03 import BaseServiceGroup03Mixin

class BaseService(BaseServiceGroup01Mixin, BaseServiceGroup02Mixin, BaseServiceGroup03Mixin):
    """BaseService — 主类，方法在 mixin 中"""
    
    """基础数据服务类"""
    
    ROLE_LEVELS = ROLE_LEVELS
    


# === 反向注入：把主类注入到所有 group mixin 模块 ===
# PyArmor 加密后模块加载顺序不确定，mixin 里硬编码引用主类会 NameError
from app.services._inject import inject_main_class
inject_main_class(BaseService, 'base_service_group01', 'base_service_group02', 'base_service_group03')
