# Auto-split skeleton

"""
表单分享服务模块
处理表单分享的创建、管理和数据提交
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

from flask import current_app

from app.extensions import db, cache
from app.models.form_share import FormShare
from app.models.form_submission import FormSubmission
from app.models.table import Table
from app.models.field import Field, FieldType
from app.models.base import Base, MemberRole
from app.services.record_service import RecordService
from app.services.table_service import TableService
from app.services.field_service import FieldService
from app.services.link_service import LinkService
from app.services.permission_service import PermissionService
from app.utils.captcha import CaptchaService
from app.i18n import translate


class FormShareError(Exception):
    """表单分享错误"""
    pass

from .form_share_service_group01 import FormShareServiceGroup01Mixin
from .form_share_service_group02 import FormShareServiceGroup02Mixin
from .form_share_service_group03 import FormShareServiceGroup03Mixin

class FormShareService(FormShareServiceGroup01Mixin, FormShareServiceGroup02Mixin, FormShareServiceGroup03Mixin):
    """FormShareService — 主类，方法在 mixin 中"""
    
    """表单分享服务类"""
    
    SUBMIT_RATE_LIMIT = 100  # 每个分享链接每 15 分钟最多的提交次数（用于防刷，而非限制正常多用户填写）
    
    RATE_LIMIT_WINDOW = 900  # 15 分钟（秒）
    


# === 反向注入：把主类注入到所有 group mixin 模块 ===
# PyArmor 加密后模块加载顺序不确定，mixin 里硬编码引用主类会 NameError
from app.services._inject import inject_main_class
inject_main_class(FormShareService, 'form_share_service_group01', 'form_share_service_group02', 'form_share_service_group03')
