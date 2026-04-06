"""
添加管理员用户管理系统模型

- 创建 operation_logs 表 (操作日志)
- 创建 system_configs 表 (系统配置)
- 扩展 users 表添加 must_change_password 和 password_changed_at 字段

修订 ID: 002
创建时间: 2025-04-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# 修订标识符
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级数据库模式 - 添加管理员用户管理系统相关表"""
    
    # 创建操作日志表
    op.create_table(
        'operation_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('action', sa.String(50), nullable=False, index=True),
        sa.Column('entity_type', sa.String(50), nullable=False, index=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.text('CURRENT_TIMESTAMP'), nullable=False, index=True)
    )
    
    # 创建操作日志复合索引
    op.create_index('ix_op_log_entity', 'operation_logs', ['entity_type', 'entity_id'])
    
    # 创建系统配置表
    op.create_table(
        'system_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('config_key', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('config_value', postgresql.JSONB(), nullable=False, default={}),
        sa.Column('config_group', sa.String(50), nullable=False, index=True, default='basic'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False)
    )
    
    # 创建系统配置复合索引
    op.create_index('ix_config_key_group', 'system_configs', ['config_key', 'config_group'], unique=True)
    
    # 扩展 users 表添加新字段
    op.add_column('users', sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime(), nullable=True))
    
    # 创建索引
    op.create_index('ix_op_log_user', 'operation_logs', ['user_id'])
    op.create_index('ix_op_log_action', 'operation_logs', ['action'])
    op.create_index('ix_op_log_time', 'operation_logs', ['created_at'])
    op.create_index('ix_config_group', 'system_configs', ['config_group'])


def downgrade() -> None:
    """降级数据库模式 - 删除新增的表和字段"""
    
    # 删除 users 表的新字段
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'must_change_password')
    
    # 删除系统配置表
    op.drop_index('ix_config_key_group', table_name='system_configs')
    op.drop_index('ix_config_group', table_name='system_configs')
    op.drop_table('system_configs')
    
    # 删除操作日志表
    op.drop_index('ix_op_log_entity', table_name='operation_logs')
    op.drop_index('ix_op_log_user', table_name='operation_logs')
    op.drop_index('ix_op_log_action', table_name='operation_logs')
    op.drop_index('ix_op_log_time', table_name='operation_logs')
    op.drop_table('operation_logs')
