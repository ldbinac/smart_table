"""
Alembic 迁移环境配置
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 导入应用和模型
from app import create_app
from app.extensions import db
from app.models import *

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# Alembic 配置对象
config = context.config

# 解释配置文件中的 Python 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标元数据（用于自动生成迁移脚本）
target_metadata = db.Model.metadata

# 从应用配置获取数据库URL
app = create_app(os.getenv('FLASK_ENV', 'development'))
config.set_main_option('sqlalchemy.url', app.config['SQLALCHEMY_DATABASE_URI'])


def run_migrations_offline() -> None:
    """
    离线模式运行迁移（不建立数据库连接）
    
    用于生成 SQL 脚本
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在线模式运行迁移（建立数据库连接）
    
    用于实际执行迁移
    """
    # 创建数据库连接
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # 比较列类型变化
            compare_server_default=True,  # 比较默认值变化
        )

        with context.begin_transaction():
            context.run_migrations()


# 根据运行模式选择迁移方式
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
