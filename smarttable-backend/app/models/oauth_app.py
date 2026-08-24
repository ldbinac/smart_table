"""
第三方应用接入模型

包含：
- OAuthApp: 第三方应用（凭据 / 授权 Base 范围 / scope / 状态）
- ApiAppToken: 已签发应用令牌的元数据（仅存 jti，不存明文 token）
- ApiAppAuditLog: 应用相关操作的审计日志（与用户操作日志分离）
"""
import secrets
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db_types import CompatUUID as UUID, CompatJSON as JSON
from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OAuthApp(db.Model):
    """
    第三方应用模型（OAuth2 Client Credentials 模式）

    属性：
        id: UUID 主键
        app_name: 应用名称
        client_id: 系统生成的唯一客户端标识
        client_secret_hash: client_secret 的哈希（仅存哈希，不存明文）
        owner_id: 创建者 / 管理员用户 ID
        callback_url: 回调地址（预留，客户端凭证模式暂未使用）
        allowed_bases: 授权可访问的 Base id 白名单（JSON 数组）
        scopes: 空格分隔的 scope 权限字符串
        is_active: 应用是否启用（停用后所有令牌立即失效）
        created_at / updated_at: 时间戳
    """

    __tablename__ = 'oauth_apps'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    app_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    client_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True
    )
    client_secret_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    callback_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True
    )
    allowed_bases: Mapped[list] = mapped_column(
        JSON(),
        nullable=False,
        default=list
    )
    scopes: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default=''
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean(),
        nullable=False,
        default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False
    )

    owner = relationship(
        'User',
        back_populates='oauth_apps',
        lazy='joined'
    )
    tokens = relationship(
        'ApiAppToken',
        back_populates='app',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    audit_logs = relationship(
        'ApiAppAuditLog',
        back_populates='app',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self) -> str:
        return f'<OAuthApp {self.app_name} ({self.client_id})>'

    def to_dict(self, include_secret: bool = False, base_names: Optional[dict] = None) -> dict:
        """序列化为字典；include_secret 为 True 时附带明文 client_secret（仅创建/重置时返回）。

        base_names: {base_id(str): name(str)} 映射，用于展示授权 Base 名称；
        未传入时自动查询（列表接口建议传入以避免 N+1）。
        """
        data = {
            'id': str(self.id),
            'app_name': self.app_name,
            'client_id': self.client_id,
            'owner_id': str(self.owner_id),
            'callback_url': self.callback_url,
            'allowed_bases': self.allowed_bases or [],
            'allowed_base_names': self._resolve_base_names(base_names),
            'scopes': self.scopes.split() if self.scopes else [],
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_secret:
            data['client_secret'] = getattr(self, '_plain_secret', None)
        return data

    def _resolve_base_names(self, base_names: Optional[dict] = None) -> List[str]:
        """返回授权 Base 的名称列表（顺序与 allowed_bases 一致，缺失时回退为 id）"""
        ids = self.allowed_bases or []
        if not ids:
            return []
        if base_names is None:
            from app.models.base import Base as BaseModel
            bases = BaseModel.query.filter(BaseModel.id.in_(ids)).all()
            base_names = {str(b.id): b.name for b in bases}
        return [base_names.get(str(i), str(i)) for i in ids]


class ApiAppToken(db.Model):
    """
    已签发应用令牌元数据

    仅持久化 jti 等元数据，不存明文 token。撤销时通过 revoked 标志 + Redis jti 黑名单实现即时失效。
    """

    __tablename__ = 'api_app_tokens'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    jti: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('oauth_apps.id', ondelete='CASCADE'),
        nullable=False
    )
    scope: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default=''
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean(),
        nullable=False,
        default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False
    )

    app = relationship(
        'OAuthApp',
        back_populates='tokens',
        lazy='joined'
    )

    __table_args__ = (
        Index('ix_api_app_tokens_app_id', 'app_id'),
        Index('ix_api_app_tokens_jti', 'jti'),
    )

    def __repr__(self) -> str:
        return f'<ApiAppToken {self.jti} app={self.app_id}>'

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'jti': self.jti,
            'app_id': str(self.app_id),
            'scope': self.scope.split() if self.scope else [],
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'revoked': self.revoked,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ApiAppAuditLog(db.Model):
    """
    第三方应用审计日志

    记录应用创建 / 编辑 / 密钥重置 / 令牌颁发 / 撤销 / 开放 API 调用等行为，与用户操作日志分离。
    """

    __tablename__ = 'api_app_audit_logs'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    app_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('oauth_apps.id', ondelete='SET NULL'),
        nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    detail: Mapped[str | None] = mapped_column(
        Text(),
        nullable=True
    )
    ip: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False
    )

    app = relationship(
        'OAuthApp',
        back_populates='audit_logs',
        lazy='joined'
    )

    __table_args__ = (
        Index('ix_api_app_audit_logs_app_id', 'app_id'),
        Index('ix_api_app_audit_logs_created_at', 'created_at'),
    )

    def __repr__(self) -> str:
        return f'<ApiAppAuditLog {self.action} app={self.app_id}>'

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'app_id': str(self.app_id) if self.app_id else None,
            'action': self.action,
            'detail': self.detail,
            'ip': self.ip,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


def generate_client_id() -> str:
    """生成唯一的 client_id（前缀 oa_ + 随机 hex）"""
    return 'oa_' + secrets.token_hex(16)


def generate_client_secret() -> str:
    """生成 client_secret（明文，调用方负责哈希存储）"""
    return 'os_' + secrets.token_urlsafe(32)
