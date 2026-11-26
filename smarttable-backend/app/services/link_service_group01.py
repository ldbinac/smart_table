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

class LinkServiceGroup01Mixin:
    """Mixin auto-split"""
    
    """关联字段服务类"""
    
    
    @staticmethod
    def invalidate_all_record_links_cache() -> None:
        """清除所有记录关联数据的缓存（displayFieldId 等配置变更后使用）"""
        try:
            # 优先通过 Redis 扫描精确清除 link:record:*:links 键
            from app.extensions import redis_client
            if redis_client:
                pattern = _get_record_links_cache_key('*')  # link:record:*:links
                cursor = 0
                deleted = 0
                while True:
                    cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                    if keys:
                        redis_client.delete(*keys)
                        deleted += len(keys)
                    if cursor == 0:
                        break
                current_app.logger.info(f'[LinkService] 已清除所有记录关联缓存，共 {deleted} 条')
                return
        except Exception as e:
            current_app.logger.warning(f'[LinkService] Redis 清除关联缓存失败: {e}')
    
        # 无 Redis 时回退：清除 Flask-Caching 中所有缓存
        try:
            cache.clear()
            current_app.logger.info('[LinkService] 已清除 Flask-Caching 全部缓存')
        except Exception as e:
            current_app.logger.error(f'[LinkService] 清除关联缓存失败: {e}')
    
    @staticmethod
    def get_inverse_relationship_type(relationship_type: str) -> str:
        """
        获取反向关联类型
    
        根据关联关系类型返回对应的反向类型：
        - one_to_one → one_to_one
        - one_to_many → many_to_one
        - many_to_one → one_to_many
        - many_to_many → many_to_many
    
        Args:
            relationship_type: 原始关联类型
    
        Returns:
            反向关联类型
        """
        mapping = {
            RelationshipType.ONE_TO_ONE.value: RelationshipType.ONE_TO_ONE.value,
            RelationshipType.ONE_TO_MANY.value: RelationshipType.MANY_TO_ONE.value,
            RelationshipType.MANY_TO_ONE.value: RelationshipType.ONE_TO_MANY.value,
            RelationshipType.MANY_TO_MANY.value: RelationshipType.MANY_TO_MANY.value,
        }
        return mapping.get(relationship_type, RelationshipType.ONE_TO_MANY.value)
    
    @staticmethod
    def check_relationship_conflict(
        source_table_id: str,
        target_table_id: str,
        relationship_type: str,
        exclude_field_id: str = None
    ) -> Tuple[bool, Optional[str]]:
        """
        检查关联关系冲突
    
        检测是否存在冲突的关联关系配置：
        - 同一字段已有不同类型的关联
        - 目标表中已存在不兼容的关联类型
    
        Args:
            source_table_id: 源表 ID
            target_table_id: 目标表 ID
            relationship_type: 关联类型
            exclude_field_id: 排除的字段 ID（用于更新时排除自身）
    
        Returns:
            (是否存在冲突, 冲突描述)
        """
        try:
            existing_relations = db.session.execute(
                select(LinkRelation).where(
                    and_(
                        LinkRelation.source_table_id == source_table_id,
                        LinkRelation.target_table_id == target_table_id
                    )
                )
            ).scalars().all()
    
            for relation in existing_relations:
                if exclude_field_id and str(relation.source_field_id) == exclude_field_id:
                    continue
    
                if relation.relationship_type != relationship_type:
                    existing_field = db.session.get(Field, relation.source_field_id)
                    field_name = existing_field.name if existing_field else '未知字段'
                    return True, translate('link_conflict_existing_type', field_name, relation.relationship_type)
    
            return False, None
    
        except Exception as e:
            current_app.logger.error(f'[LinkService] 检查关联冲突失败: {str(e)}')
            return False, None
    
    @staticmethod
    def create_link_relation(data: Dict[str, Any]) -> Tuple[Optional[LinkRelation], Optional[str]]:
        """
        创建关联关系
    
        Args:
            data: 创建数据，包含:
                - source_table_id: 源表 ID (必需)
                - target_table_id: 目标表 ID (必需)
                - source_field_id: 源字段 ID (必需)
                - target_field_id: 目标字段 ID (可选，用于双向关联)
                - relationship_type: 关联类型，'one_to_one' 或 'one_to_many' (默认)
                - bidirectional: 是否为双向关联 (默认 False)
    
        Returns:
            (创建的关联关系对象, 错误信息)
        """
        try:
            # 验证必需字段
            required_fields = ['source_table_id', 'target_table_id', 'source_field_id']
            for field in required_fields:
                if field not in data:
                    return None, translate('missing_required_field', field)
    
            # 验证源字段是否存在且为 LINK_TO_RECORD 或 LINK 类型
            source_field = db.session.get(Field, data['source_field_id'])
            if not source_field:
                'source_field_does_not_exist'
            if source_field.type not in [FieldType.LINK_TO_RECORD.value, FieldType.LINK.value]:
                'source_field_link_type'
    
            # 验证表是否存在
            source_table = db.session.get(Table, data['source_table_id'])
            target_table = db.session.get(Table, data['target_table_id'])
            if not source_table:
                'source_table_does_not_exist'
            if not target_table:
                'target_table_does_not_exist'
    
            # 验证关联类型
            relationship_type = data.get('relationship_type', RelationshipType.ONE_TO_MANY.value)
            if relationship_type not in [rt.value for rt in RelationshipType]:
                return None, translate('invalid_link_type', relationship_type)
    
            # 检查是否已存在相同的关联关系
            existing = db.session.execute(
                select(LinkRelation).where(
                    and_(
                        LinkRelation.source_field_id == data['source_field_id'],
                        LinkRelation.target_table_id == data['target_table_id']
                    )
                )
            ).scalar_one_or_none()
    
            if existing:
                'field_already_link_relation'
    
            # 创建关联关系
            link_relation = LinkRelation(
                source_table_id=data['source_table_id'],
                target_table_id=data['target_table_id'],
                source_field_id=data['source_field_id'],
                target_field_id=data.get('target_field_id'),
                relationship_type=relationship_type,
                bidirectional=data.get('bidirectional', False)
            )
    
            db.session.add(link_relation)
            db.session.flush()
    
            current_app.logger.info(
                f'[LinkService] 创建关联关系: {link_relation.id}, '
                f'source_table={data["source_table_id"]}, target_table={data["target_table_id"]}'
            )
    
            db.session.commit()
            return link_relation, None
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[LinkService] 创建关联关系失败: {str(e)}')
            'failed_create_link_relation_try_again_later'
    
    @staticmethod
    def update_link_relation(link_relation_id: str, data: Dict[str, Any]) -> Tuple[Optional[LinkRelation], Optional[str]]:
        """
        更新关联关系
    
        Args:
            link_relation_id: 关联关系 ID
            data: 更新数据，可包含:
                - relationship_type: 关联类型
                - bidirectional: 是否为双向关联
                - target_field_id: 目标字段 ID
    
        Returns:
            (更新后的关联关系对象, 错误信息)
        """
        try:
            link_relation = db.session.get(LinkRelation, link_relation_id)
            if not link_relation:
                'link_relation_does_not_exist'
    
            # 允许更新的字段
            allowed_fields = ['relationship_type', 'bidirectional', 'target_field_id']
    
            for field in allowed_fields:
                if field in data:
                    # 验证关联类型
                    if field == 'relationship_type':
                        if data[field] not in [rt.value for rt in RelationshipType]:
                            return None, translate('invalid_link_type', data[field])
                    setattr(link_relation, field, data[field])
    
            link_relation.updated_at = datetime.now(timezone.utc)
    
            current_app.logger.info(f'[LinkService] 更新关联关系: {link_relation_id}')
    
            db.session.commit()
            return link_relation, None
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[LinkService] 更新关联关系失败: {str(e)}')
            'failed_update_link_relation_try_again_later'
    
    @staticmethod
    def delete_link_relation(link_relation_id: str) -> Tuple[bool, Optional[str]]:
        """
        删除关联关系，处理级联删除
    
        Args:
            link_relation_id: 关联关系 ID
    
        Returns:
            (是否成功, 错误信息)
        """
        try:
            link_relation = db.session.get(LinkRelation, link_relation_id)
            if not link_relation:
                'link_relation_does_not_exist'
    
            # 获取关联的 LinkValue 数量（用于日志）
            link_value_count = db.session.execute(
                select(db.func.count()).select_from(LinkValue).where(
                    LinkValue.link_relation_id == link_relation_id
                )
            ).scalar()
    
            # 删除关联关系（级联删除 LinkValue）
            db.session.delete(link_relation)
    
            current_app.logger.info(
                f'[LinkService] 删除关联关系: {link_relation_id}, '
                f'级联删除 {link_value_count} 个关联值'
            )
    
            db.session.commit()
            return True, None
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[LinkService] 删除关联关系失败: {str(e)}')
            'failed_delete_link_relation_try_again_later'
    
    @staticmethod
    def get_link_relation_by_field(field_id: str, target_table_id: str = None) -> Optional[LinkRelation]:
        """
        根据字段获取关联关系
    
        Args:
            field_id: 字段 ID
            target_table_id: 可选，目标表ID用于精确匹配
    
        Returns:
            关联关系对象或 None
        """
        try:
            # 检查字段作为源字段的关联关系
            if target_table_id:
                result = db.session.execute(
                    select(LinkRelation).where(
                        and_(
                            LinkRelation.source_field_id == field_id,
                            LinkRelation.target_table_id == target_table_id
                        )
                    )
                ).scalar_one_or_none()
            else:
                # 只根据源字段ID查询
                result = db.session.execute(
                    select(LinkRelation).where(
                        LinkRelation.source_field_id == field_id
                    )
                ).scalar_one_or_none()
    
            return result
    
        except Exception as e:
            current_app.logger.error(f'[LinkService] 获取关联关系失败: {str(e)}')
            return None
    
    @staticmethod
    def get_link_relation_by_id(link_relation_id: str) -> Optional[LinkRelation]:
        """
        根据 ID 获取关联关系
    
        Args:
            link_relation_id: 关联关系 ID
    
        Returns:
            关联关系对象或 None
        """
        try:
            return db.session.get(LinkRelation, link_relation_id)
        except Exception as e:
            current_app.logger.error(f'[LinkService] 获取关联关系失败: {str(e)}')
            return None
    
    @staticmethod
    def get_linked_records(
        link_relation_id: str,
        source_record_id: str,
        include_record_data: bool = False
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        获取关联的记录
    
        Args:
            link_relation_id: 关联关系 ID
            source_record_id: 源记录 ID
            include_record_data: 是否包含完整的记录数据
    
        Returns:
            (关联记录列表, 错误信息)
            每个记录包含: id, primary_value 等
        """
        try:
            link_relation = db.session.get(LinkRelation, link_relation_id)
            if not link_relation:
                'link_relation_does_not_exist'
    
            # 查询关联值
            link_values = db.session.execute(
                select(LinkValue).where(
                    and_(
                        LinkValue.link_relation_id == link_relation_id,
                        LinkValue.source_record_id == source_record_id
                    )
                )
            ).scalars().all()
    
            result = []
            for link_value in link_values:
                target_record = link_value.target_record
                if target_record:
                    record_data = {
                        'id': str(target_record.id),
                        'primary_value': target_record.get_primary_value()
                    }
                    if include_record_data:
                        record_data['values'] = target_record.values
                        record_data['created_at'] = target_record.created_at.isoformat()
                        record_data['updated_at'] = target_record.updated_at.isoformat()
                    result.append(record_data)
    
            return result, None
    
        except Exception as e:
            current_app.logger.error(f'[LinkService] 获取关联记录失败: {str(e)}')
            'failed_fetch_linked_records_try_again_later'
    
    @staticmethod
    def update_link_values(
        link_relation_id: str,
        source_record_id: str,
        target_record_ids: List[str],
        updated_by: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        更新关联值
    
        Args:
            link_relation_id: 关联关系 ID
            source_record_id: 源记录 ID
            target_record_ids: 目标记录 ID 列表
            updated_by: 更新者 ID
    
        Returns:
            (是否成功, 错误信息)
        """
        try:
            link_relation = db.session.get(LinkRelation, link_relation_id)
            if not link_relation:
                'link_relation_does_not_exist'
    
            # 验证源记录是否存在
            source_record = db.session.get(Record, source_record_id)
            if not source_record:
                'source_record_does_not_exist'
    
            # 验证所有目标记录是否存在且属于目标表
            target_records = []
            for target_id in target_record_ids:
                target_record = db.session.get(Record, target_id)
                if not target_record:
                    return False, translate('target_record_not_exist', target_id)
                if str(target_record.table_id) != str(link_relation.target_table_id):
                    return False, translate('target_record_not_in_target_table', target_id)
                target_records.append(target_record)
    
            # 获取现有的关联值
            existing_links = db.session.execute(
                select(LinkValue).where(
                    and_(
                        LinkValue.link_relation_id == link_relation_id,
                        LinkValue.source_record_id == source_record_id
                    )
                )
            ).scalars().all()
    
            existing_target_ids = {str(link.target_record_id) for link in existing_links}
            new_target_ids = set(target_record_ids)
    
            # 需要删除的关联
            to_delete = existing_target_ids - new_target_ids
            # 需要添加的关联
            to_add = new_target_ids - existing_target_ids
    
            # 删除不再关联的记录
            if to_delete:
                db.session.execute(
                    delete(LinkValue).where(
                        and_(
                            LinkValue.link_relation_id == link_relation_id,
                            LinkValue.source_record_id == source_record_id,
                            LinkValue.target_record_id.in_(to_delete)
                        )
                    )
                )
    
            # 添加新的关联
            for target_id in to_add:
                link_value = LinkValue(
                    link_relation_id=link_relation_id,
                    source_record_id=source_record_id,
                    target_record_id=target_id
                )
                db.session.add(link_value)
    
            # 更新源记录的字段值（用于快速查询）
            field_values = source_record.values or {}
            field_values[str(link_relation.source_field_id)] = list(new_target_ids)
            source_record.values = field_values
            flag_modified(source_record, 'values')
    
            current_app.logger.info(
                f'[LinkService] 更新关联值: link_relation={link_relation_id}, '
                f'source_record={source_record_id}, 添加 {len(to_add)}, 删除 {len(to_delete)}'
            )
    
            # 如果是双向关联，同步更新反向关联
            if link_relation.bidirectional and link_relation.target_field_id:
                sync_result, sync_error = LinkService._sync_bidirectional_links(
                    link_relation, source_record_id, list(new_target_ids)
                )
                if not sync_result:
                    db.session.rollback()
                    return False, translate('bidirectional_sync_failed', sync_error)
    
            db.session.commit()
    
            # 清除缓存：源记录和所有涉及的目标记录
            _invalidate_record_links_cache(source_record_id)
            for tid in existing_target_ids | new_target_ids:
                _invalidate_record_links_cache(tid)
    
            current_app.logger.info(
                f'[LinkService] 更新关联值成功: link_relation={link_relation_id}, '
                f'source_record={source_record_id}, 添加 {len(to_add)}, 删除 {len(to_delete)}'
            )
    
            return True, None
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[LinkService] 更新关联值失败: {str(e)}')
            'failed_update_linked_value_try_again_later'
    
    @staticmethod
    def _get_or_create_link_relation_for_field(field: Field) -> Tuple[Optional[LinkRelation], Optional[str]]:
        """
        根据关联字段获取关联关系，缺失时按字段配置自动补建
    
        Args:
            field: link 类型字段对象
    
        Returns:
            (关联关系对象或 None, 错误信息)
        """
        field_config = field.config or {}
        target_table_id = field_config.get('linkedTableId')
        if not target_table_id:
            return None, 'field_configuration_missing_linked_table_id'
    
        link_relation = LinkService.get_link_relation_by_field(str(field.id), target_table_id)
        if link_relation:
            return link_relation, None
    
        link_data = {
            'source_table_id': str(field.table_id),
            'target_table_id': str(target_table_id),
            'source_field_id': str(field.id),
            'target_field_id': None,
            'relationship_type': field_config.get('relationshipType', RelationshipType.ONE_TO_MANY.value),
            'bidirectional': field_config.get('bidirectional', False)
        }
        link_result = LinkService.create_link_relation(link_data)
        if not link_result[0]:
            return None, link_result[1] or 'failed_create_link_relation'
        return link_result[0], None
    
