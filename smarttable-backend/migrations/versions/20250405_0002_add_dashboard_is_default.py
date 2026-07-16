"""
添加仪表盘 is_default 字段

修订 ID: 002
创建时间：2025-04-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# 修订标识符
revision = '20250405_0002'
down_revision = '20250403_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级数据库模式 - 添加 is_default 字段"""
    
    # 为 dashboards 表添加 is_default 字段（仅当不存在时）
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns = [col['name'] for col in inspector.get_columns('dashboards')]
    if 'is_default' not in columns:
        op.add_column('dashboards', sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """降级数据库模式 - 移除 is_default 字段"""
    
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns = [col['name'] for col in inspector.get_columns('dashboards')]
    if 'is_default' in columns:
        op.drop_column('dashboards', 'is_default')
