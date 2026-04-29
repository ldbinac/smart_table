"""
记录服务模块
"""
from typing import List, Optional, Dict, Any
import uuid
import re
from datetime import datetime, timezone

from sqlalchemy import cast, or_
from sqlalchemy.types import String

from app.extensions import db
from app.models.record import Record
from app.models.field import Field, FieldType
from app.models.record_history import RecordHistory, HistoryAction
from app.models.table import Table
from app.services.field_service import FieldService
from app.services.link_service import LinkService
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
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        # 如果解析失败，返回原始值
        return value


class RecordService:
    """记录服务类"""

    @staticmethod
    def _get_next_auto_number_sequence(table_id: str, field_id: str, field: Field) -> int:
        """
        获取自动编号字段的下一个序列号（使用 Redis 原子计数器保证并发安全）

        Args:
            table_id: 表格 ID
            field_id: 字段 ID
            field: 字段对象

        Returns:
            下一个序列号
        """
        from app.extensions import redis_client
        
        config = field.get_auto_number_config()
        start_number = config.get('startNumber', 1)
        
        redis_key = f'auto_number:seq:{table_id}:{field_id}'
        
        if redis_client:
            try:
                current = redis_client.get(redis_key)
                if current is None:
                    max_number = RecordService._get_max_sequence_from_db(table_id, field_id, config)
                    initial_value = max(max_number + 1, start_number)
                    redis_client.set(redis_key, initial_value - 1)
                
                next_seq = redis_client.incr(redis_key)
                return max(next_seq, start_number)
            except Exception as e:
                log.warning(f'[RecordService] Redis atomic counter failed, falling back to DB: {e}')
        
        return RecordService._get_next_sequence_with_lock(table_id, field_id, config)

    @staticmethod
    def _get_max_sequence_from_db(table_id: str, field_id: str, config: dict) -> int:
        """
        从数据库查询当前最大序列号

        Args:
            table_id: 表格 ID
            field_id: 字段 ID
            config: 自动编号配置

        Returns:
            当前最大序列号
        """
        import re
        
        records = Record.query.filter_by(table_id=table_id).all()
        max_number = 0
        suffix = config.get('suffix', '')
        
        for record in records:
            values = record.values or {}
            field_value = values.get(field_id)
            if field_value:
                try:
                    value_str = str(field_value)
                    if suffix and value_str.endswith(suffix):
                        value_str = value_str[:-len(suffix)]
                    match = re.search(r'.*?(\d+)$', value_str)
                    if match:
                        num = int(match.group(1))
                        max_number = max(max_number, num)
                except (ValueError, TypeError):
                    continue
        
        return max_number

    @staticmethod
    def _get_next_sequence_with_lock(table_id: str, field_id: str, config: dict) -> int:
        """
        使用数据库锁获取下一个序列号（Redis 不可用时的回退方案）

        Args:
            table_id: 表格 ID
            field_id: 字段 ID
            config: 自动编号配置

        Returns:
            下一个序列号
        """
        from sqlalchemy import select, func
        from sqlalchemy.dialects.postgresql import JSONB
        
        start_number = config.get('startNumber', 1)
        
        try:
            db.session.execute('SELECT 1')
        except:
            pass
        
        max_number = RecordService._get_max_sequence_from_db(table_id, field_id, config)
        
        return max(max_number + 1, start_number)

    @staticmethod
    def get_table_records(table_id: str, page: int = 1,
                         per_page: int = 20) -> tuple:
        """
        获取表格下的记录列表
        
        Args:
            table_id: 表格 ID
            page: 页码
            per_page: 每页数量
            
        Returns:
            (记录列表, 总数量)
        """
        query = Record.query.filter_by(table_id=table_id)
        total = query.count()
        records = query.order_by(Record.created_at.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        return records, total
    
    @staticmethod
    def create_record(table_id: str, values: Dict[str, Any],
                     created_by: str = None) -> Record:
        """
        创建记录
        
        创建记录时会自动应用字段的默认值（如果字段有配置默认值且提供的 values 中没有该字段）
        
        Args:
            table_id: 表格 ID
            values: 字段值字典
            created_by: 创建者 ID
            
        Returns:
            创建的记录对象
        """
        
        # 获取所有字段并应用默认值
        fields = FieldService.get_all_fields(table_id)
        
        # 从提供的 values 开始
        final_values = dict(values) if values else {}

        # 创建字段 ID 到字段对象的映射，用于后续处理
        field_map = {str(field.id): field for field in fields}

        # 处理日期字段值：根据字段类型格式化
        for field_id, value in list(final_values.items()):
            field = field_map.get(field_id)
            if field and field.type in [FieldType.DATE.value, FieldType.DATE_TIME.value]:
                final_values[field_id] = _format_date_value(value, field)

        # 对每个有默认值的字段，如果没有提供值，则应用默认值
        for field in fields:
            field_id = str(field.id)
            if field_id not in final_values:
                default_value = field.get_default_value()
                # 只应用非 None 的默认值
                if default_value is not None:
                    # 特殊处理动态日期默认值 'now'
                    if default_value == 'now':
                        # 根据字段类型格式化当前时间
                        if field.type == FieldType.DATE_TIME.value:
                            final_values[field_id] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            final_values[field_id] = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                    else:
                        final_values[field_id] = default_value

        # 处理自动编号字段
        auto_number_fields = [f for f in fields if f.type == FieldType.AUTO_NUMBER.value]
        # 获取当前时间作为记录的创建日期（用于自动编号的日期前缀）
        from datetime import datetime
        record_created_at = datetime.now()
        for field in auto_number_fields:
            field_id = str(field.id)
            if field_id not in final_values or not final_values[field_id]:
                # 获取当前表格中该自动编号字段的最大值
                sequence = RecordService._get_next_auto_number_sequence(table_id, field_id, field)
                # 生成自动编号，传入记录创建日期以确保日期前缀使用创建时的日期
                final_values[field_id] = field.generate_auto_number(sequence, record_created_at)

        log.info(f'create_record: {final_values}')
        record = Record(
            table_id=table_id,
            values=final_values,
            created_by=created_by,
            updated_by=created_by
        )

        db.session.add(record)
        db.session.flush()  # 获取 record.id

        # 创建变更历史记录
        # 确保 ID 是 UUID 对象
        record_id = record.id if isinstance(record.id, uuid.UUID) else uuid.UUID(str(record.id))
        tbl_id = uuid.UUID(table_id) if isinstance(table_id, str) else table_id
        # created_by 可能是 UUID 对象或字符串
        if created_by:
            changer_id = created_by if isinstance(created_by, uuid.UUID) else uuid.UUID(str(created_by))
        else:
            changer_id = None
        
        history = RecordHistory.create_history(
            record_id=record_id,
            table_id=tbl_id,
            action=HistoryAction.CREATE,
            changed_by=changer_id,
            changes=None,  # 创建操作没有变更对比
            snapshot=final_values  # 保存创建时的数据快照
        )
        db.session.add(history)

        db.session.commit()

        try:
            from app.services.collaboration_service import CollaborationService
            table = Table.query.get(table_id)
            if table:
                CollaborationService.broadcast_if_enabled('data:record_created', str(table.base_id), {
                    'table_id': table_id,
                    'record': record.to_dict(),
                    'changed_by': str(created_by) if created_by else None,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f'[RecordService] broadcast_if_enabled (create) error: {e}')

        return record
    
    @staticmethod
    def get_record_by_id(record_id: str) -> Optional[Record]:
        """
        根据 ID 获取记录
        
        Args:
            record_id: 记录 ID
            
        Returns:
            记录对象或 None
        """
        return Record.query.get(record_id)
    
    @staticmethod
    def update_record(record: Record, values: Dict[str, Any] = None,
                     updated_by: str = None,
                     expected_updated_at: str = None) -> Record:
        """
        更新记录

        Args:
            record: 记录对象
            values: 更新的字段值
            updated_by: 更新者 ID
            expected_updated_at: 乐观锁预期更新时间（ISO格式字符串）

        Returns:
            更新后的记录对象

        Raises:
            ConflictError: 乐观锁校验失败时抛出409冲突
        """
        if expected_updated_at is not None:
            current_updated_at = record.updated_at.isoformat() if record.updated_at else None
            if current_updated_at != expected_updated_at:
                raise ConflictError('记录已被其他用户修改，请刷新后重试')
        # 保存旧值用于历史记录
        old_values = dict(record.values) if record.values else {}
        changes = []

        if values:
            # 获取表格的所有字段，用于处理日期字段
            fields = FieldService.get_all_fields(str(record.table_id))
            field_map = {str(field.id): field for field in fields}

            # 过滤掉自动编号字段的修改（自动编号字段不可编辑）
            auto_number_field_ids = {
                str(field.id) for field in fields
                if field.type == FieldType.AUTO_NUMBER.value
            }
            filtered_values = {
                k: v for k, v in values.items()
                if k not in auto_number_field_ids
            }

            # 如果有尝试修改自动编号字段的情况，记录日志
            if len(filtered_values) < len(values):
                from flask import current_app
                current_app.logger.warning(
                    f'[RecordService] Attempt to modify auto_number fields blocked. '
                    f'Record: {record.id}, Fields: {auto_number_field_ids & set(values.keys())}'
                )

            # 处理日期字段值：根据字段类型格式化
            formatted_values = {}
            for field_id, new_value in filtered_values.items():
                field = field_map.get(field_id)
                if field and field.type in [FieldType.DATE.value, FieldType.DATE_TIME.value]:
                    formatted_values[field_id] = _format_date_value(new_value, field)
                else:
                    formatted_values[field_id] = new_value

            # 计算变更的字段
            for field_id, new_value in formatted_values.items():
                old_value = old_values.get(field_id)
                # 只有当值真正发生变化时才记录
                if old_value != new_value:
                    changes.append({
                        'field_id': field_id,
                        'old_value': old_value,
                        'new_value': new_value
                    })

            # 合并新值到现有值
            # 创建新的字典对象，确保 SQLAlchemy 检测到变化
            current_values = dict(old_values)
            current_values.update(formatted_values)
            # 直接赋值新字典对象，SQLAlchemy 会检测到变化
            record.values = current_values

        if updated_by:
            record.updated_by = updated_by

        # 如果有变更，创建历史记录
        if changes:
            # 确保 ID 是 UUID 对象
            record_id = record.id if isinstance(record.id, uuid.UUID) else uuid.UUID(str(record.id))
            table_id = record.table_id if isinstance(record.table_id, uuid.UUID) else uuid.UUID(str(record.table_id))
            # changed_by 可能是 UUID 对象或字符串
            if updated_by:
                changed_by = updated_by if isinstance(updated_by, uuid.UUID) else uuid.UUID(str(updated_by))
            else:
                changed_by = None
            
            history = RecordHistory.create_history(
                record_id=record_id,
                table_id=table_id,
                action=HistoryAction.UPDATE,
                changed_by=changed_by,
                changes=changes,
                snapshot=dict(record.values)  # 保存更新后的快照
            )
            db.session.add(history)

        # 刷新对象以确保获取最新的数据库状态
        db.session.flush()
        db.session.commit()

        try:
            from app.services.collaboration_service import CollaborationService
            table = Table.query.get(str(record.table_id))
            if table:
                CollaborationService.broadcast_if_enabled('data:record_updated', str(table.base_id), {
                    'table_id': str(record.table_id),
                    'record_id': str(record.id),
                    'changes': changes,
                    'changed_by': str(updated_by) if updated_by else None,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f'[RecordService] broadcast_if_enabled error: {e}')

        return record
    
    @staticmethod
    def delete_record(record: Record, deleted_by: str = None) -> bool:
        """
        删除记录

        Args:
            record: 记录对象
            deleted_by: 删除者 ID

        Returns:
            是否成功
        """
        try:
            snapshot = dict(record.values) if record.values else {}

            saved_base_id = str(record.table.base_id)
            saved_table_id = str(record.table_id)
            saved_record_id = str(record.id)

            # 创建删除历史记录
            # 确保 ID 是 UUID 对象
            record_id = record.id if isinstance(record.id, uuid.UUID) else uuid.UUID(str(record.id))
            table_id = record.table_id if isinstance(record.table_id, uuid.UUID) else uuid.UUID(str(record.table_id))
            # deleted_by 可能是 UUID 对象或字符串
            if deleted_by:
                changer_id = deleted_by if isinstance(deleted_by, uuid.UUID) else uuid.UUID(str(deleted_by))
            else:
                changer_id = None
            
            history = RecordHistory.create_history(
                record_id=record_id,
                table_id=table_id,
                action=HistoryAction.DELETE,
                changed_by=changer_id,
                changes=None,  # 删除操作没有字段变更对比
                snapshot=snapshot  # 保存删除前的完整数据
            )
            db.session.add(history)

            # 清理关联数据
            LinkService.delete_record_links(str(record_id))

            db.session.delete(record)
            db.session.commit()

            try:
                from app.services.collaboration_service import CollaborationService
                CollaborationService.broadcast_if_enabled('data:record_deleted', saved_base_id, {
                    'table_id': saved_table_id,
                    'record_id': saved_record_id,
                    'snapshot': snapshot,
                    'changed_by': str(deleted_by) if deleted_by else None,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f'[RecordService] broadcast_if_enabled (delete) error: {e}')

            return True
        except Exception as e:
            db.session.rollback()
            from flask import current_app
            current_app.logger.error(f'[RecordService] 删除记录失败：{record_id}, 错误：{str(e)}')
            return False
    
    @staticmethod
    def search_records(table_id: str, query: str, 
                      field_ids: List[str] = None) -> List[Record]:
        """
        搜索记录
        
        Args:
            table_id: 表格 ID
            query: 搜索关键词
            field_ids: 要搜索的字段 ID 列表
            
        Returns:
            记录列表
        """
        escaped_query = _escape_like_pattern(query)
        like_pattern = f'%{escaped_query}%'
        
        query_obj = Record.query.filter_by(table_id=table_id)
        
        if field_ids:
            valid_field_ids = []
            uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
            for field_id in field_ids:
                if uuid_pattern.match(str(field_id)):
                    valid_field_ids.append(field_id)
                else:
                    log.warning(f'[RecordService] Invalid field_id format, skipped: {field_id}')
            
            if valid_field_ids:
                conditions = []
                for field_id in valid_field_ids:
                    conditions.append(
                        cast(Record.values[field_id].astext, String).ilike(like_pattern)
                    )
                if conditions:
                    query_obj = query_obj.filter(or_(*conditions))
        else:
            query_obj = query_obj.filter(
                cast(Record.values.astext, String).ilike(like_pattern)
            )
        
        results = query_obj.all()
        return results
