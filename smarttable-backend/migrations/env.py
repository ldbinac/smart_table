"""
Alembic 迁移环境配置
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
import sqlalchemy as sa

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

# 从环境变量获取数据库 URL（避免调 create_app 触发 db.create_all 等副作用）
# 历史上这里调 create_app('development') 会让 env.py 每次被加载时
# 都创建 Flask app 并执行 development 模式的 db.create_all() —— 这个副作用
# 在 SQLite WAL 模式下与 Alembic batch_alter_table(recreate) 组合会导致重建
# 表时清空核心业务表数据（tables/records/fields/views）。
# 改为直接读 DATABASE_URL 环境变量（dotenv 已在上面 load_dotenv 加载）。
db_url = os.environ.get('DATABASE_URL', 'sqlite:///instance/smarttable.db')
config.set_main_option('sqlalchemy.url', db_url)


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
        # SQLite batch_alter_table 会 RENAME → CREATE → INSERT → DROP old，
        # 若外键开启，DROP old 表时 ON DELETE CASCADE 会级联删除关联表数据。
        # 迁移过程中外键语义无关紧要（新表重建后外键自动恢复），
        # 这里显式关闭外键保护业务数据不被迁移过程误删。
        try:
            connection.execute(sa.text("PRAGMA foreign_keys=OFF"))
        except Exception:
            pass

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
