# Auto-split skeleton

"""
记录服务模块
"""
from typing import List, Optional, Dict, Any
import uuid
import re
from datetime import datetime, timezone

from sqlalchemy import cast, or_, select, and_
from sqlalchemy.types import String
from sqlalchemy.orm.attributes import flag_modified

from app.extensions import db
from app.models.record import Record
from app.models.link_relation import LinkRelation, LinkValue, RelationshipType
from app.models.field import Field, FieldType
from app.models.record_history import RecordHistory, HistoryAction
from app.models.table import Table
from app.services.field_service import FieldService
from app.services.formula_service import FormulaService
from app.services.link_service import LinkService
from app.services.workflow_event_bus import workflow_event_bus
from app.errors.handlers import ConflictError

import logging


log = logging.getLogger(__name__)


def _escape_like_pattern(pattern: str) -> str:
    """
    转义 SQL LIKE 查询中的通配符，防止通配符注入
    
    Args:
        pattern: 原始搜索模式
        
    Returns:
        转义后的安全搜索模式
    """
    if not pattern:
        return pattern
    return pattern.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _format_date_value(value: str, field: Field) -> str:
    """
    根据字段类型（date 或 date_time）格式化日期值

    Args:
        value: 原始日期值（ISO 8601 格式或 YYYY-MM-DD 格式）
        field: 字段对象

    Returns:
        格式化后的日期字符串
    """
    if value is None:
        return None

    # 根据字段类型决定格式
    is_date_time = field.type == FieldType.DATE_TIME.value

    try:
        # 解析日期时间
        if 'T' in str(value):
            # ISO 8601 格式: 2026-04-12T00:00:00.000Z 或 2026-04-12T00:00:00+00:00
            dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        else:
            # 已经是 YYYY-MM-DD 或 YYYY-MM-DD HH:mm:ss 格式
            if len(str(value)) <= 10:
                dt = datetime.strptime(str(value), '%Y-%m-%d')
            else:
                dt = datetime.strptime(str(value), '%Y-%m-%d %H:%M:%S')

        # 根据字段类型格式化
        if is_date_time:
            # 保留 UTC ISO 格式（如 2026-05-10T16:16:40.478Z）
            return dt.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
        else:
            return dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        # 如果解析失败，返回原始值
        return value

from .record_service_group01 import RecordServiceGroup01Mixin
from .record_service_group02 import RecordServiceGroup02Mixin
from .record_service_group03 import RecordServiceGroup03Mixin

class RecordService(RecordServiceGroup01Mixin, RecordServiceGroup02Mixin, RecordServiceGroup03Mixin):
    """RecordService — 主类，方法在 mixin 中"""
    
    """记录服务类"""
    


def filter_record_values_by_field_permission(
    values: Dict[str, Any],
    table_id: str,
    user_id: str,
    base_id: str,
) -> Dict[str, Any]:
    """根据字段权限过滤记录值，移除无权限（none）的字段值

    Args:
        values: 原始记录值字典
        table_id: 表格 ID
        user_id: 用户 ID
        base_id: Base ID

    Returns:
        过滤后的记录值字典（仅包含有权限的字段）
    """
    try:
        from app.services.permission_resolver import PermissionResolver
    except ImportError:
        PermissionResolver = None

    try:
        permissions = PermissionResolver.resolve_permissions(user_id, base_id)
        field_permissions = permissions.get('field_permissions', {})

        # 如果没有字段权限配置，不过滤
        if not field_permissions:
            return values

        # 过滤掉权限为 none 的字段值
        filtered = {}
        for field_id, value in values.items():
            perm = field_permissions.get(field_id, permissions.get('_default', 'none'))
            if perm != 'none':
                filtered[field_id] = value

        return filtered
    except Exception as e:
        log.error(f'[RecordService] 字段权限过滤失败: {e}')
        # 过滤失败时不过滤，返回原始值（避免影响正常功能）
        return values

def strip_none_permission_fields(
    values: Dict[str, Any],
    table_id: str,
    user_id: str,
    base_id: str,
) -> Dict[str, Any]:
    """从更新数据中移除无权限（none）的字段，避免影响无权限字段的值

    与 filter_record_values_by_field_permission 不同的是，
    此函数只移除 values 中权限为 none 的字段，保留其他字段不变。

    Args:
        values: 待更新的字段值
        table_id: 表格 ID
        user_id: 用户 ID
        base_id: Base ID

    Returns:
        移除无权限字段后的更新值
    """
    try:
        from app.services.permission_resolver import PermissionResolver
    except ImportError:
        PermissionResolver = None

    try:
        permissions = PermissionResolver.resolve_permissions(user_id, base_id)
        field_permissions = permissions.get('field_permissions', {})

        # 如果没有字段权限配置，不过滤
        if not field_permissions:
            return values

        # 只移除权限为 none 的字段
        result = {}
        for field_id, value in values.items():
            perm = field_permissions.get(field_id, permissions.get('_default', 'none'))
            if perm != 'none':
                result[field_id] = value

        return result
    except Exception as e:
        log.error(f'[RecordService] 更新字段权限过滤失败: {e}')
        return values

def filter_history_changes_by_field_permission(
    changes: list,
    table_id: str,
    user_id: str,
    base_id: str,
) -> list:
    """根据字段权限过滤变更历史中的 changes 列表

    移除权限为 none 的字段的变更记录，防止数据泄露。

    Args:
        changes: 变更历史中的 changes 列表 [{field_id, old_value, new_value}, ...]
        table_id: 表格 ID
        user_id: 用户 ID
        base_id: Base ID

    Returns:
        过滤后的 changes 列表
    """
    try:
        from app.services.permission_resolver import PermissionResolver
    except ImportError:
        PermissionResolver = None

    try:
        permissions = PermissionResolver.resolve_permissions(user_id, base_id)
        field_permissions = permissions.get('field_permissions', {})

        if not field_permissions:
            return changes

        filtered = []
        for change in changes:
            field_id = change.get('field_id')
            if field_id:
                perm = field_permissions.get(field_id, permissions.get('_default', 'none'))
                if perm != 'none':
                    filtered.append(change)
            else:
                # 没有 field_id 的变更保留
                filtered.append(change)

        return filtered
    except Exception as e:
        log.error(f'[RecordService] 变更历史字段权限过滤失败: {e}')
        return changes


# === 反向注入：把主类注入到所有 group mixin 模块 ===
# PyArmor 加密后模块加载顺序不确定，mixin 里硬编码引用主类会 NameError
from app.services._inject import inject_main_class
inject_main_class(RecordService, 'record_service_group01', 'record_service_group02', 'record_service_group03')
