"""
添加 is_starred 字段到 base_members 表
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def migrate():
    """执行数据库迁移"""
    app = create_app()
    
    with app.app_context():
        try:
            # 执行 SQL 添加字段
            db.session.execute(db.text("""
                ALTER TABLE base_members 
                ADD COLUMN is_starred BOOLEAN DEFAULT FALSE NOT NULL
            """))
            db.session.commit()
            print("✅ 成功添加 is_starred 字段到 base_members 表")
        except Exception as e:
            db.session.rollback()
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("ℹ️  is_starred 字段已存在，跳过迁移")
            else:
                print(f"❌ 迁移失败：{e}")
                raise

if __name__ == '__main__':
    migrate()
