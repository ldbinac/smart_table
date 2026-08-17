"""创建 workflow_record_time_triggers 表

Revision ID: 20260718_0016
Revises: 20260718_0015
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa
from app.db_types import CompatUUID as UUID

revision = '20260718_0016'
down_revision = '20260718_0015'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'workflow_record_time_triggers',
        sa.Column('id', UUID(), primary_key=True),
        sa.Column('workflow_id', UUID(), sa.ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('record_id', UUID(), sa.ForeignKey('records.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('field_id', UUID(), nullable=False),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('workflow_id', 'record_id', 'field_id', name='uq_wf_rec_time_trigger'),
    )


def downgrade():
    op.drop_table('workflow_record_time_triggers')
