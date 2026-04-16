"""
添加协作会话表

Revision ID: 20250416_0008
Revises: 20250414_0007
Create Date: 2026-04-16
"""
from alembic import op
import sqlalchemy as sa

revision = '20250416_0008'
down_revision = '20250414_0007'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('collaboration_sessions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('base_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('socket_id', sa.String(64), nullable=False),
        sa.Column('current_table_id', sa.String(36), nullable=True),
        sa.Column('current_view_id', sa.String(36), nullable=True),
        sa.Column('current_view_type', sa.String(20), nullable=True),
        sa.Column('locked_cells', sa.Text(), nullable=True),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.Column('last_active_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.ForeignKeyConstraint(['base_id'], ['bases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_collab_sessions_base_id', 'collaboration_sessions', ['base_id'])
    op.create_index('ix_collab_sessions_user_id', 'collaboration_sessions', ['user_id'])
    op.create_index('ix_collab_sessions_socket_id', 'collaboration_sessions', ['socket_id'])
    op.create_index('ix_collab_sessions_is_active', 'collaboration_sessions', ['is_active'])


def downgrade():
    op.drop_index('ix_collab_sessions_is_active', table_name='collaboration_sessions')
    op.drop_index('ix_collab_sessions_socket_id', table_name='collaboration_sessions')
    op.drop_index('ix_collab_sessions_user_id', table_name='collaboration_sessions')
    op.drop_index('ix_collab_sessions_base_id', table_name='collaboration_sessions')

    op.drop_table('collaboration_sessions')
