"""
添加 Base 分享功能模型

- 创建 base_shares 表 (Base 分享配置)

修订 ID: 003
创建时间：2025-04-06 00:03:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# 修订标识符
revision = '20250406_0003'
down_revision = '20250406_0002'
branch_labels = None
depends_on = None


def _get_indexes(table_name):
    """获取表上已存在的索引名称集合"""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    return {idx['name'] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    """升级数据库模式 - 添加 Base 分享功能相关表"""
    
    # 创建 Base 分享配置表
    op.create_table(
        'base_shares',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('base_id', sa.String(36), sa.ForeignKey('bases.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('share_token', sa.String(64), nullable=False, unique=True, index=True),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('permission', sa.Enum('view', 'edit', name='sharepermission'), nullable=False, default='view'),
        sa.Column('expires_at', sa.Integer(), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=False, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True)
    )
    
    # 创建索引（跳过由 index=True/unique=True 自动生成的重复索引）
    existing_indexes = _get_indexes('base_shares')
    if 'ix_base_shares_base_id' not in existing_indexes:
        op.create_index('ix_base_shares_base_id', 'base_shares', ['base_id'])
    if 'ix_base_shares_share_token' not in existing_indexes:
        op.create_index('ix_base_shares_share_token', 'base_shares', ['share_token'])
    if 'ix_base_shares_created_by' not in existing_indexes:
        op.create_index('ix_base_shares_created_by', 'base_shares', ['created_by'])


def downgrade() -> None:
    """回滚数据库模式 - 删除 Base 分享功能相关表"""
    
    # 删除索引（仅当存在时）
    existing_indexes = _get_indexes('base_shares')
    if 'ix_base_shares_created_by' in existing_indexes:
        op.drop_index('ix_base_shares_created_by', table_name='base_shares')
    if 'ix_base_shares_share_token' in existing_indexes:
        op.drop_index('ix_base_shares_share_token', table_name='base_shares')
    if 'ix_base_shares_base_id' in existing_indexes:
        op.drop_index('ix_base_shares_base_id', table_name='base_shares')
    
    # 删除表
    op.drop_table('base_shares')
