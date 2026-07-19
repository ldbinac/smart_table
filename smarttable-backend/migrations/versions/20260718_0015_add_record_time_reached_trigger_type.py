"""
为 workflowtriggertype ENUM 添加 record_time_reached 值

Revision ID: 20260718_0015
Revises: 20260718_0014
Create Date: 2026-07-18
"""
from alembic import op

revision = '20260718_0015'
down_revision = '20260718_0014'
branch_labels = None
depends_on = None


def upgrade():
    # PostgreSQL ENUM 类型新增值（SQLite 无原生 ENUM，跳过）
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE workflowtriggertype ADD VALUE 'record_time_reached'")


def downgrade():
    # PostgreSQL 不支持直接删除 ENUM 值
    pass
