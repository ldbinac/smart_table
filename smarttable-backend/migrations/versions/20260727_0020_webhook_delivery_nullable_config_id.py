"""将 webhook_delivery_logs.webhook_config_id 改为可空

内联 Webhook（循环节点中的 inline_webhook）不再持久化到 webhook_configs 表，
其投递日志的 webhook_config_id 为 NULL，因此需要放宽外键列约束。

使用 batch_alter_table 以兼容 SQLite（SQLite 不支持 ALTER COLUMN 语法）。

Revision ID: 20260727_0020
Revises: 20260727_0019
Create Date: 2026-07-27
"""
from alembic import op
import sqlalchemy as sa

revision = '20260727_0020'
down_revision = '20260727_0019'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('webhook_delivery_logs', recreate='always') as batch_op:
        batch_op.alter_column(
            'webhook_config_id',
            existing_type=sa.UUID(as_uuid=True),
            nullable=True,
        )


def downgrade():
    op.execute(
        "DELETE FROM webhook_delivery_logs WHERE webhook_config_id IS NULL"
    )
    with op.batch_alter_table('webhook_delivery_logs', recreate='always') as batch_op:
        batch_op.alter_column(
            'webhook_config_id',
            existing_type=sa.UUID(as_uuid=True),
            nullable=False,
        )
