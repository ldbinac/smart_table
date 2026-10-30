"""
为 users 表添加 username 唯一字段

Revision ID: 20261029_0001
Revises: 20261027_0002
Create Date: 2026-10-29 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20261029_0001'
down_revision = '20261027_0002'
branch_labels = None
depends_on = None


def upgrade():
    # 1. 添加 username 列（可空，避免存量数据阻塞）
    op.add_column('users', sa.Column('username', sa.String(100), nullable=True))

    # 2. 存量数据回填：用邮箱 '@' 前缀作为初始 username，冲突时加数字后缀
    conn = op.get_bind()

    # 获取所有用户
    users = conn.execute(
        sa.text("SELECT id, email FROM users WHERE username IS NULL ORDER BY created_at ASC")
    ).fetchall()

    # 收集已占用的 username
    used = set()

    for row in users:
        user_id, email = row
        # 取邮箱前缀作为候选
        candidate = email.split('@')[0][:100] if email else ''
        if not candidate:
            candidate = f"user_{str(user_id)[:8]}"

        # 保证唯一
        final = candidate
        counter = 1
        while final.lower() in used:
            suffix = f"_{counter}"
            final = (candidate[: 100 - len(suffix)] + suffix) if len(candidate) + len(suffix) > 100 else candidate + suffix
            counter += 1

        used.add(final.lower())
        conn.execute(
            sa.text("UPDATE users SET username = :username WHERE id = :id"),
            {"username": final, "id": user_id},
        )

    # 3. 确保没有任何一条 username 为 NULL
    conn.execute(sa.text("UPDATE users SET username = CONCAT('user_', SUBSTRING(CAST(id AS CHAR), 1, 8)) WHERE username IS NULL"))

    # 4. 创建索引和唯一约束
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)


def downgrade():
    # 删除索引
    try:
        op.drop_index(op.f('ix_users_username'), table_name='users')
    except Exception:
        pass

    # 删除字段
    op.drop_column('users', 'username')
