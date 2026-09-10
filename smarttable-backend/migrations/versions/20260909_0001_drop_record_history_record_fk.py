"""
移除 record_history.record_id 到 records.id 的外键约束（审计日志修复）

问题：模型中原先定义了 ForeignKey('records.id', ondelete='CASCADE')。
PostgreSQL 强制执行该外键，删除数据记录时，数据库会级联删除该记录的
全部历史日志（包括删除前刚写入的 DELETE 日志），审计信息随之丢失；
SQLite 默认不启用外键强制（PRAGMA foreign_keys 默认 OFF），级联不生效，
日志得以保留——造成两种数据库行为不一致。

修复：record_id 仅作为普通数据列保留（删除记录后历史行仍可通过
record_id 关联查询），不再建立外键约束。

说明：record_history 表由 db.create_all() 创建、无历史迁移管理，因此：
- 全新数据库：更新后的模型建表时天然不含该外键，本迁移自动跳过；
- 存量 PostgreSQL 库：通过本迁移删除已存在的外键约束；
- 存量 SQLite 库：该外键本就不生效，无需处理。

Revision ID: 20260909_0001
Revises: 20260907_0001
Create Date: 2026-09-09
"""
from alembic import op
from sqlalchemy import inspect


revision = '20260909_0001'
down_revision = '20260907_0001'
branch_labels = None
depends_on = None


def _find_record_id_fk(inspector):
    """定位 record_history.record_id -> records.id 的外键约束名（无则返回 None）"""
    if 'record_history' not in inspector.get_table_names():
        return None
    for fk in inspector.get_foreign_keys('record_history'):
        if (fk.get('referred_table') == 'records'
                and fk.get('constrained_columns') == ['record_id']):
            return fk.get('name')
    return None


def upgrade():
    bind = op.get_bind()

    # SQLite 默认不强制外键，该约束本就不生效，无需处理
    if bind.dialect.name != 'postgresql':
        return

    inspector = inspect(bind)
    fk_name = _find_record_id_fk(inspector)
    if not fk_name:
        return

    # 该约束由 create_all 自动命名（通常为 record_history_record_id_fkey），
    # 通过 inspector 动态定位，避免命名差异导致失败
    op.drop_constraint(fk_name, 'record_history', type_='foreignkey')


def downgrade():
    # 不恢复外键：重新加回 ON DELETE CASCADE 会恢复「删除记录连带删除历史
    # 日志」的缺陷；且升级后已删除记录的历史行（record_id 指向已不存在的
    # 记录）会导致约束创建失败。保持无外键的审计语义。
    pass
