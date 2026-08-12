"""
扩展 workflow_nodes.node_type 枚举新增 'script' 值，用于自定义脚本节点

Revision ID: 20260801_0022
Revises: 20260727_163
Create Date: 2026-08-01
"""
from alembic import op
import sqlalchemy as sa


revision = '20260801_0022'
down_revision = '20260727_163'
branch_labels = None
depends_on = None


# 现有枚举值（不含 script）
EXISTING_NODE_TYPES = [
    'trigger', 'approval', 'condition', 'webhook', 'loop',
    'find_records', 'send_email', 'update_record', 'create_record',
    'trigger_webhook', 'action',
]

# 扩展后枚举值（含 script）
NODE_TYPES_WITH_SCRIPT = EXISTING_NODE_TYPES + ['script']


def upgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # PostgreSQL: 先扩展原生枚举类型
    if is_postgres:
        op.execute("ALTER TYPE workflownodetype ADD VALUE IF NOT EXISTS 'script'")

    # 使用 batch_alter_table 重建 node_type 列
    # SQLite 不支持 ALTER COLUMN 语法，必须使用 batch 模式重建表
    # create_type=False 避免 PostgreSQL 重复创建已存在的原生枚举类型
    with op.batch_alter_table('workflow_nodes', recreate='always') as batch_op:
        batch_op.alter_column(
            'node_type',
            type_=sa.Enum(
                *NODE_TYPES_WITH_SCRIPT,
                name='workflownodetype',
                create_type=False,
            ),
            existing_type=sa.Enum(
                *EXISTING_NODE_TYPES,
                name='workflownodetype',
                create_type=False,
            ),
            existing_nullable=False,
        )


def downgrade():
    # 使用 batch_alter_table 重建 node_type 列，移除 'script' 值
    with op.batch_alter_table('workflow_nodes', recreate='always') as batch_op:
        batch_op.alter_column(
            'node_type',
            type_=sa.Enum(
                *EXISTING_NODE_TYPES,
                name='workflownodetype',
                create_type=False,
            ),
            existing_type=sa.Enum(
                *NODE_TYPES_WITH_SCRIPT,
                name='workflownodetype',
                create_type=False,
            ),
            existing_nullable=False,
        )

    # 注意：PostgreSQL 不支持直接从 ENUM 类型中移除值
    # 如需完全移除 'script' 值，需重建 ENUM 类型并迁移数据
