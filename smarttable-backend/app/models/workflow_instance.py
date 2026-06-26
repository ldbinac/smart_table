"""
工作流实例模型模块
包含 WorkflowInstance、WorkflowTask、WorkflowExecutionLog 模型
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional, Dict, Any

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean, JSON, Enum, Index
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


def _enum_values(enum_class: type[PyEnum]) -> list[str]:
    """返回枚举成员的值列表，用于 SQLAlchemy Enum 数据库存储"""
    return [e.value for e in enum_class]


class WorkflowInstanceStatus(PyEnum):
    """工作流实例状态枚举"""
    RUNNING = 'running'
    COMPLETED = 'completed'
    REJECTED = 'rejected'
    CANCELLED = 'cancelled'
    ERROR = 'error'


class WorkflowTaskStatus(PyEnum):
    """工作流任务状态枚举"""
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    TRANSFERRED = 'transferred'
    EXPIRED = 'expired'


class WorkflowInstance(db.Model):
    """
    工作流实例模型

    属性:
        id: UUID 主键
        workflow_id: 所属工作流 ID
        version_number: 执行的版本号
        trigger_type: 触发类型
        trigger_record_id: 触发记录 ID
        status: 实例状态
        context: 执行上下文（JSON）
        started_at: 开始时间
        completed_at: 完成时间
    """

    __tablename__ = 'workflow_instances'

    __table_args__ = (
        Index('ix_workflow_instances_workflow_id', 'workflow_id'),
        Index('ix_workflow_instances_status', 'status'),
        Index('ix_workflow_instances_trigger_record', 'trigger_record_id'),
        Index('ix_workflow_instances_started_at', 'started_at'),
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
    trigger_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    trigger_record_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('records.id', ondelete='SET NULL'),
        nullable=True
    )
    status: Mapped[WorkflowInstanceStatus] = mapped_column(
        Enum(WorkflowInstanceStatus, values_callable=_enum_values),
        default=WorkflowInstanceStatus.RUNNING,
        nullable=False
    )
    context: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    workflow = relationship(
        'Workflow',
        back_populates='instances',
        lazy='joined'
    )

    trigger_record = relationship(
        'Record',
        lazy='joined'
    )

    tasks = relationship(
        'WorkflowTask',
        back_populates='instance',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    execution_logs = relationship(
        'WorkflowExecutionLog',
        back_populates='instance',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='WorkflowExecutionLog.started_at'
    )

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'workflow_id': str(self.workflow_id),
            'version_number': self.version_number,
            'trigger_type': self.trigger_type,
            'trigger_record_id': str(self.trigger_record_id) if self.trigger_record_id else None,
            'status': self.status.value if isinstance(self.status, WorkflowInstanceStatus) else self.status,
            'context': self.context or {},
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

    def __repr__(self) -> str:
        return f'<WorkflowInstance {self.workflow_id} #{self.version_number}>'


class WorkflowTask(db.Model):
    """
    工作流任务模型

    属性:
        id: UUID 主键
        instance_id: 所属实例 ID
        node_id: 所属节点 ID
        assignee_id: 处理人 ID
        status: 任务状态
        comment: 处理意见
        acted_at: 处理时间
        transferred_from_id: 转交来源任务 ID
    """

    __tablename__ = 'workflow_tasks'

    __table_args__ = (
        Index('ix_workflow_tasks_instance_id', 'instance_id'),
        Index('ix_workflow_tasks_assignee_id', 'assignee_id'),
        Index('ix_workflow_tasks_status', 'status'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('workflow_instances.id', ondelete='CASCADE'),
        nullable=False
    )
    node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('workflow_nodes.id', ondelete='SET NULL'),
        nullable=True
    )
    assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    status: Mapped[WorkflowTaskStatus] = mapped_column(
        Enum(WorkflowTaskStatus, values_callable=_enum_values),
        default=WorkflowTaskStatus.PENDING,
        nullable=False
    )
    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    acted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    transferred_from_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('workflow_tasks.id', ondelete='SET NULL'),
        nullable=True
    )

    instance = relationship(
        'WorkflowInstance',
        back_populates='tasks',
        lazy='joined'
    )

    node = relationship(
        'WorkflowNode',
        lazy='joined'
    )

    assignee = relationship(
        'User',
        lazy='joined'
    )

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'instance_id': str(self.instance_id),
            'node_id': str(self.node_id) if self.node_id else None,
            'assignee_id': str(self.assignee_id) if self.assignee_id else None,
            'status': self.status.value if isinstance(self.status, WorkflowTaskStatus) else self.status,
            'comment': self.comment,
            'acted_at': self.acted_at.isoformat() if self.acted_at else None,
            'transferred_from_id': str(self.transferred_from_id) if self.transferred_from_id else None
        }

    def __repr__(self) -> str:
        return f'<WorkflowTask {self.id}>'


class WorkflowExecutionLog(db.Model):
    """
    工作流执行日志模型

    属性:
        id: UUID 主键
        instance_id: 所属实例 ID
        node_id: 执行节点 ID
        node_type: 节点类型
        status: 执行状态
        input_context: 输入上下文（JSON）
        output_result: 输出结果（JSON）
        error_message: 错误信息
        started_at: 开始时间
        completed_at: 完成时间
    """

    __tablename__ = 'workflow_execution_logs'

    __table_args__ = (
        Index('ix_workflow_execution_logs_instance_id', 'instance_id'),
        Index('ix_workflow_execution_logs_status', 'status'),
        Index('ix_workflow_execution_logs_started_at', 'started_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('workflow_instances.id', ondelete='CASCADE'),
        nullable=False
    )
    node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('workflow_nodes.id', ondelete='SET NULL'),
        nullable=True
    )
    node_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    input_context: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )
    output_result: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    instance = relationship(
        'WorkflowInstance',
        back_populates='execution_logs',
        lazy='joined'
    )

    node = relationship(
        'WorkflowNode',
        lazy='joined'
    )

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'instance_id': str(self.instance_id),
            'node_id': str(self.node_id) if self.node_id else None,
            'node_type': self.node_type,
            'status': self.status,
            'input_context': self.input_context or {},
            'output_result': self.output_result or {},
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

    def __repr__(self) -> str:
        return f'<WorkflowExecutionLog {self.instance_id} {self.node_type}>'
