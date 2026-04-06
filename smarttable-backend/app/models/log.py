"""
操作日志模型模块
记录管理员用户管理系统中的所有操作日志
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Enum, Text, ForeignKey, Index
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class AdminActionType(PyEnum):
    """管理员操作类型枚举"""
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'
    SUSPEND = 'suspend'
    ACTIVATE = 'activate'
    RESET_PASSWORD = 'reset_password'
    CHANGE_ROLE = 'change_role'
    VERIFY_EMAIL = 'verify_email'
    LOGIN = 'login'
    LOGOUT = 'logout'
    EXPORT = 'export'
    IMPORT = 'import'
    CONFIG_CHANGE = 'config_change'


class EntityType(PyEnum):
    """实体类型枚举"""
    USER = 'user'
    BASE = 'base'
    TABLE = 'table'
    FIELD = 'field'
    RECORD = 'record'
    VIEW = 'view'
    DASHBOARD = 'dashboard'
    CONFIG = 'config'


class OperationLog(db.Model):
    """
    操作日志模型
    
    用于记录管理员用户管理系统中的所有关键操作，包括用户管理、配置变更等
    
    属性:
        id: UUID 主键
        user_id: 操作用户的 UUID 外键
        action: 操作类型 (CREATE, UPDATE, DELETE, SUSPEND, ACTIVATE, RESET_PASSWORD 等)
        entity_type: 实体类型 (user, base, table, field, record, view, dashboard, config)
        entity_id: 实体 UUID (可选)
        old_value: 旧值 (JSON 格式，可选)
        new_value: 新值 (JSON 格式，可选)
        ip_address: IP 地址 (最多 45 字符，支持 IPv6)
        user_agent: 用户代理 (可选)
        created_at: 创建时间
    """
    
    __tablename__ = 'operation_logs'
    
    __table_args__ = (
        Index('ix_op_log_user', 'user_id'),
        Index('ix_op_log_action', 'action'),
        Index('ix_op_log_entity', 'entity_type', 'entity_id'),
        Index('ix_op_log_time', 'created_at'),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )
    old_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    new_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=False
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    user = relationship(
        'User',
        lazy='joined',
        foreign_keys=[user_id]
    )
    
    def __init__(self, **kwargs):
        """初始化操作日志，自动处理枚举值"""
        action = kwargs.get('action')
        if isinstance(action, AdminActionType):
            kwargs['action'] = action.value
        entity_type = kwargs.get('entity_type')
        if isinstance(entity_type, EntityType):
            kwargs['entity_type'] = entity_type.value
        super(OperationLog, self).__init__(**kwargs)
    
    @staticmethod
    def log(user_id: uuid.UUID, action: AdminActionType, entity_type: EntityType,
            entity_id: Optional[uuid.UUID] = None, old_value: Optional[dict] = None,
            new_value: Optional[dict] = None, ip_address: str = '',
            user_agent: Optional[str] = None) -> 'OperationLog':
        """
        创建操作日志记录
        
        Args:
            user_id: 操作用户 ID
            action: 操作类型
            entity_type: 实体类型
            entity_id: 实体 ID (可选)
            old_value: 旧值字典 (可选)
            new_value: 新值字典 (可选)
            ip_address: IP 地址
            user_agent: 用户代理 (可选)
        
        Returns:
            OperationLog: 创建的操作日志对象
        """
        import json
        log = OperationLog(
            user_id=user_id,
            action=action.value if isinstance(action, AdminActionType) else action,
            entity_type=entity_type.value if isinstance(entity_type, EntityType) else entity_type,
            entity_id=entity_id,
            old_value=json.dumps(old_value, ensure_ascii=False) if old_value else None,
            new_value=json.dumps(new_value, ensure_ascii=False) if new_value else None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(log)
        return log
    
    @classmethod
    def get_user_logs(cls, user_id: uuid.UUID, limit: int = 100) -> list:
        """
        获取指定用户的操作日志
        
        Args:
            user_id: 用户 ID
            limit: 返回数量限制
        
        Returns:
            操作日志列表
        """
        return cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_entity_logs(cls, entity_type: EntityType, entity_id: uuid.UUID, limit: int = 100) -> list:
        """
        获取指定实体的操作日志
        
        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            limit: 返回数量限制
        
        Returns:
            操作日志列表
        """
        et = entity_type.value if isinstance(entity_type, EntityType) else entity_type
        return cls.query.filter_by(entity_type=et, entity_id=entity_id).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_action_logs(cls, action: AdminActionType, limit: int = 100) -> list:
        """
        获取指定操作类型的日志
        
        Args:
            action: 操作类型
            limit: 返回数量限制
        
        Returns:
            操作日志列表
        """
        act = action.value if isinstance(action, AdminActionType) else action
        return cls.query.filter_by(action=act).order_by(cls.created_at.desc()).limit(limit).all()
    
    def to_dict(self) -> dict:
        """
        将操作日志转换为字典
        
        Returns:
            包含操作日志信息的字典
        """
        import json
        return {
            'id': str(self.id),
            'user_id': str(self.user_id) if self.user_id else None,
            'user': {'name': self.user.name, 'avatar': self.user.avatar} if self.user else None,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': str(self.entity_id) if self.entity_id else None,
            'old_value': json.loads(self.old_value) if self.old_value else None,
            'new_value': json.loads(self.new_value) if self.new_value else None,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self) -> str:
        return f'<OperationLog {self.action} {self.entity_type}:{self.entity_id}>'
