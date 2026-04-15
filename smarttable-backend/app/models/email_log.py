"""
邮件日志模型模块
定义邮件发送日志的数据库模型，用于记录邮件发送状态和追踪
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import String, DateTime, Text, Integer, Enum, Index
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class EmailStatus(PyEnum):
    """邮件发送状态枚举"""
    PENDING = 'pending'
    SENT = 'sent'
    FAILED = 'failed'
    RETRYING = 'retrying'


class EmailLog(db.Model):
    """
    邮件发送日志模型

    用于记录邮件发送状态、重试次数和错误信息

    属性:
        id: UUID 主键
        recipient_email: 收件人邮箱
        recipient_name: 收件人名称
        template_key: 使用的模板标识
        subject: 邮件主题
        status: 发送状态 (pending, sent, failed, retrying)
        retry_count: 重试次数
        error_message: 错误信息
        sent_at: 发送时间
        created_at: 创建时间
    """

    __tablename__ = 'email_logs'

    __table_args__ = (
        Index('ix_email_log_recipient', 'recipient_email'),
        Index('ix_email_log_status', 'status'),
        Index('ix_email_log_template', 'template_key'),
        Index('ix_email_log_created', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    recipient_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    recipient_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    template_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    subject: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    status: Mapped[EmailStatus] = mapped_column(
        Enum(EmailStatus),
        default=EmailStatus.PENDING,
        nullable=False,
        index=True
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
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    def __init__(self, **kwargs):
        """初始化邮件日志，自动处理枚举值"""
        status = kwargs.get('status')
        if isinstance(status, EmailStatus):
            kwargs['status'] = status
        super(EmailLog, self).__init__(**kwargs)

    def mark_as_sent(self) -> None:
        """标记邮件为已发送状态"""
        self.status = EmailStatus.SENT
        self.sent_at = datetime.now(timezone.utc)

    def mark_as_failed(self, error_message: str) -> None:
        """标记邮件为发送失败状态"""
        self.status = EmailStatus.FAILED
        self.error_message = error_message

    def mark_as_retrying(self) -> None:
        """标记邮件为重试中状态"""
        self.status = EmailStatus.RETRYING
        self.retry_count += 1

    @classmethod
    def get_pending_emails(cls, limit: int = 100) -> list:
        """
        获取待发送的邮件列表

        Args:
            limit: 返回数量限制

        Returns:
            待发送邮件列表
        """
        return cls.query.filter_by(status=EmailStatus.PENDING).order_by(cls.created_at.asc()).limit(limit).all()

    @classmethod
    def get_failed_emails(cls, limit: int = 100) -> list:
        """
        获取发送失败的邮件列表

        Args:
            limit: 返回数量限制

        Returns:
            发送失败邮件列表
        """
        return cls.query.filter_by(status=EmailStatus.FAILED).order_by(cls.created_at.desc()).limit(limit).all()

    @classmethod
    def get_emails_by_recipient(cls, recipient_email: str, limit: int = 100) -> list:
        """
        获取指定收件人的邮件记录

        Args:
            recipient_email: 收件人邮箱
            limit: 返回数量限制

        Returns:
            邮件记录列表
        """
        return cls.query.filter_by(recipient_email=recipient_email).order_by(cls.created_at.desc()).limit(limit).all()

    def to_dict(self) -> dict:
        """
        将邮件日志转换为字典

        Returns:
            包含邮件日志信息的字典
        """
        return {
            'id': str(self.id),
            'recipient_email': self.recipient_email,
            'recipient_name': self.recipient_name,
            'template_key': self.template_key,
            'subject': self.subject,
            'status': self.status.value if isinstance(self.status, EmailStatus) else self.status,
            'retry_count': self.retry_count,
            'error_message': self.error_message,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<EmailLog {self.recipient_email} {self.template_key}>'
