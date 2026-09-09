"""
为 views 表添加 parent_field_id 字段

Revision ID: 20260803_0023
Revises: 20260801_0022
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '20260803_0023'
down_revision = '20260801_0022'
branch_labels = None
depends_on = None


def upgrade():
    # 幂等：列已存在（历史 create_all 已建表）则跳过，避免 duplicate column
    inspector = inspect(op.get_bind())
    existing_cols = {c['name'] for c in inspector.get_columns('views')}
    if 'parent_field_id' in existing_cols:
        return

    # 注意：不能使用 recreate='always' 强制重建表（同 20260818_0002）：
    # PostgreSQL 上重建表需删除原表主键约束，会被依赖该主键的外键
    # 阻塞而报 DependentObjectsStillExist。默认 recreate='auto' 时
    # PostgreSQL 全部原地执行（ADD COLUMN / ADD CONSTRAINT / CREATE INDEX），
    # SQLite 仅在需要（如添加外键）时才重建表。
    with op.batch_alter_table('views') as batch_op:
        batch_op.add_column(sa.Column('parent_field_id', sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            'fk_views_parent_field_id_fields',
            'fields',
            ['parent_field_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_index('ix_views_parent_field_id', ['parent_field_id'])


def downgrade():
    # 幂等：列不存在则跳过
    inspector = inspect(op.get_bind())
    existing_cols = {c['name'] for c in inspector.get_columns('views')}
    if 'parent_field_id' not in existing_cols:
        return

    # recreate='auto'：PostgreSQL 原地执行，SQLite 必要时重建表
    with op.batch_alter_table('views') as batch_op:
        batch_op.drop_index('ix_views_parent_field_id')
        batch_op.drop_constraint('fk_views_parent_field_id_fields', type_='foreignkey')
        batch_op.drop_column('parent_field_id')