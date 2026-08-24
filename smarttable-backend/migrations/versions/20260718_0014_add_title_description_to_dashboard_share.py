"""add title and description to dashboard_share

Revision ID: 20260718_0014
Revises: 20250705_0013
Create Date: 2026-07-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20260718_0014'
down_revision = '20250705_0013'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated ###
    # 幂等：列已存在则跳过，避免 duplicate column（历史 create_all 已建表场景）
    inspector = inspect(op.get_bind())
    existing_cols = {c['name'] for c in inspector.get_columns('dashboard_shares')}
    if 'title' in existing_cols and 'description' in existing_cols:
        return

    with op.batch_alter_table('dashboard_shares', schema=None) as batch_op:
        if 'title' not in existing_cols:
            batch_op.add_column(sa.Column('title', sa.String(length=200), nullable=True))
        if 'description' not in existing_cols:
            batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))


def downgrade():
    # ### commands auto generated ###
    # 幂等：列不存在则跳过
    inspector = inspect(op.get_bind())
    existing_cols = {c['name'] for c in inspector.get_columns('dashboard_shares')}

    with op.batch_alter_table('dashboard_shares', schema=None) as batch_op:
        if 'description' in existing_cols:
            batch_op.drop_column('description')
        if 'title' in existing_cols:
            batch_op.drop_column('title')
