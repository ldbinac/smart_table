"""
附件模型模块
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class AttachmentType(PyEnum):
    """附件类型枚举"""
    IMAGE = 'image'           # 图片
    DOCUMENT = 'document'     # 文档
    SPREADSHEET = 'spreadsheet'  # 电子表格
    PRESENTATION = 'presentation'  # 演示文稿
    PDF = 'pdf'               # PDF
    VIDEO = 'video'           # 视频
    AUDIO = 'audio'           # 音频
    ARCHIVE = 'archive'       # 压缩包
    CODE = 'code'             # 代码文件
    OTHER = 'other'           # 其他


class Attachment(db.Model):
    """
    附件模型
    
    属性:
        id: UUID 主键
        filename: 原始文件名
        stored_filename: 存储文件名
        original_name: 原始上传名称
        mime_type: MIME 类型
        size: 文件大小（字节）
        type: 附件类型
        url: 访问 URL
        thumbnail_url: 缩略图 URL（图片类型）
        width: 宽度（图片/视频）
        height: 高度（图片/视频）
        duration: 时长（音视频）
        uploaded_by: 上传用户 ID
        base_id: 所属基础数据 ID（可选）
        created_at: 创建时间
    """
    
    __tablename__ = 'attachments'
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    stored_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True
    )
    original_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    size: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(50),
        default=AttachmentType.OTHER.value,
        nullable=False
    )
    url: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    thumbnail_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    width: Mapped[Optional[int]] = mapped_column(
        nullable=True
    )
    height: Mapped[Optional[int]] = mapped_column(
        nullable=True
    )
    duration: Mapped[Optional[int]] = mapped_column(
        nullable=True
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    base_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('bases.id', ondelete='SET NULL'),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    # 关系定义
    uploader = relationship(
        'User',
        lazy='joined'
    )
    
    base = relationship(
        'Base',
        lazy='joined'
    )
    
    @classmethod
    def detect_type(cls, mime_type: str, filename: str) -> str:
        """
        根据 MIME 类型和文件名检测附件类型
        
        Args:
            mime_type: MIME 类型
            filename: 文件名
            
        Returns:
            附件类型字符串
        """
        mime_type = mime_type.lower()
        filename_lower = filename.lower()
        
        # 图片类型
        if mime_type.startswith('image/'):
            return AttachmentType.IMAGE.value
        
        # 视频类型
        if mime_type.startswith('video/'):
            return AttachmentType.VIDEO.value
        
        # 音频类型
        if mime_type.startswith('audio/'):
            return AttachmentType.AUDIO.value
        
        # PDF
        if mime_type == 'application/pdf':
            return AttachmentType.PDF.value
        
        # 文档类型
        doc_types = [
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.oasis.opendocument.text'
        ]
        if mime_type in doc_types or filename_lower.endswith(('.doc', '.docx', '.odt', '.rtf')):
            return AttachmentType.DOCUMENT.value
        
        # 电子表格
        sheet_types = [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.oasis.opendocument.spreadsheet',
            'text/csv'
        ]
        if mime_type in sheet_types or filename_lower.endswith(('.xls', '.xlsx', '.ods', '.csv')):
            return AttachmentType.SPREADSHEET.value
        
        # 演示文稿
        pres_types = [
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.oasis.opendocument.presentation'
        ]
        if mime_type in pres_types or filename_lower.endswith(('.ppt', '.pptx', '.odp')):
            return AttachmentType.PRESENTATION.value
        
        # 压缩包
        archive_types = [
            'application/zip',
            'application/x-rar-compressed',
            'application/x-7z-compressed',
            'application/gzip',
            'application/x-tar'
        ]
        if mime_type in archive_types or filename_lower.endswith(('.zip', '.rar', '.7z', '.gz', '.tar')):
            return AttachmentType.ARCHIVE.value
        
        # 代码文件
        code_extensions = ['.py', '.js', '.ts', '.html', '.css', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php']
        if any(filename_lower.endswith(ext) for ext in code_extensions):
            return AttachmentType.CODE.value
        
        return AttachmentType.OTHER.value
    
    def get_formatted_size(self) -> str:
        """
        获取格式化后的文件大小
        
        Returns:
            格式化的大小字符串（如：1.5 MB）
        """
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def is_image(self) -> bool:
        """检查是否为图片"""
        return self.type == AttachmentType.IMAGE.value
    
    def is_previewable(self) -> bool:
        """检查是否可以预览"""
        previewable_types = [
            AttachmentType.IMAGE.value,
            AttachmentType.PDF.value,
            AttachmentType.VIDEO.value,
            AttachmentType.AUDIO.value
        ]
        return self.type in previewable_types
    
    def to_dict(self, include_urls: bool = True) -> dict:
        """
        转换为字典
        
        Args:
            include_urls: 是否包含 URL
            
        Returns:
            附件数据字典
        """
        data = {
            'id': str(self.id),
            'filename': self.filename,
            'original_name': self.original_name,
            'mime_type': self.mime_type,
            'size': self.size,
            'formatted_size': self.get_formatted_size(),
            'type': self.type,
            'width': self.width,
            'height': self.height,
            'duration': self.duration,
            'uploaded_by': str(self.uploaded_by) if self.uploaded_by else None,
            'base_id': str(self.base_id) if self.base_id else None,
            'created_at': self.created_at.isoformat()
        }
        
        if include_urls:
            data['url'] = self.url
            data['thumbnail_url'] = self.thumbnail_url
        
        return data
    
    def __repr__(self) -> str:
        return f'<Attachment {self.original_name}>'
