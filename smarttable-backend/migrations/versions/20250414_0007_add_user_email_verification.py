"""
添加用户邮箱验证和密码重置字段

Revision ID: 20250414_0007
Revises: 20250414_0006
Create Date: 2026-04-14 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from app.db_types import CompatUUID

# revision identifiers, used by Alembic.
revision = '20250414_0007'
down_revision = '20250414_0006'
branch_labels = None
depends_on = None


def upgrade():
    # 添加用户邮箱验证相关字段
    op.add_column('users', sa.Column('verification_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('verification_token_expires', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('reset_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('reset_token_expires', sa.DateTime(), nullable=True))
    
    # 创建索引
    op.create_index('ix_users_verification_token', 'users', ['verification_token'])
    op.create_index('ix_users_reset_token', 'users', ['reset_token'])


def downgrade():
    # 删除索引
    op.drop_index('ix_users_verification_token', table_name='users')
    op.drop_index('ix_users_reset_token', table_name='users')
    
    # 删除字段
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'verification_token_expires')
    op.drop_column('users', 'reset_token')
    op.drop_column('users', 'reset_token_expires')
