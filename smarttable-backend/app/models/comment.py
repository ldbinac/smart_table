"""
评论相关模型模块
定义 @提及关联表与记录关注者表，配合已有的 RecordComment 模型实现
「记录评论与 @提及」功能。
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime, Boolean, ForeignKey, UniqueConstraint, Index
from app.db_types import CompatUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class CommentMention(db.Model):
    """
    @提及关联模型

    将评论正文中被 @ 提及的成员结构化存储，用于触发通知与前端高亮。
    评论正文本身保留 @名称 字面量，便于还原与编辑。

    属性:
        id: UUID 主键
        comment_id: 所属评论 ID
        mentioned_user_id: 被提及用户 ID
        mention_type: 提及类型（mention=显式 @，reply_parent=回复指向）
        created_at: 创建时间
    """

    __tablename__ = 'comment_mentions'

    __table_args__ = (
        UniqueConstraint('comment_id', 'mentioned_user_id', name='uq_comment_mentions_comment_user'),
        Index('ix_comment_mentions_comment_id', 'comment_id'),
        Index('ix_comment_mentions_user_id', 'mentioned_user_id'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('record_comments.id', ondelete='CASCADE'),
        nullable=False
    )
    mentioned_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    mention_type: Mapped[str] = mapped_column(
        String(20),
        default='mention',
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    comment = relationship(
        'RecordComment',
        foreign_keys=[comment_id],
        back_populates='mentions'
    )
    mentioned_user = relationship(
        'User',
        foreign_keys=[mentioned_user_id]
    )

    def to_dict(self) -> dict:
        return {
            'user_id': str(self.mentioned_user_id),
            'type': self.mention_type
        }

    def __repr__(self) -> str:
        return f'<CommentMention {self.comment_id}:{self.mentioned_user_id}>'


class RecordFollower(db.Model):
    """
    记录关注者模型

    用户对某条记录主动关注后，该记录新增顶层评论时其收到通知。

    属性:
        id: UUID 主键
        record_id: 关注记录 ID
        user_id: 关注用户 ID
        created_at: 创建时间
    """

    __tablename__ = 'record_followers'

    __table_args__ = (
        UniqueConstraint('record_id', 'user_id', name='uq_record_followers_record_user'),
        Index('ix_record_followers_record_id', 'record_id'),
        Index('ix_record_followers_user_id', 'user_id'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('records.id', ondelete='CASCADE'),
        nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    record = relationship(
        'Record',
        foreign_keys=[record_id]
    )
    user = relationship(
        'User',
        foreign_keys=[user_id]
    )

    def to_dict(self) -> dict:
        return {
            'record_id': str(self.record_id),
            'user_id': str(self.user_id)
        }

    def __repr__(self) -> str:
        return f'<RecordFollower {self.record_id}:{self.user_id}>'
