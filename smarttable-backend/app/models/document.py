"""
文档数据模型模块
包含 Document（文档）模型
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Document(db.Model):
    """
    文档模型

    属性:
        id: UUID 主键
        base_id: 所属 Base ID
        name: 文档名称
        content: 文档内容（Delta 或 Markdown 格式）
        content_format: 内容格式（delta/markdown）
        order: 排序顺序
        is_pinned: 是否置顶
        created_by: 创建者 ID
        updated_by: 最后更新者 ID
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = 'documents'

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
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text,
        default='',
        nullable=False
    )
    content_format: Mapped[str] = mapped_column(
        String(20),
        default='delta',
        nullable=False
    )
    order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    is_pinned: Mapped[bool] = mapped_column(
        default=False,
        nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    updated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    base = relationship(
        'Base',
        back_populates='documents',
        lazy='joined'
    )

    creator = relationship(
        'User',
        foreign_keys=[created_by],
        lazy='joined'
    )

    updater = relationship(
        'User',
        foreign_keys=[updated_by],
        lazy='joined'
    )

    def to_dict(self, include_content: bool = False) -> dict:
        """转换为字典"""
        data = {
            'id': str(self.id),
            'base_id': str(self.base_id),
            'name': self.name,
            'content_format': self.content_format,
            'order': self.order,
            'is_pinned': self.is_pinned,
            'created_by': str(self.created_by) if self.created_by else None,
            'updated_by': str(self.updated_by) if self.updated_by else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        if include_content:
            data['content'] = self.content
        return data

    def __repr__(self) -> str:
        return f'<Document {self.name}>'
