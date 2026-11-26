# Auto-split skeleton

"""
字段服务模块
处理 Field 的 CRUD 操作、排序管理和类型验证
支持 22 种字段类型
"""
import logging
import re
from typing import List, Optional, Dict, Any, Tuple
import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import func

from app.extensions import db
from app.models.field import Field, FieldType
from app.models.record import Record
from app.models.table import Table
from app.models.base import MemberRole
from app.services.base_service import BaseService
from app.services.formula_service import FormulaService
from app.i18n import translate
from app.services.workflow_event_bus import workflow_event_bus
import logging


logger = logging.getLogger(__name__)


def _format_date_default_value(default_value: str, field_type: str) -> str:
    """
    根据字段类型（date 或 date_time）格式化默认值

    Args:
        default_value: 原始默认值（ISO 8601 格式或 YYYY-MM-DD 格式）
        field_type: 字段类型（'date' 或 'date_time'）

    Returns:
        格式化后的日期字符串
    """
    if default_value is None or default_value == 'now':
        return default_value

    # 根据字段类型决定格式
    is_date_time = field_type == FieldType.DATE_TIME.value

    try:
        # 解析日期时间
        if 'T' in default_value:
            # ISO 8601 格式: 2026-04-12T00:00:00.000Z 或 2026-04-12T00:00:00+00:00
            dt = datetime.fromisoformat(default_value.replace('Z', '+00:00'))
        else:
            # 已经是 YYYY-MM-DD 或 YYYY-MM-DD HH:mm:ss 格式
            if len(default_value) <= 10:
                dt = datetime.strptime(default_value, '%Y-%m-%d')
            else:
                dt = datetime.strptime(default_value, '%Y-%m-%d %H:%M:%S')

        # 根据字段类型格式化
        if is_date_time:
            # 保留 UTC ISO 格式（如 2026-05-10T16:16:40Z）
            return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            return dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        # 如果解析失败，返回原始值
        return default_value


def _validate_ai_options(ai_config, table_id, current_field_id=None):
    """AI 字段 options.ai_config 校验（B1/B8；延迟导入避免 services.ai 循环依赖）"""
    try:
        from app.services.ai.ai_field_service import validate_ai_config
    except ImportError:
        validate_ai_config = None
    return validate_ai_config(ai_config, table_id, current_field_id)

from .field_service_group01 import FieldServiceGroup01Mixin
from .field_service_group02 import FieldServiceGroup02Mixin
from .field_service_group03 import FieldServiceGroup03Mixin

