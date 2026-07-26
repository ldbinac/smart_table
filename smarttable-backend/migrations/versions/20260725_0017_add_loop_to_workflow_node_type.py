"""为 workflownodetype ENUM 添加 loop 值

Revision ID: 20260725_0017
Revises: 20260718_0016
Create Date: 2026-07-25
"""
from alembic import op

revision = '20260725_0017'
down_revision = '20260718_0016'
branch_labels = None
depends_on = None


def upgrade():
    # PostgreSQL ENUM 类型新增值（SQLite 无原生 ENUM，跳过）
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE workflownodetype ADD VALUE 'loop'")


def downgrade():
    # PostgreSQL 不支持直接删除 ENUM 值
    pass
