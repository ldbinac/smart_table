"""
记录模型模块
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Record(db.Model):
    """
    记录模型
    
    属性:
        id: UUID 主键
        table_id: 所属表格 ID
        values: 字段值（JSON）
        created_by: 创建者 ID
        updated_by: 最后更新者 ID
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    __tablename__ = 'records'
    
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
    values: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
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
        back_populates='records',
        lazy='joined'
    )
    
    creator = relationship(
        'User',
        foreign_keys=[created_by],
        lazy='joined'
    )
    
    updater = relationship(
        'User',
        foreign_keys=[updated_by],
        lazy='joined'
    )
    
    comments = relationship(
        'RecordComment',
        back_populates='record',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='RecordComment.created_at.desc()'
    )
    
    def get_value(self, field_id: str) -> Any:
        """
        获取指定字段的值
        
        Args:
            field_id: 字段 ID
            
        Returns:
            字段值
        """
        return self.values.get(field_id)
    
    def set_value(self, field_id: str, value: Any) -> None:
        """
        设置指定字段的值
        
        Args:
            field_id: 字段 ID
            value: 字段值
        """
        if self.values is None:
            self.values = {}
        self.values[field_id] = value
    
    def get_primary_value(self) -> str:
        """
        获取主字段的值（用于显示）
        
        Returns:
            主字段值字符串
        """
        if self.table and self.table.primary_field_id:
            primary_value = self.values.get(str(self.table.primary_field_id))
            return str(primary_value) if primary_value else '未命名记录'
        return '未命名记录'
    
    def validate_values(self) -> tuple[bool, Optional[list]]:
        """
        验证记录的所有字段值
        
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        # 获取表格的所有字段
        fields = self.table.fields.all()
        
        for field in fields:
            value = self.values.get(str(field.id))
            is_valid, error = field.validate_value(value)
            if not is_valid:
                errors.append(error)
        
        return len(errors) == 0, errors if errors else None
    
    def to_dict(self, include_values: bool = True, include_meta: bool = True) -> dict:
        """
        转换为字典
        
        Args:
            include_values: 是否包含字段值
            include_meta: 是否包含元数据
            
        Returns:
            记录数据字典
        """
        data = {
            'id': str(self.id),
            'table_id': str(self.table_id)
        }
        
        if include_values:
            data['values'] = self.values or {}
            data['primary_value'] = self.get_primary_value()
        
        if include_meta:
            data['created_by'] = str(self.created_by) if self.created_by else None
            data['updated_by'] = str(self.updated_by) if self.updated_by else None
            data['created_at'] = self.created_at.isoformat()
            data['updated_at'] = self.updated_at.isoformat()
        
        return data
    
    def __repr__(self) -> str:
        return f'<Record {self.id}>'


class RecordComment(db.Model):
    """
    记录评论模型
    
    属性:
        id: UUID 主键
        record_id: 所属记录 ID
        user_id: 评论用户 ID
        content: 评论内容
        parent_id: 父评论 ID（用于回复）
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    __tablename__ = 'record_comments'
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('records.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('record_comments.id', ondelete='CASCADE'),
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
    record = relationship(
        'Record',
        back_populates='comments',
        lazy='joined'
    )
    
    user = relationship(
        'User',
        lazy='joined'
    )
    
    replies = relationship(
        'RecordComment',
        back_populates='parent',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    parent = relationship(
        'RecordComment',
        remote_side=[id],
        back_populates='replies',
        lazy='joined'
    )
    
    def to_dict(self, include_user: bool = True) -> dict:
        """
        转换为字典
        
        Args:
            include_user: 是否包含用户信息
            
        Returns:
            评论数据字典
        """
        data = {
            'id': str(self.id),
            'record_id': str(self.record_id),
            'content': self.content,
            'parent_id': str(self.parent_id) if self.parent_id else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_user and self.user:
            data['user'] = {
                'id': str(self.user.id),
                'name': self.user.name,
                'avatar': self.user.avatar
            }
        else:
            data['user_id'] = str(self.user_id)
        
        return data
    
    def __repr__(self) -> str:
        return f'<RecordComment {self.id}>'
