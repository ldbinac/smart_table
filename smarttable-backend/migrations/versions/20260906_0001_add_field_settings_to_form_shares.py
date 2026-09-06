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

    with op.batch_alter_table('form_shares', recreate='always') as batch_op:
        batch_op.add_column(
            sa.Column('field_settings', sa.Text(), nullable=True)
        )


def downgrade():
    # 幂等：列不存在则跳过
    inspector = inspect(op.get_bind())
    existing_cols = {c['name'] for c in inspector.get_columns('form_shares')}
    if 'field_settings' not in existing_cols:
        return

    with op.batch_alter_table('form_shares', recreate='always') as batch_op:
        batch_op.drop_column('field_settings')
