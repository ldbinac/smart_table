"""
工作流模板模型模块
包含 WorkflowTemplate 模型
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import String, Text, DateTime, Boolean, JSON, Index, ForeignKey
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class WorkflowTemplate(db.Model):
    """
    工作流模板模型

    属性:
        id: UUID 主键
        name: 模板名称
        description: 描述
        category: 分类
        config_snapshot: 配置快照（JSON）
        is_system: 是否系统模板
        created_by: 创建者 ID
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = 'workflow_templates'

    __table_args__ = (
        Index('ix_workflow_templates_category', 'category'),
        Index('ix_workflow_templates_is_system', 'is_system'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    config_snapshot: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
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

    creator = relationship(
        'User',
        lazy='joined'
    )

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'config_snapshot': self.config_snapshot or {},
            'is_system': self.is_system,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<WorkflowTemplate {self.name}>'
