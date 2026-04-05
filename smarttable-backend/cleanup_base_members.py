"""
清理 base_members 表中的错误数据
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.base import BaseMember, MemberRole

def cleanup_base_members():
    """清理错误的成员关系数据"""
    app = create_app()
    
    with app.app_context():
        # 查找所有 role 字段不是有效枚举值的记录
        try:
            # 尝试查询所有成员关系
            all_members = BaseMember.query.all()
            print(f"✅ 当前共有 {len(all_members)} 条成员关系记录")
            
            # 检查每条记录
            for member in all_members:
                try:
                    # 尝试访问 role 字段，如果失败说明数据有问题
                    _ = member.role
                    print(f"  ✓ {member.base_id} - {member.user_id}: {member.role}")
                except LookupError as e:
                    print(f"  ❌ 发现错误记录：{member.base_id} - {member.user_id}")
                    # 删除错误记录
                    db.session.delete(member)
            
            db.session.commit()
            print("✅ 数据清理完成")
            
        except Exception as e:
            print(f"❌ 查询失败：{e}")
            # 如果无法查询，直接清空表
            print("⚠️  将清空 base_members 表")
            db.session.execute(db.text("DELETE FROM base_members"))
            db.session.commit()
            print("✅ 表已清空")

if __name__ == '__main__':
    cleanup_base_members()
