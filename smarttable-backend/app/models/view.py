"""
视图模型模块
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, Dict, Any, List

from sqlalchemy import String, DateTime, ForeignKey, Integer, Boolean, Text, JSON, Index
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class ViewType(PyEnum):
    """视图类型枚举"""
    TABLE = 'table'        # 表格视图
    GALLERY = 'gallery'    # 画廊视图
    KANBAN = 'kanban'      # 看板视图
    GANTT = 'gantt'        # 甘特图视图
    CALENDAR = 'calendar'  # 日历视图
    FORM = 'form'          # 表单视图
    TIMELINE = 'timeline'  # 时间线视图
    LIST = 'list'          # 列表视图


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
    filters: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        default=list
    )
    sort_config: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
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
    # 新增字段支持
    hidden_fields: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        default=list
    )
    frozen_fields: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        default=list
    )
    row_height: Mapped[str] = mapped_column(
        String(20),
        default='medium',
        nullable=False
    )
    field_widths: Mapped[Optional[Dict[str, int]]] = mapped_column(
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
        # 如果 type 是枚举对象，获取其 value 值；如果是字符串，直接使用
        type_value = self.type.value if hasattr(self.type, 'value') else self.type
        
        # 从 group_config 中提取 group_bys
        group_bys = []
        if self.group_config and isinstance(self.group_config, dict):
            group_bys = self.group_config.get('group_bys', [])
        
        return {
            'id': str(self.id),
            'table_id': str(self.table_id),
            'name': self.name,
            'type': type_value,
            'description': self.description,
            'order': self.order,
            'is_default': self.is_default,
            'is_public': self.is_public,
            'filters': self.filters or [],  # filters 是数组
            'sorts': self.sort_config or [],  # 使用 sorts 而不是 sort_config
            'sort_config': self.sort_config or [],
            'group_bys': group_bys,  # 添加 group_bys 字段
            'group_config': self.group_config or {},
            'field_visibility': self.field_visibility or {},
            # 新增字段
            'hidden_fields': self.hidden_fields or [],
            'frozen_fields': self.frozen_fields or [],
            'row_height': self.row_height or 'medium',
            'field_widths': self.field_widths or {},
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self) -> str:
        # 如果 type 是枚举对象，获取其 value 值；如果是字符串，直接使用
        type_value = self.type.value if hasattr(self.type, 'value') else self.type
        return f'<View {self.name} ({type_value})>'
