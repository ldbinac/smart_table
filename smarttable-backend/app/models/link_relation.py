"""
链接关系模型模块
包含 LinkRelation（链接关系定义）和 LinkValue（链接值）模型
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, ForeignKey, Boolean, Index
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class RelationshipType(PyEnum):
    """关联类型枚举"""
    ONE_TO_ONE = 'one_to_one'
    ONE_TO_MANY = 'one_to_many'


class LinkRelation(db.Model):
    """
    链接关系模型
    定义两个表之间的链接关系

    属性:
        id: UUID 主键
        source_table_id: 源表 ID
        target_table_id: 目标表 ID
        source_field_id: 源字段 ID
        target_field_id: 目标字段 ID（可为空，用于双向关联）
        relationship_type: 关联类型（'one_to_one', 'one_to_many'）
        bidirectional: 是否为双向关联
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = 'link_relations'

    __table_args__ = (
        Index('ix_link_relation_source_table', 'source_table_id'),
        Index('ix_link_relation_target_table', 'target_table_id'),
        Index('ix_link_relation_source_field', 'source_field_id'),
        Index('ix_link_relation_target_field', 'target_field_id'),
        Index('ix_link_relation_tables', 'source_table_id', 'target_table_id'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    source_table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('tables.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    target_table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('tables.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    source_field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('fields.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    target_field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('fields.id', ondelete='CASCADE'),
        nullable=True,
        index=True
    )
    relationship_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=RelationshipType.ONE_TO_MANY.value
    )
    bidirectional: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
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

    source_table = relationship(
        'Table',
        foreign_keys=[source_table_id],
        lazy='joined'
    )

    target_table = relationship(
        'Table',
        foreign_keys=[target_table_id],
        lazy='joined'
    )

    source_field = relationship(
        'Field',
        foreign_keys=[source_field_id],
        lazy='joined'
    )

    target_field = relationship(
        'Field',
        foreign_keys=[target_field_id],
        lazy='joined'
    )

    link_values = relationship(
        'LinkValue',
        back_populates='link_relation',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def to_dict(self, include_related: bool = False) -> dict:
        data = {
            'id': str(self.id),
            'source_table_id': str(self.source_table_id),
            'target_table_id': str(self.target_table_id),
            'source_field_id': str(self.source_field_id),
            'target_field_id': str(self.target_field_id) if self.target_field_id else None,
            'relationship_type': self.relationship_type,
            'bidirectional': self.bidirectional,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

        if include_related:
            if self.source_table:
                data['source_table'] = self.source_table.to_dict()
            if self.target_table:
                data['target_table'] = self.target_table.to_dict()
            if self.source_field:
                data['source_field'] = self.source_field.to_dict()
            if self.target_field:
                data['target_field'] = self.target_field.to_dict()

        return data

    def __repr__(self) -> str:
        return f'<LinkRelation {self.id} ({self.relationship_type})>'


class LinkValue(db.Model):
    """
    链接值模型
    存储记录之间的链接关系值

    属性:
        id: UUID 主键
        link_relation_id: 链接关系 ID
        source_record_id: 源记录 ID
        target_record_id: 目标记录 ID
        created_at: 创建时间
    """

    __tablename__ = 'link_values'

    __table_args__ = (
        Index('ix_link_value_relation', 'link_relation_id'),
        Index('ix_link_value_source_record', 'source_record_id'),
        Index('ix_link_value_target_record', 'target_record_id'),
        Index('ix_link_value_source_target', 'source_record_id', 'target_record_id'),
        Index('ix_link_value_relation_source', 'link_relation_id', 'source_record_id'),
        Index('ix_link_value_relation_target', 'link_relation_id', 'target_record_id'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    link_relation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('link_relations.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('records.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    target_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('records.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    link_relation = relationship(
        'LinkRelation',
        back_populates='link_values',
        lazy='joined'
    )

    source_record = relationship(
        'Record',
        foreign_keys=[source_record_id],
        lazy='joined'
    )

    target_record = relationship(
        'Record',
        foreign_keys=[target_record_id],
        lazy='joined'
    )

    def to_dict(self, include_records: bool = False) -> dict:
        data = {
            'id': str(self.id),
            'link_relation_id': str(self.link_relation_id),
            'source_record_id': str(self.source_record_id),
            'target_record_id': str(self.target_record_id),
            'created_at': self.created_at.isoformat()
        }

        if include_records:
            if self.source_record:
                data['source_record'] = self.source_record.to_dict()
            if self.target_record:
                data['target_record'] = self.target_record.to_dict()

        return data

    def __repr__(self) -> str:
        return f'<LinkValue {self.id} ({self.source_record_id} -> {self.target_record_id})>'
