"""
测试创建 Base 时是否自动创建成员关系
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.base import Base, BaseMember
from app.models.user import User

def test_create_base():
    """测试创建 Base"""
    app = create_app()
    
    with app.app_context():
        # 获取第一个用户
        user = User.query.first()
        if not user:
            print("❌ 没有找到用户")
            return
        
        print(f"✅ 使用用户：{user.email} (ID: {user.id})")
        
        # 创建 Base
        base = Base(
            name='测试 Base',
            owner_id=user.id,
            description='测试描述',
            icon='📊',
            color='#409EFF',
            is_personal=False
        )
        
        db.session.add(base)
        db.session.flush()  # 获取 base.id
        
        print(f"✅ 创建 Base: {base.name} (ID: {base.id})")
        
        # 创建成员关系
        membership = BaseMember(
            base_id=base.id,
            user_id=user.id,
            role='owner',
            is_starred=False
        )
        db.session.add(membership)
        
        db.session.commit()
        
        print(f"✅ 创建成员关系：{membership.role}")
        
        # 验证成员关系是否存在
        member = BaseMember.query.filter_by(
            base_id=base.id,
            user_id=user.id
        ).first()
        
        if member:
            print(f"✅ 验证成功：成员关系已创建 (role={member.role})")
        else:
            print("❌ 验证失败：成员关系未找到")
        
        # 清理测试数据
        db.session.delete(member)
        db.session.delete(base)
        db.session.commit()
        print("✅ 测试数据已清理")

if __name__ == '__main__':
    test_create_base()
