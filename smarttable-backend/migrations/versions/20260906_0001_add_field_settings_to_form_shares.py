"""
为 form_shares 表添加 field_settings 字段（字段级默认值与只读配置）

Revision ID: 20260906_0001
Revises: 20260818_0002
Create Date: 2026-09-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '20260906_0001'
down_revision = '20260818_0002'
branch_labels = None
depends_on = None


def upgrade():
    # 幂等：列已存在（历史 create_all 已建表）则跳过，避免 duplicate column
    inspector = inspect(op.get_bind())
    existing_cols = {c['name'] for c in inspector.get_columns('form_shares')}
    if 'field_settings' in existing_cols:
        return

    # 注意：不能使用 recreate='always' 强制重建表（同 20260818_0002）：
    # PostgreSQL 上重建需删除 form_shares_pkey，会被
    # form_submissions_form_share_id_fkey 依赖而报 DependentObjectsStillExist。
    # 默认 recreate='auto' 时 PostgreSQL 原地执行，SQLite 必要时才重建表。
    with op.batch_alter_table('form_shares') as batch_op:
        batch_op.add_column(
            sa.Column('field_settings', sa.Text(), nullable=True)
        )


def downgrade():
    # 幂等：列不存在则跳过
    inspector = inspect(op.get_bind())
    existing_cols = {c['name'] for c in inspector.get_columns('form_shares')}
    if 'field_settings' not in existing_cols:
        return

    # recreate='auto'：PostgreSQL 原地 DROP COLUMN，SQLite 必要时重建表
    with op.batch_alter_table('form_shares') as batch_op:
        batch_op.drop_column('field_settings')
