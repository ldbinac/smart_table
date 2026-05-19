"""
添加文档表

Revision ID: 20250518_0009
Revises: 20250416_0008
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa
from app.db_types import CompatUUID as UUID

revision = '20250518_0009'
down_revision = '20250416_0008'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('base_id', UUID(as_uuid=True), sa.ForeignKey('bases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('content', sa.Text, default='', nullable=False),
        sa.Column('content_format', sa.String(20), default='delta', nullable=False),
        sa.Column('order', sa.Integer, default=0, nullable=False),
        sa.Column('is_pinned', sa.Boolean, default=False, nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_documents_base_id', 'documents', ['base_id'])
    op.create_index('ix_documents_base_order', 'documents', ['base_id', 'order'])


def downgrade():
    op.drop_table('documents')
