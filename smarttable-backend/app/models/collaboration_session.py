import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.db_types import CompatJSON


class CollaborationSession(db.Model):

    __tablename__ = 'collaboration_sessions'

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    base_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey('bases.id', ondelete='CASCADE'),
        nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    socket_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )
    current_table_id: Mapped[str] = mapped_column(
        String(36),
        nullable=True
    )
    current_view_id: Mapped[str] = mapped_column(
        String(36),
        nullable=True
    )
    current_view_type: Mapped[str] = mapped_column(
        String(20),
        nullable=True
    )
    locked_cells = mapped_column(
        CompatJSON,
        default=list,
        nullable=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    base = relationship(
        'Base',
        lazy='joined'
    )

    user = relationship(
        'User',
        lazy='joined'
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'base_id': self.base_id,
            'user_id': self.user_id,
            'socket_id': self.socket_id,
            'current_table_id': self.current_table_id,
            'current_view_id': self.current_view_id,
            'current_view_type': self.current_view_type,
            'locked_cells': self.locked_cells or [],
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'last_active_at': self.last_active_at.isoformat() if self.last_active_at else None,
            'is_active': self.is_active
        }

    def __repr__(self) -> str:
        return f'<CollaborationSession {self.user_id}@{self.base_id}>'
