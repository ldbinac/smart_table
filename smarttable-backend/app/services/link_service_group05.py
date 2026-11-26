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

class LinkServiceGroup05Mixin:
    """Mixin auto-split"""
    
    """关联字段服务类"""
    
    
    @staticmethod
    def get_linked_records_detail(
        record_id: str,
        field_id: str,
        page: int = 1,
        per_page: int = 50,
        keyword: str = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        获取主从表子表数据详情
    
        根据源记录和关联字段，返回目标表中关联记录的完整数据、目标表字段定义以及分页信息。
    
        Args:
            record_id: 源记录 ID
            field_id: 关联字段 ID
            page: 页码，默认 1
            per_page: 每页数量，默认 50
            keyword: 可选关键词，对目标记录主字段值进行模糊过滤
    
        Returns:
            (结果字典, 错误信息)
            结果字典包含: records, fields, total, page, per_page, link_relation
        """
        try:
            # 1. 通过 field_id 查询 Field，确认是 LINK 类型字段
            field = db.session.get(Field, field_id)
            if not field:
                'field_does_not_exist'
            if field.type not in [FieldType.LINK_TO_RECORD.value, FieldType.LINK.value]:
                'field_not_link_type'
    
            # 2. 从 field.options 或 field.config 获取 linkedTableId（目标表ID）
            linked_table_id = None
            for storage in (field.config, field.options):
                if storage and isinstance(storage, dict):
                    linked_table_id = storage.get('linkedTableId') or storage.get('linked_table_id')
                    if linked_table_id:
                        break
            if not linked_table_id:
                'field_configuration_missing_linked_table_id'
    
            # 3. 获取关联关系
            link_relation = LinkService.get_link_relation_by_field(field_id, linked_table_id)
            if not link_relation:
                'link_relation_does_not_exist'
    
            # 4. 查询 LinkValue 表，获取所有 source_record_id == record_id 且 link_relation_id 匹配的记录
            link_values = db.session.execute(
                select(LinkValue).where(
                    and_(
                        LinkValue.link_relation_id == link_relation.id,
                        LinkValue.source_record_id == record_id
                    )
                )
            ).scalars().all()
    
            # 5. 获取目标记录的完整数据
            target_record_ids = [lv.target_record_id for lv in link_values]
            if target_record_ids:
                target_records = db.session.execute(
                    select(Record).where(Record.id.in_(target_record_ids))
                ).scalars().all()
            else:
                target_records = []
    
            # 6. 如果有 keyword 参数，对目标记录的主字段值进行模糊过滤
            if keyword:
                kw = str(keyword).lower()
                target_records = [
                    tr for tr in target_records
                    if kw in str(tr.get_primary_value()).lower()
                ]
    
            # 7. 分页处理
            total = len(target_records)
            if page < 1:
                page = 1
            if per_page < 1:
                per_page = 50
            start = (page - 1) * per_page
            end = start + per_page
            paged_records = target_records[start:end]
    
            # 8. 查询目标表的字段定义
            target_fields = FieldService.get_all_fields(str(linked_table_id))
    
            # 9. 组装返回结果
            records_data = []
            for tr in paged_records:
                records_data.append({
                    'id': str(tr.id),
                    'values': tr.values,
                    'created_at': tr.created_at.isoformat() if tr.created_at else None,
                    'updated_at': tr.updated_at.isoformat() if tr.updated_at else None
                })
    
            return {
                'records': records_data,
                'fields': [f.to_dict() for f in target_fields],
                'total': total,
                'page': page,
                'per_page': per_page,
                'link_relation': link_relation.to_dict()
            }, None
    
        except Exception as e:
            current_app.logger.error(f'[LinkService] 获取关联记录详情失败: {str(e)}')
            'failed_fetch_linked_record_details_try_again_later'
    
    @staticmethod
    def create_and_link_record(
        source_record_id: str,
        field_id: str,
        values: Dict[str, Any],
        user_id: str = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        在目标表中创建记录并建立与源记录的关联
    
        Args:
            source_record_id: 源记录 ID
            field_id: 关联字段 ID
            values: 新记录的字段值
            user_id: 操作用户 ID
    
        Returns:
            (结果字典, 错误信息)
            结果字典包含: record, link_value
        """
        # 局部导入 RecordService，避免与 record_service 模块产生循环导入
        from app.services.record_service import RecordService
    
        try:
            # 1. 通过 field_id 查询 Field，确认是 LINK 类型
            field = db.session.get(Field, field_id)
            if not field:
                'field_does_not_exist'
            if field.type not in [FieldType.LINK_TO_RECORD.value, FieldType.LINK.value]:
                'field_not_link_type'
    
            # 2. 获取 linkedTableId（目标表ID）
            linked_table_id = None
            for storage in (field.config, field.options):
                if storage and isinstance(storage, dict):
                    linked_table_id = storage.get('linkedTableId') or storage.get('linked_table_id')
                    if linked_table_id:
                        break
            if not linked_table_id:
                'field_configuration_missing_linked_table_id'
    
            # 3. 获取关联关系
            link_relation = LinkService.get_link_relation_by_field(field_id, linked_table_id)
            if not link_relation:
                'link_relation_does_not_exist'
    
            # 4. 一对一约束检查：如果已有关联记录，返回错误
            if link_relation.relationship_type == RelationshipType.ONE_TO_ONE.value:
                existing = db.session.execute(
                    select(LinkValue).where(
                        and_(
                            LinkValue.link_relation_id == link_relation.id,
                            LinkValue.source_record_id == source_record_id
                        )
                    )
                ).scalars().first()
                if existing:
                    'one_one_constraint_source_record_already_linked_record'
    
            # 5. 在目标表创建记录
            new_record = RecordService.create_record(
                str(linked_table_id),
                values,
                created_by=user_id
            )
    
            # 6. 建立关联（追加到已有关联列表，避免覆盖一对多场景下的现有关联）
            existing_links = db.session.execute(
                select(LinkValue).where(
                    and_(
                        LinkValue.link_relation_id == link_relation.id,
                        LinkValue.source_record_id == source_record_id
                    )
                )
            ).scalars().all()
            target_ids = [str(lv.target_record_id) for lv in existing_links]
            new_target_id = str(new_record.id)
            if new_target_id not in target_ids:
                target_ids.append(new_target_id)
    
            # update_link_values 内部会处理双向关联同步
            result, err = LinkService.update_link_values(
                link_relation_id=str(link_relation.id),
                source_record_id=source_record_id,
                target_record_ids=target_ids,
                updated_by=user_id
            )
            if not result:
                return None, translate('link_creation_failed', err)
    
            # 获取新建的 link_value
            link_value = db.session.execute(
                select(LinkValue).where(
                    and_(
                        LinkValue.link_relation_id == link_relation.id,
                        LinkValue.source_record_id == source_record_id,
                        LinkValue.target_record_id == str(new_record.id)
                    )
                )
            ).scalar_one_or_none()
    
            return {
                'record': new_record.to_dict(),
                'link_value': link_value.to_dict() if link_value else None
            }, None
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[LinkService] 创建并关联记录失败: {str(e)}')
            'failed_create_link_record_try_again_later'
    
