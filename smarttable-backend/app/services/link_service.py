# Auto-split skeleton

"""
关联字段服务模块
处理 LinkRelation（关联关系）和 LinkValue（关联值）的 CRUD 操作
支持双向关联的自动同步
使用 Redis 缓存优化性能
"""
import json
import re
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone

from sqlalchemy import select, and_, or_, delete
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import flag_modified
from flask import current_app

from app.extensions import db, cache
from app.models.link_relation import LinkRelation, LinkValue, RelationshipType
from app.models.field import Field, FieldType
from app.models.record import Record
from app.models.table import Table
from app.services.table_service import TableService
from app.services.field_service import FieldService
from app.i18n import translate


# 缓存键前缀
CACHE_PREFIX = "link:"
CACHE_TTL = 300  # 5分钟缓存过期时间


def _get_cache_key(*parts: str) -> str:
    """生成缓存键"""
    return f"{CACHE_PREFIX}{':'.join(parts)}"


def _get_record_links_cache_key(record_id: str) -> str:
    """获取记录关联数据的缓存键"""
    return _get_cache_key("record", record_id, "links")


def _get_field_links_cache_key(field_id: str) -> str:
    """获取字段关联关系的缓存键"""
    return _get_cache_key("field", field_id, "relation")


def _invalidate_record_links_cache(record_id: str) -> None:
    """清除记录关联数据的缓存"""
    cache_key = _get_record_links_cache_key(record_id)
    cache.delete(cache_key)
    current_app.logger.debug(f"[LinkService] 清除缓存: {cache_key}")


def _invalidate_field_links_cache(field_id: str) -> None:
    """清除字段关联关系的缓存"""
    cache_key = _get_field_links_cache_key(field_id)
    cache.delete(cache_key)
    current_app.logger.debug(f"[LinkService] 清除缓存: {cache_key}")


def _format_select_display_value(raw_value: Any, field: Field) -> str:
    """
    将单选/多选字段的原始值转换为可读的选项名称
    
    Args:
        raw_value: 字段原始值（可能是 ID、ID 列表、JSON 字符串或对象）
        field: 字段对象
        
    Returns:
        可读的选项名称字符串
    """
    if not field or not field.options:
        return str(raw_value) if raw_value is not None else ''
    
    options = field.options.get('choices') or field.options.get('options') or []
    if not isinstance(options, list):
        return str(raw_value) if raw_value is not None else ''
    
    # 构建 ID->名称 和 名称->名称 的映射
    option_map: Dict[str, str] = {}
    for opt in options:
        if isinstance(opt, dict):
            opt_id = str(opt.get('id', ''))
            opt_name = str(opt.get('name', ''))
            if opt_id:
                option_map[opt_id] = opt_name or opt_id
            if opt_name:
                option_map[opt_name] = opt_name
    
    if field.type == FieldType.SINGLE_SELECT.value:
        # 兼容对象格式 {id, name}
        if isinstance(raw_value, dict):
            raw_value = raw_value.get('name') or raw_value.get('id')
        key = str(raw_value) if raw_value is not None else ''
        return option_map.get(key, key)
    
    if field.type == FieldType.MULTI_SELECT.value:
        ids: List[Any] = []
        if isinstance(raw_value, list):
            ids = raw_value
        elif isinstance(raw_value, str):
            try:
                parsed = json.loads(raw_value)
                if isinstance(parsed, list):
                    ids = parsed
            except Exception:
                ids = [v.strip() for v in raw_value.split(',') if v.strip()]
        
        names: List[str] = []
        for item in ids:
            if isinstance(item, dict):
                item_id = str(item.get('id', ''))
                item_name = str(item.get('name', ''))
                names.append(item_name or option_map.get(item_id, item_id))
            else:
                item_key = str(item)
                names.append(option_map.get(item_key, item_key))
        return ', '.join(names)
    
    return str(raw_value) if raw_value is not None else ''

from .link_service_group01 import LinkServiceGroup01Mixin
from .link_service_group02 import LinkServiceGroup02Mixin
from .link_service_group03 import LinkServiceGroup03Mixin
from .link_service_group04 import LinkServiceGroup04Mixin
from .link_service_group05 import LinkServiceGroup05Mixin

class LinkService(LinkServiceGroup01Mixin, LinkServiceGroup02Mixin, LinkServiceGroup03Mixin, LinkServiceGroup04Mixin, LinkServiceGroup05Mixin):
    """LinkService — 主类，方法在 mixin 中"""
    
    """关联字段服务类"""
    


# === 反向注入：把主类注入到所有 group mixin 模块 ===
# PyArmor 加密后模块加载顺序不确定，mixin 里硬编码引用主类会 NameError
from app.services._inject import inject_main_class
inject_main_class(LinkService, 'link_service_group01', 'link_service_group02', 'link_service_group03', 'link_service_group04', 'link_service_group05', 'import_export_service_group02', 'record_service_group01')
