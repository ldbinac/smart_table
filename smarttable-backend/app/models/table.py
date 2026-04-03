"""
表格模型模块
"""
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Table(db.Model):
    """
    表格模型
    
    属性:
        id: UUID 主键
        base_id: 所属基础数据 ID
        name: 表格名称
        description: 描述
        order: 排序顺序
        primary_field_id: 主字段 ID
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    __tablename__ = 'tables'
    
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
    name: Mapped[str] = mapped_column(
        String(100),
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
    primary_field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('fields.id', ondelete='SET NULL', use_alter=True),
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
    base = relationship(
        'Base',
        back_populates='tables',
        lazy='joined'
    )
    
    fields = relationship(
        'Field',
        back_populates='table',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='Field.order',
        foreign_keys='Field.table_id'
    )
    
    primary_field = relationship(
        'Field',
        lazy='joined',
        foreign_keys=[primary_field_id],
        post_update=True
    )
    
    records = relationship(
        'Record',
        back_populates='table',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    views = relationship(
        'View',
        back_populates='table',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    def get_record_count(self) -> int:
        """获取记录数量"""
        return self.records.count()
    
    def get_field_count(self) -> int:
        """获取字段数量"""
        return self.fields.count()
    
    def to_dict(self, include_stats: bool = False) -> dict:
        """
        转换为字典
        
        Args:
            include_stats: 是否包含统计信息
            
        Returns:
            表格数据字典
        """
        data = {
            'id': str(self.id),
            'base_id': str(self.base_id),
            'name': self.name,
            'description': self.description,
            'order': self.order,
            'primary_field_id': str(self.primary_field_id) if self.primary_field_id else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_stats:
            data['record_count'] = self.get_record_count()
            data['field_count'] = self.get_field_count()
        
        return data
    
    def __repr__(self) -> str:
        return f'<Table {self.name}>'
