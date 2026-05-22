"""
文档版本历史模型模块
包含 DocumentVersion（文档版本）模型
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class DocumentVersion(db.Model):
    """
    文档版本历史模型

    属性:
        id: UUID 主键
        document_id: 所属文档 ID
        name: 版本名称（可自定义，默认自动生成）
        content: 文档内容（完整快照）
        content_format: 内容格式（delta/markdown）
        version_number: 版本号（自增）
        change_summary: 变更摘要（可选）
        created_by: 创建者 ID
        created_at: 创建时间
    """

    __tablename__ = 'document_versions'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('documents.id', ondelete='CASCADE'),
        nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    content_format: Mapped[str] = mapped_column(
        String(20),
        default='delta',
        nullable=False
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    change_summary: Mapped[str] = mapped_column(
        String(500),
        nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    document = relationship(
        'Document',
        back_populates='versions',
        lazy='joined'
    )

    creator = relationship(
        'User',
        lazy='joined'
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': str(self.id),
            'document_id': str(self.document_id),
            'name': self.name,
            'content': self.content,
            'content_format': self.content_format,
            'version_number': self.version_number,
            'change_summary': self.change_summary,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<DocumentVersion {self.name} #{self.version_number}>'
