"""
为 workflow_nodes 表添加 ui_layout 字段

Revision ID: 20250705_0013
Revises: 20250629_0012
Create Date: 2026-07-05
"""
from alembic import op
import sqlalchemy as sa

revision = '20250705_0013'
down_revision = '20250629_0012'
branch_labels = None
depends_on = None


def upgrade():
    # 新增 ui_layout JSON 字段，用于存储节点在画布上的坐标等 UI 元数据
    op.add_column(
        'workflow_nodes',
        sa.Column('ui_layout', sa.JSON, nullable=True)
    )


def downgrade():
    op.drop_column('workflow_nodes', 'ui_layout')
