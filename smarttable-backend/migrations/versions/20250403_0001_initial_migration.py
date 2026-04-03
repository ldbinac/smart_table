"""
初始数据库迁移

创建所有核心表结构

修订 ID: 001
创建时间: 2025-04-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# 修订标识符
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级数据库模式 - 创建所有表"""
    
    # 创建用户表
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('username', sa.String(80), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('nickname', sa.String(80), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('role', sa.String(20), default='user'),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 创建多维表格基础表
    op.create_table(
        'bases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(50), default='table'),
        sa.Column('color', sa.String(7), default='#6366f1'),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_archived', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 创建基础成员表
    op.create_table(
        'base_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('base_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), default='viewer'),
        sa.Column('joined_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('base_id', 'user_id', name='unique_base_member')
    )
    
    # 创建表格表
    op.create_table(
        'tables',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('base_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), default=0),
        sa.Column('record_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 创建字段表
    op.create_table(
        'fields',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('table_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tables.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('options', postgresql.JSONB(), default={}),
        sa.Column('order', sa.Integer(), default=0),
        sa.Column('is_required', sa.Boolean(), default=False),
        sa.Column('is_unique', sa.Boolean(), default=False),
        sa.Column('is_system', sa.Boolean(), default=False),
        sa.Column('default_value', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 创建记录表
    op.create_table(
        'records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('table_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tables.id', ondelete='CASCADE'), nullable=False),
        sa.Column('values', postgresql.JSONB(), default={}),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 创建视图表
    op.create_table(
        'views',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('table_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tables.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('type', sa.String(50), default='grid'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('config', postgresql.JSONB(), default={}),
        sa.Column('filters', postgresql.JSONB(), default=list),
        sa.Column('sorts', postgresql.JSONB(), default=list),
        sa.Column('hidden_fields', postgresql.JSONB(), default=list),
        sa.Column('field_widths', postgresql.JSONB(), default={}),
        sa.Column('order', sa.Integer(), default=0),
        sa.Column('is_default', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 创建仪表盘表
    op.create_table(
        'dashboards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('base_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('layout', sa.String(20), default='grid'),
        sa.Column('widgets', postgresql.JSONB(), default=list),
        sa.Column('is_default', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 创建附件表
    op.create_table(
        'attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_name', sa.String(255), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('size', sa.BigInteger(), nullable=False),
        sa.Column('storage_path', sa.String(500), nullable=False),
        sa.Column('thumbnail_path', sa.String(500), nullable=True),
        sa.Column('uploader_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('record_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('records.id', ondelete='SET NULL'), nullable=True),
        sa.Column('field_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('fields.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 创建Token黑名单表
    op.create_table(
        'token_blocklist',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('jti', sa.String(36), nullable=False, index=True),
        sa.Column('token_type', sa.String(10), default='access'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.DateTime(), nullable=False)
    )
    
    # 创建索引
    op.create_index('idx_bases_owner', 'bases', ['owner_id'])
    op.create_index('idx_bases_archived', 'bases', ['is_archived'])
    op.create_index('idx_base_members_base', 'base_members', ['base_id'])
    op.create_index('idx_base_members_user', 'base_members', ['user_id'])
    op.create_index('idx_tables_base', 'tables', ['base_id'])
    op.create_index('idx_fields_table', 'fields', ['table_id'])
    op.create_index('idx_fields_type', 'fields', ['type'])
    op.create_index('idx_records_table', 'records', ['table_id'])
    op.create_index('idx_records_created_by', 'records', ['created_by'])
    op.create_index('idx_views_table', 'views', ['table_id'])
    op.create_index('idx_dashboards_base', 'dashboards', ['base_id'])
    op.create_index('idx_attachments_record', 'attachments', ['record_id'])
    op.create_index('idx_token_blocklist_jti', 'token_blocklist', ['jti'])
    
    # 创建GIN索引用于JSONB字段搜索
    op.create_index('idx_records_values', 'records', ['values'], postgresql_using='gin')
    op.create_index('idx_fields_options', 'fields', ['options'], postgresql_using='gin')
    op.create_index('idx_views_filters', 'views', ['filters'], postgresql_using='gin')


def downgrade() -> None:
    """降级数据库模式 - 删除所有表"""
    
    # 删除表（按依赖关系逆序）
    op.drop_table('token_blocklist')
    op.drop_table('attachments')
    op.drop_table('dashboards')
    op.drop_table('views')
    op.drop_table('records')
    op.drop_table('fields')
    op.drop_table('tables')
    op.drop_table('base_members')
    op.drop_table('bases')
    op.drop_table('users')
