"""
基础数据模型模块
包含 Base（数据库/工作区）和 BaseMember（成员关系）模型
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Enum, ForeignKey, UniqueConstraint
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class MemberRole(PyEnum):
    """成员角色枚举"""
    OWNER = 'owner'
    ADMIN = 'admin'
    EDITOR = 'editor'
    COMMENTER = 'commenter'
    VIEWER = 'viewer'


class Base(db.Model):
    """
    基础数据模型（工作区/数据库）

    属性:
        id: UUID 主键
        name: 基础数据名称
        description: 描述
        owner_id: 所有者用户 ID
        icon: 图标
        color: 主题颜色
        is_personal: 是否为个人空间
        is_starred: 是否已收藏
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = 'bases'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        String(500),
        nullable=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    icon: Mapped[str] = mapped_column(
        String(50),
        nullable=True
    )
    color: Mapped[str] = mapped_column(
        String(7),
        default='#6366F1',
        nullable=True
    )
    is_personal: Mapped[bool] = mapped_column(
        default=False,
        nullable=False
    )
    is_starred: Mapped[bool] = mapped_column(
        default=False,
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

    owner = relationship(
        'User',
        back_populates='owned_bases',
        lazy='joined'
    )

    members = relationship(
        'BaseMember',
        back_populates='base',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    tables = relationship(
        'Table',
        back_populates='base',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='Table.order'
    )

    dashboards = relationship(
        'Dashboard',
        back_populates='base',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def get_member_count(self) -> int:
        return self.members.count()

    def get_table_count(self) -> int:
        return self.tables.count()

    def to_dict(self, include_stats: bool = False) -> dict:
        data = {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'owner_id': str(self.owner_id),
            'icon': self.icon,
            'color': self.color,
            'is_personal': self.is_personal,
            'is_starred': self.is_starred,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

        if include_stats:
            data['member_count'] = self.get_member_count()
            data['table_count'] = self.get_table_count()

        return data

    def __repr__(self) -> str:
        return f'<Base {self.name}>'


class BaseMember(db.Model):
    """
    基础数据成员关系模型

    属性:
        id: UUID 主键
        base_id: 基础数据 ID
        user_id: 用户 ID
        role: 成员角色
        invited_by: 邀请人 ID
        joined_at: 加入时间
    """

    __tablename__ = 'base_members'

    __table_args__ = (
        UniqueConstraint('base_id', 'user_id', name='uix_base_member'),
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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    role: Mapped[MemberRole] = mapped_column(
        Enum(MemberRole),
        default=MemberRole.EDITOR,
        nullable=False
    )
    invited_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    base = relationship(
        'Base',
        back_populates='members',
        lazy='joined'
    )

    user = relationship(
        'User',
        back_populates='base_memberships',
        foreign_keys=[user_id],
        lazy='joined'
    )

    inviter = relationship(
        'User',
        foreign_keys=[invited_by],
        lazy='joined'
    )

    def to_dict(self, include_user: bool = False) -> dict:
        data = {
            'id': str(self.id),
            'base_id': str(self.base_id),
            'user_id': str(self.user_id),
            'role': self.role.value,
            'invited_by': str(self.invited_by) if self.invited_by else None,
            'joined_at': self.joined_at.isoformat()
        }

        if include_user and self.user:
            data['user'] = self.user.to_dict()

        return data

    def __repr__(self) -> str:
        return f'<BaseMember {self.user_id}@{self.base_id}>'
