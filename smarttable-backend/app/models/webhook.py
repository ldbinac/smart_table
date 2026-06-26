"""
Webhook 模型模块
包含 WebhookConfig、WebhookDeliveryLog 模型
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional, Dict, Any

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean, JSON, Enum, Index
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


def _enum_values(enum_class: type[PyEnum]) -> list[str]:
    """返回枚举成员的值列表，用于 SQLAlchemy Enum 数据库存储"""
    return [e.value for e in enum_class]


class WebhookMethod(PyEnum):
    """Webhook 请求方法枚举"""
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'


class WebhookDeliveryStatus(PyEnum):
    """Webhook 投递状态枚举"""
    PENDING = 'pending'
    SUCCESS = 'success'
    FAILED = 'failed'


class WebhookConfig(db.Model):
    """
    Webhook 配置模型

    属性:
        id: UUID 主键
        base_id: 所属基础数据 ID
        name: Webhook 名称
        url: 请求地址
        method: 请求方法
        headers: 请求头（JSON）
        body_template: 请求体模板
        secret: 签名密钥
        retry_policy: 重试策略（JSON）
        is_active: 是否启用
        created_by: 创建者 ID
        created_at: 创建时间
    """

    __tablename__ = 'webhook_configs'

    __table_args__ = (
        Index('ix_webhook_configs_base_id', 'base_id'),
        Index('ix_webhook_configs_is_active', 'is_active'),
        Index('ix_webhook_configs_created_by', 'created_by'),
    )

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
    url: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    method: Mapped[WebhookMethod] = mapped_column(
        Enum(WebhookMethod),
        default=WebhookMethod.POST,
        nullable=False
    )
    headers: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )
    body_template: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    secret: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    retry_policy: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
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

    base = relationship(
        'Base',
        lazy='joined'
    )

    creator = relationship(
        'User',
        lazy='joined'
    )

    delivery_logs = relationship(
        'WebhookDeliveryLog',
        back_populates='webhook_config',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'base_id': str(self.base_id),
            'name': self.name,
            'url': self.url,
            'method': self.method.value if isinstance(self.method, WebhookMethod) else self.method,
            'headers': self.headers or {},
            'body_template': self.body_template,
            'retry_policy': self.retry_policy or {},
            'is_active': self.is_active,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<WebhookConfig {self.name}>'


class WebhookDeliveryLog(db.Model):
    """
    Webhook 投递日志模型

    属性:
        id: UUID 主键
        webhook_config_id: Webhook 配置 ID
        instance_id: 工作流实例 ID
        payload: 发送的负载
        status: 投递状态
        response_status: 响应状态码
        response_body: 响应体
        retry_count: 重试次数
        error_message: 错误信息
        next_retry_at: 下次重试时间
        delivered_at: 投递完成时间
        created_at: 创建时间
    """

    __tablename__ = 'webhook_delivery_logs'

    __table_args__ = (
        Index('ix_webhook_delivery_logs_config_id', 'webhook_config_id'),
        Index('ix_webhook_delivery_logs_instance_id', 'instance_id'),
        Index('ix_webhook_delivery_logs_status', 'status'),
        Index('ix_webhook_delivery_logs_created_at', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    webhook_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('webhook_configs.id', ondelete='CASCADE'),
        nullable=False
    )
    instance_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('workflow_instances.id', ondelete='SET NULL'),
        nullable=True
    )
    payload: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    status: Mapped[WebhookDeliveryStatus] = mapped_column(
        Enum(WebhookDeliveryStatus, values_callable=_enum_values),
        default=WebhookDeliveryStatus.PENDING,
        nullable=False
    )
    response_status: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    response_body: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
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
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    webhook_config = relationship(
        'WebhookConfig',
        back_populates='delivery_logs',
        lazy='joined'
    )

    instance = relationship(
        'WorkflowInstance',
        lazy='joined'
    )

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'webhook_config_id': str(self.webhook_config_id),
            'instance_id': str(self.instance_id) if self.instance_id else None,
            'payload': self.payload,
            'status': self.status.value if isinstance(self.status, WebhookDeliveryStatus) else self.status,
            'response_status': self.response_status,
            'response_body': self.response_body,
            'retry_count': self.retry_count,
            'error_message': self.error_message,
            'next_retry_at': self.next_retry_at.isoformat() if self.next_retry_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<WebhookDeliveryLog {self.webhook_config_id} {self.status}>'
