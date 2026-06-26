"""
工作流核心服务模块

提供工作流的 CRUD、状态管理、版本发布与触发匹配能力。
"""
import logging
import re
import uuid
from datetime import datetime, timezone
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

    @staticmethod
    def _eval_operator(actual: Any, operator: str, expected: Any) -> bool:
        """评估单个过滤条件"""
        if operator == 'eq':
            return actual == expected

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

        if operator in ('gt', 'lt'):
            try:
                actual_num = float(actual)
                expected_num = float(expected)
            except (TypeError, ValueError):
                return False
            return actual_num > expected_num if operator == 'gt' else actual_num < expected_num

        if operator == 'regex':
            if actual is None:
                return False
            try:
                return re.search(str(expected), str(actual)) is not None
            except re.error:
                return False

        return False

    @classmethod
    def _evaluate_filter_condition(
        cls,
        condition: Dict[str, Any],
        record_values: Dict[str, Any],
        changes: Optional[Dict[str, Any]]
    ) -> bool:
        """递归评估过滤条件（支持 AND/OR 组合）"""
        if not isinstance(condition, dict):
            return False

        operator = condition.get('operator')

        if operator in ('and', 'or'):
            sub_conditions = condition.get('conditions', [])
            if operator == 'and':
                return all(
                    cls._evaluate_filter_condition(c, record_values, changes)
                    for c in sub_conditions
                )
            return any(
                cls._evaluate_filter_condition(c, record_values, changes)
                for c in sub_conditions
            )

        field_id = condition.get('field_id')
        expected = condition.get('value')

        actual = None
        if record_values and field_id in record_values:
            actual = record_values[field_id]
        elif changes and field_id in changes:
            actual = changes[field_id].get('new_value')

        return cls._eval_operator(actual, operator, expected)

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
                filter_config=trigger_config.get('filter_config', {}),
                field_ids=trigger_config.get('field_ids', [])
            )
            db.session.add(trigger)

        if nodes_config:
            for index, node_data in enumerate(nodes_config):
                node = WorkflowNode(
                    workflow_id=workflow.id,
                    node_type=WorkflowNodeType(node_data.get('node_type', 'action')),
                    name=node_data.get('name', f'节点 {index + 1}'),
                    config=node_data.get('config', {}),
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

        # 结构变更（节点/触发器）仅草稿状态可编辑
        has_structure_changes = 'trigger_config' in kwargs or 'nodes_config' in kwargs
        if has_structure_changes and workflow.status != WorkflowStatus.DRAFT:
            log.warning(f'[WorkflowService] 仅草稿状态可编辑节点与触发器: {workflow_id}')
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
                    filter_config=trigger_config.get('filter_config', {}),
                    field_ids=trigger_config.get('field_ids', [])
                )
                db.session.add(trigger)

        if 'nodes_config' in kwargs:
            WorkflowNode.query.filter_by(workflow_id=workflow.id).delete()
            nodes_config = kwargs['nodes_config']
            if nodes_config:
                for index, node_data in enumerate(nodes_config):
                    node = WorkflowNode(
                        workflow_id=workflow.id,
                        node_type=WorkflowNodeType(node_data.get('node_type', 'action')),
                        name=node_data.get('name', f'节点 {index + 1}'),
                        config=node_data.get('config', {}),
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

        log.info(f'[WorkflowService] 工作流已发布: {workflow.id} #{workflow.current_version}')
        return workflow

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
            filter_config = trigger.filter_config or {}
            if not filter_config:
                matched = True
            else:
                matched = cls._evaluate_filter_condition(filter_config, record_values, changes)

            if matched and trigger.workflow_id not in seen_workflow_ids:
                seen_workflow_ids.add(trigger.workflow_id)
                matched_workflows.append(trigger.workflow)

        return matched_workflows
