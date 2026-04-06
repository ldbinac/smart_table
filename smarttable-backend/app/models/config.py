"""
系统配置模型模块
管理系统的各种配置项
"""
import uuid
from datetime import datetime
from typing import Optional, Any, Dict

from sqlalchemy import String, DateTime, Text, Index
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class SystemConfig(db.Model):
    """
    系统配置模型
    
    用于存储和管理系统的各种配置项，支持分组管理
    
    属性:
        id: UUID 主键
        config_key: 配置键 (唯一，索引)
        config_value: 配置值 (JSON 格式)
        config_group: 配置分组 (basic, security, email 等)
        description: 配置描述 (可选)
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    __tablename__ = 'system_configs'
    
    __table_args__ = (
        Index('ix_config_group', 'config_group'),
        Index('ix_config_key_group', 'config_key', 'config_group', unique=True),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    config_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True
    )
    config_value: Mapped[Any] = mapped_column(
        db.JSON,
        nullable=False,
        default=dict
    )
    config_group: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        default='basic'
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
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
    
    @staticmethod
    def get_config(key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
        
        Returns:
            配置值，如果不存在则返回默认值
        """
        config = SystemConfig.query.filter_by(config_key=key).first()
        if config:
            return config.config_value
        return default
    
    @staticmethod
    def set_config(key: str, value: Any, group: str = 'basic', description: Optional[str] = None) -> 'SystemConfig':
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            group: 配置分组
            description: 配置描述
        
        Returns:
            配置对象
        """
        config = SystemConfig.query.filter_by(config_key=key).first()
        if config:
            config.config_value = value
            if group:
                config.config_group = group
            if description:
                config.description = description
        else:
            config = SystemConfig(
                config_key=key,
                config_value=value,
                config_group=group,
                description=description
            )
            db.session.add(config)
        return config
    
    @staticmethod
    def get_group_configs(group: str) -> Dict[str, Any]:
        """
        获取指定分组的所有配置
        
        Args:
            group: 配置分组名称
        
        Returns:
            配置键值对字典
        """
        configs = SystemConfig.query.filter_by(config_group=group).all()
        return {config.config_key: config.config_value for config in configs}
    
    @staticmethod
    def delete_config(key: str) -> bool:
        """
        删除配置
        
        Args:
            key: 配置键
        
        Returns:
            是否删除成功
        """
        config = SystemConfig.query.filter_by(config_key=key).first()
        if config:
            db.session.delete(config)
            return True
        return False
    
    def to_dict(self) -> dict:
        """
        将配置转换为字典
        
        Returns:
            包含配置信息的字典
        """
        return {
            'id': str(self.id),
            'config_key': self.config_key,
            'config_value': self.config_value,
            'config_group': self.config_group,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self) -> str:
        return f'<SystemConfig {self.config_key}={self.config_value}>'
