"""
仪表盘模型模块
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import String, DateTime, ForeignKey, Boolean, Text, JSON, Integer
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Dashboard(db.Model):
    """
    仪表盘模型

    属性:
        id: UUID 主键
        base_id: 所属 Base ID
        user_id: 创建者 ID
        name: 名称
        description: 描述
        layout: 布局配置（JSON）
        widgets: 组件列表（JSON）
        is_public: 是否公开
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = 'dashboards'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('bases.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    layout: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    widgets: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=list
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
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

    base = relationship(
        'Base',
        back_populates='dashboards',
        lazy='joined'
    )

    user = relationship(
        'User',
        back_populates='dashboards',
        lazy='joined'
    )

    shares = relationship('DashboardShare', back_populates='dashboard', cascade='all, delete-orphan')

    def to_dict(self, include_widgets: bool = True) -> dict:
        result = {
            'id': str(self.id),
            'base_id': str(self.base_id),
            'user_id': str(self.user_id) if self.user_id else None,
            'name': self.name,
            'description': self.description,
            'layout': self.layout or {},
            'is_public': self.is_public,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        # 如果需要包含组件，添加 widgets 字段
        if include_widgets:
            result['widgets'] = self.widgets or []
        
        return result

    def __repr__(self) -> str:
        return f'<Dashboard {self.name}>'


class DashboardWidget(db.Model):
    """
    仪表盘组件模型

    属性:
        id: UUID 主键
        dashboard_id: 所属仪表盘 ID
        type: 组件类型
        title: 标题
        config: 配置（JSON）
        position_x: X 位置
        position_y: Y 位置
        width: 宽度
        height: 高度
        order: 排序
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = 'dashboard_widgets'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('dashboards.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    position_x: Mapped[int] = mapped_column(Integer, default=0)
    position_y: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int] = mapped_column(Integer, default=6)
    height: Mapped[int] = mapped_column(Integer, default=4)
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    dashboard = relationship('Dashboard', lazy='joined')

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'dashboard_id': str(self.dashboard_id),
            'type': self.type,
            'title': self.title,
            'config': self.config or {},
            'position_x': self.position_x,
            'position_y': self.position_y,
            'width': self.width,
            'height': self.height,
            'order': self.order,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<DashboardWidget {self.type} ({self.title})>'
