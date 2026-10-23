"""
记录评论与 @提及功能：新增 comment_mentions / record_followers 表，
并为 record_comments 增加软删除字段、users 增加通知偏好字段。

Revision ID: 20261021_0001
Revises: 20261016_0001
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# 与模型一致：UUID 列在 PostgreSQL 下编译为原生 UUID，在 SQLite 下为 String(36)
from app.db_types import CompatUUID as UUID


revision = '20261021_0001'
down_revision = '20261016_0001'
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    inspector = inspect(op.get_bind())
    return name in inspector.get_table_names()


def _column_exists(table: str, column: str) -> bool:
    inspector = inspect(op.get_bind())
    return column in [c['name'] for c in inspector.get_columns(table)]


def upgrade():
    # 1. comment_mentions 表
    if not _table_exists('comment_mentions'):
        op.create_table(
            'comment_mentions',
            sa.Column('id', UUID(), nullable=False),
            sa.Column('comment_id', UUID(), nullable=False),
            sa.Column('mentioned_user_id', UUID(), nullable=False),
            sa.Column('mention_type', sa.String(20), nullable=False, server_default='mention'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['comment_id'], ['record_comments.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['mentioned_user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('comment_id', 'mentioned_user_id', name='uq_comment_mentions_comment_user')
        )
        op.create_index('ix_comment_mentions_comment_id', 'comment_mentions', ['comment_id'])
        op.create_index('ix_comment_mentions_user_id', 'comment_mentions', ['mentioned_user_id'])

    # 2. record_followers 表
    if not _table_exists('record_followers'):
        op.create_table(
            'record_followers',
            sa.Column('id', UUID(), nullable=False),
            sa.Column('record_id', UUID(), nullable=False),
            sa.Column('user_id', UUID(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['record_id'], ['records.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('record_id', 'user_id', name='uq_record_followers_record_user')
        )
        op.create_index('ix_record_followers_record_id', 'record_followers', ['record_id'])
        op.create_index('ix_record_followers_user_id', 'record_followers', ['user_id'])

    # 3. record_comments 软删除字段
    if _table_exists('record_comments'):
        if not _column_exists('record_comments', 'is_deleted'):
            op.add_column('record_comments',
                          sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()))
            op.create_index('ix_record_comments_is_deleted', 'record_comments', ['is_deleted'])
        if not _column_exists('record_comments', 'deleted_at'):
            op.add_column('record_comments',
                          sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

    # 4. users 通知偏好字段
    if _table_exists('users'):
        if not _column_exists('users', 'notification_prefs'):
            op.add_column('users',
                          sa.Column('notification_prefs', sa.JSON(), nullable=True))


def downgrade():
    if _table_exists('record_followers'):
        op.drop_index('ix_record_followers_user_id', table_name='record_followers')
        op.drop_index('ix_record_followers_record_id', table_name='record_followers')
        op.drop_table('record_followers')

    if _table_exists('comment_mentions'):
        op.drop_index('ix_comment_mentions_user_id', table_name='comment_mentions')
        op.drop_index('ix_comment_mentions_comment_id', table_name='comment_mentions')
        op.drop_table('comment_mentions')

    if _table_exists('record_comments'):
        if _column_exists('record_comments', 'deleted_at'):
            op.drop_column('record_comments', 'deleted_at')
        if _column_exists('record_comments', 'is_deleted'):
            op.drop_index('ix_record_comments_is_deleted', table_name='record_comments')
            op.drop_column('record_comments', 'is_deleted')

    if _table_exists('users'):
        if _column_exists('users', 'notification_prefs'):
            op.drop_column('users', 'notification_prefs')
