"""
字段模型模块
"""
import uuid
from datetime import datetime
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
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    table = relationship(
        'Table',
        back_populates='fields',
        lazy='joined',
        foreign_keys=[table_id]
    )

    def get_default_value(self) -> Any:
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

    def validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        if self.is_required and value is None:
            return False, f'字段 "{self.name}" 为必填项'

        field_type = FieldType(self.type)

        if field_type == FieldType.NUMBER and value is not None:
            if not isinstance(value, (int, float)):
                return False, f'字段 "{self.name}" 必须是数字'
        elif field_type == FieldType.EMAIL and value:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, str(value)):
                return False, f'字段 "{self.name}" 必须是有效的邮箱地址'
        elif field_type == FieldType.URL and value:
            import re
            url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
            if not re.match(url_pattern, str(value)):
                return False, f'字段 "{self.name}" 必须是有效的 URL'

        return True, None

    def to_dict(self) -> dict:
        return {
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

    def __repr__(self) -> str:
        return f'<Field {self.name} ({self.type})>'
