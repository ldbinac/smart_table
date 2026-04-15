"""
用户模型模块
包含用户和令牌黑名单模型
"""
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum as PyEnum

from sqlalchemy import String, Boolean, DateTime, Enum, Text, ForeignKey
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db, bcrypt


class UserRole(PyEnum):
    """用户角色枚举"""
    OWNER = 'owner'
    ADMIN = 'admin'
    WORKSPACE_ADMIN = 'workspace_admin'
    EDITOR = 'editor'
    COMMENTER = 'commenter'
    VIEWER = 'viewer'


class UserStatus(PyEnum):
    """用户状态枚举"""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SUSPENDED = 'suspended'
    DELETED = 'deleted'


class User(db.Model):
    """
    用户模型
    
    属性:
        id: UUID 主键
        email: 邮箱地址（唯一）
        password_hash: 密码哈希
        name: 用户姓名
        avatar: 头像 URL
        role: 用户角色
        status: 用户状态
        email_verified: 邮箱是否已验证
        last_login_at: 最后登录时间
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    __tablename__ = 'users'
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    avatar: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.EDITOR,
        nullable=False
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus),
        default=UserStatus.ACTIVE,
        nullable=False
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    verification_token: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )
    verification_token_expires: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True
    )
    reset_token: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )
    reset_token_expires: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True
    )
    last_login_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True
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
    
    owned_bases = relationship(
        'Base',
        back_populates='owner',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    base_memberships = relationship(
        'BaseMember',
        back_populates='user',
        foreign_keys='BaseMember.user_id',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    base_shares_created = relationship(
        'BaseShare',
        back_populates='creator',
        foreign_keys='BaseShare.created_by',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    dashboards = relationship(
        'Dashboard',
        back_populates='user',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    def __init__(self, **kwargs):
        """初始化用户，自动处理密码哈希"""
        password = kwargs.pop('password', None)
        super(User, self).__init__(**kwargs)
        if password:
            self.set_password(password)
    
    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        self.password_changed_at = datetime.now(timezone.utc)
        self.must_change_password = False
    
    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def update_last_login(self) -> None:
        self.last_login_at = datetime.now(timezone.utc)
        db.session.commit()
    
    def generate_verification_token(self) -> str:
        """生成邮箱验证令牌，有效期24小时"""
        import secrets
        self.verification_token = secrets.token_urlsafe(32)
        self.verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        db.session.commit()
        return self.verification_token
    
    def verify_email(self, token: str) -> bool:
        """验证邮箱令牌"""
        if not self.verification_token or self.verification_token != token:
            return False
        if not self.verification_token_expires or datetime.now(timezone.utc) > self.verification_token_expires:
            return False
        self.email_verified = True
        self.verification_token = None
        self.verification_token_expires = None
        db.session.commit()
        return True
    
    def generate_reset_token(self) -> str:
        """生成密码重置令牌，有效期1小时"""
        import secrets
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        db.session.commit()
        return self.reset_token
    
    def verify_reset_token(self, token: str) -> bool:
        """验证密码重置令牌"""
        if not self.reset_token or self.reset_token != token:
            return False
        if not self.reset_token_expires or datetime.now(timezone.utc) > self.reset_token_expires:
            return False
        return True
    
    def clear_reset_token(self) -> None:
        """清除密码重置令牌"""
        self.reset_token = None
        self.reset_token_expires = None
        db.session.commit()
    
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE
    
    def is_admin(self) -> bool:
        return self.role in [UserRole.ADMIN, UserRole.WORKSPACE_ADMIN]
    
    def to_dict(self, include_email: bool = False) -> dict:
        data = {
            'id': str(self.id),
            'name': self.name,
            'avatar': self.avatar,
            'role': self.role.value,
            'status': self.status.value,
            'email_verified': self.email_verified,
            'must_change_password': self.must_change_password,
            'password_changed_at': self.password_changed_at.isoformat() if self.password_changed_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        if include_email:
            data['email'] = self.email
        return data
    
    def __repr__(self) -> str:
        return f'<User {self.email}>'


class TokenBlocklist(db.Model):
    """JWT 令牌黑名单模型"""
    
    __tablename__ = 'token_blocklist'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    token_type: Mapped[str] = mapped_column(String(10), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    revoked_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    user = relationship('User', lazy='joined')
    
    def __repr__(self) -> str:
        return f'<TokenBlocklist {self.jti}>'
