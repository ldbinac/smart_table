"""
添加 form_config 字段到 views 表
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.extensions import db
from app import create_app
from sqlalchemy import text

def upgrade():
    """添加 form_config 字段"""
    app = create_app()
    with app.app_context():
        try:
            # 检查字段是否已存在
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('views')]
            
            if 'form_config' not in columns:
                # 添加 form_config 字段
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE views ADD COLUMN form_config JSON"
                    ))
                    conn.commit()
                print("成功添加 form_config 字段到 views 表")
            else:
                print("form_config 字段已存在")
                
        except Exception as e:
            print(f"添加字段失败：{e}")
            raise

def downgrade():
    """删除 form_config 字段"""
    app = create_app()
    with app.app_context():
        try:
            # 检查字段是否存在
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('views')]
            
            if 'form_config' in columns:
                # 删除 form_config 字段
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE views DROP COLUMN form_config"
                    ))
                    conn.commit()
                print("成功删除 form_config 字段")
            else:
                print("form_config 字段不存在")
                
        except Exception as e:
            print(f"删除字段失败：{e}")
            raise

if __name__ == '__main__':
    # 默认执行升级
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade()
