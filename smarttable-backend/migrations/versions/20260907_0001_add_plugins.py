"""
新增插件体系相关表

包含：plugins / plugin_versions / plugin_configs / plugin_installations / plugin_run_logs

Revision ID: 20260907_0001
Revises: 20260906_0001
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

from app.db_types import CompatUUID as UUID, CompatJSON as JSON


# revision identifiers, used by Alembic.
revision = '20260907_0001'
down_revision = '20260906_0001'
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    inspector = inspect(op.get_bind())
    return name in inspector.get_table_names()


def upgrade():
    if not _table_exists('plugins'):
        op.create_table(
            'plugins',
            sa.Column('id', sa.String(200), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('icon', sa.String(500), nullable=True),
            sa.Column('type', sa.String(20), nullable=False),
            sa.Column('status', sa.String(20), nullable=False),
            sa.Column('current_version', sa.String(50), nullable=False),
            sa.Column('manifest', JSON(), nullable=False),
            sa.Column('engines_text', sa.String(200), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_plugins_type', 'plugins', ['type'])
        op.create_index('ix_plugins_status', 'plugins', ['status'])

    if not _table_exists('plugin_versions'):
        op.create_table(
            'plugin_versions',
            sa.Column('id', UUID(), nullable=False),
            sa.Column('plugin_id', sa.String(200), nullable=False),
            sa.Column('version', sa.String(50), nullable=False),
            sa.Column('package_path', sa.String(500), nullable=False),
            sa.Column('checksum', sa.String(64), nullable=False),
            sa.Column('installed_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['plugin_id'], ['plugins.id'], ondelete='CASCADE')
        )
        op.create_index('ix_plugin_versions_plugin_id', 'plugin_versions', ['plugin_id'])

    if not _table_exists('plugin_configs'):
        op.create_table(
            'plugin_configs',
            sa.Column('id', UUID(), nullable=False),
            sa.Column('plugin_id', sa.String(200), nullable=False),
            sa.Column('scope', sa.String(20), nullable=False),
            sa.Column('base_id', UUID(), nullable=True),
            sa.Column('config_key', sa.String(128), nullable=True),
            sa.Column('config', JSON(), nullable=False),
            sa.Column('updated_by', UUID(), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['plugin_id'], ['plugins.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['base_id'], ['bases.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL')
        )
        op.create_index('ix_plugin_configs_plugin_id', 'plugin_configs', ['plugin_id'])
        op.create_index('ix_plugin_configs_base_id', 'plugin_configs', ['base_id'])
        op.create_index('ix_plugin_configs_scope', 'plugin_configs', ['scope'])

    if not _table_exists('plugin_installations'):
        op.create_table(
            'plugin_installations',
            sa.Column('id', UUID(), nullable=False),
            sa.Column('plugin_id', sa.String(200), nullable=False),
            sa.Column('base_id', UUID(), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False, default=True),
            sa.Column('installed_by', UUID(), nullable=True),
            sa.Column('installed_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['plugin_id'], ['plugins.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['base_id'], ['bases.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['installed_by'], ['users.id'], ondelete='SET NULL')
        )
        op.create_index('ix_plugin_installations_plugin_id',
                        'plugin_installations', ['plugin_id'])
        op.create_index('ix_plugin_installations_base_id',
                        'plugin_installations', ['base_id'])
        op.create_index('uq_plugin_installation', 'plugin_installations',
                        ['plugin_id', 'base_id'], unique=True)

    if not _table_exists('plugin_run_logs'):
        op.create_table(
            'plugin_run_logs',
            sa.Column('id', UUID(), nullable=False),
            sa.Column('plugin_id', sa.String(200), nullable=False),
            sa.Column('base_id', UUID(), nullable=False),
            sa.Column('status', sa.String(20), nullable=False),
            sa.Column('duration_ms', sa.Integer(), nullable=True),
            sa.Column('triggered_by', UUID(), nullable=True),
            sa.Column('output', sa.Text(), nullable=True),
            sa.Column('result', JSON(), nullable=True),
            sa.Column('error_summary', sa.String(500), nullable=True),
            sa.Column('traceback_text', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['plugin_id'], ['plugins.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['base_id'], ['bases.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], ondelete='SET NULL')
        )
        op.create_index('ix_plugin_run_logs_plugin_id', 'plugin_run_logs', ['plugin_id'])
        op.create_index('ix_plugin_run_logs_base_id', 'plugin_run_logs', ['base_id'])
        op.create_index('ix_plugin_run_logs_created_at', 'plugin_run_logs', ['created_at'])


def downgrade():
    for _t in ('plugin_run_logs', 'plugin_installations',
               'plugin_configs', 'plugin_versions', 'plugins'):
        try:
            op.drop_table(_t)
        except sa.exc.NoSuchTableError:
            pass
        except sa.exc.OperationalError:
            pass
