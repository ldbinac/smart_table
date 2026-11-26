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

class WorkflowServiceGroup02Mixin:
    """Mixin auto-split"""
    
    """工作流核心服务"""
    
    NOTIFY_RECIPIENT_SOURCES = ('fixed', 'field', 'trigger_user', 'record_creator', 'base_members')
    
    
    @classmethod
    def create_workflow(
        cls,
        base_id: Any,
        table_id: Any,
        name: str,
        description: Optional[str] = None,
        created_by: Any = None,
        trigger_config: Optional[Dict[str, Any]] = None,
        nodes_config: Optional[List[Dict[str, Any]]] = None
    ) -> Workflow:
        """
        创建草稿状态的工作流
    
        Args:
            base_id: 所属 Base ID
            table_id: 关联表格 ID
            name: 工作流名称
            description: 描述
            created_by: 创建者 ID
            trigger_config: 触发器配置
            nodes_config: 节点配置列表
    
        Returns:
            创建的工作流对象
        """
        if created_by:
            if not PermissionService.check_permission(
                base_id=str(base_id),
                user_id=str(created_by),
                min_role=MemberRole.EDITOR
            ):
                raise PermissionError('权限不足，需要 EDITOR 或以上角色')
    
        workflow = Workflow(
            base_id=cls._to_uuid(base_id),
            table_id=cls._to_uuid(table_id),
            name=name,
            description=description,
            status=WorkflowStatus.DRAFT,
            created_by=cls._to_uuid(created_by)
        )
    
        db.session.add(workflow)
        db.session.flush()
    
        if trigger_config:
            trigger_type = trigger_config.get('trigger_type')
            trigger = WorkflowTrigger(
                workflow_id=workflow.id,
                trigger_type=WorkflowTriggerType(trigger_type) if trigger_type else WorkflowTriggerType.RECORD_CREATED,
                filter_config=cls._clean_filter_config(trigger_config.get('filter_config', {})),
                field_ids=trigger_config.get('field_ids', [])
            )
            db.session.add(trigger)
    
        if nodes_config:
            # 细粒度类型直接作为 WorkflowNodeType 枚举值存储，
            # 不再转换为 ACTION + config.action_type。
            # 保留对旧 'action' + config.action_type 的兼容升级。
            _ACTION_TYPE_UPGRADE = {
                'update_record': 'update_record',
                'create_record': 'create_record',
                'send_email': 'send_email',
                'trigger_webhook': 'trigger_webhook',
                'find_records': 'find_records',
            }
            # 单个工作流最多 5 个循环节点（含嵌套循环体内的）
            loop_count = cls._count_loop_nodes(nodes_config)
            if loop_count > 5:
                raise ValueError('single_workflow_most_loop_nodes')
    
            # 收集所有顶层节点 id（str 形式），用于校验脚本分支目标存在性
            all_node_ids = {
                str(n.get('id'))
                for n in nodes_config
                if isinstance(n, dict) and n.get('id') is not None
            }
    
            for index, node_data in enumerate(nodes_config):
                node_type = node_data.get('node_type', 'action')
                node_config = dict(node_data.get('config', {}))
                if node_type == 'loop':
                    cls._validate_loop_node(node_data)
                elif node_type == 'script':
                    cls._validate_script_node(node_data, all_node_ids)
                elif node_type == 'update_record':
                    cls._validate_update_record_node(node_data)
                elif node_type == 'notify':
                    cls._validate_notify_node(node_data)
                elif node_type == 'action':
                    # 兼容：旧 'action' + config.action_type 升级为细粒度 node_type
                    action_type = node_config.get('action_type')
                    if action_type and action_type in _ACTION_TYPE_UPGRADE:
                        node_type = _ACTION_TYPE_UPGRADE[action_type]
                if node_type == 'condition':
                    node_config = cls._normalize_condition_config(node_config)
                    node_config = cls._clean_condition_config(node_config)
                node = WorkflowNode(
                    workflow_id=workflow.id,
                    node_type=WorkflowNodeType(node_type),
                    name=node_data.get('name', f'节点 {index + 1}'),
                    config=node_config,
                    order=node_data.get('order', index),
                    next_nodes=node_data.get('next_nodes', []),
                    ui_layout=node_data.get('ui_layout', {})
                )
                db.session.add(node)
    
        db.session.commit()
        log.info(f'[WorkflowService] 工作流已创建: {workflow.id}')
        return workflow
    
    @classmethod
    def get_workflow(cls, workflow_id: Any) -> Optional[Dict[str, Any]]:
        """
        获取工作流详情（含当前版本、节点）
    
        Args:
            workflow_id: 工作流 ID
    
        Returns:
            详情字典，未找到返回 None
        """
        workflow = Workflow.query.filter_by(
            id=cls._to_uuid(workflow_id),
            is_deleted=False
        ).first()
    
        if not workflow:
            return None
    
        current_version = WorkflowVersion.query.filter_by(
            workflow_id=workflow.id,
            version_number=workflow.current_version
        ).first()
    
        return {
            'workflow': workflow.to_dict(),
            'current_version': current_version.to_dict() if current_version else None,
            'nodes': [node.to_dict() for node in workflow.nodes.order_by(WorkflowNode.order).all()],
            'triggers': [trigger.to_dict() for trigger in workflow.triggers.all()]
        }
    
    @classmethod
    def update_workflow(
        cls,
        workflow_id: Any,
        user_id: Any = None,
        **kwargs
    ) -> Optional[Workflow]:
        """
        更新工作流（仅 draft 状态可编辑节点与触发器）
    
        Args:
            workflow_id: 工作流 ID
            user_id: 操作者 ID（用于权限校验）
            **kwargs: 更新字段
    
        Returns:
            更新后的工作流对象，未找到或非 draft 返回 None
        """
        workflow = Workflow.query.filter_by(
            id=cls._to_uuid(workflow_id),
            is_deleted=False
        ).first()
    
        if not workflow:
            return None
    
        if user_id:
            if not PermissionService.check_permission(
                base_id=str(workflow.base_id),
                user_id=str(user_id),
                min_role=MemberRole.EDITOR
            ):
                raise PermissionError('权限不足，需要 EDITOR 或以上角色')
    
        # 名称和描述：任何状态均可编辑
        for field_name in ('name', 'description'):
            if field_name in kwargs:
                setattr(workflow, field_name, kwargs[field_name])
    
        # 关联数据表：仅草稿状态可编辑
        if 'table_id' in kwargs:
            if workflow.status != WorkflowStatus.DRAFT:
                log.warning(f'[WorkflowService] 仅草稿状态可变更数据表: {workflow_id}')
                return None
            setattr(workflow, 'table_id', kwargs['table_id'])
    
        # 节点和触发器配置：仅草稿状态可编辑
        has_structure_changes = 'trigger_config' in kwargs or 'nodes_config' in kwargs
        if has_structure_changes:
            if workflow.status != WorkflowStatus.DRAFT:
                log.warning(f'[WorkflowService] 仅草稿状态可编辑节点和触发器: {workflow_id}')
                return None
    
        if 'trigger_config' in kwargs:
            WorkflowTrigger.query.filter_by(workflow_id=workflow.id).delete()
            trigger_config = kwargs['trigger_config']
            if trigger_config:
                trigger_type = trigger_config.get('trigger_type')
                trigger = WorkflowTrigger(
                    workflow_id=workflow.id,
                    trigger_type=WorkflowTriggerType(trigger_type) if trigger_type else WorkflowTriggerType.RECORD_CREATED,
                    filter_config=cls._clean_filter_config(trigger_config.get('filter_config', {})),
                    field_ids=trigger_config.get('field_ids', [])
                )
                db.session.add(trigger)
                if trigger.trigger_type == WorkflowTriggerType.SPECIFIED_TIME:
                    schedule = trigger.filter_config.get('schedule')
                    if not schedule:
                        raise ValueError('specified_time_trigger_schedule_configured')
                    cls._validate_schedule_config(schedule)
    
        if 'nodes_config' in kwargs:
            WorkflowNode.query.filter_by(workflow_id=workflow.id).delete()
            nodes_config = kwargs['nodes_config']
            if nodes_config:
                # 单个工作流最多 5 个循环节点（含嵌套循环体内的）
                loop_count = cls._count_loop_nodes(nodes_config)
                if loop_count > 5:
                    raise ValueError('single_workflow_most_loop_nodes')
    
                # 收集所有顶层节点 id（str 形式），用于校验脚本分支目标存在性
                all_node_ids = {
                    str(n.get('id'))
                    for n in nodes_config
                    if isinstance(n, dict) and n.get('id') is not None
                }
    
                _ACTION_TYPE_UPGRADE = {
                    'update_record': 'update_record',
                    'create_record': 'create_record',
                    'send_email': 'send_email',
                    'trigger_webhook': 'trigger_webhook',
                    'find_records': 'find_records',
                }
                for index, node_data in enumerate(nodes_config):
                    node_type_str = node_data.get('node_type', 'action')
                    config = dict(node_data.get('config', {}))
                    if node_type_str == 'loop':
                        cls._validate_loop_node(node_data)
                    elif node_type_str == 'script':
                        cls._validate_script_node(node_data, all_node_ids)
                    elif node_type_str == 'update_record':
                        cls._validate_update_record_node(node_data)
                    elif node_type_str == 'notify':
                        cls._validate_notify_node(node_data)
                    elif node_type_str == 'action':
                        # 兼容：旧 'action' + config.action_type 升级为细粒度 node_type
                        action_type = config.get('action_type')
                        if action_type and action_type in _ACTION_TYPE_UPGRADE:
                            node_type_str = _ACTION_TYPE_UPGRADE[action_type]
                    if node_type_str == 'condition':
                        config = cls._normalize_condition_config(config)
                        config = cls._clean_condition_config(config)
                    node = WorkflowNode(
                        workflow_id=workflow.id,
                        node_type=WorkflowNodeType(node_type_str),
                        name=node_data.get('name', f'节点 {index + 1}'),
                        config=config,
                        order=node_data.get('order', index),
                        next_nodes=node_data.get('next_nodes', []),
                        ui_layout=node_data.get('ui_layout', {})
                    )
                    db.session.add(node)
    
        db.session.commit()
        log.info(f'[WorkflowService] 工作流已更新: {workflow.id}')
        return workflow
    
    @classmethod
    def delete_workflow(cls, workflow_id: Any, user_id: Any = None) -> bool:
        """
        软删除工作流，并将进行中的实例标记为 cancelled
    
        Args:
            workflow_id: 工作流 ID
            user_id: 操作者 ID（用于权限校验）
    
        Returns:
            是否删除成功
        """
        workflow = Workflow.query.filter_by(
            id=cls._to_uuid(workflow_id),
            is_deleted=False
        ).first()
    
        if not workflow:
            return False
    
        if user_id:
            if not PermissionService.check_permission(
                base_id=str(workflow.base_id),
                user_id=str(user_id),
                min_role=MemberRole.EDITOR
            ):
                raise PermissionError('权限不足，需要 EDITOR 或以上角色')
    
        workflow.is_deleted = True
    
        running_instances = WorkflowInstance.query.filter_by(
            workflow_id=workflow.id,
            status=WorkflowInstanceStatus.RUNNING
        ).all()
    
        for instance in running_instances:
            instance.status = WorkflowInstanceStatus.CANCELLED
            instance.completed_at = datetime.now(timezone.utc)
    
        db.session.commit()
    
        # 删除工作流后移除对应调度任务
        workflow_scheduler_service.unschedule_workflow(workflow.id)
    
        log.info(f'[WorkflowService] 工作流已软删除: {workflow_id}')
        return True
    
    @classmethod
    def clone_workflow(cls, workflow_id: Any, user_id: Any = None) -> Optional[Workflow]:
        """
        基于现有工作流创建副本（草稿状态）
    
        Args:
            workflow_id: 源工作流 ID
            user_id: 操作者 ID（用于权限校验）
    
        Returns:
            新创建的草稿工作流对象
        """
        workflow = Workflow.query.filter_by(
            id=cls._to_uuid(workflow_id),
            is_deleted=False
        ).first()
    
        if not workflow:
            return None
    
        if user_id:
            if not PermissionService.check_permission(
                base_id=str(workflow.base_id),
                user_id=str(user_id),
                min_role=MemberRole.EDITOR
            ):
                raise PermissionError('权限不足，需要 EDITOR 或以上角色')
    
        cloned = Workflow(
            base_id=workflow.base_id,
            table_id=workflow.table_id,
            name=f'{workflow.name}-副本',
            description=workflow.description,
            status=WorkflowStatus.DRAFT,
            created_by=cls._to_uuid(user_id)
        )
        db.session.add(cloned)
        db.session.flush()
    
        # 第一遍：创建所有节点（占位 next_nodes 与深拷贝 config），构建 old_id -> new_id 映射
        # 新节点由模型默认 default=uuid.uuid4 在 flush 时获得新 UUID，
        # 因此源工作流中的节点 ID 引用（next_nodes、branches.target_node_id）
        # 必须基于映射重写，否则克隆后的引用会指向源工作流的旧节点 ID。
        id_mapping: Dict[str, str] = {}
        new_nodes_by_old_id: Dict[str, WorkflowNode] = {}
    
        for node in workflow.nodes.order_by(WorkflowNode.order).all():
            new_config = copy.deepcopy(node.config) if node.config else {}
            new_node = WorkflowNode(
                workflow_id=cloned.id,
                node_type=node.node_type,
                name=node.name,
                config=new_config,
                order=node.order,
                next_nodes=[],  # 占位，第二遍基于 id_mapping 重写
                ui_layout=node.ui_layout
            )
            db.session.add(new_node)
            new_nodes_by_old_id[str(node.id)] = new_node
    
        db.session.flush()
        for old_id_str, new_node in new_nodes_by_old_id.items():
            id_mapping[old_id_str] = str(new_node.id)
    
        # 第二遍：基于 id_mapping 重写 next_nodes 与条件节点 branches.target_node_id
        # 仅重映射存在于映射中的引用，过滤失效引用；不重映射 webhook_id 等外部资源 ID
        for node in workflow.nodes.order_by(WorkflowNode.order).all():
            new_node = new_nodes_by_old_id[str(node.id)]
    
            remapped_next = [
                id_mapping[old_ref]
                for old_ref in (node.next_nodes or [])
                if old_ref in id_mapping
            ]
            new_node.next_nodes = remapped_next
    
            if node.node_type == WorkflowNodeType.CONDITION and isinstance(new_node.config, dict):
                branches = new_node.config.get('branches')
                if isinstance(branches, list):
                    for branch in branches:
                        if not isinstance(branch, dict):
                            continue
                        old_target = branch.get('target_node_id')
                        if old_target and old_target in id_mapping:
                            branch['target_node_id'] = id_mapping[old_target]
                    # 普通 JSON 列不跟踪就地变更，需显式标记以触发 UPDATE
                    flag_modified(new_node, "config")
    
        for trigger in workflow.triggers.all():
            new_trigger = WorkflowTrigger(
                workflow_id=cloned.id,
                trigger_type=trigger.trigger_type,
                filter_config=trigger.filter_config,
                field_ids=trigger.field_ids
            )
            db.session.add(new_trigger)
    
        db.session.commit()
        log.info(f'[WorkflowService] 工作流已克隆: {workflow.id} -> {cloned.id}')
        return cloned
    
    @classmethod
    def list_workflow_versions(cls, workflow_id: Any) -> List[WorkflowVersion]:
        """
        获取工作流的所有历史版本
    
        Args:
            workflow_id: 工作流 ID
    
        Returns:
            WorkflowVersion 列表（按版本号降序）
        """
        workflow = Workflow.query.filter_by(
            id=cls._to_uuid(workflow_id),
            is_deleted=False
        ).first()
    
        if not workflow:
            return []
    
        return WorkflowVersion.query.filter_by(
            workflow_id=workflow.id
        ).order_by(WorkflowVersion.version_number.desc()).all()
    
    @classmethod
    def list_workflows(
        cls,
        table_id: Any = None,
        base_id: Any = None,
        status: Optional[str] = None,
        user_id: Any = None
    ) -> List[Workflow]:
        """
        工作流列表查询
    
        Args:
            table_id: 表格 ID 过滤
            base_id: Base ID 过滤
            status: 状态过滤
            user_id: 操作者 ID（用于权限校验，列表需 VIEWER 及以上）
    
        Returns:
            工作流对象列表
        """
        if base_id and user_id:
            if not PermissionService.check_permission(
                base_id=str(base_id),
                user_id=str(user_id),
                min_role=MemberRole.VIEWER
            ):
                return []
    
        query = Workflow.query.filter_by(is_deleted=False)
    
        if table_id:
            query = query.filter_by(table_id=cls._to_uuid(table_id))
        if base_id:
            query = query.filter_by(base_id=cls._to_uuid(base_id))
        if status:
            query = query.filter_by(status=WorkflowStatus(status))
    
        return query.order_by(Workflow.updated_at.desc()).all()
    
    @classmethod
    def publish_workflow(cls, workflow_id: Any, created_by: Any) -> Optional[Workflow]:
        """
        发布工作流：生成新的 WorkflowVersion 快照，状态变为 active
    
        Args:
            workflow_id: 工作流 ID
            created_by: 发布者 ID
    
        Returns:
            发布后的工作流对象
    
        Raises:
            ValueError: 状态不允许发布或配置验证失败
        """
        workflow = Workflow.query.filter_by(
            id=cls._to_uuid(workflow_id),
            is_deleted=False
        ).first()
    
        if not workflow:
            return None
    
        PermissionService.check_permission(
            base_id=str(workflow.base_id),
            user_id=str(created_by),
            min_role=MemberRole.EDITOR
        )
    
        # 状态校验：仅草稿和暂停状态可发布
        if workflow.status not in (WorkflowStatus.DRAFT, WorkflowStatus.PAUSED):
            raise ValueError(translate('workflow_publish_status_invalid', workflow.status.value))
    
        # 配置完整性验证
        cls._validate_workflow_config(workflow)
    
        previous_status = workflow.status.value
        workflow.current_version += 1
    
        version = WorkflowVersion(
            workflow_id=workflow.id,
            version_number=workflow.current_version,
            config_snapshot=cls._build_version_snapshot(workflow),
            created_by=cls._to_uuid(created_by)
        )
    
        workflow.status = WorkflowStatus.ACTIVE
    
        db.session.add(version)
        db.session.commit()
    
        # 发布成功后，若触发类型为 specified_time 则注册定时任务
        trigger = workflow.triggers.first()
        if trigger and trigger.trigger_type == WorkflowTriggerType.SPECIFIED_TIME:
            workflow_scheduler_service.schedule_workflow(workflow.id)
    
        log.info(
            f'[WorkflowService] 工作流已发布: {workflow.id} #{workflow.current_version} '
            f'(从 {previous_status} 状态发布)'
        )
        return workflow
    
