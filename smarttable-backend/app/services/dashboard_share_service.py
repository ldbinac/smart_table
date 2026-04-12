"""
仪表盘分享服务模块
"""
from typing import List, Optional, Dict, Any
import uuid
import secrets
import string
from datetime import datetime, timezone

from app.extensions import db
from app.models.dashboard_share import DashboardShare, SharePermission


class DashboardShareService:
    """仪表盘分享服务类"""
    
    @staticmethod
    def generate_share_token() -> str:
        """生成随机分享令牌"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def generate_access_code() -> str:
        """生成 6 位数字访问密码"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    @staticmethod
    def create_share(
        dashboard_id: str,
        user_id: str,
        require_access_code: bool = False,
        expires_in_hours: Optional[int] = None,
        max_access_count: Optional[int] = None,
        permission: str = 'view'
    ) -> DashboardShare:
        """
        创建分享链接
        
        参数:
            dashboard_id: 仪表盘 ID
            user_id: 创建用户 ID
            require_access_code: 是否需要访问密码
            expires_in_hours: 过期时间（小时）
            max_access_count: 最大访问次数
            permission: 分享权限（view/edit）
            
        返回:
            创建的分享对象
        """
        # 生成分享令牌
        share_token = DashboardShareService.generate_share_token()
        
        # 生成访问密码（如果需要）
        access_code = DashboardShareService.generate_access_code() if require_access_code else None
        
        # 计算过期时间
        expires_at = None
        if expires_in_hours:
            expires_at = int((datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)).timestamp())
        
        # 创建分享对象
        share = DashboardShare(
            dashboard_id=dashboard_id,
            share_token=share_token,
            access_code=access_code,
            expires_at=expires_at,
            max_access_count=max_access_count,
            current_access_count=0,
            is_active=True,
            permission=SharePermission(permission),
            created_by=user_id
        )
        
        db.session.add(share)
        db.session.commit()
        
        return share
    
    @staticmethod
    def get_share_by_token(token: str) -> Optional[DashboardShare]:
        """
        通过分享令牌获取分享信息
        
        参数:
            token: 分享令牌
            
        返回:
            分享对象或 None
        """
        return DashboardShare.query.filter_by(share_token=token).first()
    
    @staticmethod
    def get_shares_by_dashboard(dashboard_id: str) -> List[DashboardShare]:
        """
        获取仪表盘的所有分享链接
        
        参数:
            dashboard_id: 仪表盘 ID
            
        返回:
            分享列表
        """
        return DashboardShare.query.filter_by(
            dashboard_id=dashboard_id,
            is_active=True
        ).order_by(DashboardShare.created_at.desc()).all()
    
    @staticmethod
    def validate_share(
        token: str,
        access_code: Optional[str] = None
    ) -> tuple[bool, Optional[DashboardShare], Optional[str]]:
        """
        验证分享链接是否有效
        
        参数:
            token: 分享令牌
            access_code: 访问密码
            
        返回:
            (是否有效，分享对象，错误信息)
        """
        share = DashboardShareService.get_share_by_token(token)
        
        if not share:
            return False, None, '分享链接不存在'
        
        if not share.is_active:
            return False, share, '分享链接已被禁用'
        
        # 检查是否过期
        if share.expires_at and datetime.now(timezone.utc).timestamp() > share.expires_at:
            return False, share, '分享链接已过期'
        
        # 检查访问次数
        if share.max_access_count and share.current_access_count >= share.max_access_count:
            return False, share, '分享链接访问次数已达上限'
        
        # 验证访问密码（使用时间安全比较防止时序攻击）
        if share.access_code and not secrets.compare_digest(share.access_code, access_code or ''):
            return False, share, '访问密码错误'
        
        return True, share, None
    
    @staticmethod
    def record_access(share_id: str) -> bool:
        """
        记录访问
        
        参数:
            share_id: 分享 ID
            
        返回:
            是否成功
        """
        share = DashboardShare.query.get(share_id)
        if not share:
            return False
        
        share.current_access_count += 1
        share.last_accessed_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return True
    
    @staticmethod
    def deactivate_share(share_id: str) -> bool:
        """
        禁用分享链接
        
        参数:
            share_id: 分享 ID
            
        返回:
            是否成功
        """
        share = DashboardShare.query.get(share_id)
        if not share:
            return False
        
        share.is_active = False
        db.session.commit()
        
        return True
    
    @staticmethod
    def delete_share(share_id: str) -> bool:
        """
        删除分享链接
        
        参数:
            share_id: 分享 ID
            
        返回:
            是否成功
        """
        share = DashboardShare.query.get(share_id)
        if not share:
            return False
        
        db.session.delete(share)
        db.session.commit()
        
        return True
    
    @staticmethod
    def cleanup_expired_shares() -> int:
        """
        清理过期的分享链接
        
        返回:
            清理的数量
        """
        now = int(datetime.now(timezone.utc).timestamp())
        expired_shares = DashboardShare.query.filter(
            DashboardShare.is_active == True,
            DashboardShare.expires_at != None,
            DashboardShare.expires_at < now
        ).all()
        
        count = 0
        for share in expired_shares:
            share.is_active = False
            count += 1
        
        if count > 0:
            db.session.commit()
        
        return count
