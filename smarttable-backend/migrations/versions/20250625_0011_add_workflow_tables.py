"""
添加工作流相关表

Revision ID: 20250625_0011
Revises: 20250518_0010
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa
from app.db_types import CompatUUID as UUID

revision = '20250625_0011'
down_revision = '20250518_0010'
branch_labels = None
depends_on = None


def upgrade():
    # workflows
    op.create_table(
        'workflows',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('base_id', UUID(as_uuid=True), sa.ForeignKey('bases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('table_id', UUID(as_uuid=True), sa.ForeignKey('tables.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.Enum('draft', 'active', 'paused', 'archived', name='workflowstatus'), nullable=False),
        sa.Column('current_version', sa.Integer, default=0, nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    op.create_index('ix_workflows_base_id', 'workflows', ['base_id'])
    op.create_index('ix_workflows_table_id', 'workflows', ['table_id'])
    op.create_index('ix_workflows_status', 'workflows', ['status'])
    op.create_index('ix_workflows_created_by', 'workflows', ['created_by'])

    # workflow_versions
    op.create_table(
        'workflow_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('workflow_id', UUID(as_uuid=True), sa.ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('config_snapshot', sa.JSON, default=dict, nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_workflow_versions_workflow_id', 'workflow_versions', ['workflow_id'])
    op.create_index('ix_workflow_versions_version_number', 'workflow_versions', ['workflow_id', 'version_number'])

    # workflow_nodes
    op.create_table(
        'workflow_nodes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('workflow_id', UUID(as_uuid=True), sa.ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('node_type', sa.Enum('trigger', 'approval', 'action', 'condition', 'webhook', name='workflownodetype'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('config', sa.JSON, default=dict, nullable=False),
        sa.Column('order', sa.Integer, default=0, nullable=False),
        sa.Column('next_nodes', sa.JSON, default=list, nullable=False),
    )
    op.create_index('ix_workflow_nodes_workflow_id', 'workflow_nodes', ['workflow_id'])
    op.create_index('ix_workflow_nodes_type', 'workflow_nodes', ['node_type'])

    # workflow_triggers
    op.create_table(
        'workflow_triggers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('workflow_id', UUID(as_uuid=True), sa.ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('trigger_type', sa.Enum('record_created', 'record_updated', 'field_changed', 'manual', name='workflowtriggertype'), nullable=False),
        sa.Column('filter_config', sa.JSON, default=dict, nullable=False),
        sa.Column('field_ids', sa.JSON, default=list, nullable=False),
    )
    op.create_index('ix_workflow_triggers_workflow_id', 'workflow_triggers', ['workflow_id'])
    op.create_index('ix_workflow_triggers_type', 'workflow_triggers', ['trigger_type'])

    # workflow_instances
    op.create_table(
        'workflow_instances',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('workflow_id', UUID(as_uuid=True), sa.ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('trigger_type', sa.String(50), nullable=False),
        sa.Column('trigger_record_id', UUID(as_uuid=True), sa.ForeignKey('records.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.Enum('running', 'completed', 'rejected', 'cancelled', 'error', name='workflowinstancestatus'), nullable=False),
        sa.Column('context', sa.JSON, default=dict, nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_workflow_instances_workflow_id', 'workflow_instances', ['workflow_id'])
    op.create_index('ix_workflow_instances_status', 'workflow_instances', ['status'])
    op.create_index('ix_workflow_instances_trigger_record', 'workflow_instances', ['trigger_record_id'])
    op.create_index('ix_workflow_instances_started_at', 'workflow_instances', ['started_at'])

    # workflow_tasks
    op.create_table(
        'workflow_tasks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('instance_id', UUID(as_uuid=True), sa.ForeignKey('workflow_instances.id', ondelete='CASCADE'), nullable=False),
        sa.Column('node_id', UUID(as_uuid=True), sa.ForeignKey('workflow_nodes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assignee_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', 'transferred', 'expired', name='workflowtaskstatus'), nullable=False),
        sa.Column('comment', sa.Text, nullable=True),
        sa.Column('acted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('transferred_from_id', UUID(as_uuid=True), sa.ForeignKey('workflow_tasks.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_workflow_tasks_instance_id', 'workflow_tasks', ['instance_id'])
    op.create_index('ix_workflow_tasks_assignee_id', 'workflow_tasks', ['assignee_id'])
    op.create_index('ix_workflow_tasks_status', 'workflow_tasks', ['status'])

    # workflow_execution_logs
    op.create_table(
        'workflow_execution_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('instance_id', UUID(as_uuid=True), sa.ForeignKey('workflow_instances.id', ondelete='CASCADE'), nullable=False),
        sa.Column('node_id', UUID(as_uuid=True), sa.ForeignKey('workflow_nodes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('node_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('input_context', sa.JSON, default=dict, nullable=False),
        sa.Column('output_result', sa.JSON, default=dict, nullable=False),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_workflow_execution_logs_instance_id', 'workflow_execution_logs', ['instance_id'])
    op.create_index('ix_workflow_execution_logs_status', 'workflow_execution_logs', ['status'])
    op.create_index('ix_workflow_execution_logs_started_at', 'workflow_execution_logs', ['started_at'])

    # webhook_configs
    op.create_table(
        'webhook_configs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('base_id', UUID(as_uuid=True), sa.ForeignKey('bases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('url', sa.Text, nullable=False),
        sa.Column('method', sa.Enum('GET', 'POST', 'PUT', name='webhookmethod'), nullable=False),
        sa.Column('headers', sa.JSON, default=dict, nullable=False),
        sa.Column('body_template', sa.Text, nullable=True),
        sa.Column('secret', sa.Text, nullable=True),
        sa.Column('retry_policy', sa.JSON, default=dict, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_webhook_configs_base_id', 'webhook_configs', ['base_id'])
    op.create_index('ix_webhook_configs_is_active', 'webhook_configs', ['is_active'])
    op.create_index('ix_webhook_configs_created_by', 'webhook_configs', ['created_by'])

    # webhook_delivery_logs
    op.create_table(
        'webhook_delivery_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('webhook_config_id', UUID(as_uuid=True), sa.ForeignKey('webhook_configs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('instance_id', UUID(as_uuid=True), sa.ForeignKey('workflow_instances.id', ondelete='SET NULL'), nullable=True),
        sa.Column('payload', sa.Text, nullable=True),
        sa.Column('status', sa.Enum('pending', 'success', 'failed', name='webhookdeliverystatus'), nullable=False),
        sa.Column('response_status', sa.Integer, nullable=True),
        sa.Column('response_body', sa.Text, nullable=True),
        sa.Column('retry_count', sa.Integer, default=0, nullable=False),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_webhook_delivery_logs_config_id', 'webhook_delivery_logs', ['webhook_config_id'])
    op.create_index('ix_webhook_delivery_logs_instance_id', 'webhook_delivery_logs', ['instance_id'])
    op.create_index('ix_webhook_delivery_logs_status', 'webhook_delivery_logs', ['status'])
    op.create_index('ix_webhook_delivery_logs_created_at', 'webhook_delivery_logs', ['created_at'])

    # workflow_templates
    op.create_table(
        'workflow_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('config_snapshot', sa.JSON, default=dict, nullable=False),
        sa.Column('is_system', sa.Boolean, default=False, nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_workflow_templates_category', 'workflow_templates', ['category'])
    op.create_index('ix_workflow_templates_is_system', 'workflow_templates', ['is_system'])


def downgrade():
    op.drop_table('workflow_templates')
    op.drop_table('webhook_delivery_logs')
    op.drop_table('webhook_configs')
    op.drop_table('workflow_execution_logs')
    op.drop_table('workflow_tasks')
    op.drop_table('workflow_instances')
    op.drop_table('workflow_triggers')
    op.drop_table('workflow_nodes')
    op.drop_table('workflow_versions')
    op.drop_table('workflows')

    # 清理 PostgreSQL ENUM 类型
    op.execute("DROP TYPE IF EXISTS workflowstatus")
    op.execute("DROP TYPE IF EXISTS workflownodetype")
    op.execute("DROP TYPE IF EXISTS workflowtriggertype")
    op.execute("DROP TYPE IF EXISTS workflowinstancestatus")
    op.execute("DROP TYPE IF EXISTS workflowtaskstatus")
    op.execute("DROP TYPE IF EXISTS webhookmethod")
    op.execute("DROP TYPE IF EXISTS webhookdeliverystatus")
