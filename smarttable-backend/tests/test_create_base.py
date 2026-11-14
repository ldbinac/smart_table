"""
测试创建 Base 时是否自动创建成员关系
"""
from app import db
from app.models.base import Base, BaseMember, MemberRole


def test_create_base(app, test_user):
    """测试创建 Base"""
    # 使用 conftest 提供的 fixture：app 已配置 SQLite 内存库 + create_all
    # test_user 已在 users 表中创建
    
    # 创建 Base
    base = Base(
        name='测试 Base',
        owner_id=test_user.id,
        description='测试描述',
        icon='📊',
        color='#409EFF',
        is_personal=False
    )
    
    db.session.add(base)
    db.session.flush()  # 获取 base.id
    
    # 创建成员关系（使用 MemberRole Enum 确保 SQLite adapter 兼容）
    membership = BaseMember(
        base_id=base.id,
        user_id=test_user.id,
        role=MemberRole.OWNER,
        is_starred=False
    )
    db.session.add(membership)
    
    db.session.commit()
    
    # 验证成员关系是否存在
    member = BaseMember.query.filter_by(
        base_id=base.id,
        user_id=test_user.id
    ).first()
    
    assert member is not None, "验证失败：成员关系未找到"
    assert member.role == MemberRole.OWNER
