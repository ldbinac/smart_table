"""
邮件模板模型模块
定义邮件模板的数据库模型，用于存储和管理各类邮件模板
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Text, Boolean, Index
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class EmailTemplate(db.Model):
    """
    邮件模板模型

    用于存储系统邮件模板，支持HTML和纯文本两种格式

    属性:
        id: UUID 主键
        template_key: 模板标识（唯一，如 'user_registration', 'password_reset'）
        name: 模板名称
        subject: 邮件主题
        content_html: HTML格式邮件内容
        content_text: 纯文本格式邮件内容
        description: 模板描述
        is_default: 是否为系统默认模板
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = 'email_templates'

    __table_args__ = (
        Index('ix_email_template_key', 'template_key'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    template_key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    subject: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    content_html: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    content_text: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
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

    def to_dict(self) -> dict:
        """
        将邮件模板转换为字典

        Returns:
            包含邮件模板信息的字典
        """
        return {
            'id': str(self.id),
            'template_key': self.template_key,
            'name': self.name,
            'subject': self.subject,
            'content_html': self.content_html,
            'content_text': self.content_text,
            'description': self.description,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<EmailTemplate {self.template_key}>'