class FieldService(FieldServiceGroup01Mixin, FieldServiceGroup02Mixin, FieldServiceGroup03Mixin):
    """FieldService — 主类，方法在 mixin 中"""
    
    """字段服务类"""
    
    SYSTEM_FIELD_TYPES = [
        FieldType.AUTO_NUMBER
    ]
    
    OPTIONS_REQUIRED_TYPES = [
        FieldType.SINGLE_SELECT.value,
        FieldType.MULTI_SELECT.value
    ]
    
    VALID_FIELD_TYPES = [ft.value for ft in FieldType]
    
    TEXT_TYPES = [
        FieldType.SINGLE_LINE_TEXT.value,
        FieldType.LONG_TEXT.value,
        FieldType.RICH_TEXT.value,
    ]
    
    NUMERIC_TYPES = [
        FieldType.NUMBER.value,
        FieldType.CURRENCY.value,
        FieldType.PERCENT.value,
        FieldType.RATING.value,
        FieldType.DURATION.value,
    ]
    
    DATE_TYPES = [
        FieldType.DATE.value,
        FieldType.DATE_TIME.value,
    ]
    
    CONVERT_SYSTEM_TYPES = [
        FieldType.CREATED_BY.value,
        FieldType.CREATED_TIME.value,
        FieldType.UPDATED_BY.value,
        FieldType.UPDATED_TIME.value,
        FieldType.LAST_MODIFIED_BY.value,
        FieldType.AUTO_NUMBER.value,
    ]
    
    CONVERT_FORBIDDEN_TYPES = CONVERT_SYSTEM_TYPES + [
        FieldType.LINK_TO_RECORD.value,
        FieldType.LINK.value,
        FieldType.LOOKUP.value,
        FieldType.ROLLUP.value,
        FieldType.BUTTON.value,
    ]
    
    CONVERT_FORBIDDEN_TARGET_TYPES = [
        FieldType.FORMULA.value,
        FieldType.AI.value,
    ]
    
    LOSSLESS_CONVERSIONS = {
        # 文本升级（单行 -> 多行/富文本）
        FieldType.SINGLE_LINE_TEXT.value: [
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        FieldType.LONG_TEXT.value: [
            FieldType.RICH_TEXT.value,
        ],
        # 选择类：单选转多选无损；转文本保留选项 ID
        FieldType.SINGLE_SELECT.value: [
            FieldType.MULTI_SELECT.value,
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        FieldType.MULTI_SELECT.value: [
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        # 文本格式类转文本类
        FieldType.EMAIL.value: list(TEXT_TYPES),
        FieldType.PHONE.value: list(TEXT_TYPES),
        FieldType.URL.value: list(TEXT_TYPES),
        FieldType.BARCODE.value: list(TEXT_TYPES),
        # 文本类 <-> 地理位置：文本直接承载为地址串，地理对象转文本按层级拼接
        FieldType.GEOLOCATION.value: list(TEXT_TYPES),
        # 数值族互转 + 转文本类
        FieldType.NUMBER.value: [
            FieldType.CURRENCY.value,
            FieldType.PERCENT.value,
            FieldType.RATING.value,
            FieldType.DURATION.value,
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        FieldType.CURRENCY.value: [
            FieldType.NUMBER.value,
            FieldType.PERCENT.value,
            FieldType.RATING.value,
            FieldType.DURATION.value,
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        FieldType.PERCENT.value: [
            FieldType.NUMBER.value,
            FieldType.CURRENCY.value,
            FieldType.RATING.value,
            FieldType.DURATION.value,
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        FieldType.RATING.value: [
            FieldType.NUMBER.value,
            FieldType.CURRENCY.value,
            FieldType.PERCENT.value,
            FieldType.DURATION.value,
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        FieldType.DURATION.value: [
            FieldType.NUMBER.value,
            FieldType.CURRENCY.value,
            FieldType.PERCENT.value,
            FieldType.RATING.value,
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        # 日期族互转 + 转文本类
        FieldType.DATE.value: [
            FieldType.DATE_TIME.value,
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        FieldType.DATE_TIME.value: [
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        # 成员转文本类（保留成员 ID）
        FieldType.COLLABORATOR.value: list(TEXT_TYPES),
        # 公式冻结：转为常规值类型，实际能否承载由值兼容性预检判定
        FieldType.FORMULA.value: [
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
            FieldType.NUMBER.value,
            FieldType.CURRENCY.value,
            FieldType.PERCENT.value,
            FieldType.RATING.value,
            FieldType.DURATION.value,
            FieldType.DATE.value,
            FieldType.DATE_TIME.value,
        ],
    }
    
    _geolocation_target = FieldType.GEOLOCATION.value
    
    LOSSLESS_CONVERSIONS[FieldType.AI.value] = list(TEXT_TYPES)
    
    LOSSY_CONVERSIONS = {
        FieldType.DATE_TIME.value: [
            FieldType.DATE.value,
        ],
    }
    



# === 反向注入：把主类注入到所有 group mixin 模块 ===
# PyArmor 加密后模块加载顺序不确定，mixin 里硬编码引用主类会 NameError
from app.services._inject import inject_main_class
inject_main_class(FieldService, 'field_service_group01', 'field_service_group02', 'field_service_group03')
