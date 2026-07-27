"""将 workflow_execution_logs.node_id 改为 String 类型并移除外键约束，新增 node_name 字段

循环体节点使用前端传递的临时 ID（字符串），不是数据库 UUID，
因此需要将 node_id 字段改为 String 类型以支持任意标识符。
同时新增 node_name 字段记录节点名称，避免外键依赖。

Revision ID: 20260727_0021
Revises: 20260727_0020
Create Date: 2026-07-27
"""
from alembic import op
import sqlalchemy as sa

revision = '20260727_0021'
down_revision = '20260727_0020'
branch_labels = None
depends_on = None


def upgrade():
    # 使用 batch 模式处理 SQLite 的限制
    with op.batch_alter_table('workflow_execution_logs', schema=None) as batch_op:
        # SQLite 的 batch 模式会自动处理外键约束的重建
        # 将 UUID 类型改为 String(64)
        batch_op.alter_column(
            'node_id',
            existing_type=sa.UUID(as_uuid=True),
            type_=sa.String(64),
            nullable=True,
            existing_nullable=True,
            postgresql_using="node_id::text"
        )

        # 新增 node_name 字段
        batch_op.add_column(
            sa.Column('node_name', sa.String(200), nullable=True)
        )

    # 从 workflow_nodes 表回填 node_name（仅对有效的 UUID 格式）
    # 使用原始 SQL，因为 SQLite 不支持复杂 JOIN
    op.execute(
        """
        UPDATE workflow_execution_logs
        SET node_name = (
            SELECT wn.name
            FROM workflow_nodes wn
            WHERE workflow_execution_logs.node_id = CAST(wn.id AS TEXT)
        )
        WHERE node_id IS NOT NULL
        """
    )


def downgrade():
    # 使用 batch 模式处理 SQLite 的限制
    with op.batch_alter_table('workflow_execution_logs', schema=None) as batch_op:
        # 删除 node_name 字段
        batch_op.drop_column('node_name')

        # 将 String 转回 UUID（仅保留有效的 UUID 格式）
        batch_op.alter_column(
            'node_id',
            existing_type=sa.String(64),
            type_=sa.UUID(as_uuid=True),
            nullable=True,
            existing_nullable=True
        )