"""
数据表文件夹模型模块
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, ForeignKey
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class TableFolder(db.Model):
    """
    数据表文件夹模型（Base 内单层分组，不嵌套）

    属性:
        id: UUID 主键
        base_id: 所属基础数据 ID
        name: 文件夹名称
        order: 排序顺序
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = 'table_folders'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('bases.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'base_id': str(self.base_id),
            'name': self.name,
            'order': self.order,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<TableFolder {self.name}>'
