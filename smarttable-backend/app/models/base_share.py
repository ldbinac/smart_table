"""
Base 分享模型
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.extensions import db


class SharePermission(str, enum.Enum):
    """分享权限类型"""
    VIEW = 'view'
    EDIT = 'edit'


class BaseShare(db.Model):
    """
    Base 分享配置表
    
    属性:
        id: UUID 主键
        base_id: 关联的 Base ID
        share_token: 分享令牌（用于生成分享链接）
        created_by: 创建者用户 ID
        permission: 分享权限（view/edit）
        expires_at: 过期时间（可选，Unix 时间戳）
        access_count: 访问次数
        is_active: 是否激活
        created_at: 创建时间
        updated_at: 更新时间
        last_accessed_at: 最后访问时间
    """
    
    __tablename__ = 'base_shares'
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    # 关联的 Base ID
    base_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey('bases.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # 分享令牌（用于生成分享链接）
    share_token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True
    )
    
    # 创建者 ID
    created_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    
    # 分享权限
    permission: Mapped[SharePermission] = mapped_column(
        SQLEnum(SharePermission),
        default=SharePermission.VIEW,
        nullable=False
    )
    
    # 过期时间（可选，Unix 时间戳）
    expires_at: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    # 访问次数
    access_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    # 是否激活
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # 最后访问时间
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    
    # 关联关系
    base = relationship('Base', back_populates='shares')
    creator = relationship('User', foreign_keys=[created_by])
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': str(self.id),
            'base_id': str(self.base_id),
            'share_token': self.share_token,
            'permission': self.permission.value,
            'expires_at': self.expires_at,
            'access_count': self.access_count,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_accessed_at': self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            'created_by': str(self.created_by)
        }
    
    def __repr__(self) -> str:
        return f'<BaseShare {self.share_token}>'
