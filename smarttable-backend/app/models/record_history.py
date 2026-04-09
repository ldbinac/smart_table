"""
记录变更历史模型模块
用于存储记录的创建、更新、删除操作历史
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from sqlalchemy import String, DateTime, ForeignKey, Text, JSON, Index
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class HistoryAction(str, Enum):
    """历史记录操作类型"""
    CREATE = "CREATE"      # 创建记录
    UPDATE = "UPDATE"      # 更新记录
    DELETE = "DELETE"      # 删除记录


class RecordHistory(db.Model):
    """
    记录变更历史模型

    属性:
        id: UUID 主键
        record_id: 关联记录 ID
        table_id: 所属表格 ID
        action: 操作类型（CREATE/UPDATE/DELETE）
        changed_by: 变更人 ID
        changed_at: 变更时间
        changes: 变更详情（JSON，包含字段名、旧值、新值）
        snapshot: 数据快照（JSON，记录变更时的完整数据）
    """

    __tablename__ = 'record_history'

    __table_args__ = (
        Index('ix_record_history_record_id', 'record_id'),
        Index('ix_record_history_table_id', 'table_id'),
        Index('ix_record_history_changed_at', 'changed_at'),
        Index('ix_record_history_record_changed', 'record_id', 'changed_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('records.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('tables.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    action: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    changes: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        comment='变更详情，包含字段名、旧值、新值的列表'
    )
    snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment='数据快照，记录变更时的完整数据'
    )

    # 关联关系
    record = relationship(
        'Record',
        lazy='joined'
    )

    changer = relationship(
        'User',
        lazy='joined'
    )

    def to_dict(self, include_changer: bool = True) -> dict:
        """
        转换为字典格式

        Args:
            include_changer: 是否包含变更人信息

        Returns:
            字典格式的历史记录数据
        """
        data = {
            'id': str(self.id),
            'record_id': str(self.record_id),
            'table_id': str(self.table_id),
            'action': self.action,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
            'changes': self.changes or [],
            'snapshot': self.snapshot or {}
        }

        if include_changer and self.changer:
            data['changed_by'] = {
                'id': str(self.changer.id),
                'name': self.changer.name,
                'avatar': self.changer.avatar
            }
        else:
            data['changed_by'] = {
                'id': str(self.changed_by) if self.changed_by else None,
                'name': '未知用户',
                'avatar': None
            }

        return data

    @staticmethod
    def create_history(
        record_id: uuid.UUID,
        table_id: uuid.UUID,
        action: HistoryAction,
        changed_by: Optional[uuid.UUID],
        changes: Optional[List[Dict[str, Any]]] = None,
        snapshot: Optional[Dict[str, Any]] = None
    ) -> 'RecordHistory':
        """
        创建历史记录

        Args:
            record_id: 记录 ID
            table_id: 表格 ID
            action: 操作类型
            changed_by: 变更人 ID
            changes: 变更详情
            snapshot: 数据快照

        Returns:
            创建的 RecordHistory 实例
        """
        return RecordHistory(
            record_id=record_id,
            table_id=table_id,
            action=action.value,
            changed_by=changed_by,
            changes=changes,
            snapshot=snapshot
        )

    def __repr__(self) -> str:
        return f'<RecordHistory {self.id} {self.action}>'
