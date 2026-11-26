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

class LinkServiceGroup04Mixin:
    """Mixin auto-split"""
    
    """关联字段服务类"""
    
    
    @staticmethod
    def delete_link_value_by_target(
        link_relation_id: str,
        source_record_id: str,
        target_record_id: str,
        updated_by: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        删除单个关联值（解除两个记录之间的关联关系）
    
        仅解除关联关系，不删除关联数据本身。
        如果是双向关联，同步删除反向的关联关系。
    
        Args:
            link_relation_id: 关联关系 ID
            source_record_id: 源记录 ID
            target_record_id: 目标记录 ID
            updated_by: 更新者 ID
    
        Returns:
            (是否成功, 错误信息)
        """
        try:
            link_relation = db.session.get(LinkRelation, link_relation_id)
            if not link_relation:
                'link_relation_does_not_exist'
    
            # 查找要删除的关联值
            link_value = db.session.execute(
                select(LinkValue).where(
                    and_(
                        LinkValue.link_relation_id == link_relation_id,
                        LinkValue.source_record_id == source_record_id,
                        LinkValue.target_record_id == target_record_id
                    )
                )
            ).scalar_one_or_none()
    
            if not link_value:
                'link_relation_does_not_exist'
    
            # 删除关联值
            db.session.delete(link_value)
    
            # 更新源记录的字段值
            source_record = db.session.get(Record, source_record_id)
            if source_record:
                values = source_record.values or {}
                field_links = values.get(str(link_relation.source_field_id), [])
                if isinstance(field_links, list):
                    field_links = [id for id in field_links if str(id) != target_record_id]
                    values[str(link_relation.source_field_id)] = field_links
                    source_record.values = values
                    flag_modified(source_record, 'values')
                elif isinstance(field_links, str):
                    if field_links == target_record_id:
                        values[str(link_relation.source_field_id)] = None
                        source_record.values = values
                        flag_modified(source_record, 'values')
    
            # 如果是双向关联，同步删除反向关联
            if link_relation.bidirectional and link_relation.target_field_id:
                # 查找反向关联关系
                reverse_relation = db.session.execute(
                    select(LinkRelation).where(
                        and_(
                            LinkRelation.source_field_id == link_relation.target_field_id,
                            LinkRelation.target_field_id == link_relation.source_field_id
                        )
                    )
                ).scalar_one_or_none()
    
                if reverse_relation:
                    # 删除对应的反向 LinkValue
                    reverse_link = db.session.execute(
                        select(LinkValue).where(
                            and_(
                                LinkValue.link_relation_id == reverse_relation.id,
                                LinkValue.source_record_id == target_record_id,
                                LinkValue.target_record_id == source_record_id
                            )
                        )
                    ).scalar_one_or_none()
    
                    if reverse_link:
                        db.session.delete(reverse_link)
    
                    # 更新目标记录的字段值
                    target_record = db.session.get(Record, target_record_id)
                    if target_record:
                        target_values = target_record.values or {}
                        reverse_field_links = target_values.get(str(link_relation.target_field_id), [])
                        if isinstance(reverse_field_links, list):
                            reverse_field_links = [id for id in reverse_field_links if str(id) != source_record_id]
                            target_values[str(link_relation.target_field_id)] = reverse_field_links
                            target_record.values = target_values
                            flag_modified(target_record, 'values')
                        elif isinstance(reverse_field_links, str):
                            if reverse_field_links == source_record_id:
                                target_values[str(link_relation.target_field_id)] = None
                                target_record.values = target_values
                                flag_modified(target_record, 'values')
    
            # 清除缓存
            _invalidate_record_links_cache(source_record_id)
            _invalidate_record_links_cache(target_record_id)
    
            current_app.logger.info(
                f'[LinkService] 删除关联值: link_relation={link_relation_id}, '
                f'source_record={source_record_id}, target_record={target_record_id}, '
                f'bidirectional={link_relation.bidirectional}'
            )
    
            db.session.commit()
            return True, None
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[LinkService] 删除关联值失败: {str(e)}')
            'failed_delete_linked_value_try_again_later'
    
    @staticmethod
    def create_link_field(table_id: str, data: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """
        创建关联字段（包含字段创建、反向字段创建和关联关系创建的完整业务逻辑）
    
        支持的双向关联类型映射：
        - one_to_one → one_to_one（双向一对一）
        - one_to_many → many_to_one（一对多 ↔ 多对一）
        - many_to_one → one_to_many（多对一 ↔ 一对多）
        - many_to_many → many_to_many（双向多对多）
    
        Args:
            table_id: 源表 ID
            data: 创建数据，包含:
                - name: 字段名称
                - target_table_id: 目标表 ID（必需）
                - relationship_type: 关联类型（必需）
                - display_field_id: 显示字段 ID（可选）
                - bidirectional: 是否双向关联（可选，默认 True）
                - description: 描述（可选）
            user_id: 用户 ID（用于协同广播）
    
        Returns:
            包含操作结果的字典
        """
    
        target_table_id = data.get('target_table_id')
        relationship_type = data.get('relationship_type')
        name = data.get('name', '关联字段')
        bidirectional = data.get('bidirectional', True)
    
        current_app.logger.info(
            f'[LinkService] create_link_field 调用参数: '
            f'table_id={table_id}, target_table_id={target_table_id}, '
            f'relationship_type={relationship_type}, bidirectional={bidirectional}'
        )
    
        source_table = TableService.get_table_by_id(str(table_id))
        if not source_table:
            return {'success': False, 'error': 'source_table_does_not_exist'}
    
        target_table = TableService.get_table_by_id(str(target_table_id))
        if not target_table:
            return {'success': False, 'error': 'target_table_does_not_exist'}
    
        has_conflict, conflict_msg = LinkService.check_relationship_conflict(
            str(table_id), str(target_table_id), relationship_type
        )
        if has_conflict:
            return {'success': False, 'error': translate('link_relationship_conflict', conflict_msg)}
    
        try:
            field_data = {
                'name': name,
                'type': FieldType.LINK_TO_RECORD.value,
                'description': data.get('description', ''),
                'config': {
                    'linkedTableId': target_table_id,
                    'relationshipType': relationship_type,
                    'displayFieldId': data.get('display_field_id'),
                    'bidirectional': bidirectional
                }
            }
    
            result = FieldService.create_field(str(table_id), field_data, user_id)
            if not result['success']:
                return result
    
            field = result['field']
    
            inverse_field = None
            if bidirectional:
                inverse_relationship_type = LinkService.get_inverse_relationship_type(relationship_type)
    
                current_app.logger.info(
                    f'[LinkService] 创建反向关联字段: '
                    f'原始类型={relationship_type}, 反向类型={inverse_relationship_type}'
                )
    
                source_table_name = source_table.name if source_table else '源表'
                # 反向关联字段默认使用源表主字段作为显示字段，避免显示关联记录 ID
                inverse_display_field_id = str(source_table.primary_field_id) if source_table.primary_field_id else None
                if not inverse_display_field_id:
                    # 源表未维护 primary_field_id 时回退到第一个可展示字段，
                    # 否则反向字段没有 displayFieldId，水果表侧会显示记录 ID。
                    candidates = db.session.execute(
                        select(Field).where(Field.table_id == str(table_id)).order_by(Field.order)
                    ).scalars().all()
                    excluded_types = {
                        FieldType.LINK_TO_RECORD.value, FieldType.LINK.value,
                        FieldType.LOOKUP.value, FieldType.ATTACHMENT.value,
                        FieldType.FORMULA.value,
                    }
                    for candidate in candidates:
                        if candidate.type in excluded_types:
                            continue
                        inverse_display_field_id = str(candidate.id)
                        break
                inverse_field_data = {
                    'name': translate('inverse_link_field_name', table=source_table_name),
                    'type': FieldType.LINK_TO_RECORD.value,
                    'description': translate('inverse_link_field_description', table=source_table_name),
                    'config': {
                        'linkedTableId': table_id,
                        'relationshipType': inverse_relationship_type,
                        'displayFieldId': inverse_display_field_id,
                        'bidirectional': True,
                        'inverseFieldId': field['id']
                    }
                }
    
                inverse_result = FieldService.create_field(str(target_table_id), inverse_field_data, user_id)
                if inverse_result['success']:
                    inverse_field = inverse_result['field']
    
                    source_field = db.session.get(Field, field['id'])
                    if source_field and source_field.config:
                        config = source_field.config.copy() if source_field.config else {}
                        config['inverseFieldId'] = inverse_field['id']
                        source_field.config = config
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(source_field, 'config')
    
            link_data = {
                'source_table_id': str(table_id),
                'target_table_id': str(target_table_id),
                'source_field_id': field['id'],
                'target_field_id': inverse_field['id'] if inverse_field else None,
                'relationship_type': relationship_type,
                'bidirectional': bidirectional
            }
    
            link_result = LinkService.create_link_relation(link_data)
            if not link_result[0]:
                FieldService.delete_field(field['id'])
                if inverse_field:
                    FieldService.delete_field(inverse_field['id'])
                return {'success': False, 'error': link_result[1]}
    
            if bidirectional and inverse_field:
                inverse_relationship_type = LinkService.get_inverse_relationship_type(relationship_type)
                reverse_link_data = {
                    'source_table_id': str(target_table_id),
                    'target_table_id': str(table_id),
                    'source_field_id': inverse_field['id'],
                    'target_field_id': field['id'],
                    'relationship_type': inverse_relationship_type,
                    'bidirectional': True
                }
                reverse_link_result = LinkService.create_link_relation(reverse_link_data)
                if reverse_link_result[0]:
                    current_app.logger.info(
                        f'[LinkService] 创建反向关联关系成功: '
                        f'source_field={inverse_field["id"]}, type={inverse_relationship_type}'
                    )
    
            try:
                from app.services.collaboration_service import CollaborationService
                CollaborationService.broadcast_if_enabled('data:field_created', str(source_table.base_id), {
                    'table_id': str(table_id),
                    'field': field,
                    'changed_by': user_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                if inverse_field:
                    CollaborationService.broadcast_if_enabled('data:field_created', str(target_table.base_id), {
                        'table_id': str(target_table_id),
                        'field': inverse_field,
                        'changed_by': user_id,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
            except Exception:
                pass
    
            return {
                'success': True,
                'field': field,
                'inverse_field': inverse_field,
                'link_relation': link_result[0].to_dict() if link_result[0] else None
            }
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[LinkService] 创建关联字段失败: {str(e)}')
            return {'success': False, 'error': 'failed_create_link_field_try_again_later'}
    
    @staticmethod
    def update_link_field_relationship(
        field_id: str,
        new_relationship_type: str,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        更新关联字段的关系类型，并同步更新反向字段
    
        当一方关系类型变更时，自动调整对应数据表的关联配置
    
        Args:
            field_id: 字段 ID
            new_relationship_type: 新的关联类型
            user_id: 用户 ID
    
        Returns:
            操作结果
        """
        try:
            field = db.session.get(Field, field_id)
            if not field:
                return {'success': False, 'error': 'field_does_not_exist'}
    
            if field.type not in [FieldType.LINK_TO_RECORD.value, FieldType.LINK.value]:
                return {'success': False, 'error': 'field_not_link_type'}
    
            link_relation = LinkService.get_link_relation_by_field(field_id)
            if not link_relation:
                return {'success': False, 'error': 'link_relation_does_not_exist'}
    
            old_relationship_type = link_relation.relationship_type
            if old_relationship_type == new_relationship_type:
                return {'success': True, 'message': 'link_type_not_changed'}
    
            has_conflict, conflict_msg = LinkService.check_relationship_conflict(
                str(link_relation.source_table_id),
                str(link_relation.target_table_id),
                new_relationship_type,
                exclude_field_id=field_id
            )
            if has_conflict:
                return {'success': False, 'error': translate('link_relationship_conflict', conflict_msg)}
    
            link_relation.relationship_type = new_relationship_type
            link_relation.updated_at = datetime.now(timezone.utc)
    
            if field.config:
                config = field.config.copy() if field.config else {}
                config['relationshipType'] = new_relationship_type
                field.config = config
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(field, 'config')
    
            if link_relation.bidirectional and link_relation.target_field_id:
                inverse_relationship_type = LinkService.get_inverse_relationship_type(new_relationship_type)
    
                inverse_field = db.session.get(Field, link_relation.target_field_id)
                if inverse_field and inverse_field.config:
                    config = inverse_field.config.copy() if inverse_field.config else {}
                    config['relationshipType'] = inverse_relationship_type
                    inverse_field.config = config
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(inverse_field, 'config')
    
                reverse_relation = db.session.execute(
                    select(LinkRelation).where(
                        and_(
                            LinkRelation.source_field_id == link_relation.target_field_id,
                            LinkRelation.target_field_id == link_relation.source_field_id
                        )
                    )
                ).scalar_one_or_none()
    
                if reverse_relation:
                    reverse_relation.relationship_type = inverse_relationship_type
                    reverse_relation.updated_at = datetime.now(timezone.utc)
    
            db.session.commit()
    
            current_app.logger.info(
                f'[LinkService] 更新关联字段关系类型: field={field_id}, '
                f'{old_relationship_type} -> {new_relationship_type}'
            )
    
            return {
                'success': True,
                'field': field.to_dict(),
                'inverse_field': inverse_field.to_dict() if link_relation.target_field_id else None
            }
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[LinkService] 更新关联字段关系类型失败: {str(e)}')
            return {'success': False, 'error': 'failed_update_link_relation_type_try_again_later'}
    
