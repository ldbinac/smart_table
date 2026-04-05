"""
为 views 表添加新字段：hidden_fields, frozen_fields, row_height, field_widths
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def migrate():
    """执行数据库迁移"""
    app = create_app()
    
    with app.app_context():
        try:
            # 添加 hidden_fields 字段
            db.session.execute(text("""
                ALTER TABLE views 
                ADD COLUMN hidden_fields JSON
            """))
            print("✅ 添加 hidden_fields 字段")
        except Exception as e:
            if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                print("ℹ️  hidden_fields 字段已存在")
            else:
                print(f"❌ 添加 hidden_fields 失败：{e}")
                raise
        
        try:
            # 添加 frozen_fields 字段
            db.session.execute(text("""
                ALTER TABLE views 
                ADD COLUMN frozen_fields JSON
            """))
            print("✅ 添加 frozen_fields 字段")
        except Exception as e:
            if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                print("ℹ️  frozen_fields 字段已存在")
            else:
                print(f"❌ 添加 frozen_fields 失败：{e}")
                raise
        
        try:
            # 添加 row_height 字段
            db.session.execute(text("""
                ALTER TABLE views 
                ADD COLUMN row_height VARCHAR(20) DEFAULT 'medium'
            """))
            print("✅ 添加 row_height 字段")
        except Exception as e:
            if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                print("ℹ️  row_height 字段已存在")
            else:
                print(f"❌ 添加 row_height 失败：{e}")
                raise
        
        try:
            # 添加 field_widths 字段
            db.session.execute(text("""
                ALTER TABLE views 
                ADD COLUMN field_widths JSON
            """))
            print("✅ 添加 field_widths 字段")
        except Exception as e:
            if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                print("ℹ️  field_widths 字段已存在")
            else:
                print(f"❌ 添加 field_widths 失败：{e}")
                raise
        
        db.session.commit()
        print("✅ 数据库迁移完成")

if __name__ == '__main__':
    migrate()
