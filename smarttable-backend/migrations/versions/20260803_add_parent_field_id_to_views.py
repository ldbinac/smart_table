"""
为 views 表添加 parent_field_id 字段

Revision ID: 20260803_0023
Revises: 20260801_0022
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa


revision = '20260803_0023'
down_revision = '20260801_0022'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('views', recreate='always') as batch_op:
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
    with op.batch_alter_table('views', recreate='always') as batch_op:
        batch_op.drop_index('ix_views_parent_field_id')
        batch_op.drop_constraint('fk_views_parent_field_id_fields', type_='foreignkey')
        batch_op.drop_column('parent_field_id')