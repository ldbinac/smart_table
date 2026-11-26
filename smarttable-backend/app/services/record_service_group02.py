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

class RecordServiceGroup02Mixin:
    """Mixin auto-split"""
    
    """记录服务类"""
    
    
    @staticmethod
    def update_record(record: Record, values: Dict[str, Any] = None,
                     updated_by: str = None,
                     expected_updated_at: str = None,
                     user_id: str = None, base_id: str = None,
                     commit: bool = True,
                     source: str = None,
                     changes_out: list = None) -> Record:
        """
        更新记录
    
        Args:
            record: 记录对象
            values: 更新的字段值
            updated_by: 更新者 ID
            expected_updated_at: 乐观锁预期更新时间（ISO格式字符串）
            user_id: 用户 ID（用于数据权限检查）
            base_id: Base ID（用于数据权限检查）
            source: 变更来源标记（如 'ai_field'，随 workflow_event_bus 事件
                    metadata 下发，供 AI 字段自动刷新做环路防护，B8）
            changes_out: 变更收集器（可选）。传入列表时把本次变更填入其中，
                    供批量更新（commit=False）在最终提交后补发事件使用。
    
        Returns:
            更新后的记录对象
    
        Raises:
            ConflictError: 乐观锁校验失败时抛出409冲突
            PermissionError: 数据权限不足时抛出
        """
        if user_id and base_id:
            try:
                from app.services.data_permission_service import DataPermissionService
            except ImportError:
                DataPermissionService = None
            is_accessible, reason = DataPermissionService.check_record_access(
                str(record.id), user_id, base_id
            )
            if not is_accessible:
                raise PermissionError(f'无权编辑该记录: {reason}')
    
        # 整列数据快照随记录变更失效（含同 Base 引用本表的其他表缓存）
        FormulaService.invalidate_table_context_cache(table_id=str(record.table_id))
        if expected_updated_at is not None:
            current_updated_at = record.updated_at.isoformat() if record.updated_at else None
            if current_updated_at != expected_updated_at:
                raise ConflictError('record_been_modified_another_user_refresh_try_again')
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
    
            # 字段级编辑权限检查
            if user_id and base_id and filtered_values:
                try:
                    from app.services.permission_resolver import PermissionResolver
                except ImportError:
                    PermissionResolver = None
                # 确保缓存是最新的
                PermissionResolver.clear_cache(user_id, base_id)
                allowed_field_ids = PermissionResolver.get_allowed_field_ids(
                    user_id, base_id, permission_type='write',
                    table_id=str(record.table_id)
                )
                allowed_field_ids_set = set(allowed_field_ids)
                filtered_values = {
                    k: v for k, v in filtered_values.items()
                    if k in allowed_field_ids_set
                }
                if len(filtered_values) < len(values) - len(auto_number_field_ids & set(values.keys())):
                    log.warning(
                        f'[RecordService] update_record field write permission filtered: '
                        f'record_id={record.id}, user_id={user_id}, '
                        f'allowed={allowed_field_ids}, filtered_count={len(filtered_values)}'
                    )
                else:
                    log.info(
                        f'[RecordService] update_record field write permission check: '
                        f'record_id={record.id}, user_id={user_id}, '
                        f'allowed={allowed_field_ids}, total_values={len(values)}'
                    )
    
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
    
        # 变更收集器：批量更新（commit=False）在最终 commit 后据此补发事件
        if changes_out is not None and changes:
            changes_out.extend(changes)
    
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
        if commit:
            db.session.commit()
            # 事件广播仅在真正提交后触发，避免事务回滚后发送错误的实时消息；
            # 批量更新（commit=False）由调用方在最终提交后补发（emit_update_events）
            if changes:
                RecordService.emit_update_events(record, changes,
                                                 updated_by=updated_by,
                                                 source=source)
            # 粘贴到关联单元格等路径可能直接写关联目标 ID，同步补建 LinkValue。
            # 仅在独立提交时执行：workflow 事务（commit=False）中 update_link_values
            # 的内部 commit 会破坏多表一致性。
            if values:
                RecordService._sync_link_values_from_input(record, values, field_map, updated_by)
    
        return record
    
    @staticmethod
    def emit_update_events(record: Record, changes: list,
                           updated_by: str = None, source: str = None) -> None:
        """
        记录提交后的事件广播：workflow 触发（record_updated）+ realtime 协同
        刷新（data:record_updated）。
    
        单条更新（update_record commit=True）内部调用；批量更新（commit=False
        分批提交）由调用方在最终提交后逐条补发，否则前端表格不会自动刷新、
        AI 字段自动触发也不会工作。
        """
        if not changes:
            return
        # workflow 事件（自动化触发、AI 字段自动刷新等）
        try:
            change_dict = {
                change['field_id']: {
                    'old_value': change['old_value'],
                    'new_value': change['new_value']
                }
                for change in changes
            }
            workflow_event_bus.publish(
                event_type='record_updated',
                table_id=str(record.table_id),
                record_id=str(record.id),
                changes=change_dict,
                actor_id=str(updated_by) if updated_by else None,
                metadata={'source': source} if source else None
            )
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f'[RecordService] workflow_event_bus publish (update) error: {e}')
    
        # realtime 协同广播（其他在线客户端的表格自动刷新）
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
    
    @staticmethod
    def _get_self_referencing_link_fields(table_id: str):
        """
        获取表格中所有自引用的 LINK_TO_RECORD 字段
    
        自引用字段是指关联目标表与当前表相同的 LINK_TO_RECORD 字段。
        这些字段用于表示表格内部的父子关系。
    
        Args:
            table_id: 表格 ID
    
        Returns:
            自引用 LINK_TO_RECORD 字段列表
        """
        fields = Field.query.filter_by(
            table_id=table_id,
            type=FieldType.LINK_TO_RECORD.value
        ).all()
    
        self_ref_fields = []
        for field in fields:
            # 从 config 或 options 中获取 linkedTableId
            linked_table_id = None
            for storage in (field.config, field.options):
                if storage and isinstance(storage, dict):
                    linked_table_id = storage.get('linkedTableId') or storage.get('linked_table_id')
                    if linked_table_id:
                        break
            # 如果关联的目标表与当前表相同，则为自引用字段
            if linked_table_id and str(linked_table_id) == str(table_id):
                self_ref_fields.append(field)
    
        return self_ref_fields
    
    @staticmethod
    def _clear_parent_references(record_id: str, table_id: str):
        """
        清除记录作为父记录时的子记录引用
    
        当一条记录被删除时，如果它是其他记录的父记录（即其他记录的自引用字段值中包含该记录 ID），
        需要清除这些子记录中的引用，使其成为孤儿记录（不被删除）。
    
        Args:
            record_id: 被删除的记录 ID
            table_id: 表格 ID
        """
        self_ref_fields = RecordService._get_self_referencing_link_fields(table_id)
    
        for field in self_ref_fields:
            field_id = str(field.id)
            # 查找所有子记录：values[field_id] 中包含 record_id 的记录
            children = Record.query.filter(
                Record.table_id == table_id,
                cast(Record.values[field_id], String).contains(record_id)
            ).all()
    
            for child in children:
                current_values = dict(child.values) if child.values else {}
                field_value = current_values.get(field_id)
    
                if isinstance(field_value, list):
                    # 从列表中移除被删除的记录 ID
                    filtered = [v for v in field_value if str(v) != str(record_id)]
                    if len(filtered) != len(field_value):
                        current_values[field_id] = filtered
                        child.values = current_values
                        flag_modified(child, 'values')
                        log.info(
                            f'[RecordService] 清除子记录 {child.id} 的父引用（字段 {field_id}），'
                            f'移除记录 {record_id}'
                        )
                elif field_value and str(field_value) == str(record_id):
                    # 单值情况
                    current_values[field_id] = None
                    child.values = current_values
                    flag_modified(child, 'values')
                    log.info(
                        f'[RecordService] 清除子记录 {child.id} 的父引用（字段 {field_id}），'
                        f'移除记录 {record_id}'
                    )
    
    @staticmethod
    def _delete_descendants(record_id: str, table_id: str, deleted_by: str = None):
        """
        递归删除记录的所有后代记录（级联删除）
    
        当一条记录被删除时，查找其所有子记录（通过自引用 LINK_TO_RECORD 字段），
        并递归删除这些子记录及其后代。
    
        Args:
            record_id: 被删除的记录 ID
            table_id: 表格 ID
            deleted_by: 删除者 ID
        """
        self_ref_fields = RecordService._get_self_referencing_link_fields(table_id)
    
        for field in self_ref_fields:
            field_id = str(field.id)
            # 查找所有子记录：values[field_id] 中包含 record_id 的记录
            children = Record.query.filter(
                Record.table_id == table_id,
                cast(Record.values[field_id], String).contains(record_id)
            ).all()
    
            for child in children:
                child_id = str(child.id)
                # 先递归删除后代的记录
                RecordService._delete_descendants(child_id, table_id, deleted_by)
    
                # 为子记录创建删除历史
                snapshot = dict(child.values) if child.values else {}
                child_uuid = child.id if isinstance(child.id, uuid.UUID) else uuid.UUID(child_id)
                tbl_uuid = uuid.UUID(table_id) if isinstance(table_id, str) else table_id
                changer_id = uuid.UUID(str(deleted_by)) if deleted_by else None
    
                history = RecordHistory.create_history(
                    record_id=child_uuid,
                    table_id=tbl_uuid,
                    action=HistoryAction.DELETE,
                    changed_by=changer_id,
                    changes=None,
                    snapshot=snapshot
                )
                db.session.add(history)
    
                # 清理关联数据
                LinkService.delete_record_links(child_id)
    
                # 删除子记录
                db.session.delete(child)
                log.info(
                    f'[RecordService] 级联删除后代记录 {child_id}（父记录 {record_id}）'
                )
    
    @staticmethod
    def delete_record(record: Record, deleted_by: str = None,
                     user_id: str = None, base_id: str = None) -> bool:
        """
        删除记录
    
        删除时处理父子关系：
        - 如果记录是父记录（有子记录引用它），先清除子记录的引用（子记录成为孤儿，不被删除）
        - 如果记录有子记录，递归删除所有后代记录（级联删除）
    
        Args:
            record: 记录对象
            deleted_by: 删除者 ID
            user_id: 用户 ID（用于数据权限检查）
            base_id: Base ID（用于数据权限检查）
    
        Returns:
            是否成功
        """
        if user_id and base_id:
            try:
                from app.services.data_permission_service import DataPermissionService
            except ImportError:
                DataPermissionService = None
            is_accessible, reason = DataPermissionService.check_record_access(
                str(record.id), user_id, base_id
            )
            if not is_accessible:
                log.warning(
                    f'[RecordService] delete_record access denied: '
                    f'record_id={record.id}, user_id={user_id}, reason={reason}'
                )
                return False
    
        FormulaService.invalidate_table_context_cache(table_id=str(record.table_id))
        try:
            snapshot = dict(record.values) if record.values else {}
    
            saved_base_id = str(record.table.base_id)
            saved_table_id = str(record.table_id)
            saved_record_id = str(record.id)
    
            # 处理父子关系：
            # 1. 先递归删除所有后代记录（级联删除），
            #    必须在清除父引用之前执行，否则 _delete_descendants 无法找到子记录
            RecordService._delete_descendants(
                saved_record_id, saved_table_id, deleted_by
            )
            # 2. 清除父引用（清理可能残留的引用，确保数据一致性）
            RecordService._clear_parent_references(
                saved_record_id, saved_table_id
            )
    
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
                workflow_event_bus.publish(
                    event_type='record_deleted',
                    table_id=saved_table_id,
                    record_id=saved_record_id,
                    actor_id=str(deleted_by) if deleted_by else None,
                    metadata={'snapshot': snapshot}
                )
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f'[RecordService] workflow_event_bus publish (delete) error: {e}')
    
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
    
