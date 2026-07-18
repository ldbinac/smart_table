"""add title and description to dashboard_share

Revision ID: 20260718_0014
Revises: 20250705_0013
Create Date: 2026-07-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260718_0014'
down_revision = '20250705_0013'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated ###
    with op.batch_alter_table('dashboard_shares', schema=None) as batch_op:
        batch_op.add_column(sa.Column('title', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))


def downgrade():
    # ### commands auto generated ###
    with op.batch_alter_table('dashboard_shares', schema=None) as batch_op:
        batch_op.drop_column('description')
        batch_op.drop_column('title')
