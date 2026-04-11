"""
基础数据服务模块
处理 Base（工作区/数据库）的 CRUD 操作和成员管理
"""
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

from sqlalchemy import or_

from app.extensions import db
from app.models.base import Base, BaseMember, MemberRole
from app.models.base_share import BaseShare, SharePermission
from app.models.user import User
from app.utils.constants import ROLE_LEVELS


class BaseService:
    """基础数据服务类"""
    
    # 角色权限等级映射（引用公共常量）
    ROLE_LEVELS = ROLE_LEVELS
    
    @staticmethod
    def get_all_bases(user_id: str) -> List[Base]:
        """
        获取用户的所有基础数据（包括拥有的和作为成员的）
        
        Args:
            user_id: 用户 ID
            
        Returns:
            基础数据列表
        """
        # 获取用户拥有的基础数据
        owned_bases = Base.query.filter_by(owner_id=user_id).all()
        
        # 获取用户作为成员的基础数据
        memberships = BaseMember.query.filter_by(user_id=user_id).all()
        member_base_ids = [m.base_id for m in memberships]
        member_bases = Base.query.filter(Base.id.in_(member_base_ids)).all() if member_base_ids else []
        
        # 合并并去重（以 id 为键）
        all_bases = {str(b.id): b for b in owned_bases}
        for b in member_bases:
            base_id = str(b.id)
            if base_id not in all_bases:
                all_bases[base_id] = b
        
        # 批量查询所有相关成员关系，避免 N+1 查询
        all_base_ids = list(all_bases.keys())
        all_memberships = BaseMember.query.filter(
            BaseMember.base_id.in_(all_base_ids),
            BaseMember.user_id == user_id
        ).all() if all_base_ids else []
        
        membership_map = {str(m.base_id): m for m in all_memberships}
        
        for base in all_bases.values():
            membership = membership_map.get(str(base.id))
            if membership:
                base.is_starred = membership.is_starred
            else:
                # 如果是拥有者但没有成员记录，创建一个
                if str(base.owner_id) == user_id:
                    base.is_starred = False
        
        return list(all_bases.values())
    
    @staticmethod
    def get_base(base_id: str) -> Optional[Base]:
        """
        获取单个基础数据
        
        Args:
            base_id: 基础数据 ID
            
        Returns:
            基础数据对象或 None
        """
        return Base.query.get(base_id)
    
    @staticmethod
    def create_base(data: Dict[str, Any], user_id: str) -> Base:
        """
        创建新基础数据
        
        Args:
            data: 创建数据，包含 name, description, icon, color 等
            user_id: 创建者用户 ID
            
        Returns:
            创建的基础数据对象
        """
        from flask import current_app
        
        base = Base(
            name=data.get('name', '未命名基础数据'),
            owner_id=user_id,
            description=data.get('description'),
            icon=data.get('icon'),
            color=data.get('color', '#6366F1'),
            is_personal=data.get('is_personal', False)
        )
        
        db.session.add(base)
        db.session.flush()  # 获取 base.id
        
        current_app.logger.info(f'[BaseService] 创建 Base: {base.id}, owner: {user_id}')
        
        # 创建成员关系（拥有者自动成为成员）
        from app.models.base import MemberRole
        membership = BaseMember(
            base_id=base.id,
            user_id=user_id,
            role=MemberRole.OWNER,
            is_starred=False
        )
        db.session.add(membership)
        
        current_app.logger.info(f'[BaseService] 创建成员关系：base={base.id}, user={user_id}, role=OWNER')
        
        db.session.commit()
        
        current_app.logger.info(f'[BaseService] Base 创建完成：{base.id}')
        
        return base
    
    @staticmethod
    def update_base(base_id: str, data: Dict[str, Any]) -> Optional[Base]:
        """
        更新基础数据
        
        Args:
            base_id: 基础数据 ID
            data: 更新数据
            
        Returns:
            更新后的基础数据对象，如果不存在返回 None
        """
        base = Base.query.get(base_id)
        if not base:
            return None
        
        # 允许更新的字段
        allowed_fields = ['name', 'description', 'icon', 'color', 'is_personal']
        
        for field in allowed_fields:
            if field in data:
                setattr(base, field, data[field])
        
        base.updated_at = datetime.utcnow()
        db.session.commit()
        
        return base
    
    @staticmethod
    def delete_base(base_id: str) -> bool:
        """
        删除基础数据（级联删除关联的表格、字段、记录等）
        
        Args:
            base_id: 基础数据 ID
            
        Returns:
            是否删除成功
        """
        base = Base.query.get(base_id)
        if not base:
            return False
        
        try:
            db.session.delete(base)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[BaseService] 删除 Base 失败：{base_id}, 错误：{str(e)}')
            return False
    
    @staticmethod
    def toggle_star(base_id: str, user_id: str) -> Optional[Base]:
        """
        切换基础数据的星标状态
        
        Args:
            base_id: 基础数据 ID
            user_id: 用户 ID
            
        Returns:
            更新后的基础数据对象
        """
        base = Base.query.get(base_id)
        if not base:
            return None
        
        # 查找或创建成员关系
        membership = BaseMember.query.filter_by(
            base_id=base_id,
            user_id=user_id
        ).first()
        
        if membership:
            # 切换收藏状态
            membership.is_starred = not membership.is_starred
        else:
            # 创建新的成员关系（如果是拥有者）
            if str(base.owner_id) == user_id:
                membership = BaseMember(
                    base_id=base_id,
                    user_id=user_id,
                    role=MemberRole.OWNER,
                    is_starred=True
                )
                db.session.add(membership)
            else:
                return None
        
        db.session.commit()
        base.is_starred = membership.is_starred
        return base
    
    @staticmethod
    def get_members(base_id: str) -> List[Dict[str, Any]]:
        """
        获取基础数据的所有成员
        
        Args:
            base_id: 基础数据 ID
            
        Returns:
            成员列表（包含用户信息）
        """
        memberships = BaseMember.query.filter_by(base_id=base_id).all()
        
        members = []
        for membership in memberships:
            member_data = membership.to_dict(include_user=True)
            members.append(member_data)
        
        return members
    
    @staticmethod
    def add_member(base_id: str, email: str, role: str, invited_by: str) -> Dict[str, Any]:
        """
        添加成员到基础数据
        
        Args:
            base_id: 基础数据 ID
            email: 被邀请用户邮箱
            role: 角色（owner/admin/editor/commenter/viewer）
            invited_by: 邀请人用户 ID
            
        Returns:
            包含操作结果的字典
        """
        # 查找用户
        user = User.query.filter_by(email=email.lower()).first()
        if not user:
            return {'success': False, 'error': '用户不存在'}
        
        # 检查是否已经是成员
        existing = BaseMember.query.filter_by(
            base_id=base_id,
            user_id=user.id
        ).first()
        
        if existing:
            return {'success': False, 'error': '该用户已经是成员'}
        
        # 检查是否是基础数据所有者
        base = Base.query.get(base_id)
        if base and str(base.owner_id) == str(user.id):
            return {'success': False, 'error': '所有者是基础数据的拥有者，不能添加为成员'}
        
        # 验证角色
        try:
            member_role = MemberRole(role.lower())
        except ValueError:
            return {'success': False, 'error': '无效的角色类型'}
        
        # 创建成员关系
        membership = BaseMember(
            base_id=base_id,
            user_id=user.id,
            role=member_role,
            invited_by=invited_by
        )
        
        db.session.add(membership)
        db.session.commit()
        
        return {
            'success': True,
            'member': membership.to_dict(include_user=True)
        }
    
    @staticmethod
    def remove_member(base_id: str, user_id: str) -> bool:
        """
        从基础数据中移除成员
        
        Args:
            base_id: 基础数据 ID
            user_id: 要移除的用户 ID
            
        Returns:
            是否移除成功
        """
        membership = BaseMember.query.filter_by(
            base_id=base_id,
            user_id=user_id
        ).first()
        
        if not membership:
            return False
        
        try:
            db.session.delete(membership)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def update_member_role(base_id: str, user_id: str, new_role: str) -> Dict[str, Any]:
        """
        更新成员角色
        
        Args:
            base_id: 基础数据 ID
            user_id: 用户 ID
            new_role: 新角色
            
        Returns:
            包含操作结果的字典
        """
        membership = BaseMember.query.filter_by(
            base_id=base_id,
            user_id=user_id
        ).first()
        
        if not membership:
            return {'success': False, 'error': '成员不存在'}
        
        try:
            member_role = MemberRole(new_role.lower())
        except ValueError:
            return {'success': False, 'error': '无效的角色类型'}
        
        membership.role = member_role
        db.session.commit()
        
        return {
            'success': True,
            'member': membership.to_dict(include_user=True)
        }
    
    @classmethod
    def check_permission(cls, base_id: str, user_id: str, 
                         min_role: MemberRole = MemberRole.VIEWER) -> bool:
        """
        检查用户权限
        
        Args:
            base_id: 基础数据 ID
            user_id: 用户 ID
            min_role: 最低要求角色（默认为 VIEWER）
            
        Returns:
            是否有权限
        """
        from flask import current_app
        
        base = Base.query.get(base_id)
        
        if not base:
            current_app.logger.error(f'[BaseService] Base 不存在：{base_id}')
            return False
        
        current_app.logger.info(f'[BaseService] 检查权限：base={base_id}, user={user_id}, owner={base.owner_id}')
        
        # 检查是否为所有者
        if str(base.owner_id) == str(user_id):
            current_app.logger.info(f'[BaseService] 用户是所有者，有权限')
            return True
        
        current_app.logger.info(f'[BaseService] 用户不是所有者，检查成员关系...')
        
        # 检查成员权限
        membership = BaseMember.query.filter_by(
            base_id=base_id,
            user_id=user_id
        ).first()
        
        if not membership:
            current_app.logger.error(f'[BaseService] 用户不是成员，无权限')
            return False
        
        user_role_level = cls.ROLE_LEVELS.get(membership.role, -1)
        required_role_level = cls.ROLE_LEVELS.get(min_role, 0)
        
        current_app.logger.info(f'[BaseService] 用户角色：{membership.role} (level={user_role_level}), 需要：{min_role} (level={required_role_level})')
        
        has_permission = user_role_level >= required_role_level
        
        if has_permission:
            current_app.logger.info(f'[BaseService] 权限检查通过')
        else:
            current_app.logger.error(f'[BaseService] 权限不足')
        
        return has_permission
    
    @classmethod
    def get_user_role(cls, base_id: str, user_id: str) -> Optional[MemberRole]:
        """
        获取用户在基础数据中的角色
        
        Args:
            base_id: 基础数据 ID
            user_id: 用户 ID
            
        Returns:
            用户角色，如果不是成员则返回 None
        """
        base = Base.query.get(base_id)
        
        if not base:
            return None
        
        # 检查是否为所有者
        if str(base.owner_id) == str(user_id):
            return MemberRole.OWNER
        
        # 检查成员权限
        membership = BaseMember.query.filter_by(
            base_id=base_id,
            user_id=user_id
        ).first()
        
        if membership:
            return membership.role
        
        return None
    
    @classmethod
    def require_permission(cls, min_role: MemberRole = MemberRole.VIEWER):
        """
        权限检查装饰器工厂
        
        Args:
            min_role: 最低要求角色
            
        Returns:
            装饰器函数
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # 这里需要结合 Flask 的 g 对象使用
                # 实际使用在路由层处理
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def check_permission_for_table(table_id: str, user_id: str, min_role: MemberRole) -> bool:
        """
        检查用户对表格的权限
        
        Args:
            table_id: 表格 ID
            user_id: 用户 ID
            min_role: 最低要求角色
            
        Returns:
            是否有权限
        """
        from app.models.table import Table
        
        table = Table.query.get(table_id)
        if not table:
            return False
        
        return BaseService.check_permission(str(table.base_id), user_id, min_role)

    @staticmethod
    def verify_share_token_and_add_member(base_id: str, user_id: str, share_token: str) -> Dict[str, Any]:
        """
        验证分享令牌并自动添加用户为 Base 成员
        
        Args:
            base_id: Base ID
            user_id: 用户 ID
            share_token: 分享令牌
            
        Returns:
            包含验证结果和角色信息的字典
        """
        from flask import current_app
        
        current_app.logger.info(f'[BaseService] 验证分享令牌：base={base_id}, user={user_id}')
        
        # 查找分享记录
        share = BaseShare.query.filter_by(share_token=share_token, base_id=base_id).first()
        
        if not share:
            current_app.logger.error(f'[BaseService] 分享令牌不存在')
            return {'success': False, 'error': '分享令牌不存在'}
        
        # 检查分享是否激活
        if not share.is_active:
            current_app.logger.error(f'[BaseService] 分享链接已失效')
            return {'success': False, 'error': '分享链接已失效'}
        
        # 检查是否过期
        if share.expires_at is not None:
            if int(datetime.utcnow().timestamp()) > share.expires_at:
                current_app.logger.error(f'[BaseService] 分享链接已过期')
                return {'success': False, 'error': '分享链接已过期'}
        
        # 检查用户是否已经是成员
        existing = BaseMember.query.filter_by(base_id=base_id, user_id=user_id).first()
        if existing:
            current_app.logger.info(f'[BaseService] 用户已是成员，角色：{existing.role}')
            return {'success': True, 'role': existing.role}
        
        # 根据分享权限确定角色
        # 分享权限 view -> VIEWER, edit -> EDITOR
        if share.permission == SharePermission.EDIT:
            member_role = MemberRole.EDITOR
        else:
            member_role = MemberRole.VIEWER
        
        # 创建成员关系
        membership = BaseMember(
            base_id=base_id,
            user_id=user_id,
            role=member_role,
            invited_by=share.created_by
        )
        
        db.session.add(membership)
        db.session.commit()
        
        current_app.logger.info(f'[BaseService] 已通过分享链接添加成员：base={base_id}, user={user_id}, role={member_role}')
        
        return {'success': True, 'role': member_role}
