"""
仪表盘分享模型
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import String, Text, Boolean, DateTime, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.extensions import db


class SharePermission(str, enum.Enum):
    """分享权限类型"""
    VIEW = 'view'
    EDIT = 'edit'


class DashboardShare(db.Model):
    """仪表盘分享配置表"""
    
    __tablename__ = 'dashboard_shares'
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    # 关联的仪表盘 ID
    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        ForeignKey('dashboards.id', ondelete='CASCADE'),
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
    
    # 访问密码（可选）
    access_code: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True
    )
    
    # 过期时间（可选，Unix 时间戳）
    expires_at: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    # 最大访问次数（可选，-1 表示无限制）
    max_access_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    # 当前访问次数
    current_access_count: Mapped[int] = mapped_column(
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
    
    # 分享权限
    permission: Mapped[SharePermission] = mapped_column(
        SQLEnum(SharePermission),
        default=SharePermission.VIEW,
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
    
    # 创建者 ID（可选）
    created_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    
    # 关联关系
    dashboard = relationship('Dashboard', back_populates='shares')
    creator = relationship('User', foreign_keys=[created_by])
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': str(self.id),
            'dashboard_id': str(self.dashboard_id),
            'share_token': self.share_token,
            'has_access_code': self.access_code is not None,
            'expires_at': self.expires_at,
            'max_access_count': self.max_access_count,
            'current_access_count': self.current_access_count,
            'is_active': self.is_active,
            'permission': self.permission.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_accessed_at': self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            'created_by': str(self.created_by) if self.created_by else None
        }
    
    def __repr__(self) -> str:
        return f'<DashboardShare {self.share_token}>'
