"""
表单分享模型
用于存储表格的表单分享配置，支持匿名用户提交数据
"""
import uuid
import secrets
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class FormShare(db.Model):
    """
    表单分享配置表
    
    属性:
        id: UUID 主键
        table_id: 关联的表格 ID
        share_token: 分享令牌（用于生成分享链接）
        created_by: 创建者用户 ID
        is_active: 是否激活
        allow_anonymous: 是否允许匿名提交
        require_captcha: 是否需要验证码
        expires_at: 过期时间（可选，Unix 时间戳）
        max_submissions: 最大提交次数（可选）
        current_submissions: 当前提交次数
        allowed_fields: 允许提交的字段列表（JSON）
        title: 表单标题（可选）
        description: 表单描述（可选）
        submit_button_text: 提交按钮文字（可选）
        success_message: 提交成功后的提示信息（可选）
        theme: 表单主题样式（可选）
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    __tablename__ = 'form_shares'
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    # 关联的表格 ID
    table_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey('tables.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # 分享令牌（用于生成分享链接）
    share_token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: secrets.token_urlsafe(32)
    )
    
    # 创建者 ID
    created_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    
    # 是否激活
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    
    # 是否允许匿名提交
    allow_anonymous: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    
    # 是否需要验证码
    require_captcha: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    # 过期时间（可选，Unix 时间戳）
    expires_at: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    # 最大提交次数（可选）
    max_submissions: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    # 当前提交次数
    current_submissions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    # 允许提交的字段列表（JSON）
    allowed_fields: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment='JSON格式的字段ID列表，为空表示允许所有字段'
    )
    
    # 表单标题
    title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True
    )
    
    # 表单描述
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # 提交按钮文字
    submit_button_text: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default='提交'
    )
    
    # 提交成功后的提示信息
    success_message: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        default='提交成功，感谢您的参与！'
    )
    
    # 表单主题样式
    theme: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default='default'
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
    
    # 关联关系
    table = relationship('Table', back_populates='form_shares')
    creator = relationship('User', foreign_keys=[created_by])
    submissions = relationship('FormSubmission', back_populates='form_share', cascade='all, delete-orphan')
    
    def get_allowed_fields_list(self) -> List[str]:
        """获取允许的字段列表"""
        if not self.allowed_fields:
            return []
        import json
        try:
            return json.loads(self.allowed_fields)
        except json.JSONDecodeError:
            return []
    
    def set_allowed_fields_list(self, fields: List[str]) -> None:
        """设置允许的字段列表"""
        import json
        self.allowed_fields = json.dumps(fields)
    
    def is_expired(self) -> bool:
        """检查是否已过期"""
        if self.expires_at is None:
            return False
        return int(datetime.now(timezone.utc).timestamp()) > self.expires_at
    
    def is_reached_limit(self) -> bool:
        """检查是否已达到提交次数限制"""
        if self.max_submissions is None:
            return False
        return self.current_submissions >= self.max_submissions
    
    def can_submit(self) -> bool:
        """检查是否可以提交"""
        return (
            self.is_active and
            not self.is_expired() and
            not self.is_reached_limit()
        )
    
    def increment_submissions(self) -> None:
        """增加提交次数"""
        self.current_submissions += 1
    
    def to_dict(self, include_stats: bool = False) -> dict:
        """转换为字典"""
        data = {
            'id': str(self.id),
            'table_id': str(self.table_id),
            'share_token': self.share_token,
            'is_active': self.is_active,
            'allow_anonymous': self.allow_anonymous,
            'require_captcha': self.require_captcha,
            'expires_at': self.expires_at,
            'max_submissions': self.max_submissions,
            'current_submissions': self.current_submissions,
            'allowed_fields': self.get_allowed_fields_list(),
            'title': self.title,
            'description': self.description,
            'submit_button_text': self.submit_button_text,
            'success_message': self.success_message,
            'theme': self.theme,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': str(self.created_by)
        }
        
        if include_stats:
            data['is_expired'] = self.is_expired()
            data['is_reached_limit'] = self.is_reached_limit()
            data['can_submit'] = self.can_submit()
        
        return data
    
    def __repr__(self) -> str:
        return f'<FormShare {self.share_token}>'
