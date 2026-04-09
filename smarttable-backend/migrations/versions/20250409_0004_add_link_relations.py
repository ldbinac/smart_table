"""
添加链接关系功能模型

- 创建 link_relations 表 (链接关系定义)
- 创建 link_values 表 (链接值)

修订 ID: 004
创建时间: 2025-04-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# 修订标识符
revision = '004'
down_revision = '20250406_0003_add_base_sharing'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级数据库模式 - 添加链接关系相关表"""
    
    # 创建链接关系表
    op.create_table(
        'link_relations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('source_table_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tables.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('target_table_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tables.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('source_field_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('fields.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('target_field_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('fields.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('relationship_type', sa.String(20), nullable=False, default='one_to_many'),
        sa.Column('bidirectional', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False)
    )
    
    # 创建链接值表
    op.create_table(
        'link_values',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('link_relation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('link_relations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('source_record_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('records.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('target_record_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('records.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False)
    )
    
    # 创建 link_relations 表的索引
    op.create_index('ix_link_relation_source_table', 'link_relations', ['source_table_id'])
    op.create_index('ix_link_relation_target_table', 'link_relations', ['target_table_id'])
    op.create_index('ix_link_relation_source_field', 'link_relations', ['source_field_id'])
    op.create_index('ix_link_relation_target_field', 'link_relations', ['target_field_id'])
    op.create_index('ix_link_relation_tables', 'link_relations', ['source_table_id', 'target_table_id'])
    
    # 创建 link_values 表的索引
    op.create_index('ix_link_value_relation', 'link_values', ['link_relation_id'])
    op.create_index('ix_link_value_source_record', 'link_values', ['source_record_id'])
    op.create_index('ix_link_value_target_record', 'link_values', ['target_record_id'])
    op.create_index('ix_link_value_source_target', 'link_values', ['source_record_id', 'target_record_id'])
    op.create_index('ix_link_value_relation_source', 'link_values', ['link_relation_id', 'source_record_id'])
    op.create_index('ix_link_value_relation_target', 'link_values', ['link_relation_id', 'target_record_id'])


def downgrade() -> None:
    """降级数据库模式 - 删除链接关系相关表"""
    
    # 删除 link_values 表的索引
    op.drop_index('ix_link_value_relation_target', table_name='link_values')
    op.drop_index('ix_link_value_relation_source', table_name='link_values')
    op.drop_index('ix_link_value_source_target', table_name='link_values')
    op.drop_index('ix_link_value_target_record', table_name='link_values')
    op.drop_index('ix_link_value_source_record', table_name='link_values')
    op.drop_index('ix_link_value_relation', table_name='link_values')
    
    # 删除 link_relations 表的索引
    op.drop_index('ix_link_relation_tables', table_name='link_relations')
    op.drop_index('ix_link_relation_target_field', table_name='link_relations')
    op.drop_index('ix_link_relation_source_field', table_name='link_relations')
    op.drop_index('ix_link_relation_target_table', table_name='link_relations')
    op.drop_index('ix_link_relation_source_table', table_name='link_relations')
    
    # 删除表（按依赖关系逆序）
    op.drop_table('link_values')
    op.drop_table('link_relations')
