"""
视图模型模块
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, Dict, Any, List

from sqlalchemy import String, DateTime, ForeignKey, Integer, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class ViewType(PyEnum):
    """视图类型枚举"""
    GRID = 'grid'              # 网格视图
    GALLERY = 'gallery'        # 画廊视图
    KANBAN = 'kanban'          # 看板视图
    CALENDAR = 'calendar'      # 日历视图
    TIMELINE = 'timeline'      # 时间线视图
    LIST = 'list'              # 列表视图
    FORM = 'form'              # 表单视图


class View(db.Model):
    """
    视图模型
    
    属性:
        id: UUID 主键
        table_id: 所属表格 ID
        name: 视图名称
        type: 视图类型
        description: 描述
        is_default: 是否为默认视图
        config: 视图配置（JSON）
        filters: 筛选条件（JSON）
        sorts: 排序规则（JSON）
        hidden_fields: 隐藏字段列表（JSON）
        field_widths: 字段宽度（JSON）
        order: 排序顺序
        created_by: 创建者 ID
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    __tablename__ = 'views'
    
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
    type: Mapped[str] = mapped_column(
        String(50),
        default=ViewType.GRID.value,
        nullable=False
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
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    filters: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        default=list
    )
    sorts: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        default=list
    )
    hidden_fields: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        default=list
    )
    field_widths: Mapped[Optional[Dict[str, int]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
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
    
    # 关系定义
    table = relationship(
        'Table',
        back_populates='views',
        lazy='joined'
    )
    
    creator = relationship(
        'User',
        lazy='joined'
    )
    
    def apply_filters(self, query):
        """
        应用筛选条件到查询
        
        Args:
            query: SQLAlchemy 查询对象
            
        Returns:
            应用筛选后的查询对象
        """
        if not self.filters:
            return query
        
        for filter_item in self.filters:
            field_id = filter_item.get('field_id')
            operator = filter_item.get('operator')
            value = filter_item.get('value')
            
            # 这里需要根据具体的筛选逻辑实现
            # 示例：简单的相等筛选
            if operator == 'equals':
                query = query.filter(
                    db.func.jsonb_extract_path_text(
                        Record.values, field_id
                    ) == str(value)
                )
            elif operator == 'contains':
                query = query.filter(
                    db.func.jsonb_extract_path_text(
                        Record.values, field_id
                    ).ilike(f'%{value}%')
                )
        
        return query
    
    def apply_sorts(self, query):
        """
        应用排序规则到查询
        
        Args:
            query: SQLAlchemy 查询对象
            
        Returns:
            应用排序后的查询对象
        """
        if not self.sorts:
            return query.order_by(Record.created_at.desc())
        
        for sort_item in self.sorts:
            field_id = sort_item.get('field_id')
            direction = sort_item.get('direction', 'asc')
            
            # 这里需要根据具体的排序逻辑实现
            sort_expr = db.func.jsonb_extract_path_text(
                Record.values, field_id
            )
            
            if direction == 'desc':
                query = query.order_by(sort_expr.desc())
            else:
                query = query.order_by(sort_expr.asc())
        
        return query
    
    def get_visible_fields(self) -> List[str]:
        """
        获取可见字段列表
        
        Returns:
            可见字段 ID 列表
        """
        if not self.hidden_fields:
            return []
        
        # 获取表格所有字段
        all_fields = [str(f.id) for f in self.table.fields.all()]
        
        # 返回未隐藏的字段
        return [f for f in all_fields if f not in self.hidden_fields]
    
    def to_dict(self, include_config: bool = True) -> dict:
        """
        转换为字典
        
        Args:
            include_config: 是否包含详细配置
            
        Returns:
            视图数据字典
        """
        data = {
            'id': str(self.id),
            'table_id': str(self.table_id),
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'is_default': self.is_default,
            'order': self.order,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_config:
            data['config'] = self.config or {}
            data['filters'] = self.filters or []
            data['sorts'] = self.sorts or []
            data['hidden_fields'] = self.hidden_fields or []
            data['field_widths'] = self.field_widths or {}
        
        return data
    
    def __repr__(self) -> str:
        return f'<View {self.name} ({self.type})>'


# 导入 Record 用于类型提示
from app.models.record import Record
