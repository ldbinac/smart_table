"""
视图模型模块
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, Dict, Any

from sqlalchemy import String, DateTime, ForeignKey, Integer, Boolean, Text, JSON, Index
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class ViewType(PyEnum):
    """视图类型枚举"""
    TABLE = 'table'
    GALLERY = 'gallery'
    KANBAN = 'kanban'
    CALENDAR = 'calendar'
    TIMELINE = 'timeline'
    LIST = 'list'


class View(db.Model):
    """
    视图模型

    属性:
        id: UUID 主键
        table_id: 所属表格 ID
        name: 视图名称
        type: 视图类型
        description: 描述
        order: 排序顺序
        is_default: 是否为默认视图
        is_public: 是否公开
        filters: 筛选条件（JSON）
        sort_config: 排序配置（JSON）
        group_config: 分组配置（JSON）
        field_visibility: 字段可见性（JSON）
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = 'views'

    __table_args__ = (
        Index('ix_views_table_default', 'table_id', 'is_default'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('tables.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    type: Mapped[ViewType] = mapped_column(
        String(20),
        default=ViewType.TABLE,
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    filters: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    sort_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=list
    )
    group_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True
    )
    field_visibility: Mapped[Optional[Dict[str, bool]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    table = relationship(
        'Table',
        back_populates='views',
        lazy='joined'
    )

    def apply_filters(self, query):
        if not self.filters:
            return query
        from app.models.record import Record
        for filter_item in self.filters:
            field_name = filter_item.get('field')
            operator = filter_item.get('operator')
            value = filter_item.get('value')
            column = getattr(Record.values, field_name)
            if operator == 'eq':
                query = query.filter(column == value)
            elif operator == 'ne':
                query = query.filter(column != value)
            elif operator == 'contains':
                query = query.filter(column.contains(value))
            elif operator == 'gt':
                query = query.filter(column > value)
            elif operator == 'lt':
                query = query.filter(column < value)
        return query

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'table_id': str(self.table_id),
            'name': self.name,
            'type': self.type.value,
            'description': self.description,
            'order': self.order,
            'is_default': self.is_default,
            'is_public': self.is_public,
            'filters': self.filters or {},
            'sort_config': self.sort_config or [],
            'group_config': self.group_config or {},
            'field_visibility': self.field_visibility or {},
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<View {self.name} ({self.type.value})>'
