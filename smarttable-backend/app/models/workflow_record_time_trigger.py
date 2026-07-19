"""
工作流记录时间触发追踪模型
用于记录已触发的 (workflow_id, record_id, field_id) 组合，确保一次性触发语义。
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db_types import CompatUUID as UUID
from app.extensions import db


class WorkflowRecordTimeTrigger(db.Model):
    """
    工作流记录时间触发追踪模型

    记录已因"到达记录中的时间时"触发的工作流实例，
    通过 UNIQUE(workflow_id, record_id, field_id) 约束确保同一记录不重复触发。

    属性:
        id: UUID 主键
        workflow_id: 工作流 ID
        record_id: 记录 ID
        field_id: 时间字段 ID
        triggered_at: 触发时间
    """

    __tablename__ = 'workflow_record_time_triggers'

    __table_args__ = (
        UniqueConstraint('workflow_id', 'record_id', 'field_id', name='uq_wf_rec_time_trigger'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('workflows.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('records.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False
    )
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'workflow_id': str(self.workflow_id),
            'record_id': str(self.record_id),
            'field_id': str(self.field_id),
            'triggered_at': self.triggered_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<WorkflowRecordTimeTrigger {self.workflow_id}:{self.record_id}:{self.field_id}>'
