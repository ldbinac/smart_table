"""
创建数据库表（开发环境使用）
"""
from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    db.create_all()
    print("所有表创建成功！")
