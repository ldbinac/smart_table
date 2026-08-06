"""
站内信模型模块
定义站内信通知的数据库模型，用于记录系统通知的发送状态与阅读追踪
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import String, DateTime, Text, Integer, Boolean, Enum, Index, JSON, ForeignKey
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class NotificationStatus(PyEnum):
    """站内信发送状态枚举"""
    PENDING = 'pending'
    SENT = 'sent'
    FAILED = 'failed'
    RETRYING = 'retrying'


class Notification(db.Model):
    """
    站内信通知模型

    用于记录系统向用户发送的站内信通知，支持模板化内容、状态追踪与已读管理

    属性:
        id: UUID 主键
        recipient_user_id: 接收用户 ID
        recipient_email: 接收用户邮箱（可选，用于关联邮件）
        title: 通知标题
        content: HTML 格式通知内容
        content_text: 纯文本通知内容
        template_key: 使用的模板标识
        source: 通知来源（system/auth/admin/workflow/approval 等）
        status: 发送状态 (pending, sent, failed, retrying)
        is_read: 是否已读
        read_at: 阅读时间
        sent_at: 发送时间
        created_at: 创建时间
        retry_count: 重试次数
        error_message: 错误信息
        extra_metadata: 附加元数据（to_dict 输出 key 为 'metadata'）
    """

    __tablename__ = 'notifications'

    __table_args__ = (
        Index('ix_notifications_recipient_user_id', 'recipient_user_id'),
        Index('ix_notifications_status', 'status'),
        Index('ix_notifications_is_read', 'is_read'),
        Index('ix_notifications_created_at', 'created_at'),
        Index('ix_notifications_source', 'source'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=False
    )
    recipient_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    content_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    template_key: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus),
        default=NotificationStatus.PENDING,
        nullable=False
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True
    )

    def __init__(self, **kwargs):
        """初始化站内信，自动处理状态枚举值"""
        status = kwargs.get('status')
        if isinstance(status, NotificationStatus):
            kwargs['status'] = status
        super(Notification, self).__init__(**kwargs)

    def mark_as_sent(self) -> None:
        """标记站内信为已发送状态"""
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.now(timezone.utc)

    def mark_as_failed(self, error_message: str) -> None:
        """标记站内信为发送失败状态"""
        self.status = NotificationStatus.FAILED
        self.error_message = error_message

    def mark_as_retrying(self) -> None:
        """标记站内信为重试中状态"""
        self.status = NotificationStatus.RETRYING
        self.retry_count += 1

    def mark_as_read(self) -> None:
        """标记站内信为已读状态"""
        self.is_read = True
        self.read_at = datetime.now(timezone.utc)

    @classmethod
    def get_unread_count(cls, user_id) -> int:
        """
        获取指定用户的未读站内信数量

        Args:
            user_id: 用户 ID

        Returns:
            未读站内信数量
        """
        return cls.query.filter_by(
            recipient_user_id=user_id,
            is_read=False
        ).count()

    @classmethod
    def get_user_notifications(cls, user_id, page: int = 1, per_page: int = 20, filters: Optional[dict] = None) -> dict:
        """
        分页获取指定用户的站内信列表

        Args:
            user_id: 用户 ID
            page: 页码（从 1 开始）
            per_page: 每页数量
            filters: 过滤条件字典，支持 is_read / status / source

        Returns:
            包含 items、total、pages、current_page、per_page 的字典
        """
        query = cls.query.filter_by(recipient_user_id=user_id)
        if filters:
            if 'is_read' in filters:
                query = query.filter_by(is_read=filters['is_read'])
            if 'status' in filters:
                query = query.filter_by(status=filters['status'])
            if 'source' in filters:
                query = query.filter_by(source=filters['source'])
        query = query.order_by(cls.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return {
            'items': [item.to_dict() for item in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page,
            'per_page': pagination.per_page
        }

    def to_dict(self) -> dict:
        """
        将站内信转换为字典

        Returns:
            包含站内信信息的字典
        """
        return {
            'id': str(self.id),
            'recipient_user_id': str(self.recipient_user_id),
            'recipient_email': self.recipient_email,
            'title': self.title,
            'content': self.content,
            'content_text': self.content_text,
            'template_key': self.template_key,
            'source': self.source,
            'status': self.status.value if isinstance(self.status, NotificationStatus) else self.status,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'created_at': self.created_at.isoformat(),
            'retry_count': self.retry_count,
            'error_message': self.error_message,
            'metadata': self.extra_metadata
        }

    def __repr__(self) -> str:
        return f'<Notification {self.title} {self.status}>'
