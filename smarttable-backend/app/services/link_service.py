"""
关联字段服务模块
处理 LinkRelation（关联关系）和 LinkValue（关联值）的 CRUD 操作
支持双向关联的自动同步
使用 Redis 缓存优化性能
"""
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from sqlalchemy import select, and_, or_, delete
from sqlalchemy.orm import joinedload
from flask import current_app

from app.extensions import db, cache
from app.models.link_relation import LinkRelation, LinkValue, RelationshipType
from app.models.field import Field, FieldType
from app.models.record import Record
from app.models.table import Table


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


class LinkService:
    """关联字段服务类"""

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
                    return None, f'缺少必需字段: {field}'

            # 验证源字段是否存在且为 LINK_TO_RECORD 或 LINK 类型
            source_field = db.session.get(Field, data['source_field_id'])
            if not source_field:
                return None, '源字段不存在'
            if source_field.type not in [FieldType.LINK_TO_RECORD.value, FieldType.LINK.value]:
                return None, '源字段必须是关联字段类型'

            # 验证表是否存在
            source_table = db.session.get(Table, data['source_table_id'])
            target_table = db.session.get(Table, data['target_table_id'])
            if not source_table:
                return None, '源表不存在'
            if not target_table:
                return None, '目标表不存在'

            # 验证关联类型
            relationship_type = data.get('relationship_type', RelationshipType.ONE_TO_MANY.value)
            if relationship_type not in [rt.value for rt in RelationshipType]:
                return None, f'无效的关联类型: {relationship_type}'

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
                return None, '该字段已存在关联关系'

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
            return None, f'创建关联关系失败: {str(e)}'

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
                return None, '关联关系不存在'

            # 允许更新的字段
            allowed_fields = ['relationship_type', 'bidirectional', 'target_field_id']

            for field in allowed_fields:
                if field in data:
                    # 验证关联类型
                    if field == 'relationship_type':
                        if data[field] not in [rt.value for rt in RelationshipType]:
                            return None, f'无效的关联类型: {data[field]}'
                    setattr(link_relation, field, data[field])

            link_relation.updated_at = datetime.utcnow()

            current_app.logger.info(f'[LinkService] 更新关联关系: {link_relation_id}')

            db.session.commit()
            return link_relation, None

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[LinkService] 更新关联关系失败: {str(e)}')
            return None, f'更新关联关系失败: {str(e)}'

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
                return False, '关联关系不存在'

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
            return False, f'删除关联关系失败: {str(e)}'

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
            from sqlalchemy import and_
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
                return None, '关联关系不存在'

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
            return None, f'获取关联记录失败: {str(e)}'

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
                return False, '关联关系不存在'

            # 验证源记录是否存在
            source_record = db.session.get(Record, source_record_id)
            if not source_record:
                return False, '源记录不存在'

            # 验证所有目标记录是否存在且属于目标表
            target_records = []
            for target_id in target_record_ids:
                target_record = db.session.get(Record, target_id)
                if not target_record:
                    return False, f'目标记录不存在: {target_id}'
                if str(target_record.table_id) != str(link_relation.target_table_id):
                    return False, f'目标记录 {target_id} 不属于目标表'
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
                    return False, f'双向同步失败: {sync_error}'

            db.session.commit()
            return True, None

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[LinkService] 更新关联值失败: {str(e)}')
            return False, f'更新关联值失败: {str(e)}'

    @staticmethod
    def _sync_bidirectional_links(
        link_relation: LinkRelation,
        source_record_id: str,
        target_record_ids: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        同步双向关联

        Args:
            link_relation: 关联关系对象
            source_record_id: 源记录 ID
            target_record_ids: 目标记录 ID 列表

        Returns:
            (是否成功, 错误信息)
        """
        try:
            if not link_relation.target_field_id:
                return True, None  # 没有目标字段，无需同步

            # 查找或创建反向的关联关系
            reverse_relation = db.session.execute(
                select(LinkRelation).where(
                    and_(
                        LinkRelation.source_field_id == link_relation.target_field_id,
                        LinkRelation.target_field_id == link_relation.source_field_id
                    )
                )
            ).scalar_one_or_none()

            # 如果没有反向关联关系，创建一个
            if not reverse_relation:
                reverse_relation = LinkRelation(
                    source_table_id=link_relation.target_table_id,
                    target_table_id=link_relation.source_table_id,
                    source_field_id=link_relation.target_field_id,
                    target_field_id=link_relation.source_field_id,
                    relationship_type=link_relation.relationship_type,
                    bidirectional=True
                )
                db.session.add(reverse_relation)
                db.session.flush()

            # 对每个目标记录，更新其反向关联
            for target_id in target_record_ids:
                target_record = db.session.get(Record, target_id)
                if not target_record:
                    continue

                # 获取目标记录当前的反向关联
                existing_reverse = db.session.execute(
                    select(LinkValue).where(
                        and_(
                            LinkValue.link_relation_id == reverse_relation.id,
                            LinkValue.source_record_id == target_id,
                            LinkValue.target_record_id == source_record_id
                        )
                    )
                ).scalar_one_or_none()

                # 如果不存在，创建反向关联
                if not existing_reverse:
                    reverse_link = LinkValue(
                        link_relation_id=reverse_relation.id,
                        source_record_id=target_id,
                        target_record_id=source_record_id
                    )
                    db.session.add(reverse_link)

                # 更新目标记录的字段值
                target_values = target_record.values or {}
                current_links = target_values.get(str(link_relation.target_field_id), [])
                if not isinstance(current_links, list):
                    current_links = [current_links] if current_links else []
                if source_record_id not in current_links:
                    current_links.append(source_record_id)
                    target_values[str(link_relation.target_field_id)] = current_links
                    target_record.values = target_values

            # 处理已移除的关联（需要删除反向关联）
            # 获取所有应该存在的反向关联
            existing_reverse_links = db.session.execute(
                select(LinkValue).where(
                    and_(
                        LinkValue.link_relation_id == reverse_relation.id,
                        LinkValue.target_record_id == source_record_id
                    )
                )
            ).scalars().all()

            for reverse_link in existing_reverse_links:
                if str(reverse_link.source_record_id) not in target_record_ids:
                    # 删除这个反向关联
                    db.session.delete(reverse_link)

                    # 更新对应记录的字段值
                    target_record = db.session.get(Record, reverse_link.source_record_id)
                    if target_record:
                        target_values = target_record.values or {}
                        current_links = target_values.get(str(link_relation.target_field_id), [])
                        if isinstance(current_links, list) and source_record_id in current_links:
                            current_links.remove(source_record_id)
                            target_values[str(link_relation.target_field_id)] = current_links
                            target_record.values = target_values

            current_app.logger.info(
                f'[LinkService] 双向关联同步完成: link_relation={link_relation.id}'
            )

            return True, None

        except Exception as e:
            current_app.logger.error(f'[LinkService] 双向关联同步失败: {str(e)}')
            return False, str(e)

    @staticmethod
    def sync_bidirectional_link(link_relation_id: str) -> Tuple[bool, Optional[str]]:
        """
        同步双向关联（重新计算所有关联）

        Args:
            link_relation_id: 关联关系 ID

        Returns:
            (是否成功, 错误信息)
        """
        try:
            link_relation = db.session.get(LinkRelation, link_relation_id)
            if not link_relation:
                return False, '关联关系不存在'

            if not link_relation.bidirectional:
                return True, None  # 不是双向关联，无需同步

            # 获取所有关联值
            all_link_values = db.session.execute(
                select(LinkValue).where(
                    LinkValue.link_relation_id == link_relation_id
                )
            ).scalars().all()

            # 按源记录分组
            links_by_source: Dict[str, List[str]] = {}
            for link_value in all_link_values:
                source_id = str(link_value.source_record_id)
                target_id = str(link_value.target_record_id)
                if source_id not in links_by_source:
                    links_by_source[source_id] = []
                links_by_source[source_id].append(target_id)

            # 对每个源记录同步双向关联
            for source_id, target_ids in links_by_source.items():
                result, error = LinkService._sync_bidirectional_links(
                    link_relation, source_id, target_ids
                )
                if not result:
                    db.session.rollback()
                    return False, f'同步记录 {source_id} 失败: {error}'

            current_app.logger.info(
                f'[LinkService] 双向关联全量同步完成: link_relation={link_relation_id}, '
                f'处理了 {len(links_by_source)} 个源记录'
            )

            db.session.commit()
            return True, None

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[LinkService] 双向关联同步失败: {str(e)}')
            return False, f'双向关联同步失败: {str(e)}'

    @staticmethod
    def get_table_link_relations(table_id: str) -> List[LinkRelation]:
        """
        获取表格的所有关联关系（作为源表或目标表）

        Args:
            table_id: 表格 ID

        Returns:
            关联关系列表
        """
        try:
            results = db.session.execute(
                select(LinkRelation).where(
                    or_(
                        LinkRelation.source_table_id == table_id,
                        LinkRelation.target_table_id == table_id
                    )
                )
            ).scalars().all()

            return list(results)

        except Exception as e:
            current_app.logger.error(f'[LinkService] 获取表格关联关系失败: {str(e)}')
            return []

    @staticmethod
    def validate_link_constraint(
        link_relation_id: str,
        source_record_id: str,
        target_record_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        验证关联约束（如一对一约束）

        Args:
            link_relation_id: 关联关系 ID
            source_record_id: 源记录 ID
            target_record_id: 目标记录 ID

        Returns:
            (是否通过验证, 错误信息)
        """
        try:
            link_relation = db.session.get(LinkRelation, link_relation_id)
            if not link_relation:
                return False, '关联关系不存在'

            # 一对一约束检查
            if link_relation.relationship_type == RelationshipType.ONE_TO_ONE.value:
                # 检查源记录是否已有其他关联
                existing = db.session.execute(
                    select(LinkValue).where(
                        and_(
                            LinkValue.link_relation_id == link_relation_id,
                            LinkValue.source_record_id == source_record_id
                        )
                    )
                ).scalar_one_or_none()

                if existing and str(existing.target_record_id) != target_record_id:
                    return False, '一对一关联约束：源记录已有关联'

                # 检查目标记录是否已被其他源记录关联
                existing_target = db.session.execute(
                    select(LinkValue).where(
                        and_(
                            LinkRelation.id == link_relation_id,
                            LinkValue.target_record_id == target_record_id
                        )
                    )
                ).scalar_one_or_none()

                if existing_target and str(existing_target.source_record_id) != source_record_id:
                    return False, '一对一关联约束：目标记录已被其他记录关联'

            return True, None

        except Exception as e:
            current_app.logger.error(f'[LinkService] 验证关联约束失败: {str(e)}')
            return False, f'验证失败: {str(e)}'

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

            # 存入缓存
            if use_cache:
                cache.set(cache_key, result, timeout=CACHE_TTL)
                current_app.logger.debug(f'[LinkService] 缓存记录 {record_id} 的关联数据')

            return result

        except Exception as e:
            current_app.logger.error(f'[LinkService] 获取记录关联信息失败: {str(e)}')
            return {}
    
    @staticmethod
    def _get_link_display_value(target_record, field_id: str, _field_cache: dict = None) -> str:
        """
        获取关联记录的显示值
        
        优先使用关联字段配置中的 displayFieldId，如果没有配置则使用主字段
        
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
                from app.models.field import Field
                field = db.session.get(Field, field_id)
                if _field_cache is not None and field:
                    _field_cache[str(field_id)] = field
            
            if field and field.config:
                display_field_id = field.config.get('displayFieldId')
                if display_field_id:
                    display_value = target_record.values.get(str(display_field_id))
                    if display_value:
                        return str(display_value)
            
            # 如果没有配置 displayFieldId 或 displayFieldId 没有值，使用主字段
            return target_record.get_primary_value()
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

    @staticmethod
    def create_link_field(table_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建关联字段（包含字段创建、反向字段创建和关联关系创建的完整业务逻辑）
        
        Args:
            table_id: 源表 ID
            data: 创建数据，包含:
                - name: 字段名称
                - target_table_id: 目标表 ID（必需）
                - relationship_type: 关联类型（必需）
                - display_field_id: 显示字段 ID（可选）
                - bidirectional: 是否双向关联（可选，默认 False）
                - description: 描述（可选）
            
        Returns:
            包含操作结果的字典
        """
        from app.services.field_service import FieldService
        from app.services.table_service import TableService

        target_table_id = data.get('target_table_id')
        relationship_type = data.get('relationship_type')
        name = data.get('name', '关联字段')

        # 获取源表信息
        source_table = TableService.get_table_by_id(str(table_id))
        if not source_table:
            return {'success': False, 'error': '源表不存在'}

        try:
            # 1. 创建关联字段
            field_data = {
                'name': name,
                'type': FieldType.LINK_TO_RECORD.value,
                'description': data.get('description', ''),
                'config': {
                    'linkedTableId': target_table_id,
                    'relationshipType': relationship_type,
                    'displayFieldId': data.get('display_field_id'),
                    'bidirectional': data.get('bidirectional', False)
                }
            }

            result = FieldService.create_field(str(table_id), field_data)
            if not result['success']:
                return result

            field = result['field']

            # 2. 如果是双向关联，在目标表中创建反向关联字段
            inverse_field = None
            if data.get('bidirectional', False):
                inverse_relationship_type = 'one_to_many' if relationship_type == 'many_to_one' else 'many_to_one' if relationship_type == 'one_to_many' else 'one_to_one'

                inverse_field_data = {
                    'name': f"来自 {source_table.name if source_table else '源表'} 的关联",
                    'type': FieldType.LINK_TO_RECORD.value,
                    'description': f'自动创建的反向关联字段，关联到 {source_table.name if source_table else "源表"}',
                    'config': {
                        'linkedTableId': table_id,
                        'relationshipType': inverse_relationship_type,
                        'displayFieldId': None,
                        'bidirectional': True,
                        'inverseFieldId': field['id']
                    }
                }

                inverse_result = FieldService.create_field(str(target_table_id), inverse_field_data)
                if inverse_result['success']:
                    inverse_field = inverse_result['field']

            # 3. 创建关联关系
            link_data = {
                'source_table_id': str(table_id),
                'target_table_id': str(target_table_id),
                'source_field_id': field['id'],
                'target_field_id': inverse_field['id'] if inverse_field else None,
                'relationship_type': relationship_type,
                'bidirectional': data.get('bidirectional', False)
            }

            link_result = LinkService.create_link_relation(link_data)
            if not link_result[0]:
                # 回滚：删除已创建的字段
                FieldService.delete_field(field['id'])
                if inverse_field:
                    FieldService.delete_field(inverse_field['id'])
                return {'success': False, 'error': link_result[1]}

            return {
                'success': True,
                'field': field,
                'inverse_field': inverse_field,
                'link_relation': link_result[0].to_dict() if link_result[0] else None
            }

        except Exception as e:
            current_app.logger.error(f'[LinkService] 创建关联字段失败: {str(e)}')
            return {'success': False, 'error': f'创建关联字段失败: {str(e)}'}
