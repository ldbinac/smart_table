"""
初始化数据库脚本
"""
import os
from app import create_app, db

# 设置 SQLite 数据库 URL (使用相对路径)
os.environ['DATABASE_URL'] = 'sqlite:///smarttable.db'
print(f'Using database: {os.path.abspath("smarttable.db")}')

app = create_app()

with app.app_context():
    db.create_all()
    print('✅ 数据库表创建成功!')
