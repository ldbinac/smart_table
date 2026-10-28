"""
放宽会溢出的 varchar 列 + 修正 PostgreSQL 自增序列落后于 max(id) 的问题

背景
----
1) operation_history.operation_type 定义为 String(20)，但业务代码会写入
   'password_change_error'（21 字符）与 'password_change_failed'（22 字符）。
   SQLite 不校验 varchar 长度，因此该问题长期被隐藏；PostgreSQL 会直接抛
   22001 value too long for type character varying(20)。
   该写入发生在修改密码的审计日志里，异常会导致整个改密事务回滚。

2) bases.color 定义为 String(7)（恰好吃下 '#RRGGBB'），但颜色字段没有任何
   服务端校验，传入 '#RRGGBBAA'（9 字符）等更长的色值时同样触发 22001，
   接口返回 500 database_error。

3) 从 SQLite 迁移到 PostgreSQL 的库，如果历史数据是"带显式 id 灌入"的，
   自增序列（serial/nextval）不会随之推进，后续 INSERT 会撞主键（23505）。
   本迁移在 PostgreSQL 上把所有 serial 列对齐到 max(id)（只向前对齐，不会倒退）。

兼容性
------
- SQLite 不支持 ALTER COLUMN TYPE，所有列宽调整通过 batch_alter_table 重建表完成
  （与 20260911_0001 等既有迁移同一写法）。
- 幂等：执行前先探测当前列宽，已经足够宽则跳过；序列只在前移时 setval。

Revision ID: 20261027_0002
Revises: 20261016_0001
Create Date: 2026-10-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '20261027_0002'
down_revision = '20261016_0001'
branch_labels = None
depends_on = None


# (表名, 列名, 目标长度, 旧长度)
COLUMN_WIDENING = (
    ('operation_history', 'operation_type', 64, 20),
    ('bases', 'color', 32, 7),
)


def _column_length(inspector, table: str, column: str):
    """返回当前列宽；列不存在或非字符串类型时返回 None。"""
    if table not in inspector.get_table_names():
        return None
    for col in inspector.get_columns(table):
        if col['name'] == column:
            return getattr(col['type'], 'length', None)
    return None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # ---- 1. 放宽列宽（幂等：已经足够宽则跳过）----
    for table, column, new_len, old_len in COLUMN_WIDENING:
        current = _column_length(inspector, table, column)
        if current is None:
            # 表或列不存在（例如由 db.create_all() 建的新库尚未跑到该迁移），跳过
            continue
        if current >= new_len:
            continue
        # SQLite 不支持 ALTER COLUMN，batch 模式会重建表；PostgreSQL 下为就地 ALTER
        with op.batch_alter_table(table, recreate='auto') as batch_op:
            batch_op.alter_column(
                column,
                type_=sa.String(new_len),
                existing_type=sa.String(current),
                existing_nullable=True if (table, column) == ('bases', 'color') else False,
            )

    # ---- 2. PostgreSQL：把自增序列对齐到 max(id) ----
    if bind.dialect.name == 'postgresql':
        rows = bind.execute(sa.text("""
            SELECT c.table_name,
                   c.column_name,
                   pg_get_serial_sequence(
                       quote_ident(c.table_schema) || '.' || quote_ident(c.table_name),
                       c.column_name
                   ) AS seq
            FROM information_schema.columns c
            WHERE c.table_schema = current_schema()
              AND c.column_default LIKE 'nextval(%'
        """)).fetchall()

        for table_name, column_name, seq_name in rows:
            if not seq_name:
                continue
            max_id = bind.execute(sa.text(
                'SELECT COALESCE(MAX("%s"), 0) FROM "%s"' % (column_name, table_name)
            )).scalar() or 0
            last_value = bind.execute(sa.text(
                'SELECT last_value FROM %s' % seq_name
            )).scalar() or 0
            # 只向前对齐：避免把已经在前面、正在被并发使用的序列拨回去
            if int(max_id) > int(last_value):
                bind.execute(
                    sa.text('SELECT setval(CAST(:seq AS regclass), :val, true)'),
                    {'seq': seq_name, 'val': int(max_id)},
                )


def downgrade():
    """回退列宽。

    说明：
    - 序列对齐不做回退——把序列拨回去只会让主键冲突重新出现，
      且序列值不属于需要用 downgrade 恢复的业务数据。
    - 缩小列宽前会先检查是否有超长数据；有则直接报错中止（避免静默截断）。
    """
    bind = op.get_bind()
    inspector = inspect(bind)

    for table, column, new_len, old_len in COLUMN_WIDENING:
        current = _column_length(inspector, table, column)
        if current is None or current <= old_len:
            continue

        # 缩小列宽是有损操作：若表里已经存了比旧宽度更长的值，直接给出明确报错，
        # 而不是让数据库抛出一句难以理解的 22001/数据截断错误。
        overlength = bind.execute(
            sa.text('SELECT COUNT(*) FROM "%s" WHERE LENGTH("%s") > :n' % (table, column)),
            {'n': old_len},
        ).scalar() or 0
        if overlength:
            raise RuntimeError(
                'downgrade 中止：%s.%s 存在 %d 行长度超过 %d 的数据，'
                '缩小列宽会造成数据截断。请先清理/迁移这些数据，再执行 downgrade。'
                % (table, column, overlength, old_len)
            )

        with op.batch_alter_table(table, recreate='auto') as batch_op:
            batch_op.alter_column(
                column,
                type_=sa.String(old_len),
                existing_type=sa.String(current),
                existing_nullable=True if (table, column) == ('bases', 'color') else False,
            )
