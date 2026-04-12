"""
操作历史模型模块
记录用户在 Base/Table/Record 等资源上的操作日志
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional, Dict, Any

from sqlalchemy import String, DateTime, ForeignKey, Text, JSON, Integer, Index
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class OperationType(PyEnum):
    """操作类型枚举"""
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'
    RESTORE = 'restore'
    EXPORT = 'export'
    IMPORT = 'import'
    SHARE = 'share'
    MEMBER_ADD = 'member_add'
    MEMBER_REMOVE = 'member_remove'
    ROLE_CHANGE = 'role_change'
    STAR = 'star'
    UNSTAR = 'unstar'
    DUPLICATE = 'duplicate'
    MOVE = 'move'


class ResourceType(PyEnum):
    """资源类型枚举"""
    BASE = 'base'
    TABLE = 'table'
    FIELD = 'field'
    RECORD = 'record'
    VIEW = 'view'
    DASHBOARD = 'dashboard'
    ATTACHMENT = 'attachment'


class OperationHistory(db.Model):
    """
    操作历史模型
    """

    __tablename__ = 'operation_history'

    __table_args__ = (
        Index('ix_op_history_resource', 'resource_type', 'resource_id'),
        Index('ix_op_history_user', 'user_id'),
        Index('ix_op_history_base', 'base_id'),
        Index('ix_op_history_time', 'created_at'),
        Index('ix_op_history_type', 'operation_type'),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    resource_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    resource_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True
    )
    base_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('bases.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    operation_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    detail: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    user = relationship(
        'User',
        lazy='joined'
    )

    base = relationship(
        'Base',
        lazy='joined'
    )

    @staticmethod
    def log(user_id, resource_type, resource_id, operation_type,
             base_id=None, detail=None, ip_address=None, user_agent=None):
        history = OperationHistory(
            user_id=user_id,
            resource_type=resource_type.value if isinstance(resource_type, PyEnum) else resource_type,
            resource_id=resource_id,
            base_id=base_id,
            operation_type=operation_type.value if isinstance(operation_type, PyEnum) else operation_type,
            detail=detail,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(history)
        return history

    @classmethod
    def get_resource_history(cls, resource_type, resource_id, limit=50):
        rt = resource_type.value if isinstance(resource_type, PyEnum) else resource_type
        return cls.query.filter_by(resource_type=rt, resource_id=resource_id).order_by(cls.created_at.desc()).limit(limit).all()

    @classmethod
    def get_base_history(cls, base_id, limit=100):
        return cls.query.filter_by(base_id=base_id).order_by(cls.created_at.desc()).limit(limit).all()

    @classmethod
    def get_user_history(cls, user_id, limit=50):
        return cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc()).limit(limit).all()

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': str(self.user_id) if self.user_id else None,
            'user': {'name': self.user.name, 'avatar': self.user.avatar} if self.user else None,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'base_id': str(self.base_id) if self.base_id else None,
            'operation_type': self.operation_type,
            'detail': self.detail or {},
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<OperationHistory {self.operation_type} {self.resource_type}:{self.resource_id}>'
