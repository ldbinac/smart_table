"""
添加仪表盘 is_default 字段到数据库
"""
import sqlite3
import os

def add_is_default_column():
    # 获取数据库路径 (instance 文件夹)
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'smarttable.db')
    print(f"数据库路径：{db_path}")
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在：{db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查列是否已存在
        cursor.execute("""
            SELECT name FROM pragma_table_info('dashboards') WHERE name='is_default'
        """)
        result = cursor.fetchone()
        
        if result:
            print("is_default 列已存在")
            conn.close()
            return
        
        # 添加列
        cursor.execute("""
            ALTER TABLE dashboards ADD COLUMN is_default BOOLEAN DEFAULT FALSE NOT NULL
        """)
        conn.commit()
        conn.close()
        print("成功添加 is_default 列到 dashboards 表")
    except Exception as e:
        print(f"添加列失败：{e}")

if __name__ == '__main__':
    add_is_default_column()
