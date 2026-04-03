"""
仪表盘模型模块
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, Dict, Any, List

from sqlalchemy import String, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class WidgetType(PyEnum):
    """组件类型枚举"""
    CHART_BAR = 'chart_bar'           # 柱状图
    CHART_LINE = 'chart_line'         # 折线图
    CHART_PIE = 'chart_pie'           # 饼图
    CHART_DOUGHNUT = 'chart_doughnut' # 环形图
    CHART_AREA = 'chart_area'         # 面积图
    CHART_SCATTER = 'chart_scatter'   # 散点图
    CHART_RADAR = 'chart_radar'       # 雷达图
    NUMBER_CARD = 'number_card'       # 数字卡片
    TABLE_PREVIEW = 'table_preview'   # 表格预览
    RECORD_LIST = 'record_list'       # 记录列表
    TEXT_BLOCK = 'text_block'         # 文本块
    IMAGE_BLOCK = 'image_block'       # 图片块
    IFRAME_EMBED = 'iframe_embed'     # 嵌入页面


class Dashboard(db.Model):
    """
    仪表盘模型
    
    属性:
        id: UUID 主键
        base_id: 所属基础数据 ID
        user_id: 创建用户 ID
        name: 仪表盘名称
        description: 描述
        is_default: 是否为默认仪表盘
        layout: 布局配置（JSON）
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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(100),
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
    layout: Mapped[Optional[Dict[str, Any]]] = mapped_column(
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
    
    # 关系定义
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
    
    widgets = relationship(
        'DashboardWidget',
        back_populates='dashboard',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='DashboardWidget.order'
    )
    
    def get_widget_count(self) -> int:
        """获取组件数量"""
        return self.widgets.count()
    
    def to_dict(self, include_widgets: bool = False) -> dict:
        """
        转换为字典
        
        Args:
            include_widgets: 是否包含组件列表
            
        Returns:
            仪表盘数据字典
        """
        data = {
            'id': str(self.id),
            'base_id': str(self.base_id),
            'user_id': str(self.user_id),
            'name': self.name,
            'description': self.description,
            'is_default': self.is_default,
            'layout': self.layout or {},
            'widget_count': self.get_widget_count(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_widgets:
            data['widgets'] = [w.to_dict() for w in self.widgets.all()]
        
        return data
    
    def __repr__(self) -> str:
        return f'<Dashboard {self.name}>'


class DashboardWidget(db.Model):
    """
    仪表盘组件模型
    
    属性:
        id: UUID 主键
        dashboard_id: 所属仪表盘 ID
        type: 组件类型
        title: 组件标题
        config: 组件配置（JSON）
        data_source: 数据源配置（JSON）
        position: 位置配置（JSON）
        order: 排序顺序
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
        nullable=False
    )
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    data_source: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    position: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    order: Mapped[int] = mapped_column(
        default=0,
        nullable=False
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
    dashboard = relationship(
        'Dashboard',
        back_populates='widgets',
        lazy='joined'
    )
    
    def to_dict(self) -> dict:
        """
        转换为字典
        
        Returns:
            组件数据字典
        """
        return {
            'id': str(self.id),
            'dashboard_id': str(self.dashboard_id),
            'type': self.type,
            'title': self.title,
            'config': self.config or {},
            'data_source': self.data_source or {},
            'position': self.position or {},
            'order': self.order,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self) -> str:
        return f'<DashboardWidget {self.title} ({self.type})>'
