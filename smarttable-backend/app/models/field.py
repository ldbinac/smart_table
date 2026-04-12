"""
字段模型模块
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional, Dict, Any

from sqlalchemy import String, DateTime, ForeignKey, Integer, Boolean, Text, JSON
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class FieldType(PyEnum):
    """字段类型枚举"""
    SINGLE_LINE_TEXT = 'single_line_text'
    LONG_TEXT = 'long_text'
    RICH_TEXT = 'rich_text'
    NUMBER = 'number'
    CURRENCY = 'currency'
    PERCENT = 'percent'
    RATING = 'rating'
    DATE = 'date'
    DATE_TIME = 'date_time'
    DURATION = 'duration'
    SINGLE_SELECT = 'single_select'
    MULTI_SELECT = 'multi_select'
    CHECKBOX = 'checkbox'
    LINK_TO_RECORD = 'link_to_record'
    LINK = 'link'  # 前端使用的关联字段类型别名
    LOOKUP = 'lookup'
    ROLLUP = 'rollup'
    CREATED_BY = 'created_by'
    LAST_MODIFIED_BY = 'last_modified_by'
    COLLABORATOR = 'collaborator'
    ATTACHMENT = 'attachment'
    FORMULA = 'formula'
    AUTO_NUMBER = 'auto_number'
    BARCODE = 'barcode'
    EMAIL = 'email'
    PHONE = 'phone'
    URL = 'url'
    BUTTON = 'button'


class Field(db.Model):
    """
    字段模型

    属性:
        id: UUID 主键
        table_id: 所属表格 ID
        name: 字段名称
        type: 字段类型
        description: 描述
        order: 排序顺序
        is_primary: 是否为主字段
        is_required: 是否必填
        options: 字段选项（JSON）
        config: 字段配置（JSON）
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = 'fields'

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
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    type: Mapped[FieldType] = mapped_column(
        String(50),
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    options: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
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

    table = relationship(
        'Table',
        back_populates='fields',
        lazy='joined',
        foreign_keys=[table_id]
    )

    def get_default_value(self) -> Any:
        """
        获取字段的默认值
        
        优先从 config 中读取用户配置的默认值，如果没有配置则返回类型相关的默认值
        注意：动态默认值 'now' 会原样返回，由 record_service 在创建记录时动态计算
        """
        # 优先使用 config 中配置的默认值
        if self.config and isinstance(self.config, dict) and 'defaultValue' in self.config:
            default_value = self.config['defaultValue']
            
            # 动态默认值 'now' 原样返回，由 record_service 处理
            # 这样可以确保每次创建记录时都使用当时的日期
            if default_value == 'now':
                return 'now'  # 返回标记，由 record_service 动态计算
            
            return default_value
        
        # 否则返回类型相关的默认值
        field_type = FieldType(self.type)
        defaults = {
            FieldType.SINGLE_LINE_TEXT: '',
            FieldType.LONG_TEXT: '',
            FieldType.RICH_TEXT: '',
            FieldType.NUMBER: 0,
            FieldType.CURRENCY: 0,
            FieldType.PERCENT: 0,
            FieldType.RATING: 0,
            FieldType.DATE: None,
            FieldType.DATE_TIME: None,
            FieldType.DURATION: 0,
            FieldType.SINGLE_SELECT: None,
            FieldType.MULTI_SELECT: [],
            FieldType.CHECKBOX: False,
            FieldType.LINK_TO_RECORD: [],
            FieldType.LINK: [],
            FieldType.LOOKUP: [],
            FieldType.ROLLUP: None,
            FieldType.CREATED_BY: None,
            FieldType.LAST_MODIFIED_BY: None,
            FieldType.COLLABORATOR: [],
            FieldType.ATTACHMENT: [],
            FieldType.FORMULA: None,
            FieldType.AUTO_NUMBER: None,
            FieldType.BARCODE: None,
            FieldType.EMAIL: '',
            FieldType.PHONE: '',
            FieldType.URL: '',
            FieldType.BUTTON: None
        }
        return defaults.get(field_type)
    
    def validate_default_value(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        验证默认值是否符合字段类型
        
        Args:
            value: 待验证的默认值
            
        Returns:
            (是否有效，错误信息)
        """
        # None 值总是有效的（表示没有默认值）
        if value is None:
            return True, None
        
        field_type = FieldType(self.type)
        
        # 特殊处理动态默认值
        if value == 'now':
            if field_type in [FieldType.DATE, FieldType.DATE_TIME]:
                return True, None
            else:
                return False, f'字段 "{self.name}" 的类型不支持动态默认值'
        
        # 根据字段类型验证默认值
        if field_type in [FieldType.SINGLE_LINE_TEXT, FieldType.LONG_TEXT, FieldType.RICH_TEXT,
                         FieldType.EMAIL, FieldType.PHONE, FieldType.URL]:
            if not isinstance(value, str):
                return False, f'字段 "{self.name}" 的默认值必须是字符串'
        
        elif field_type in [FieldType.NUMBER, FieldType.CURRENCY, FieldType.PERCENT, 
                           FieldType.RATING, FieldType.DURATION]:
            if not isinstance(value, (int, float)):
                return False, f'字段 "{self.name}" 的默认值必须是数字'
        
        elif field_type in [FieldType.DATE, FieldType.DATE_TIME]:
            if not isinstance(value, str):
                return False, f'字段 "{self.name}" 的默认值必须是日期字符串'
            # 验证日期格式
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return False, f'字段 "{self.name}" 的默认值必须是有效的日期格式'
        
        elif field_type == FieldType.CHECKBOX:
            if not isinstance(value, bool):
                return False, f'字段 "{self.name}" 的默认值必须是布尔值'
        
        elif field_type == FieldType.SINGLE_SELECT:
            # 单选默认值应该是选项 ID（字符串）
            if not isinstance(value, str):
                return False, f'字段 "{self.name}" 的默认值必须是选项 ID'
            # 验证选项是否存在
            if self.options and isinstance(self.options, dict):
                choices = self.options.get('choices', [])
                if not any(choice.get('id') == value for choice in choices):
                    return False, f'字段 "{self.name}" 的默认值对应的选项不存在'
        
        elif field_type == FieldType.MULTI_SELECT:
            # 多选默认值应该是选项 ID 数组
            if not isinstance(value, list):
                return False, f'字段 "{self.name}" 的默认值必须是选项 ID 数组'
            # 验证所有选项是否存在
            if self.options and isinstance(self.options, dict):
                choices = self.options.get('choices', [])
                for option_id in value:
                    if not any(choice.get('id') == option_id for choice in choices):
                        return False, f'字段 "{self.name}" 的默认值包含不存在的选项'
        
        elif field_type in [FieldType.LINK_TO_RECORD, FieldType.LINK, FieldType.COLLABORATOR, FieldType.ATTACHMENT]:
            # 这些类型默认值应该是数组
            if not isinstance(value, list):
                return False, f'字段 "{self.name}" 的默认值必须是数组'

        return True, None

    def validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        if self.is_required and value is None:
            return False, f'字段 "{self.name}" 为必填项'

        field_type = FieldType(self.type)

        if field_type == FieldType.NUMBER and value is not None:
            if not isinstance(value, (int, float)):
                return False, f'字段 "{self.name}" 必须是数字'
        elif field_type == FieldType.EMAIL and value:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, str(value)):
                return False, f'字段 "{self.name}" 必须是有效的邮箱地址'
        elif field_type == FieldType.URL and value:
            url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
            if not re.match(url_pattern, str(value)):
                return False, f'字段 "{self.name}" 必须是有效的 URL'

        return True, None

    def to_dict(self) -> dict:
        result = {
            'id': str(self.id),
            'table_id': str(self.table_id),
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'order': self.order,
            'is_primary': self.is_primary,
            'is_required': self.is_required,
            'options': self.options or {},
            'config': self.config or {},
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        # 将 config 中的 defaultValue 提取到顶层，方便前端使用
        if self.config and isinstance(self.config, dict) and 'defaultValue' in self.config:
            result['defaultValue'] = self.config['defaultValue']
        
        return result

    def __repr__(self) -> str:
        return f'<Field {self.name} ({self.type})>'
