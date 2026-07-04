"""
为 workflowtriggertype ENUM 添加 specified_time 值

Revision ID: 20250629_0012
Revises: 20250625_0011
Create Date: 2026-06-29
"""
from alembic import op

revision = '20250629_0012'
down_revision = '20250625_0011'
branch_labels = None
depends_on = None


def upgrade():
    # PostgreSQL ENUM 类型新增值
    op.execute("ALTER TYPE workflowtriggertype ADD VALUE 'specified_time'")


def downgrade():
    # PostgreSQL 不支持直接删除 ENUM 值；如确实需要回滚，需重建 ENUM 类型并迁移数据
    pass
