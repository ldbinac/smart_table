"""
为 users 表添加 username 唯一字段

Revision ID: 20261029_0001
Revises: 20261027_0002
Create Date: 2026-10-29 00:00:00.000000

兼容场景：
1. username 列不存在：添加列 -> 回填存量数据 -> 创建唯一索引；
2. username 列已存在（例如此前已执行过本迁移或由业务侧处理）：
   跳过回填，避免覆盖已有业务数据，仅按需补建唯一索引；
3. 两种情况下脚本均正常结束，保证迁移链可按次序执行后续版本。
4. 回填/兜底均使用参数化 Python 实现，兼容 SQLite / MySQL / PostgreSQL。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20261029_0001'
down_revision = '20261027_0002'
branch_labels = None
depends_on = None

_TABLE = 'users'
_COLUMN = 'username'
_INDEX_NAME = 'ix_users_username'


def _column_exists(conn, table, column):
    """通过反射判断列是否存在（每次新建 Inspector，避免缓存到过期的表结构）"""
    inspector = sa.inspect(conn)
    return column in {c['name'] for c in inspector.get_columns(table)}


def _index_exists(conn, table, index_name):
    """通过反射判断索引/唯一约束是否存在"""
    inspector = sa.inspect(conn)
    index_names = {i['name'] for i in inspector.get_indexes(table)}
    constraint_names = {u['name'] for u in inspector.get_unique_constraints(table)}
    return index_name in index_names or index_name in constraint_names


def _ensure_username_index(conn):
    """唯一索引不存在时才创建；注意需重新反射，避免 add_column 后缓存误判"""
    if not _index_exists(conn, _TABLE, _INDEX_NAME):
        op.create_index(op.f(_INDEX_NAME), _TABLE, [_COLUMN], unique=True)


def upgrade():
    conn = op.get_bind()

    # username 列已存在：说明字段添加与数据填充此前已完成（或由业务侧处理），
    # 跳过回填以免覆盖业务数据，仅确保唯一索引存在，保证迁移链可继续执行。
    if _column_exists(conn, _TABLE, _COLUMN):
        _ensure_username_index(conn)
        return

    # 1. 添加 username 列（可空，避免存量数据阻塞）
    op.add_column(_TABLE, sa.Column(_COLUMN, sa.String(100), nullable=True))

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

    # 3. 兜底：确保没有任何一条 username 为 NULL（用 Python 实现，兼容 SQLite/MySQL/PostgreSQL）
    leftover = conn.execute(
        sa.text("SELECT id FROM users WHERE username IS NULL")
    ).fetchall()
    for (uid,) in leftover:
        conn.execute(
            sa.text("UPDATE users SET username = :username WHERE id = :id"),
            {"username": f"user_{str(uid)[:8]}", "id": uid},
        )

    # 4. 创建索引和唯一约束
    _ensure_username_index(conn)


def downgrade():
    conn = op.get_bind()

    # 删除索引
    if _index_exists(conn, _TABLE, _INDEX_NAME):
        op.drop_index(op.f(_INDEX_NAME), table_name=_TABLE)

    # 删除字段
    if _column_exists(conn, _TABLE, _COLUMN):
        op.drop_column(_TABLE, _COLUMN)
