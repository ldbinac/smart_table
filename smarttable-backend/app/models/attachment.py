"""
附件模型模块
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Integer, Text
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class AttachmentType(PyEnum):
    """附件类型枚举"""
    IMAGE = 'image'
    DOCUMENT = 'document'
    VIDEO = 'video'
    AUDIO = 'audio'
    ARCHIVE = 'archive'
    OTHER = 'other'


class Attachment(db.Model):
    """
    附件模型

    属性:
        id: UUID 主键
        record_id: 所属记录 ID
        field_id: 所属字段 ID
        filename: 文件名
        original_name: 原始文件名
        file_size: 文件大小（字节）
        mime_type: MIME 类型
        storage_type: 存储类型
        storage_path: 存储路径
        url: 访问 URL
        thumbnail_url: 缩略图 URL
        uploaded_by: 上传者 ID
        created_at: 创建时间
    """

    __tablename__ = 'attachments'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    record_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('records.id', ondelete='CASCADE'),
        nullable=True,
        index=True
    )
    field_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('fields.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    original_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        default='application/octet-stream'
    )
    storage_type: Mapped[str] = mapped_column(
        String(20),
        default='local',
        nullable=False
    )
    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    url: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    thumbnail_url: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    record = relationship(
        'Record',
        lazy='joined'
    )

    uploader = relationship(
        'User',
        lazy='joined'
    )

    def get_human_size(self) -> str:
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'record_id': str(self.record_id) if self.record_id else None,
            'field_id': str(self.field_id) if self.field_id else None,
            'filename': self.filename,
            'original_name': self.original_name,
            'file_size': self.file_size,
            'human_size': self.get_human_size(),
            'mime_type': self.mime_type,
            'url': self.url,
            'thumbnail_url': self.thumbnail_url,
            'uploaded_by': str(self.uploaded_by) if self.uploaded_by else None,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<Attachment {self.original_name}>'
