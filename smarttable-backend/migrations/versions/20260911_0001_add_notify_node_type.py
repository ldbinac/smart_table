"""
扩展 workflow_nodes.node_type 枚举新增 'notify' 值，用于站内信通知节点

Revision ID: 20260911_0001
Revises: 20260909_0001
Create Date: 2026-09-11
"""
from alembic import op
import sqlalchemy as sa


revision = '20260911_0001'
down_revision = '20260909_0001'
branch_labels = None
depends_on = None


# 现有枚举值（含 script，不含 notify）
EXISTING_NODE_TYPES = [
    'trigger', 'approval', 'condition', 'webhook', 'loop',
    'find_records', 'send_email', 'update_record', 'create_record',
    'trigger_webhook', 'script', 'action',
]

# 扩展后枚举值（含 notify）
NODE_TYPES_WITH_NOTIFY = EXISTING_NODE_TYPES + ['notify']


def upgrade():
    bind = op.get_bind()

    # PostgreSQL: 原生枚举类型只需扩展枚举值，无需重建表。
    # 重建表需删除 workflow_nodes 主键约束，将因外键依赖
    # (workflow_tasks_node_id_fkey -> workflow_nodes_pkey) 而失败。
    # PG 12+ 允许在事务块内执行 ALTER TYPE ... ADD VALUE（新值仅不能在同一事务中
    # 被使用，本迁移不使用），与既有 20260801_0022 保持一致，不额外切换 AUTOCOMMIT，
    # 避免提前提交 Alembic 的迁移事务。
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE workflownodetype ADD VALUE IF NOT EXISTS 'notify'")
        return

    insp = sa.inspect(bind)
    if 'workflow_nodes' not in insp.get_table_names():
        # 表尚不存在时由 db.create_all() 兜底创建，跳过本迁移
        return

    # SQLite 不支持 ALTER COLUMN 语法，必须使用 batch 模式重建表
    # create_type=False 避免重建时重复创建原生枚举类型
    with op.batch_alter_table('workflow_nodes', recreate='always') as batch_op:
        batch_op.alter_column(
            'node_type',
            type_=sa.Enum(
                *NODE_TYPES_WITH_NOTIFY,
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
    bind = op.get_bind()

    # PostgreSQL：原生枚举类型不支持移除枚举值，且重建表需删除
    # workflow_nodes_pkey，会因外键依赖
    # (workflow_tasks_node_id_fkey -> workflow_nodes_pkey) 而失败。
    # 保留 'notify' 枚举值不影响旧版本代码运行，因此在 PG 上跳过。
    if bind.dialect.name == 'postgresql':
        return

    insp = sa.inspect(bind)
    if 'workflow_nodes' not in insp.get_table_names():
        return

    # 使用 batch_alter_table 重建 node_type 列，移除 'notify' 值
    with op.batch_alter_table('workflow_nodes', recreate='always') as batch_op:
        batch_op.alter_column(
            'node_type',
            type_=sa.Enum(
                *EXISTING_NODE_TYPES,
                name='workflownodetype',
                create_type=False,
            ),
            existing_type=sa.Enum(
                *NODE_TYPES_WITH_NOTIFY,
                name='workflownodetype',
                create_type=False,
            ),
            existing_nullable=False,
        )
