"""
数据表文件夹功能：新增 table_folders 表 + tables.folder_id 列

Revision ID: 20260925_0001
Revises: 20260911_0001
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# 与模型一致：UUID 列在 PostgreSQL 下编译为原生 UUID，在 SQLite 下为 String(36)
from app.db_types import CompatUUID as UUID


revision = '20260925_0001'
down_revision = '20260911_0001'
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    inspector = inspect(op.get_bind())
    return name in inspector.get_table_names()


def upgrade():
    # 1. 建 table_folders 表（幂等：已存在则跳过，历史 create_all 已建表）
    if not _table_exists('table_folders'):
        op.create_table(
            'table_folders',
            sa.Column('id', UUID(), nullable=False),
            sa.Column('base_id', UUID(), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('order', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['base_id'], ['bases.id'], ondelete='CASCADE')
        )
        op.create_index('ix_table_folders_base_id', 'table_folders', ['base_id'])

    # 2. tables 加 folder_id 列（幂等：列已存在则跳过）
    inspector = inspect(op.get_bind())
    existing_cols = {c['name'] for c in inspector.get_columns('tables')}
    if 'folder_id' not in existing_cols:
        # 不加 DB 级外键：tables 被 fields/records/views 多表外键引用，
        # SQLite batch 重建有依赖风险；置空逻辑在服务层
        with op.batch_alter_table('tables') as batch_op:
            batch_op.add_column(sa.Column('folder_id', UUID(), nullable=True))
        op.create_index('ix_tables_folder_id', 'tables', ['folder_id'])


def downgrade():
    inspector = inspect(op.get_bind())
    existing_cols = {c['name'] for c in inspector.get_columns('tables')}
    if 'folder_id' in existing_cols:
        op.drop_index('ix_tables_folder_id', table_name='tables')
        with op.batch_alter_table('tables') as batch_op:
            batch_op.drop_column('folder_id')

    if _table_exists('table_folders'):
        op.drop_index('ix_table_folders_base_id', table_name='table_folders')
        op.drop_table('table_folders')
