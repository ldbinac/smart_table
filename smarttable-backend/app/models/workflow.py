"""
工作流模型模块
包含 Workflow、WorkflowVersion、WorkflowNode、WorkflowTrigger 模型
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional, Dict, Any, List

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean, JSON, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db_types import CompatUUID as UUID
from app.extensions import db


def _enum_values(enum_class: type[PyEnum]) -> list[str]:
    """返回枚举成员的值列表，用于 SQLAlchemy Enum 数据库存储"""
    return [e.value for e in enum_class]


class WorkflowStatus(PyEnum):
    """工作流状态枚举"""
    DRAFT = 'draft'
    ACTIVE = 'active'
    PAUSED = 'paused'
    ARCHIVED = 'archived'


class WorkflowNodeType(PyEnum):
    """工作流节点类型枚举"""
    TRIGGER = 'trigger'
    APPROVAL = 'approval'
    ACTION = 'action'
    CONDITION = 'condition'
    WEBHOOK = 'webhook'


class WorkflowTriggerType(PyEnum):
    """工作流触发类型枚举"""
    RECORD_CREATED = 'record_created'
    RECORD_UPDATED = 'record_updated'
    FIELD_CHANGED = 'field_changed'
    MANUAL = 'manual'
    SPECIFIED_TIME = 'specified_time'


class Workflow(db.Model):
    """
    工作流模型

    属性:
        id: UUID 主键
        base_id: 所属基础数据 ID
        table_id: 关联表格 ID
        name: 工作流名称
        description: 描述
        status: 状态
        current_version: 当前版本号
        created_by: 创建者 ID
        created_at: 创建时间
        updated_at: 更新时间
        is_deleted: 是否已删除
    """

    __tablename__ = 'workflows'

    __table_args__ = (
        Index('ix_workflows_base_id', 'base_id'),
        Index('ix_workflows_table_id', 'table_id'),
        Index('ix_workflows_status', 'status'),
        Index('ix_workflows_created_by', 'created_by'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('bases.id', ondelete='CASCADE'),
        nullable=False
    )
    table_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('tables.id', ondelete='CASCADE'),
        nullable=True
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus, values_callable=_enum_values),
        default=WorkflowStatus.DRAFT,
        nullable=False
    )
    current_version: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    base = relationship(
        'Base',
        lazy='joined'
    )

    table = relationship(
        'Table',
        lazy='joined'
    )

    creator = relationship(
        'User',
        lazy='joined'
    )

    versions = relationship(
        'WorkflowVersion',
        back_populates='workflow',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='WorkflowVersion.version_number.desc()'
    )

    nodes = relationship(
        'WorkflowNode',
        back_populates='workflow',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='WorkflowNode.order'
    )

    triggers = relationship(
        'WorkflowTrigger',
        back_populates='workflow',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    instances = relationship(
        'WorkflowInstance',
        back_populates='workflow',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'base_id': str(self.base_id),
            'table_id': str(self.table_id) if self.table_id else None,
            'name': self.name,
            'description': self.description,
            'status': self.status.value if isinstance(self.status, WorkflowStatus) else self.status,
            'current_version': self.current_version,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_deleted': self.is_deleted
        }

    def __repr__(self) -> str:
        return f'<Workflow {self.name}>'


class WorkflowVersion(db.Model):
    """
    工作流版本模型

    属性:
        id: UUID 主键
        workflow_id: 所属工作流 ID
        version_number: 版本号
        config_snapshot: 配置快照（JSON）
        created_by: 创建者 ID
        created_at: 创建时间
    """

    __tablename__ = 'workflow_versions'

    __table_args__ = (
        Index('ix_workflow_versions_workflow_id', 'workflow_id'),
        Index('ix_workflow_versions_version_number', 'workflow_id', 'version_number'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('workflows.id', ondelete='CASCADE'),
        nullable=False
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    config_snapshot: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    workflow = relationship(
        'Workflow',
        back_populates='versions',
        lazy='joined'
    )

    creator = relationship(
        'User',
        lazy='joined'
    )

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'workflow_id': str(self.workflow_id),
            'version_number': self.version_number,
            'config_snapshot': self.config_snapshot or {},
            'created_by': str(self.created_by) if self.created_by else None,
            'created_by_name': self.creator.name if self.creator else None,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<WorkflowVersion {self.workflow_id} #{self.version_number}>'


# 动作类型反向映射：后端 action + config.action_type -> 前端细粒度 node_type
_ACTION_TYPE_TO_FRONTEND = {
    'update_record': 'update_record',
    'create_record': 'create_record',
    'send_email': 'send_email',
    'trigger_webhook': 'webhook',
}


class WorkflowNode(db.Model):
    """
    工作流节点模型

    属性:
        id: UUID 主键
        workflow_id: 所属工作流 ID
        node_type: 节点类型
        name: 节点名称
        config: 节点配置（JSON）
        order: 排序顺序
        next_nodes: 下游节点 ID 列表（JSON）
    """

    __tablename__ = 'workflow_nodes'

    __table_args__ = (
        Index('ix_workflow_nodes_workflow_id', 'workflow_id'),
        Index('ix_workflow_nodes_type', 'node_type'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('workflows.id', ondelete='CASCADE'),
        nullable=False
    )
    node_type: Mapped[WorkflowNodeType] = mapped_column(
        Enum(WorkflowNodeType, values_callable=_enum_values),
        nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    config: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )
    order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    next_nodes: Mapped[List[Any]] = mapped_column(
        JSON,
        default=list,
        nullable=False
    )

    workflow = relationship(
        'Workflow',
        back_populates='nodes',
        lazy='joined'
    )

    def to_dict(self) -> dict:
        node_type_value = self.node_type.value if isinstance(self.node_type, WorkflowNodeType) else self.node_type
        config = self.config or {}
        # 将动作节点反转为前端细粒度 node_type
        if node_type_value == WorkflowNodeType.ACTION.value:
            action_type = config.get('action_type')
            if action_type in _ACTION_TYPE_TO_FRONTEND:
                node_type_value = _ACTION_TYPE_TO_FRONTEND[action_type]
        return {
            'id': str(self.id),
            'workflow_id': str(self.workflow_id),
            'node_type': node_type_value,
            'name': self.name,
            'config': config,
            'order': self.order,
            'next_nodes': self.next_nodes or []
        }

    def __repr__(self) -> str:
        return f'<WorkflowNode {self.name} ({self.node_type})>'


class WorkflowTrigger(db.Model):
    """
    工作流触发器模型

    属性:
        id: UUID 主键
        workflow_id: 所属工作流 ID
        trigger_type: 触发类型
        filter_config: 过滤条件（JSON）
        field_ids: 监听字段 ID 列表（JSON）
    """

    __tablename__ = 'workflow_triggers'

    __table_args__ = (
        Index('ix_workflow_triggers_workflow_id', 'workflow_id'),
        Index('ix_workflow_triggers_type', 'trigger_type'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('workflows.id', ondelete='CASCADE'),
        nullable=False
    )
    trigger_type: Mapped[WorkflowTriggerType] = mapped_column(
        Enum(WorkflowTriggerType, values_callable=_enum_values),
        nullable=False
    )
    filter_config: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )
    field_ids: Mapped[List[Any]] = mapped_column(
        JSON,
        default=list,
        nullable=False
    )

    workflow = relationship(
        'Workflow',
        back_populates='triggers',
        lazy='joined'
    )

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'workflow_id': str(self.workflow_id),
            'trigger_type': self.trigger_type.value if isinstance(self.trigger_type, WorkflowTriggerType) else self.trigger_type,
            'filter_config': self.filter_config or {},
            'field_ids': self.field_ids or []
        }

    def __repr__(self) -> str:
        return f'<WorkflowTrigger {self.trigger_type}>'
