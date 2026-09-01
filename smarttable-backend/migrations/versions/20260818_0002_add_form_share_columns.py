"""
为 form_shares 表添加 columns 字段（表单每行显示字段数，1-4）

Revision ID: 20260818_0002
Revises: 20260818_0001
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '20260818_0002'
down_revision = '20260818_0001'
branch_labels = None
depends_on = None


def upgrade():
    # 幂等：列已存在（历史 create_all 已建表）则跳过，避免 duplicate column
    inspector = inspect(op.get_bind())
    existing_cols = {c['name'] for c in inspector.get_columns('form_shares')}
    if 'columns' in existing_cols:
        return

    with op.batch_alter_table('form_shares', recreate='always') as batch_op:
        batch_op.add_column(
            sa.Column('columns', sa.Integer(), nullable=False, server_default=sa.text('1'))
        )


def downgrade():
    # 幂等：列不存在则跳过
    inspector = inspect(op.get_bind())
    existing_cols = {c['name'] for c in inspector.get_columns('form_shares')}
    if 'columns' not in existing_cols:
        return

    with op.batch_alter_table('form_shares', recreate='always') as batch_op:
        batch_op.drop_column('columns')
