"""
工作流核心服务模块

提供工作流的 CRUD、状态管理、版本发布与触发匹配能力。

过滤条件操作符直接使用前端 FilterOperator 字符串（驼峰命名），
不进行前后端转换，前后端字符逻辑完全一致。
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

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


log = logging.getLogger(__name__)


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


class WorkflowService:
    """工作流核心服务"""

    @staticmethod
    def _to_uuid(value: Any) -> Optional[uuid.UUID]:
        """将字符串或 UUID 对象转换为 UUID 对象"""
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))

    # 前端 FilterOperator 常量到后端操作符的映射
    # 已删除：后端直接使用前端字符（驼峰命名），不再做转换

    @staticmethod
    def _eval_operator(actual: Any, operator: str, expected: Any) -> bool:
        """评估单个过滤条件（操作符直接使用前端 FilterOperator 字符串）"""
        if operator == 'equals':
            return actual == expected

        if operator == 'notEquals':
            return actual != expected

        if operator == 'contains':
            if actual is None:
                return False
            if isinstance(actual, str):
                return str(expected) in actual
            if isinstance(actual, (list, tuple, set)):
                return expected in actual
            if isinstance(actual, dict):
                return expected in actual
            return str(expected) in str(actual)

        if operator == 'notContains':
            if actual is None:
                return True
            if isinstance(actual, str):
                return str(expected) not in actual
            if isinstance(actual, (list, tuple, set)):
                return expected not in actual
            if isinstance(actual, dict):
                return expected not in actual
            return str(expected) not in str(actual)

        if operator in ('greaterThan', 'lessThan', 'greaterThanOrEqual', 'lessThanOrEqual'):
            try:
                actual_num = float(actual)
                expected_num = float(expected)
            except (TypeError, ValueError):
                return False
            if operator == 'greaterThan':
                return actual_num > expected_num
            if operator == 'lessThan':
                return actual_num < expected_num
            if operator == 'greaterThanOrEqual':
                return actual_num >= expected_num
            return actual_num <= expected_num

        if operator == 'startsWith':
            if actual is None:
                return False
            return str(actual).startswith(str(expected))

        if operator == 'endsWith':
            if actual is None:
                return False
            return str(actual).endswith(str(expected))

        if operator == 'isAnyOf':
            if expected is None:
                return False
            if isinstance(expected, (list, tuple, set)):
                return actual in expected
            return False

        if operator == 'isNoneOf':
            if expected is None:
                return False
            if isinstance(expected, (list, tuple, set)):
                return actual not in expected
            return False

        if operator == 'isEmpty':
            if actual is None:
                return True
            if isinstance(actual, str):
                return actual.strip() == ''
            if isinstance(actual, (list, tuple, set, dict)):
                return len(actual) == 0
            return False

        if operator == 'isNotEmpty':
            if actual is None:
                return False
            if isinstance(actual, str):
                return actual.strip() != ''
            if isinstance(actual, (list, tuple, set, dict)):
                return len(actual) > 0
            return True

        if operator in ('isBefore', 'isAfter', 'isOnOrBefore', 'isOnOrAfter'):
            actual_dt = _parse_datetime(actual)
            expected_dt = _parse_datetime(expected)
            if actual_dt is None or expected_dt is None:
                return False
            if operator == 'isBefore':
                return actual_dt < expected_dt
            if operator == 'isAfter':
                return actual_dt > expected_dt
            if operator == 'isOnOrBefore':
                return actual_dt <= expected_dt
            return actual_dt >= expected_dt

        if operator == 'isWithin':
            actual_dt = _parse_datetime(actual)
            if actual_dt is None:
                return False
            range_start, range_end = _resolve_date_range(str(expected))
            if range_start is None or range_end is None:
                return False
            return range_start <= actual_dt < range_end

        return False

    @classmethod
    def _evaluate_filter_condition(
        cls,
        condition: Dict[str, Any],
        record_values: Dict[str, Any],
        changes: Optional[Dict[str, Any]]
    ) -> bool:
        """递归评估过滤条件（支持 AND/OR 组合）

        group 结构通过 conditions 数组判断（与前端一致）；
        conjunction 缺失时默认 'and'（前端 filterConjunction 未被用户修改时不会显式写入该字段）。
        """
        if not isinstance(condition, dict):
            return False

        # group 结构通过 conditions 数组判断（conjunction 默认 'and'，与前端一致）
        sub_conditions = condition.get('conditions')
        if isinstance(sub_conditions, list):
            conjunction = condition.get('conjunction', 'and')
            if conjunction == 'or':
                return any(
                    cls._evaluate_filter_condition(c, record_values, changes)
                    for c in sub_conditions
                )
            return all(
                cls._evaluate_filter_condition(c, record_values, changes)
                for c in sub_conditions
            )

        # 叶子条件：直接读取 operator 字段（无需转换）
        operator = condition.get('operator')
        field_id = condition.get('field_id')
        expected = condition.get('value')

        actual = None
        if record_values and field_id in record_values:
            actual = record_values[field_id]
        elif changes and field_id in changes:
            actual = changes[field_id].get('new_value')

        return cls._eval_operator(actual, operator, expected)

    @staticmethod
    def _clean_filter_config(filter_config: Any) -> Dict[str, Any]:
        """清理空条件结构：conditions 为空数组时返回空 dict"""
        if not isinstance(filter_config, dict):
            return {}
        conditions = filter_config.get('conditions')
        if isinstance(conditions, list) and len(conditions) == 0:
            return {}
        return filter_config

    @staticmethod
    def _build_version_snapshot(workflow: Workflow) -> Dict[str, Any]:
        """为工作流构建版本快照"""
        return {
            'name': workflow.name,
            'description': workflow.description,
            'nodes': [node.to_dict() for node in workflow.nodes.order_by(WorkflowNode.order).all()],
            'triggers': [trigger.to_dict() for trigger in workflow.triggers.all()]
        }

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
            # 前端动作类型转换为 ACTION 节点
            action_type_map = {
                'update_record': 'update_record',
                'create_record': 'create_record',
                'send_email': 'send_email',
                'trigger_webhook': 'trigger_webhook',
            }
            for index, node_data in enumerate(nodes_config):
                node_type = node_data.get('node_type', 'action')
                node_config = dict(node_data.get('config', {}))
                if node_type in action_type_map:
                    node_config['action_type'] = action_type_map[node_type]
                    node_type = 'action'
                node = WorkflowNode(
                    workflow_id=workflow.id,
                    node_type=WorkflowNodeType(node_type),
                    name=node_data.get('name', f'节点 {index + 1}'),
                    config=node_config,
                    order=node_data.get('order', index),
                    next_nodes=node_data.get('next_nodes', [])
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

        # 结构变更（节点/触发器）仅草稿和暂停状态可编辑
        has_structure_changes = 'trigger_config' in kwargs or 'nodes_config' in kwargs
        if has_structure_changes and workflow.status not in (WorkflowStatus.DRAFT, WorkflowStatus.PAUSED):
            log.warning(f'[WorkflowService] 仅草稿或暂停状态可编辑节点与触发器: {workflow_id}')
            return None

        allowed_fields = {'name', 'description', 'table_id'}
        for field_name in allowed_fields:
            if field_name in kwargs:
                setattr(workflow, field_name, kwargs[field_name])

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

        if 'nodes_config' in kwargs:
            WorkflowNode.query.filter_by(workflow_id=workflow.id).delete()
            nodes_config = kwargs['nodes_config']
            if nodes_config:
                for index, node_data in enumerate(nodes_config):
                    node_type_str = node_data.get('node_type', 'action')
                    config = dict(node_data.get('config', {}))
                    # 前端动作类型转换为 ACTION 节点
                    action_node_types = {'update_record', 'create_record', 'send_email', 'trigger_webhook'}
                    if node_type_str in action_node_types:
                        config['action_type'] = node_type_str
                        node_type_str = 'action'
                    node = WorkflowNode(
                        workflow_id=workflow.id,
                        node_type=WorkflowNodeType(node_type_str),
                        name=node_data.get('name', f'节点 {index + 1}'),
                        config=config,
                        order=node_data.get('order', index),
                        next_nodes=node_data.get('next_nodes', [])
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

        for node in workflow.nodes.order_by(WorkflowNode.order).all():
            new_node = WorkflowNode(
                workflow_id=cloned.id,
                node_type=node.node_type,
                name=node.name,
                config=node.config,
                order=node.order,
                next_nodes=node.next_nodes
            )
            db.session.add(new_node)

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
            raise ValueError(f'仅草稿或暂停状态可发布，当前状态: {workflow.status.value}')

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

        log.info(
            f'[WorkflowService] 工作流已发布: {workflow.id} #{workflow.current_version} '
            f'(从 {previous_status} 状态发布)'
        )
        return workflow

    @classmethod
    def _validate_workflow_config(cls, workflow: Workflow) -> None:
        """验证工作流配置完整性，不通过时抛出 ValueError"""
        if not workflow.table_id:
            raise ValueError('工作流必须关联数据表格')

        trigger = workflow.triggers.first()
        if not trigger:
            raise ValueError('工作流必须配置触发器')

        nodes = workflow.nodes.all()
        if not nodes:
            raise ValueError('工作流至少需要一个节点')

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
            raise ValueError('工作流不存在')

        if workflow.status != WorkflowStatus.PAUSED:
            raise ValueError('仅暂停状态的工作流可保存版本快照')

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
        log.info(f'[WorkflowService] 工作流状态已更新: {workflow.id} -> {status.value}')
        return workflow

    @classmethod
    def match_triggers(
        cls,
        table_id: Any,
        event_type: str,
        record: Any,
        changes: Optional[Dict[str, Any]] = None
    ) -> List[Workflow]:
        """
        返回匹配该事件的所有 active 工作流列表

        Args:
            table_id: 表格 ID
            event_type: 事件类型（record_created / record_updated / field_changed）
            record: 触发记录对象或字典
            changes: 变更内容

        Returns:
            匹配的工作流对象列表
        """
        try:
            trigger_type = WorkflowTriggerType(event_type)
        except ValueError:
            log.warning(f'[WorkflowService] 未知事件类型: {event_type}')
            return []

        triggers = WorkflowTrigger.query.join(Workflow).filter(
            Workflow.table_id == cls._to_uuid(table_id),
            Workflow.status == WorkflowStatus.ACTIVE,
            Workflow.is_deleted == False,
            WorkflowTrigger.trigger_type == trigger_type
        ).all()

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

            filter_config = trigger.filter_config or {}
            if not filter_config:
                matched = True
            else:
                matched = cls._evaluate_filter_condition(filter_config, record_values, changes)

            if matched and trigger.workflow_id not in seen_workflow_ids:
                seen_workflow_ids.add(trigger.workflow_id)
                matched_workflows.append(trigger.workflow)

        return matched_workflows
