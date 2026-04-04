"""
添加仪表盘 is_default 字段

修订 ID: 002
创建时间：2025-04-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# 修订标识符
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级数据库模式 - 添加 is_default 字段"""
    
    # 为 dashboards 表添加 is_default 字段
    op.add_column('dashboards', sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """降级数据库模式 - 移除 is_default 字段"""
    
    op.drop_column('dashboards', 'is_default')
