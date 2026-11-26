# Auto-split skeleton

"""
数据表分享服务模块
处理表级分享链接的创建、更新、访问与权限判定逻辑
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

from flask import current_app

from app.extensions import db
from app.models.base import BaseMember, MemberRole
from app.models.table import Table
from app.models.view import View
from app.models.field import Field
from app.models.user import User
from app.models.table_share import TableShare, TableShareMember, TableSharePermission
from app.services.permission_service import PermissionService

from .table_share_service_group01 import TableShareServiceGroup01Mixin
from .table_share_service_group02 import TableShareServiceGroup02Mixin

class TableShareService(TableShareServiceGroup01Mixin, TableShareServiceGroup02Mixin):
    """TableShareService — 主类，方法在 mixin 中"""
    
    """数据表分享服务类"""
    
    VALID_PERMISSIONS = ('editor', 'commenter', 'viewer')
    
    VALID_VIEW_SCOPES = ('all', 'specified')
    
    PERMISSION_RANK = {'viewer': 0, 'commenter': 1, 'editor': 2}
    


# === 反向注入：把主类注入到所有 group mixin 模块 ===
# PyArmor 加密后模块加载顺序不确定，mixin 里硬编码引用主类会 NameError
from app.services._inject import inject_main_class
inject_main_class(TableShareService, 'table_share_service_group01', 'table_share_service_group02')
