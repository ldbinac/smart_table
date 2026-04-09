"""
初始化关联字段表
直接创建 link_relations 和 link_values 表
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from sqlalchemy import inspect

def init_link_tables():
    """创建关联字段相关表"""
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        # 检查表是否已存在
        existing_tables = inspector.get_table_names()
        
        if 'link_relations' in existing_tables:
            print("✓ link_relations 表已存在")
        else:
            print("创建 link_relations 表...")
            db.session.execute("""
                CREATE TABLE IF NOT EXISTS link_relations (
                    id VARCHAR(36) PRIMARY KEY,
                    source_table_id VARCHAR(36) NOT NULL,
                    target_table_id VARCHAR(36) NOT NULL,
                    source_field_id VARCHAR(36) NOT NULL,
                    target_field_id VARCHAR(36),
                    relationship_type VARCHAR(20) NOT NULL DEFAULT 'one_to_many',
                    bidirectional BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_table_id) REFERENCES tables(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_table_id) REFERENCES tables(id) ON DELETE CASCADE,
                    FOREIGN KEY (source_field_id) REFERENCES fields(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_field_id) REFERENCES fields(id) ON DELETE CASCADE
                )
            """)
            
            # 创建索引
            db.session.execute("CREATE INDEX IF NOT EXISTS ix_link_relation_source_table ON link_relations(source_table_id)")
            db.session.execute("CREATE INDEX IF NOT EXISTS ix_link_relation_target_table ON link_relations(target_table_id)")
            db.session.execute("CREATE INDEX IF NOT EXISTS ix_link_relation_source_field ON link_relations(source_field_id)")
            db.session.execute("CREATE INDEX IF NOT EXISTS ix_link_relation_target_field ON link_relations(target_field_id)")
            db.session.execute("CREATE INDEX IF NOT EXISTS ix_link_relation_tables ON link_relations(source_table_id, target_table_id)")
            print("✓ link_relations 表创建成功")
        
        if 'link_values' in existing_tables:
            print("✓ link_values 表已存在")
        else:
            print("创建 link_values 表...")
            db.session.execute("""
                CREATE TABLE IF NOT EXISTS link_values (
                    id VARCHAR(36) PRIMARY KEY,
                    link_relation_id VARCHAR(36) NOT NULL,
                    source_record_id VARCHAR(36) NOT NULL,
                    target_record_id VARCHAR(36) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (link_relation_id) REFERENCES link_relations(id) ON DELETE CASCADE,
                    FOREIGN KEY (source_record_id) REFERENCES records(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_record_id) REFERENCES records(id) ON DELETE CASCADE
                )
            """)
            
            # 创建索引
            db.session.execute("CREATE INDEX IF NOT EXISTS ix_link_value_relation ON link_values(link_relation_id)")
            db.session.execute("CREATE INDEX IF NOT EXISTS ix_link_value_source_record ON link_values(source_record_id)")
            db.session.execute("CREATE INDEX IF NOT EXISTS ix_link_value_target_record ON link_values(target_record_id)")
            db.session.execute("CREATE INDEX IF NOT EXISTS ix_link_value_source_target ON link_values(source_record_id, target_record_id)")
            db.session.execute("CREATE INDEX IF NOT EXISTS ix_link_value_relation_source ON link_values(link_relation_id, source_record_id)")
            db.session.execute("CREATE INDEX IF NOT EXISTS ix_link_value_relation_target ON link_values(link_relation_id, target_record_id)")
            print("✓ link_values 表创建成功")
        
        db.session.commit()
        print("\n✅ 关联字段表初始化完成！")

if __name__ == '__main__':
    init_link_tables()
