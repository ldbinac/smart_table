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

class LinkServiceGroup03Mixin:
    """Mixin auto-split"""
    
    """关联字段服务类"""
    
    
    @staticmethod
    def get_record_links(record_id: str, use_cache: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取记录的所有关联信息
    
        使用 Redis 缓存优化性能，默认缓存 5 分钟
    
        Args:
            record_id: 记录 ID
            use_cache: 是否使用缓存，默认为 True
    
        Returns:
            按字段分组的关联信息
        """
        cache_key = _get_record_links_cache_key(record_id)
    
        # 尝试从缓存获取
        if use_cache:
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                current_app.logger.debug(f'[LinkService] 从缓存获取记录 {record_id} 的关联数据')
                return cached_result
    
        try:
            record = db.session.get(Record, record_id)
            if not record:
                return {}
    
            result = {}
            # 字段缓存，避免 N+1 查询
            field_cache = {}
            # 双向关联会在正反两个方向各存一条互为镜像的 LinkValue，
            # 且两条都归属同一个字段。按 (field_id, 关联记录 ID) 去重，
            # 避免上层（表格单元格、导出、打印）把一条关联当成两条。
            seen_links: Dict[str, set] = {}
    
            # 作为源记录的关联
            source_links = db.session.execute(
                select(LinkValue, LinkRelation).join(
                    LinkRelation,
                    LinkValue.link_relation_id == LinkRelation.id
                ).where(
                    LinkValue.source_record_id == record_id
                )
            ).all()
    
            for link_value, link_relation in source_links:
                field_id = str(link_relation.source_field_id)
                if field_id not in result:
                    result[field_id] = []
                seen_links.setdefault(field_id, set()).add(str(link_value.target_record_id))
    
                # 获取显示值 - 使用关联字段配置中的 displayFieldId
                display_value = LinkService._get_link_display_value(
                    link_value.target_record, 
                    link_relation.source_field_id,
                    _field_cache=field_cache
                )
    
                result[field_id].append({
                    'link_value_id': str(link_value.id),
                    'link_relation_id': str(link_relation.id),
                    'target_record_id': str(link_value.target_record_id),
                    'target_record': display_value,
                    'direction': 'outgoing'
                })
    
            # 作为目标记录的关联（双向关联）
            target_links = db.session.execute(
                select(LinkValue, LinkRelation).join(
                    LinkRelation,
                    LinkValue.link_relation_id == LinkRelation.id
                ).where(
                    and_(
                        LinkValue.target_record_id == record_id,
                        LinkRelation.bidirectional == True
                    )
                )
            ).all()
    
            for link_value, link_relation in target_links:
                if link_relation.target_field_id:
                    field_id = str(link_relation.target_field_id)
                    linked_record_id = str(link_value.source_record_id)
                    # 双向关联的反向 LinkValue 与正向 LinkValue 互为镜像：
                    # 同一字段已关联同一记录时只保留正向那条（outgoing）。
                    seen = seen_links.setdefault(field_id, set())
                    if linked_record_id in seen:
                        continue
                    seen.add(linked_record_id)
                    if field_id not in result:
                        result[field_id] = []
    
                    # 获取显示值 - 使用关联字段配置中的 displayFieldId
                    display_value = LinkService._get_link_display_value(
                        link_value.source_record,
                        link_relation.target_field_id,
                        _field_cache=field_cache
                    )
    
                    result[field_id].append({
                        'link_value_id': str(link_value.id),
                        'link_relation_id': str(link_relation.id),
                        'source_record_id': str(link_value.source_record_id),
                        'source_record': display_value,
                        'direction': 'incoming'
                    })
    
            # 兜底：历史坏数据（复制记录、批量粘贴等路径曾把关联目标 ID 直接写进
            # values 而未建 LinkValue）在 LinkValue 表中查不到任何关联。这里回退用
            # values 中的记录 ID 解析显示名，避免界面与导出退化为「关联 N 条」/裸 UUID。
            # 仅在该字段没有任何 LinkValue 时启用；一旦补建关联，缓存会被正常刷新。
            try:
                link_field_rows = db.session.execute(
                    select(Field).where(
                        Field.table_id == str(record.table_id),
                        Field.type.in_([FieldType.LINK.value, FieldType.LINK_TO_RECORD.value]),
                    )
                ).scalars().all()
                for field in link_field_rows:
                    field_id = str(field.id)
                    if field_id in result:
                        continue
                    raw = (record.values or {}).get(field_id)
                    candidates = raw if isinstance(raw, list) else ([raw] if raw else [])
                    for candidate in candidates:
                        candidate_id = str(candidate) if candidate else ''
                        if not candidate_id:
                            continue
                        target_record = db.session.get(Record, candidate_id)
                        if not target_record or target_record.is_deleted:
                            continue
                        result.setdefault(field_id, []).append({
                            'link_value_id': None,
                            'link_relation_id': None,
                            'target_record_id': candidate_id,
                            'target_record': LinkService._get_link_display_value(
                                target_record, field_id, _field_cache=field_cache
                            ),
                            'direction': 'outgoing',
                        })
            except Exception as e:
                current_app.logger.warning(
                    f'[LinkService] values 关联兜底解析失败: record={record_id}, error={e}'
                )
    
            # 存入缓存
            if use_cache:
                cache.set(cache_key, result, timeout=CACHE_TTL)
                current_app.logger.debug(f'[LinkService] 缓存记录 {record_id} 的关联数据')
    
            return result
    
        except Exception as e:
            current_app.logger.error(f'[LinkService] 获取记录关联信息失败: {str(e)}')
            return {}
    
    @staticmethod
    def batch_get_record_link_ids(record_ids: List[str]) -> Dict[str, Dict[str, List[str]]]:
        """
        批量获取多条记录的关联记录 ID 映射
    
        相比逐个调用 get_record_links，此方法只返回关联记录 ID，
        不查询显示值，且只需 2 条 SQL 即可完成所有记录的关联数据加载。
    
        Args:
            record_ids: 记录 ID 列表
    
        Returns:
            {record_id: {field_id: [linked_record_id, ...]}}
            每个 field_id 对应的列表已去重
        """
        if not record_ids:
            return {}
    
        result: Dict[str, Dict[str, List[str]]] = {rid: {} for rid in record_ids}
    
        try:
            # 1. 查询所有 outgoing 关联
            source_rows = db.session.execute(
                select(LinkValue, LinkRelation).join(
                    LinkRelation,
                    LinkValue.link_relation_id == LinkRelation.id
                ).where(
                    LinkValue.source_record_id.in_(record_ids)
                )
            ).all()
    
            for link_value, link_relation in source_rows:
                record_id = str(link_value.source_record_id)
                field_id = str(link_relation.source_field_id)
                target_id = str(link_value.target_record_id)
                if field_id not in result[record_id]:
                    result[record_id][field_id] = []
                result[record_id][field_id].append(target_id)
    
            # 2. 查询所有 incoming 关联（仅双向关联）
            target_rows = db.session.execute(
                select(LinkValue, LinkRelation).join(
                    LinkRelation,
                    LinkValue.link_relation_id == LinkRelation.id
                ).where(
                    and_(
                        LinkValue.target_record_id.in_(record_ids),
                        LinkRelation.bidirectional == True
                    )
                )
            ).all()
    
            for link_value, link_relation in target_rows:
                record_id = str(link_value.target_record_id)
                if link_relation.target_field_id:
                    field_id = str(link_relation.target_field_id)
                    source_id = str(link_value.source_record_id)
                    if field_id not in result[record_id]:
                        result[record_id][field_id] = []
                    result[record_id][field_id].append(source_id)
    
            # 3. 对每个字段的 ID 列表去重
            for rid in result:
                for fid in result[rid]:
                    result[rid][fid] = list(dict.fromkeys(result[rid][fid]))
    
            return result
    
        except Exception as e:
            current_app.logger.error(f'[LinkService] batch_get_record_link_ids failed: {str(e)}')
            return result
    
    @staticmethod
    def _get_link_display_value(target_record, field_id: str, _field_cache: dict = None) -> str:
        """
        获取关联记录的显示值
    
        优先使用关联字段配置中的 displayFieldId，如果没有配置则使用主字段
        如果仍然无法获取，尝试使用目标记录的第一个非空字段值
    
        Args:
            target_record: 目标记录
            field_id: 关联字段ID
            _field_cache: 字段缓存字典（避免 N+1 查询）
    
        Returns:
            显示值字符串
        """
        try:
            if not target_record:
                return '未命名记录'
    
            # 获取关联字段配置（优先使用缓存）
            field = None
            if _field_cache is not None:
                field = _field_cache.get(str(field_id))
            if field is None:
                field = db.session.get(Field, field_id)
                if _field_cache is not None and field:
                    _field_cache[str(field_id)] = field
    
            # 辅助函数：从 field 的 config 或 options 中获取 displayFieldId
            def _get_display_field_id(f):
                if not f:
                    return None
                for storage in (f.config, f.options):
                    if storage and isinstance(storage, dict):
                        display_field_id = storage.get('displayFieldId')
                        if display_field_id:
                            return display_field_id
                        # 兼容下划线命名
                        display_field_id = storage.get('display_field_id')
                        if display_field_id:
                            return display_field_id
                return None
    
            # 辅助函数：格式化显示值，对单选/多选字段转换为选项名称
            def _format_display_value(display_field_id, display_value):
                if display_value is None or display_value == '':
                    return None
                display_field = None
                if _field_cache is not None:
                    display_field = _field_cache.get(str(display_field_id))
                if display_field is None:
                    display_field = db.session.get(Field, display_field_id)
                    if _field_cache is not None and display_field:
                        _field_cache[str(display_field_id)] = display_field
                if display_field and display_field.type in (FieldType.SINGLE_SELECT.value, FieldType.MULTI_SELECT.value):
                    return _format_select_display_value(display_value, display_field)
                return str(display_value)
    
            if field:
                display_field_id = _get_display_field_id(field)
                if display_field_id:
                    display_value = target_record.values.get(str(display_field_id))
                    formatted = _format_display_value(display_field_id, display_value)
                    if formatted is not None:
                        return formatted
    
                # 尝试使用 inverseFieldId 对应的源字段的 displayFieldId
                inverse_field_id = None
                if field.config and isinstance(field.config, dict):
                    inverse_field_id = field.config.get('inverseFieldId') or field.config.get('inverse_field_id')
                if not inverse_field_id and field.options and isinstance(field.options, dict):
                    inverse_field_id = field.options.get('inverseFieldId') or field.options.get('inverse_field_id')
                if inverse_field_id:
                    inverse_field = None
                    if _field_cache is not None:
                        inverse_field = _field_cache.get(str(inverse_field_id))
                    if inverse_field is None:
                        inverse_field = db.session.get(Field, inverse_field_id)
                        if _field_cache is not None and inverse_field:
                            _field_cache[str(inverse_field_id)] = inverse_field
    
                    display_field_id = _get_display_field_id(inverse_field)
                    if display_field_id:
                        inverse_display_field = db.session.get(Field, display_field_id)
                        # inverseField 位于对端表，它的 displayFieldId 指向对端表的字段。
                        # 只有该字段确实属于当前目标记录所在表时才能用它取值，
                        # 否则会取不到值并落到「values 第一个标量」的错误回退。
                        if inverse_display_field and str(inverse_display_field.table_id) == str(target_record.table_id):
                            display_value = target_record.values.get(str(display_field_id))
                            formatted = _format_display_value(display_field_id, display_value)
                            if formatted is not None:
                                return formatted
    
            # 没有可用的 displayFieldId 时优先使用主字段。旧实现先返回 values 里的
            # 第一个标量，会把内部 UUID（如关联字段 ID）当成显示名泄漏到界面与导出。
            primary_value = target_record.get_primary_value()
            if primary_value is not None and str(primary_value).strip() and str(primary_value) != '未命名记录':
                return str(primary_value)
    
            def _looks_like_record_id(v):
                try:
                    uuid.UUID(str(v))
                    return True
                except (ValueError, TypeError, AttributeError):
                    return False
    
            if target_record.values:
                for val in target_record.values.values():
                    if val is None or val == '' or isinstance(val, (list, dict)):
                        continue
                    if _looks_like_record_id(val):
                        continue
                    return str(val)
            return str(primary_value) if primary_value else '未命名记录'
        except Exception as e:
            current_app.logger.error(f'[LinkService] 获取显示值失败: {str(e)}')
            return '未命名记录'
    
    @staticmethod
    def delete_record_links(record_id: str) -> bool:
        """
        删除记录的所有关联数据
    
        当记录被删除时，自动清理该记录的所有关联关系
    
        Args:
            record_id: 记录 ID
    
        Returns:
            是否成功
        """
        try:
            # 删除作为源记录的关联
            LinkValue.query.filter_by(source_record_id=record_id).delete()
    
            # 删除作为目标记录的关联
            LinkValue.query.filter_by(target_record_id=record_id).delete()
    
            current_app.logger.info(f'[LinkService] 已删除记录 {record_id} 的所有关联数据')
            return True
        except Exception as e:
            current_app.logger.error(f'[LinkService] 删除记录关联数据失败: {str(e)}')
            return False
    
