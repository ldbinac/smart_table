"""
插件模型模块
包含 Plugin / PluginVersion / PluginConfig / PluginInstallation / PluginRunLog 模型

插件为全局资源（包文件全局共享），Base 级仅存在安装/启用关系。
有效启用 = 全局 status == enabled 且 plugin_installations.enabled == True。
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional, Dict, Any, List

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean, JSON, Enum, Index
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PluginType(PyEnum):
    """插件形态：ui 前端 UI 插件 / script 后端脚本插件"""
    UI = 'ui'
    SCRIPT = 'script'


class PluginStatus(PyEnum):
    """插件全局状态

    installed: 已安装未启用
    enabled:   全局启用
    disabled:  全局禁用（Base 级 enabled 无效）
    error:     连续运行失败自动置入，可手动恢复
    """
    INSTALLED = 'installed'
    ENABLED = 'enabled'
    DISABLED = 'disabled'
    ERROR = 'error'


class PluginConfigScope(PyEnum):
    """配置作用域：global 全局 / base Base 级 / kv 插件自有 KV 存储"""
    GLOBAL = 'global'
    BASE = 'base'
    KV = 'kv'


class RunStatus(PyEnum):
    """脚本插件运行状态"""
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    TIMEOUT = 'timeout'


class Plugin(db.Model):
    """插件全局记录

    属性:
        id: 插件 ID（反向域名格式字符串主键，如 com.example.hello-panel）
        name: 显示名
        description: 描述
        icon: 包内图标相对路径
        type: ui / script
        status: 全局状态
        current_version: 当前生效版本号（指向 plugin_versions 中一条记录）
        manifest: 完整清单 JSON
        engines_text: 宿主版本兼容范围文本
        created_at / updated_at: 时间戳
    """

    __tablename__ = 'plugins'

    __table_args__ = (
        Index('ix_plugins_type', 'type'),
        Index('ix_plugins_status', 'status'),
    )

    id: Mapped[str] = mapped_column(
        String(200),
        primary_key=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    type: Mapped[PluginType] = mapped_column(
        Enum(PluginType, native_enum=False, length=20),
        nullable=False
    )
    status: Mapped[PluginStatus] = mapped_column(
        Enum(PluginStatus, native_enum=False, length=20),
        default=PluginStatus.INSTALLED,
        nullable=False
    )
    current_version: Mapped[str] = mapped_column(String(50), nullable=False)
    manifest: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )
    engines_text: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
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

    versions: Mapped[List["PluginVersion"]] = relationship(
        back_populates='plugin',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    installations: Mapped[List["PluginInstallation"]] = relationship(
        back_populates='plugin',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    def to_dict(self, include_versions: bool = False) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'type': self.type.value if isinstance(self.type, PluginType) else self.type,
            'status': self.status.value if isinstance(self.status, PluginStatus) else self.status,
            'current_version': self.current_version,
            'manifest': self.manifest,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PluginVersion(db.Model):
    """插件版本记录（升级保留旧版本、支持回滚）"""

    __tablename__ = 'plugin_versions'

    __table_args__ = (
        Index('ix_plugin_versions_plugin_id', 'plugin_id'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    plugin_id: Mapped[str] = mapped_column(
        String(200),
        ForeignKey('plugins.id', ondelete='CASCADE'),
        nullable=False
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    package_path: Mapped[str] = mapped_column(String(500), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False
    )

    plugin: Mapped[Plugin] = relationship(back_populates='versions')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id),
            'plugin_id': self.plugin_id,
            'version': self.version,
            'checksum': self.checksum,
            'installed_at': self.installed_at.isoformat() if self.installed_at else None,
        }


class PluginConfig(db.Model):
    """插件配置（global/base 两级作用域）与插件自有 KV 存储（scope=kv）"""

    __tablename__ = 'plugin_configs'

    __table_args__ = (
        Index('ix_plugin_configs_plugin_id', 'plugin_id'),
        Index('ix_plugin_configs_base_id', 'base_id'),
        Index('ix_plugin_configs_scope', 'scope'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    plugin_id: Mapped[str] = mapped_column(
        String(200),
        ForeignKey('plugins.id', ondelete='CASCADE'),
        nullable=False
    )
    scope: Mapped[PluginConfigScope] = mapped_column(
        Enum(PluginConfigScope, native_enum=False, length=20),
        nullable=False
    )
    base_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('bases.id', ondelete='CASCADE'),
        nullable=True
    )
    config_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    config: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id),
            'plugin_id': self.plugin_id,
            'scope': self.scope.value if isinstance(self.scope, PluginConfigScope) else self.scope,
            'base_id': str(self.base_id) if self.base_id else None,
            'config': self.config,
            'updated_by': str(self.updated_by) if self.updated_by else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PluginInstallation(db.Model):
    """插件在 Base 内的安装/启用关系"""

    __tablename__ = 'plugin_installations'

    __table_args__ = (
        Index('ix_plugin_installations_plugin_id', 'plugin_id'),
        Index('ix_plugin_installations_base_id', 'base_id'),
        Index('uq_plugin_installation', 'plugin_id', 'base_id', unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    plugin_id: Mapped[str] = mapped_column(
        String(200),
        ForeignKey('plugins.id', ondelete='CASCADE'),
        nullable=False
    )
    base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('bases.id', ondelete='CASCADE'),
        nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    installed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False
    )

    plugin: Mapped[Plugin] = relationship(back_populates='installations')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id),
            'plugin_id': self.plugin_id,
            'base_id': str(self.base_id),
            'enabled': self.enabled,
            'installed_by': str(self.installed_by) if self.installed_by else None,
            'installed_at': self.installed_at.isoformat() if self.installed_at else None,
        }


class PluginRunLog(db.Model):
    """脚本插件运行记录"""

    __tablename__ = 'plugin_run_logs'

    __table_args__ = (
        Index('ix_plugin_run_logs_plugin_id', 'plugin_id'),
        Index('ix_plugin_run_logs_base_id', 'base_id'),
        Index('ix_plugin_run_logs_created_at', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    plugin_id: Mapped[str] = mapped_column(
        String(200),
        ForeignKey('plugins.id', ondelete='CASCADE'),
        nullable=False
    )
    base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('bases.id', ondelete='CASCADE'),
        nullable=False
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False, length=20),
        nullable=False
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    triggered_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    traceback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id),
            'plugin_id': self.plugin_id,
            'base_id': str(self.base_id),
            'status': self.status.value if isinstance(self.status, RunStatus) else self.status,
            'duration_ms': self.duration_ms,
            'triggered_by': str(self.triggered_by) if self.triggered_by else None,
            'output': self.output,
            'result': self.result,
            'error_summary': self.error_summary,
            'traceback_text': self.traceback_text,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
