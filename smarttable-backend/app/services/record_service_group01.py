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

class RecordServiceGroup01Mixin:
    """Mixin auto-split"""
    
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
                         per_page: int = 20,
                         user_id: str = None, base_id: str = None) -> tuple:
        """
        获取表格下的记录列表
    
        Args:
            table_id: 表格 ID
            page: 页码
            per_page: 每页数量
            user_id: 用户 ID（用于数据权限过滤）
            base_id: Base ID（用于数据权限过滤）
    
        Returns:
            (记录列表, 总数量)
        """
        query = Record.query.filter_by(table_id=table_id, is_deleted=False)
        if user_id and base_id:
            try:
                from app.services.data_permission_service import DataPermissionService
            except ImportError:
                DataPermissionService = None
            all_records = query.order_by(Record.created_at.desc(), Record.id.desc()).all()
            # 使用按表过滤的新方法，传入 table_id 进行精确过滤
            filtered_records = DataPermissionService.apply_table_data_permission_filter(
                all_records, user_id, base_id, table_id
            )
            total = len(filtered_records)
            start = (page - 1) * per_page
            records = filtered_records[start:start + per_page]
            return records, total
    
        total = query.count()
        records = query.order_by(Record.created_at.desc(), Record.id.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
    
        return records, total
    
    @staticmethod
    def _target_already_has_backlink(field_id: str, target_id: str,
                                     self_record_id: str) -> bool:
        """目标记录是否已被其它记录占用反向关联（用于一对一 / 一对多的基数校验）。
    
        正向 LinkRelation 的 target_field_id 在自动创建时可能为 None，因此不依赖它，
        改为直接查「存在某条反向关联，其关系指向本关联字段、且已把目标记录作为源」，
        精确判断目标侧是否已被占用。
        """
        existing = db.session.execute(
            select(LinkValue).join(
                LinkRelation, LinkValue.link_relation_id == LinkRelation.id
            ).where(
                and_(
                    LinkRelation.target_field_id == field_id,
                    LinkValue.source_record_id == target_id,
                    LinkValue.target_record_id != self_record_id,
                )
            )
        ).scalar_one_or_none()
        return existing is not None
    
    @staticmethod
    def _strip_field_value(record, field_id) -> None:
        """从记录 values 中移除某字段（关联被判定为不可复制时，保持单元格与数据一致）"""
        values = dict(record.values or {})
        if field_id in values:
            values.pop(field_id, None)
            record.values = values
            flag_modified(record, 'values')
            db.session.commit()
    
    @staticmethod
    def _sync_link_values_from_input(record, values_input, field_map, user_id) -> None:
        """把 values 中的关联字段值同步为 LinkValue 关联记录。
    
        复制记录、批量创建（粘贴多行）、外部 API 等路径会把关联目标 ID 直接
        写进 record.values。如果不补建 LinkValue，get_record_links 与前端导出
        的显示名解析都会失败：界面显示「关联 N 条」，导出退化为裸 UUID。
        update_link_values 会把规范化后的关联列表写回 values 并处理双向镜像；
        解析失败（如目标记录已删除的坏数据）时保留原值，避免丢数据。
    
        基数约束：一对一 / 一对多的目标侧只能挂 1 条反向关联。若目标已被其它
        记录（通常是原记录）占用，则整条关联不予复制——既保证声明的关系类型
        始终成立，也不破坏原记录的关联。
        注意：update_link_values 内部会 commit/rollback，调用方应处于
        记录本体已提交的状态。
        """
        for field_id, raw in (values_input or {}).items():
            field = field_map.get(field_id)
            if not field or field.type not in (FieldType.LINK.value, FieldType.LINK_TO_RECORD.value):
                continue
            if isinstance(raw, list):
                target_ids = [str(v) for v in raw if v]
            elif raw:
                target_ids = [str(raw)]
            else:
                continue
            if not target_ids:
                continue
    
            relation, error = LinkService._get_or_create_link_relation_for_field(field)
            if not relation:
                log.warning(
                    f'[RecordService] 同步关联值失败（无法确定关联关系）: '
                    f'field={field_id}, record={record.id}, error={error}'
                )
                continue
    
            # 基数约束：一对一 / 一对多的目标侧只能挂 1 条反向关联。
            # 若该目标已被其它记录占用，整条关联不予复制。
            if relation.relationship_type in (
                RelationshipType.ONE_TO_ONE.value, RelationshipType.ONE_TO_MANY.value
            ) and any(
                RecordService._target_already_has_backlink(field_id, tid, str(record.id))
                for tid in target_ids
            ):
                log.info(
                    f'[RecordService] 复制关联跳过（目标侧基数约束）: field={field_id}, '
                    f'record={record.id}, type={relation.relationship_type}'
                )
                RecordService._strip_field_value(record, field_id)
                continue
    
            ok, err = LinkService.update_link_values(
                str(relation.id), str(record.id), target_ids, updated_by=user_id
            )
            if not ok:
                log.warning(
                    f'[RecordService] 同步关联值失败: field={field_id}, '
                    f'record={record.id}, error={err}'
                )
    
    @staticmethod
    def create_record(table_id: str, values: Dict[str, Any],
                     created_by: str = None,
                     user_id: str = None, base_id: str = None) -> Record:
        """
        创建记录
    
        创建记录时会自动应用字段的默认值（如果字段有配置默认值且提供的 values 中没有该字段）
    
        Args:
            table_id: 表格 ID
            values: 字段值字典
            created_by: 创建者 ID
            user_id: 用户 ID（用于数据权限检查）
            base_id: Base ID（用于数据权限检查）
    
        Returns:
            创建的记录对象
    
        Raises:
            PermissionError: 数据权限不足时抛出
        """
        if user_id and base_id:
            try:
                from app.services.data_permission_service import DataPermissionService
            except ImportError:
                DataPermissionService = None
            mode = DataPermissionService.get_data_permission_mode(base_id, user_id)
            if mode == 'own_data':
                if created_by and str(created_by) != str(user_id):
                    raise PermissionError(
                        "在'仅自己创建'模式下，用户只能为自己创建记录"
                    )
            log.info(
                f'[RecordService] create_record permission check: '
                f'table_id={table_id}, user_id={user_id}, mode={mode}'
            )
    
        # 获取所有字段并应用默认值
        fields = FieldService.get_all_fields(table_id)
        # 整列数据快照随记录变更失效（含同 Base 引用本表的其他表缓存）
        FormulaService.invalidate_table_context_cache(table_id=str(table_id))
    
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
                            final_values[field_id] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                        else:
                            final_values[field_id] = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                    else:
                        final_values[field_id] = default_value
    
        # 处理自动编号字段
        auto_number_fields = [f for f in fields if f.type == FieldType.AUTO_NUMBER.value]
        # 获取当前 UTC 时间作为记录的创建日期（用于自动编号的日期前缀）
        # 注意：不要在此函数内再 `from datetime import datetime`，
        # 局部导入会让 datetime 变为整个函数作用域的局部变量，
        # 导致上方默认值处理中的 datetime.now() 抛 UnboundLocalError
        record_created_at = datetime.now(timezone.utc)
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
    
        # 关联字段：复制记录等路径会直接把目标 ID 写进 values，必须补建
        # LinkValue（含 values 规范化与双向镜像），否则界面显示「关联 N 条」、
        # 导出退化为记录 ID。放在首次 commit 之后：update_link_values 内部
        # 会 commit/rollback，不能影响记录创建事务。
        RecordService._sync_link_values_from_input(record, values or {}, field_map, created_by)
    
        try:
            workflow_event_bus.publish(
                event_type='record_created',
                table_id=str(table_id),
                record_id=str(record.id),
                actor_id=str(created_by) if created_by else None
            )
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f'[RecordService] workflow_event_bus publish (create) error: {e}')
    
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
    def get_record_by_id(record_id: str,
                         user_id: str = None, base_id: str = None) -> Optional[Record]:
        """
        根据 ID 获取记录
    
        Args:
            record_id: 记录 ID
            user_id: 用户 ID（用于数据权限检查）
            base_id: Base ID（用于数据权限检查）
    
        Returns:
            记录对象或 None
        """
        record = Record.query.get(record_id)
    
        if record and user_id and base_id:
            try:
                from app.services.data_permission_service import DataPermissionService
            except ImportError:
                DataPermissionService = None
            is_accessible, reason = DataPermissionService.check_record_access(
                record_id, user_id, base_id
            )
            if not is_accessible:
                log.warning(
                    f'[RecordService] get_record_by_id access denied: '
                    f'record_id={record_id}, user_id={user_id}, reason={reason}'
                )
                return None
    
        return record
    
