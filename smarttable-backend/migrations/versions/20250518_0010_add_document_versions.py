"""
添加文档版本历史表

Revision ID: 20250518_0010
Revises: 20250518_0009
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa
from app.db_types import CompatUUID as UUID

revision = '20250518_0010'
down_revision = '20250518_0009'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'document_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('content_format', sa.String(20), default='delta', nullable=False),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('change_summary', sa.String(500), nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_document_versions_document_id', 'document_versions', ['document_id'])
    op.create_index('ix_document_versions_version_number', 'document_versions', ['document_id', 'version_number'])


def downgrade():
    op.drop_table('document_versions')
