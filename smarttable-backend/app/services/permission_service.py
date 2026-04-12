"""
权限验证服务模块
提供 Base 访问权限验证，包括成员权限和分享链接权限
"""
from datetime import datetime, timezone
from typing import Optional, Tuple

from app.models.base import Base, BaseMember, MemberRole
from app.models.base_share import BaseShare, SharePermission
from app.utils.constants import ROLE_LEVELS


class PermissionService:
    """权限验证服务"""
    
    # 角色等级映射（引用公共常量）
    ROLE_LEVELS = ROLE_LEVELS
    
    @classmethod
    def get_user_role(cls, base_id: str, user_id: str) -> Optional[MemberRole]:
        """
        获取用户在 Base 中的角色
        
        Args:
            base_id: Base ID
            user_id: 用户 ID
            
        Returns:
            用户角色，如果用户不是成员则返回 None
        """
        base = Base.query.get(base_id)
        if not base:
            return None
        
        # 检查是否为所有者
        if str(base.owner_id) == str(user_id):
            return MemberRole.OWNER
        
        # 检查成员关系
        membership = BaseMember.query.filter_by(
            base_id=base_id,
            user_id=user_id
        ).first()
        
        if not membership:
            return None
        
        return membership.role
    
    @classmethod
    def check_permission(
        cls, 
        base_id: str, 
        user_id: str,
        min_role: MemberRole = MemberRole.VIEWER
    ) -> bool:
        """
        检查用户权限（基于成员关系）
        
        Args:
            base_id: Base ID
            user_id: 用户 ID
            min_role: 最低要求角色
            
        Returns:
            是否有权限
        """
        role = cls.get_user_role(base_id, user_id)
        
        if not role:
            return False
        
        user_level = cls.ROLE_LEVELS.get(role, -1)
        required_level = cls.ROLE_LEVELS.get(min_role, 0)
        
        return user_level >= required_level
    
    @classmethod
    def validate_share_token(
        cls, 
        share_token: str
    ) -> Tuple[bool, Optional[BaseShare], str]:
        """
        验证分享令牌
        
        Args:
            share_token: 分享令牌
            
        Returns:
            (是否有效，分享对象，错误消息)
        """
        share = BaseShare.query.filter_by(share_token=share_token).first()
        
        if not share:
            return False, None, '分享链接不存在'
        
        if not share.is_active:
            return False, share, '该分享链接已失效'
        
        if share.expires_at is not None:
            if int(datetime.now(timezone.utc).timestamp()) > share.expires_at:
                return False, share, '该分享链接已过期'
        
        return True, share, ''
    
    @classmethod
    def get_share_permission(
        cls, 
        base_id: str, 
        share_token: str
    ) -> Optional[SharePermission]:
        """
        获取分享链接的权限
        
        Args:
            base_id: Base ID
            share_token: 分享令牌
            
        Returns:
            分享权限，如果无效则返回 None
        """
        valid, share, _ = cls.validate_share_token(share_token)
        
        if not valid:
            return None
        
        if share.base_id != base_id:
            return None
        
        return share.permission
    
    @classmethod
    def increment_share_access(cls, share: BaseShare) -> None:
        """
        增加分享链接的访问次数
        
        Args:
            share: 分享对象
        """
        
        share.access_count += 1
        share.last_accessed_at = datetime.now(timezone.utc)
        db.session.commit()
    
    @classmethod
    def can_access_base(
        cls,
        base_id: str,
        user_id: Optional[str] = None,
        share_token: Optional[str] = None
    ) -> Tuple[bool, Optional[str], str]:
        """
        检查是否可以访问 Base（支持成员权限和分享链接）
        
        Args:
            base_id: Base ID
            user_id: 用户 ID（可选，未登录时为 None）
            share_token: 分享令牌（可选）
            
        Returns:
            (是否可以访问，访问权限级别，错误消息)
            权限级别：'owner', 'admin', 'editor', 'commenter', 'view', 'edit'
        """
        # 首先检查用户是否是成员
        if user_id:
            role = cls.get_user_role(base_id, user_id)
            if role:
                return True, role.value, ''
        
        # 然后检查分享链接
        if share_token:
            valid, share, error_msg = cls.validate_share_token(share_token)
            
            if not valid:
                return False, None, error_msg
            
            if share.base_id != base_id:
                return False, None, '分享链接与该 Base 不匹配'
            
            # 增加访问次数
            cls.increment_share_access(share)
            
            # 返回分享权限
            return True, share.permission.value, ''
        
        return False, None, '您没有权限访问此 Base'
    
    @classmethod
    def can_edit_base(
        cls,
        base_id: str,
        user_id: Optional[str] = None,
        share_token: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        检查是否可以编辑 Base
        
        Args:
            base_id: Base ID
            user_id: 用户 ID
            share_token: 分享令牌
            
        Returns:
            (是否可以编辑，错误消息)
        """
        can_access, permission, error_msg = cls.can_access_base(
            base_id, user_id, share_token
        )
        
        if not can_access:
            return False, error_msg
        
        # 检查是否有编辑权限
        edit_permissions = ['owner', 'admin', 'editor', 'edit']
        
        if permission in edit_permissions:
            return True, ''
        
        return False, '您没有编辑权限'
    
    @classmethod
    def can_manage_members(
        cls,
        base_id: str,
        user_id: str
    ) -> Tuple[bool, str]:
        """
        检查是否可以管理成员
        
        Args:
            base_id: Base ID
            user_id: 用户 ID
            
        Returns:
            (是否可以管理成员，错误消息)
        """
        role = cls.get_user_role(base_id, user_id)
        
        if not role:
            return False, '您不是该 Base 的成员'
        
        # 只有 owner 和 admin 可以管理成员
        if role in [MemberRole.OWNER, MemberRole.ADMIN]:
            return True, ''
        
        return False, '您没有权限管理成员'
