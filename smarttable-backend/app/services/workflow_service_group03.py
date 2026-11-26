"""
工作流核心服务模块

提供工作流的 CRUD、状态管理、版本发布与触发匹配能力。

过滤条件操作符直接使用前端 FilterOperator 字符串（驼峰命名），
不进行前后端转换，前后端字符逻辑完全一致。
"""
import copy
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm.attributes import flag_modified

from app.i18n import translate
from app.extensions import db
from app.models.base import MemberRole
from app.models.workflow import (
    Workflow,
    WorkflowNode,
    WorkflowTrigger,
    WorkflowVersion,
    WorkflowStatus,
    WorkflowNodeType,
    WorkflowTriggerType,
)
from app.models.workflow_instance import WorkflowInstance, WorkflowInstanceStatus
from app.services.permission_service import PermissionService
from app.services import workflow_scheduler_service  # noqa: E402 — group 直接引用调度服务


log = logging.getLogger(__name__)

# 脚本节点结果变量名合法模式（字母/数字/下划线，首字符为字母或下划线，≤64 字符）
_SCRIPT_RESULT_VAR_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,63}$')


def _parse_datetime(value: Any) -> Optional[datetime]:
    """将任意值解析为 datetime 对象（含时区信息），失败返回 None"""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    try:
        text = str(value).strip()
    except Exception:
        return None
    if not text:
        return None
    # ISO 8601（含时区）
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        pass
    # 常见格式
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d'):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _resolve_date_range(range_key: str) -> tuple:
    """根据前端 isWithin 的 range key 解析 [start, end) 时间范围（UTC）"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_ms = 24 * 60 * 60
    week_ms = 7 * day_ms

    if range_key == 'today':
        return today_start, today_start + timedelta(seconds=day_ms)
    if range_key == 'yesterday':
        return today_start - timedelta(seconds=day_ms), today_start
    if range_key == 'tomorrow':
        return today_start + timedelta(seconds=day_ms), today_start + timedelta(seconds=2 * day_ms)
    if range_key == 'thisWeek':
        day_of_week = today_start.weekday()  # Monday=0
        week_start = today_start - timedelta(days=day_of_week)
        return week_start, week_start + timedelta(seconds=week_ms)
    if range_key == 'lastWeek':
        day_of_week = today_start.weekday()
        this_week_start = today_start - timedelta(days=day_of_week)
        return this_week_start - timedelta(seconds=week_ms), this_week_start
    if range_key == 'nextWeek':
        day_of_week = today_start.weekday()
        this_week_start = today_start - timedelta(days=day_of_week)
        return this_week_start + timedelta(seconds=week_ms), this_week_start + timedelta(seconds=2 * week_ms)
    if range_key == 'thisMonth':
        month_start = today_start.replace(day=1)
        next_month_start = (month_start + timedelta(days=32)).replace(day=1)
        return month_start, next_month_start
    if range_key == 'lastMonth':
        month_start = today_start.replace(day=1) - timedelta(days=1)
        month_start = month_start.replace(day=1)
        this_month_start = today_start.replace(day=1)
        return month_start, this_month_start
    if range_key == 'thisYear':
        year_start = today_start.replace(month=1, day=1)
        next_year_start = year_start.replace(year=year_start.year + 1)
        return year_start, next_year_start
    if range_key == 'lastYear':
        year_start = today_start.replace(month=1, day=1) - timedelta(days=1)
        year_start = year_start.replace(month=1, day=1)
        this_year_start = today_start.replace(month=1, day=1)
        return year_start, this_year_start
    return None, None

class WorkflowServiceGroup03Mixin:
    """Mixin auto-split"""
    
    """工作流核心服务"""
    
    NOTIFY_RECIPIENT_SOURCES = ('fixed', 'field', 'trigger_user', 'record_creator', 'base_members')
    
    
    @staticmethod
    def _validate_schedule_config(schedule: Dict[str, Any]) -> datetime:
        """校验定时器配置完整性与时间合法性，返回带时区的 start_datetime"""
        if not isinstance(schedule, dict):
            raise ValueError('timer_configuration_object')
    
        required_fields = ['start_date', 'start_time', 'repeat_type', 'end_type']
        for field in required_fields:
            if field not in schedule or schedule[field] is None or schedule[field] == '':
                raise ValueError(translate('timer_config_missing_required', field))
    
        valid_repeat_types = {'no_repeat', 'daily', 'weekly', 'monthly', 'yearly', 'weekdays', 'custom'}
        repeat_type = schedule['repeat_type']
        if repeat_type not in valid_repeat_types:
            raise ValueError(translate('repeat_type_invalid', repeat_type))
    
        if repeat_type == 'custom':
            custom_interval = schedule.get('custom_interval')
            if not isinstance(custom_interval, int) or isinstance(custom_interval, bool) or custom_interval <= 0:
                raise ValueError('custom_interval_positive_integer')
            custom_unit = schedule.get('custom_unit')
            if custom_unit not in {'day', 'week', 'month', 'year'}:
                raise ValueError('custom_unit_one_day_week_month_year')
    
        end_type = schedule['end_type']
        if end_type not in {'never', 'end_date'}:
            raise ValueError(translate('end_type_invalid', end_type))
    
        timezone_name = schedule.get('timezone')
        if timezone_name:
            try:
                tz = ZoneInfo(str(timezone_name))
            except Exception as e:
                raise ValueError(translate('timezone_invalid', timezone_name)) from e
        else:
            # 未指定时区时，使用服务器本地时区解释用户配置的日期时间
            tz = datetime.now().astimezone().tzinfo
    
        start_date = schedule['start_date']
        start_time = schedule['start_time']
        try:
            start_dt = datetime.strptime(f'{start_date} {start_time}', '%Y-%m-%d %H:%M')
        except ValueError:
            try:
                start_dt = datetime.strptime(f'{start_date} {start_time}', '%Y-%m-%dT%H:%M')
            except ValueError as e:
                raise ValueError(translate('start_datetime_format_invalid', start_date, start_time)) from e
    
        start_dt = start_dt.replace(tzinfo=tz)
    
        if end_type == 'end_date':
            end_date = schedule.get('end_date')
            if not end_date:
                raise ValueError('end_date_required_when_end_type_end_date')
            try:
                end_dt = datetime.strptime(str(end_date), '%Y-%m-%d').replace(tzinfo=tz)
            except ValueError as e:
                raise ValueError(translate('end_date_format_invalid', end_date)) from e
            if end_dt < start_dt:
                raise ValueError('end_date_earlier_than_start_date')
    
        if repeat_type == 'no_repeat':
            if start_dt <= datetime.now(timezone.utc):
                raise ValueError('start_time_after_current_utc_time_no_repeat_mode')
    
        return start_dt
    
    @staticmethod
    def _validate_record_time_config(trigger: 'WorkflowTrigger', table_id) -> None:
        """校验 record_time_reached 触发器配置：time_field_id 必须存在且为日期/日期时间类型字段"""
        from app.models.field import Field, FieldType
    
        filter_config = trigger.filter_config or {}
        time_field_id = filter_config.get('time_field_id')
        if not time_field_id:
            raise ValueError('select_time_field')
    
        field = Field.query.filter_by(id=time_field_id, table_id=table_id).first()
        if not field:
            raise ValueError(translate('time_field_not_found', time_field_id))
        field_type = field.type.value if isinstance(field.type, FieldType) else field.type
        if field_type not in (FieldType.DATE.value, FieldType.DATE_TIME.value):
            raise ValueError(translate('time_field_type_invalid', field_type))
    
    @classmethod
    def _validate_workflow_config(cls, workflow: Workflow) -> None:
        """验证工作流配置完整性，不通过时抛出 ValueError"""
        if not workflow.table_id:
            raise ValueError('workflow_linked_data_table')
    
        trigger = workflow.triggers.first()
        if trigger and trigger.trigger_type == WorkflowTriggerType.SPECIFIED_TIME:
            schedule = (trigger.filter_config or {}).get('schedule')
            if not schedule:
                raise ValueError('specified_time_trigger_schedule_configured')
            cls._validate_schedule_config(schedule)
        elif trigger and trigger.trigger_type == WorkflowTriggerType.RECORD_TIME_REACHED:
            cls._validate_record_time_config(trigger, workflow.table_id)
    
    @classmethod
    def save_version_snapshot(cls, workflow_id: Any, created_by: Any) -> Optional[WorkflowVersion]:
        """
        为暂停状态的工作流保存版本快照。
        仅当当前配置与最新版本快照存在差异时才创建新版本。
    
        Args:
            workflow_id: 工作流 ID
            created_by: 操作者 ID
    
        Returns:
            新创建的 WorkflowVersion，若无变更则返回 None
    
        Raises:
            ValueError: 工作流不存在或非暂停状态
        """
        workflow = Workflow.query.filter_by(
            id=cls._to_uuid(workflow_id),
            is_deleted=False
        ).first()
    
        if not workflow:
            raise ValueError('workflow_does_not_exist')
    
        if workflow.status != WorkflowStatus.PAUSED:
            raise ValueError('workflows_paused_status_save_version_snapshots')
    
        # 构建当前配置快照（仅对比业务字段，排除 id/workflow_id 等非实质字段）
        current_content = cls._build_content_fingerprint(workflow)
    
        # 获取最新版本快照，提取业务字段进行对比
        latest_version = WorkflowVersion.query.filter_by(
            workflow_id=workflow.id
        ).order_by(WorkflowVersion.version_number.desc()).first()
    
        if latest_version:
            latest_content = cls._extract_content_from_snapshot(latest_version.config_snapshot)
            if latest_content == current_content:
                log.info(f'[WorkflowService] 工作流 {workflow.id} 内容无变更，跳过版本快照创建')
                return None
    
        # 存在变更，创建新版本
        workflow.current_version += 1
        version = WorkflowVersion(
            workflow_id=workflow.id,
            version_number=workflow.current_version,
            config_snapshot=cls._build_version_snapshot(workflow),
            created_by=cls._to_uuid(created_by)
        )
        db.session.add(version)
        db.session.commit()
    
        log.info(
            f'[WorkflowService] 工作流 {workflow.id} 版本快照已保存: '
            f'#{workflow.current_version} (暂停状态修改)'
        )
        return version
    
    @staticmethod
    def _build_content_fingerprint(workflow: Workflow) -> Dict[str, Any]:
        """构建仅包含业务字段的指纹，用于变更对比（排除 id/workflow_id 等每次保存都会变化的字段）"""
        from app.models.workflow import _ACTION_TYPE_TO_FRONTEND, WorkflowNodeType
        nodes = workflow.nodes.order_by(WorkflowNode.order).all()
        triggers = workflow.triggers.all()
        fingerprint_nodes = []
        for node in nodes:
            node_type_value = node.node_type.value if isinstance(node.node_type, WorkflowNodeType) else node.node_type
            # 与 to_dict() 保持一致：将 action 节点转换为前端细粒度 node_type
            if node_type_value == WorkflowNodeType.ACTION.value:
                action_type = (node.config or {}).get('action_type')
                if action_type in _ACTION_TYPE_TO_FRONTEND:
                    node_type_value = _ACTION_TYPE_TO_FRONTEND[action_type]
            fingerprint_nodes.append({
                'node_type': node_type_value,
                'name': node.name,
                'config': node.config or {},
                'order': node.order,
                'next_nodes': node.next_nodes or []
                # ui_layout 为纯展示字段，不参与版本指纹
            })
        return {
            'name': workflow.name,
            'description': workflow.description,
            'nodes': fingerprint_nodes,
            'triggers': [
                {
                    'trigger_type': trigger.trigger_type.value if isinstance(trigger.trigger_type, WorkflowTriggerType) else trigger.trigger_type,
                    'filter_config': trigger.filter_config or {},
                    'field_ids': trigger.field_ids or []
                }
                for trigger in triggers
            ]
        }
    
    @staticmethod
    def _extract_content_from_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """从快照中提取业务字段指纹（与 _build_content_fingerprint 保持同构）"""
        nodes = snapshot.get('nodes', [])
        triggers = snapshot.get('triggers', [])
        return {
            'name': snapshot.get('name', ''),
            'description': snapshot.get('description'),
            'nodes': [
                {
                    'node_type': n.get('node_type'),
                    'name': n.get('name'),
                    'config': n.get('config', {}),
                    'order': n.get('order'),
                    'next_nodes': n.get('next_nodes', [])
                    # ui_layout 为纯展示字段，不参与版本指纹
                }
                for n in nodes
            ],
            'triggers': [
                {
                    'trigger_type': t.get('trigger_type'),
                    'filter_config': t.get('filter_config', {}),
                    'field_ids': t.get('field_ids', [])
                }
                for t in triggers
            ]
        }
    
    @classmethod
    def pause_workflow(cls, workflow_id: Any, user_id: Any = None) -> Optional[Workflow]:
        """暂停工作流"""
        return cls._set_status(workflow_id, WorkflowStatus.PAUSED, user_id)
    
    @classmethod
    def resume_workflow(cls, workflow_id: Any, user_id: Any = None) -> Optional[Workflow]:
        """恢复工作流为 active"""
        return cls._set_status(workflow_id, WorkflowStatus.ACTIVE, user_id)
    
    @classmethod
    def archive_workflow(cls, workflow_id: Any, user_id: Any = None) -> Optional[Workflow]:
        """归档工作流"""
        return cls._set_status(workflow_id, WorkflowStatus.ARCHIVED, user_id)
    
    @classmethod
    def _set_status(
        cls,
        workflow_id: Any,
        status: WorkflowStatus,
        user_id: Any = None
    ) -> Optional[Workflow]:
        """设置工作流状态"""
        workflow = Workflow.query.filter_by(
            id=cls._to_uuid(workflow_id),
            is_deleted=False
        ).first()
    
        if not workflow:
            return None
    
        if user_id:
            PermissionService.check_permission(
                base_id=str(workflow.base_id),
                user_id=str(user_id),
                min_role=MemberRole.EDITOR
            )
    
        workflow.status = status
        db.session.commit()
    
        # 状态变更同步调度：active 注册任务，paused/archived 移除任务
        if status == WorkflowStatus.ACTIVE:
            workflow_scheduler_service.schedule_workflow(workflow.id)
        elif status in (WorkflowStatus.PAUSED, WorkflowStatus.ARCHIVED):
            workflow_scheduler_service.unschedule_workflow(workflow.id)
    
        log.info(f'[WorkflowService] 工作流状态已更新: {workflow.id} -> {status.value}')
        return workflow
    
    @classmethod
    def match_triggers(
        cls,
        table_id: Any,
        event_type: str,
        record: Any,
        changes: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[Any] = None
    ) -> List[Workflow]:
        """
        返回匹配该事件的所有 active 工作流列表
    
        Args:
            table_id: 表格 ID
            event_type: 事件类型（record_created / record_updated / field_changed / specified_time）
            record: 触发记录对象或字典
            changes: 变更内容
            workflow_id: 可选，按工作流 ID 精确匹配（用于 specified_time 等无记录触发）
    
        Returns:
            匹配的工作流对象列表
        """
        try:
            trigger_type = WorkflowTriggerType(event_type)
        except ValueError:
            log.warning(f'[WorkflowService] 未知事件类型: {event_type}')
            return []
    
        query = WorkflowTrigger.query.join(Workflow).filter(
            Workflow.table_id == cls._to_uuid(table_id),
            Workflow.status == WorkflowStatus.ACTIVE,
            Workflow.is_deleted == False,
            WorkflowTrigger.trigger_type == trigger_type
        )
        if workflow_id is not None:
            query = query.filter(Workflow.id == cls._to_uuid(workflow_id))
        triggers = query.all()
    
        record_values = {}
        if record is not None:
            if hasattr(record, 'values'):
                record_values = record.values or {}
            elif isinstance(record, dict):
                record_values = record.get('values', record)
    
        matched_workflows = []
        seen_workflow_ids = set()
    
        for trigger in triggers:
            # record_updated / field_changed 类型需检查变更字段是否在监听列表中
            if trigger_type in (WorkflowTriggerType.RECORD_UPDATED, WorkflowTriggerType.FIELD_CHANGED):
                field_ids = trigger.field_ids or []
                if field_ids:
                    changed_field_ids = set(changes.keys()) if changes else set()
                    if not changed_field_ids.intersection(set(field_ids)):
                        continue
    
            # specified_time 不依赖记录过滤条件，按 trigger/workflow 命中即匹配
            if trigger_type == WorkflowTriggerType.SPECIFIED_TIME:
                matched = True
            else:
                filter_config = trigger.filter_config or {}
                if not filter_config:
                    matched = True
                else:
                    matched = cls._evaluate_filter_condition(filter_config, record_values, changes)
    
            if matched and trigger.workflow_id not in seen_workflow_ids:
                seen_workflow_ids.add(trigger.workflow_id)
                matched_workflows.append(trigger.workflow)
    
        return matched_workflows
    
