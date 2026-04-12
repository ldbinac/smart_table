"""
Base 分享服务模块
处理 Base 分享链接的创建、更新和访问逻辑
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from flask import current_app

from app.extensions import db
from app.models.base import Base, MemberRole
from app.models.base_share import BaseShare, SharePermission


class ShareService:
    """Base 分享服务类"""

    @staticmethod
    def create_share(base_id: str, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建 Base 分享链接
        
        Args:
            base_id: Base ID
            user_id: 创建者用户 ID
            data: 创建数据，包含 permission, expires_at
            
        Returns:
            包含操作结果的字典
        """
        # 验证必填字段
        permission_str = data.get('permission', 'view').strip().lower()
        if permission_str not in ['view', 'edit']:
            return {'success': False, 'error': '权限类型必须是 view 或 edit'}

        permission = SharePermission(permission_str)

        # 获取过期时间（可选）
        expires_at = data.get('expires_at')
        if expires_at is not None:
            try:
                expires_at = int(expires_at)
                # 验证过期时间不能是过去的时间
                if expires_at < int(datetime.now(timezone.utc).timestamp()):
                    return {'success': False, 'error': '过期时间不能是过去的时间'}
            except (ValueError, TypeError):
                return {'success': False, 'error': '过期时间必须是有效的 Unix 时间戳'}

        # 生成分享令牌
        share_token = str(uuid.uuid4())

        # 创建分享记录
        share = BaseShare(
            base_id=str(base_id),
            share_token=share_token,
            created_by=str(user_id),
            permission=permission,
            expires_at=expires_at
        )

        db.session.add(share)
        db.session.commit()

        current_app.logger.info(f'[ShareService] 创建分享链接：base={base_id}, created_by={user_id}')

        return {'success': True, 'share': share}

    @staticmethod
    def update_share(share_id: str, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新分享链接
        
        Args:
            share_id: 分享 ID
            user_id: 操作者用户 ID
            data: 更新数据，包含 is_active, permission, expires_at
            
        Returns:
            包含操作结果的字典
        """
        # 查找分享
        share = BaseShare.query.get(share_id)
        if not share:
            return {'success': False, 'error': '分享链接不存在', 'status': 404}

        # 更新字段
        if 'is_active' in data:
            share.is_active = bool(data['is_active'])

        if 'permission' in data:
            permission_str = data['permission'].strip().lower()
            if permission_str in ['view', 'edit']:
                share.permission = SharePermission(permission_str)
            else:
                return {'success': False, 'error': '权限类型必须是 view 或 edit'}

        if 'expires_at' in data:
            if data['expires_at'] is not None:
                try:
                    expires_at = int(data['expires_at'])
                    if expires_at < int(datetime.now(timezone.utc).timestamp()):
                        return {'success': False, 'error': '过期时间不能是过去的时间'}
                    share.expires_at = expires_at
                except (ValueError, TypeError):
                    return {'success': False, 'error': '过期时间必须是有效的 Unix 时间戳'}
            else:
                share.expires_at = None

        share.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        current_app.logger.info(f'[ShareService] 更新分享链接：share={share_id}, by={user_id}')

        return {'success': True, 'share': share}

    @staticmethod
    def delete_share(share_id: str, user_id: str) -> Dict[str, Any]:
        """
        删除分享链接
        
        Args:
            share_id: 分享 ID
            user_id: 操作者用户 ID
            
        Returns:
            包含操作结果的字典
        """
        share = BaseShare.query.get(share_id)
        if not share:
            return {'success': False, 'error': '分享链接不存在', 'status': 404}

        db.session.delete(share)
        db.session.commit()

        current_app.logger.info(f'[ShareService] 删除分享链接：share={share_id}, by={user_id}')

        return {'success': True}

    @staticmethod
    def access_share(share_token: str) -> Dict[str, Any]:
        """
        通过分享令牌访问 Base
        
        Args:
            share_token: 分享令牌
            
        Returns:
            包含操作结果的字典
        """
        # 查找分享
        share = BaseShare.query.filter_by(share_token=share_token).first()
        if not share:
            return {'success': False, 'error': '分享链接不存在', 'status': 404}

        # 检查分享是否激活
        if not share.is_active:
            return {'success': False, 'error': '该分享链接已失效', 'status': 403}

        # 检查是否过期
        if share.expires_at is not None:
            if int(datetime.now(timezone.utc).timestamp()) > share.expires_at:
                return {'success': False, 'error': '该分享链接已过期', 'status': 403}

        # 更新访问次数和最后访问时间
        share.access_count += 1
        share.last_accessed_at = datetime.now(timezone.utc)
        db.session.commit()

        # 获取 Base 信息
        base = Base.query.get(share.base_id)
        if not base:
            return {'success': False, 'error': '基础数据不存在', 'status': 404}

        return {
            'success': True,
            'base': base,
            'permission': share.permission.value,
            'share_token': share_token
        }

    @staticmethod
    def get_shares_by_base(base_id: str) -> List[BaseShare]:
        """
        获取 Base 的所有分享链接
        
        Args:
            base_id: Base ID
            
        Returns:
            分享链接列表
        """
        return BaseShare.query.filter_by(
            base_id=str(base_id)
        ).order_by(BaseShare.created_at.desc()).all()

    @staticmethod
    def get_shared_by_me(user_id: str) -> List[Dict[str, Any]]:
        """
        获取当前用户创建的所有分享（含 Base 信息）
        
        Args:
            user_id: 用户 ID
            
        Returns:
            分享列表（含 Base 信息）
        """
        shares = BaseShare.query.filter_by(
            created_by=str(user_id)
        ).order_by(BaseShare.created_at.desc()).all()

        if not shares:
            return []

        # 批量查询所有关联的 Base，避免 N+1 查询
        base_ids = list(set(share.base_id for share in shares))
        bases_map = {}
        if base_ids:
            bases = Base.query.filter(Base.id.in_(base_ids)).all()
            bases_map = {str(b.id): b for b in bases}

        shares_data = []
        for share in shares:
            base = bases_map.get(str(share.base_id))
            if base:
                share_data = share.to_dict()
                share_data['base'] = base.to_dict(include_stats=True)
                shares_data.append(share_data)

        return shares_data
