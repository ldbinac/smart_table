"""
数据表分享服务模块
处理表级分享链接的创建、更新、访问与权限判定逻辑
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

from flask import current_app

from app.extensions import db
from app.models.base import BaseMember, MemberRole
from app.models.table import Table
from app.models.view import View
from app.models.field import Field
from app.models.user import User
from app.models.table_share import TableShare, TableShareMember, TableSharePermission
from app.services.permission_service import PermissionService

class TableShareServiceGroup01Mixin:
    """Mixin auto-split"""
    
    """数据表分享服务类"""
    
    VALID_PERMISSIONS = ('editor', 'commenter', 'viewer')
    
    VALID_VIEW_SCOPES = ('all', 'specified')
    
    PERMISSION_RANK = {'viewer': 0, 'commenter': 1, 'editor': 2}
    
    
    @staticmethod
    def _parse_expires_at(value: Any) -> Tuple[Optional[str], Optional[int]]:
        """
        解析过期时间（毫秒时间戳自动转秒，校验不能是过去时间）
    
        Returns:
            (错误 key, 归一化后的秒级时间戳)；无错误时错误 key 为 None
        """
        if value is None:
            return None, None
        try:
            expires_at = int(value)
            # 前端可能发送毫秒级时间戳（JavaScript Date.now()），自动转换为秒
            if expires_at > 10**11:
                expires_at = expires_at // 1000
            # 验证过期时间不能是过去的时间
            if expires_at < int(datetime.now(timezone.utc).timestamp()):
                return 'expiry_time_past', None
            return None, expires_at
        except (ValueError, TypeError):
            return 'expiry_time_valid_unix_timestamp', None
    
    @staticmethod
    def _permission_value(share: TableShare) -> str:
        """读取分享权限的字符串值"""
        return share.permission.value if hasattr(share.permission, 'value') else str(share.permission)
    
    @staticmethod
    def _get_valid_share(share_token: str) -> Tuple[Optional[TableShare], Optional[Dict[str, Any]]]:
        """
        校验分享令牌的有效性（存在/激活/未过期）
    
        Returns:
            (分享对象, 错误字典)；有效时错误字典为 None
        """
        share = TableShare.query.filter_by(share_token=share_token).first()
        if not share:
            return None, {'error': 'share_link_does_not_exist', 'status': 404}
    
        if not share.is_active:
            return None, {'error': 'share_link_been_invalidated', 'status': 403}
    
        if share.expires_at is not None:
            if int(datetime.now(timezone.utc).timestamp()) > share.expires_at:
                return None, {'error': 'share_link_expired_2', 'status': 403}
    
        return share, None
    
    @staticmethod
    def _visible_views_for_share(share: TableShare) -> List[View]:
        """获取指定分享可见的视图列表（保持视图原排序）"""
        views = View.query.filter_by(table_id=share.table_id).order_by(View.order.asc()).all()
        if share.view_scope == 'specified':
            wanted = {str(v) for v in (share.view_ids or [])}
            views = [view for view in views if str(view.id) in wanted]
        return views
    
    @staticmethod
    def _validate_view_selection(table_id: str, view_scope: str, view_ids: Any,
                                 allow_empty_ids: bool = False) -> Optional[str]:
        """
        校验 view_scope 与 view_ids 的合法性
    
        Returns:
            错误 key，无错误时返回 None
        """
        if view_scope not in TableShareService.VALID_VIEW_SCOPES:
            return 'invalid_view_selection'
    
        if view_scope == 'specified':
            if not isinstance(view_ids, list) or (not allow_empty_ids and not view_ids):
                return 'invalid_view_selection'
            if view_ids:
                valid_ids = {
                    str(v.id) for v in View.query.filter_by(table_id=table_id).all()
                }
                for view_id in view_ids:
                    if str(view_id) not in valid_ids:
                        return 'invalid_view_selection'
        return None
    
    @staticmethod
    def create_share(table_id: str, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建数据表分享链接
    
        Args:
            table_id: 数据表 ID
            user_id: 创建者用户 ID
            data: 创建数据，包含 permission, view_scope, view_ids, expires_at
    
        Returns:
            包含操作结果的字典
        """
        table = Table.query.filter_by(id=table_id).first()
        if not table:
            return {'success': False, 'error': 'table_does_not_exist', 'status': 404}
    
        # 验证分享权限
        permission_str = str(data.get('permission', 'viewer')).strip().lower()
        if permission_str not in TableShareService.VALID_PERMISSIONS:
            return {'success': False, 'error': 'invalid_share_permission'}
    
        # 验证视图范围
        view_scope = str(data.get('view_scope', 'all')).strip().lower()
        view_ids = data.get('view_ids')
        error = TableShareService._validate_view_selection(str(table_id), view_scope, view_ids)
        if error:
            return {'success': False, 'error': error}
    
        # 获取过期时间（可选）
        error, expires_at = TableShareService._parse_expires_at(data.get('expires_at'))
        if error:
            return {'success': False, 'error': error}
    
        # 生成分享令牌
        share_token = str(uuid.uuid4())
    
        share = TableShare(
            table_id=str(table_id),
            share_token=share_token,
            created_by=str(user_id),
            permission=TableSharePermission(permission_str),
            view_scope=view_scope,
            view_ids=view_ids if view_scope == 'specified' else None,
            expires_at=expires_at
        )
    
        db.session.add(share)
        db.session.commit()
    
        current_app.logger.info(
            f'[TableShareService] 创建表分享链接：table={table_id}, created_by={user_id}'
        )
    
        return {'success': True, 'share': share}
    
    @staticmethod
    def update_share(share_id: str, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新分享链接
    
        Args:
            share_id: 分享 ID
            user_id: 操作者用户 ID
            data: 更新数据，包含 permission, view_scope, view_ids, is_active, expires_at
    
        Returns:
            包含操作结果的字典
        """
        # 使用 filter_by 替代 query.get 以兼容 CompatUUID 类型
        share = TableShare.query.filter_by(id=share_id).first()
        if not share:
            return {'success': False, 'error': 'share_link_does_not_exist', 'status': 404}
    
        if 'is_active' in data:
            share.is_active = bool(data['is_active'])
    
        if 'permission' in data:
            permission_str = str(data['permission']).strip().lower()
            if permission_str in TableShareService.VALID_PERMISSIONS:
                share.permission = TableSharePermission(permission_str)
            else:
                return {'success': False, 'error': 'invalid_share_permission'}
    
        # 视图范围/视图列表：合并现有值后统一校验
        if 'view_scope' in data or 'view_ids' in data:
            view_scope = str(data.get('view_scope', share.view_scope)).strip().lower()
            view_ids = data.get('view_ids', share.view_ids)
            error = TableShareService._validate_view_selection(
                str(share.table_id), view_scope, view_ids
            )
            if error:
                return {'success': False, 'error': error}
            share.view_scope = view_scope
            share.view_ids = view_ids if view_scope == 'specified' else None
    
        if 'expires_at' in data:
            if data['expires_at'] is None:
                share.expires_at = None
            else:
                error, expires_at = TableShareService._parse_expires_at(data['expires_at'])
                if error:
                    return {'success': False, 'error': error}
                share.expires_at = expires_at
    
        db.session.commit()
    
        current_app.logger.info(f'[TableShareService] 更新表分享链接：share={share_id}, by={user_id}')
    
        return {'success': True, 'share': share}
    
    @staticmethod
    def delete_share(share_id: str) -> Dict[str, Any]:
        """
        删除分享链接（级联删除成员记录）
    
        Args:
            share_id: 分享 ID
    
        Returns:
            包含操作结果的字典
        """
        # 使用 filter_by 替代 query.get 以兼容 CompatUUID 类型
        share = TableShare.query.filter_by(id=share_id).first()
        if not share:
            return {'success': False, 'error': 'share_link_does_not_exist', 'status': 404}
    
        # 显式删除成员记录，避免 SQLite 未启用外键时残留
        TableShareMember.query.filter_by(share_id=share.id).delete()
        db.session.delete(share)
        db.session.commit()
    
        current_app.logger.info(f'[TableShareService] 删除表分享链接：share={share_id}')
    
        return {'success': True}
    
    @staticmethod
    def get_shares_by_table(table_id: str) -> List[TableShare]:
        """
        获取数据表的所有分享链接
    
        Args:
            table_id: 数据表 ID
    
        Returns:
            分享链接列表
        """
        return TableShare.query.filter_by(
            table_id=str(table_id)
        ).order_by(TableShare.created_at.desc()).all()
    
    @staticmethod
    def get_share_members(share_id: str) -> List[Dict[str, Any]]:
        """
        获取分享的成员列表（关联用户信息）
    
        Args:
            share_id: 分享 ID
    
        Returns:
            成员列表，每项含 user_id, joined_at, user
        """
        rows = (
            db.session.query(TableShareMember, User)
            .join(User, TableShareMember.user_id == User.id)
            .filter(TableShareMember.share_id == str(share_id))
            .order_by(TableShareMember.joined_at.asc())
            .all()
        )
    
        return [
            {
                'user_id': str(member.user_id),
                'joined_at': member.joined_at.isoformat() if member.joined_at else None,
                'user': {
                    'id': str(user.id),
                    'name': user.name,
                    'avatar': user.avatar,
                    'email': user.email
                }
            }
            for member, user in rows
        ]
    
    @staticmethod
    def remove_share_member(share_id: str, target_user_id: str,
                            operator_id: str) -> Dict[str, Any]:
        """
        将用户从表分享成员中移除（回收其对该表的分享访问权限）
    
        Args:
            share_id: 分享 ID
            target_user_id: 被移除的用户 ID
            operator_id: 操作者用户 ID（不能与被移除者相同）
    
        Returns:
            包含操作结果的字典
        """
        share = TableShare.query.filter_by(id=str(share_id)).first()
        if not share:
            return {'success': False, 'error': 'share_link_does_not_exist', 'status': 404}
    
        # 不能移除自己（创建者/管理员自身的访问不通过表分享授予）
        if str(target_user_id) == str(operator_id):
            return {
                'success': False,
                'error': 'table_share_member_cannot_remove_yourself',
                'status': 400
            }
    
        member = TableShareMember.query.filter_by(
            share_id=share.id, user_id=str(target_user_id)
        ).first()
        if not member:
            return {
                'success': False,
                'error': 'table_share_member_does_not_exist',
                'status': 404
            }
    
        db.session.delete(member)
        db.session.commit()
    
        current_app.logger.info(
            f'[TableShareService] 移除表分享成员：share={share_id}, '
            f'user={target_user_id}, by={operator_id}'
        )
    
        return {'success': True}
    
    @staticmethod
    def access_share(share_token: str) -> Dict[str, Any]:
        """
        通过分享令牌访问数据表（公开，无需登录）
    
        Args:
            share_token: 分享令牌
    
        Returns:
            包含操作结果的字典
        """
        share, error = TableShareService._get_valid_share(share_token)
        if error:
            return {'success': False, **error}
    
        # 更新访问次数和最后访问时间
        share.access_count += 1
        share.last_accessed_at = datetime.now(timezone.utc)
        db.session.commit()
    
        # 获取数据表信息
        table = Table.query.filter_by(id=share.table_id).first()
        if not table:
            return {'success': False, 'error': 'table_does_not_exist', 'status': 404}
    
        # 获取 Base 信息
        base = table.base
        if base is None:
            return {'success': False, 'error': 'base_does_not_exist_2', 'status': 404}
    
        # 该分享可见的视图列表
        views = TableShareService._visible_views_for_share(share)
    
        return {
            'success': True,
            'share': share,
            'table': table,
            'base': base,
            'views': views
        }
    
    @staticmethod
    def join_share(share_token: str, user_id: str) -> Dict[str, Any]:
        """
        通过分享令牌加入数据表（需登录）
    
        已是 Base 成员的用户直接放行（不受限）；否则记录为表分享成员（幂等）。
    
        Args:
            share_token: 分享令牌
            user_id: 用户 ID
    
        Returns:
            包含操作结果的字典
        """
        share, error = TableShareService._get_valid_share(share_token)
        if error:
            return {'success': False, **error}
    
        table = Table.query.filter_by(id=share.table_id).first()
        if not table:
            return {'success': False, 'error': 'table_does_not_exist', 'status': 404}
    
        # 已是 Base 成员：不受限，跟随成员角色
        membership = BaseMember.query.filter_by(
            base_id=str(table.base_id), user_id=str(user_id)
        ).first()
        if membership:
            role = membership.role.value if hasattr(membership.role, 'value') else str(membership.role)
            return {'success': True, 'restricted': False, 'role': role}
    
        # 幂等：已存在的表分享成员不重复创建
        existing = TableShareMember.query.filter_by(
            share_id=share.id, user_id=str(user_id)
        ).first()
        if not existing:
            member = TableShareMember(share_id=share.id, user_id=str(user_id))
            db.session.add(member)
            db.session.commit()
            current_app.logger.info(
                f'[TableShareService] 用户通过表分享加入：table={table.id}, user={user_id}'
            )
    
        return {
            'success': True,
            'restricted': True,
            'role': TableShareService._permission_value(share),
            'table_id': str(table.id),
            'base_id': str(table.base_id),
            'view_scope': share.view_scope,
            'view_ids': share.view_ids or []
        }
    
    @staticmethod
    def get_members_role(table_id: str, user_id: str) -> Optional[str]:
        """
        查询用户是否通过表分享可访问该表，命中返回分享权限值
    
        多条分享命中时取权限最高者（editor > commenter > viewer）。
    
        Args:
            table_id: 数据表 ID
            user_id: 用户 ID
    
        Returns:
            分享权限值（editor/commenter/viewer），未命中返回 None
        """
        shares = (
            TableShare.query
            .join(TableShareMember, TableShareMember.share_id == TableShare.id)
            .filter(
                TableShare.table_id == str(table_id),
                TableShareMember.user_id == str(user_id),
                TableShare.is_active.is_(True)
            )
            .all()
        )
    
        now_ts = int(datetime.now(timezone.utc).timestamp())
        best: Optional[str] = None
        best_rank = -1
        for share in shares:
            if share.expires_at is not None and now_ts > share.expires_at:
                continue
            permission = TableShareService._permission_value(share)
            rank = TableShareService.PERMISSION_RANK.get(permission, -1)
            if rank > best_rank:
                best_rank = rank
                best = permission
    
        return best
    
    @staticmethod
    def get_members_role_by_field(field_id: str, user_id: str) -> Optional[str]:
        """get_members_role 的字段维度版本（供字段路由使用）"""
        field = Field.query.filter_by(id=field_id).first()
        if not field:
            return None
        return TableShareService.get_members_role(str(field.table_id), str(user_id))
    
    @staticmethod
    def get_shared_table_ids(base_id: str, user_id: str) -> List[str]:
        """
        获取用户在指定 Base 内通过表分享可访问的数据表 ID 列表
    
        Args:
            base_id: Base ID
            user_id: 用户 ID
    
        Returns:
            数据表 ID 列表
        """
        rows = (
            db.session.query(TableShare.table_id)
            .join(TableShareMember, TableShareMember.share_id == TableShare.id)
            .join(Table, Table.id == TableShare.table_id)
            .filter(
                Table.base_id == str(base_id),
                TableShareMember.user_id == str(user_id),
                TableShare.is_active.is_(True)
            )
            .distinct()
            .all()
        )
        return [str(row[0]) for row in rows]
    
    @staticmethod
    def is_share_only_user(base_id: str, user_id: str) -> bool:
        """
        判断用户是否为"纯表分享用户"：不在 Base 成员中，但通过表分享可访问部分数据表
    
        Args:
            base_id: Base ID
            user_id: 用户 ID
    
        Returns:
            是否为纯表分享用户
        """
        membership = BaseMember.query.filter_by(
            base_id=str(base_id), user_id=str(user_id)
        ).first()
        if membership:
            return False
        return bool(TableShareService.get_shared_table_ids(str(base_id), str(user_id)))
    
    @staticmethod
    def can_view_table(table_id: str, user_id: str) -> bool:
        """
        读权限判定：Base 成员（原有逻辑）或表分享成员（含过期校验）均可放行
        """
        table = Table.query.filter_by(id=table_id).first()
        if not table:
            return False
        if PermissionService.check_permission(str(table.base_id), str(user_id), MemberRole.VIEWER):
            return True
        return TableShareService.get_members_role(str(table_id), str(user_id)) is not None
    
    @staticmethod
    def can_edit_table(table_id: str, user_id: str) -> bool:
        """
        写权限判定：Base 成员需 ≥EDITOR（原有逻辑）；纯表分享用户仅 editor 角色可放行
        """
        table = Table.query.filter_by(id=table_id).first()
        if not table:
            return False
        if PermissionService.check_permission(str(table.base_id), str(user_id), MemberRole.EDITOR):
            return True
        return TableShareService.get_members_role(str(table_id), str(user_id)) == 'editor'
    
    @staticmethod
    def get_accessible_views(table_id: str, user_id: str) -> Optional[List[View]]:
        """
        获取用户通过表分享可见的视图列表（保持视图原排序）
    
        任一命中分享的 view_scope 为 all 时返回全部视图；
        否则取所有 specified 分享可见视图的并集。
    
        Args:
            table_id: 数据表 ID
            user_id: 用户 ID
    
        Returns:
            视图列表；用户无表分享权限时返回 None
        """
        if TableShareService.get_members_role(str(table_id), str(user_id)) is None:
            return None
    
        shares = (
            TableShare.query
            .join(TableShareMember, TableShareMember.share_id == TableShare.id)
            .filter(
                TableShare.table_id == str(table_id),
                TableShareMember.user_id == str(user_id),
                TableShare.is_active.is_(True)
            )
            .all()
        )
    
        views = View.query.filter_by(table_id=str(table_id)).order_by(View.order.asc()).all()
    
        if any(share.view_scope == 'all' for share in shares):
            return views
    
        wanted = set()
        for share in shares:
            if share.expires_at is not None:
                now_ts = int(datetime.now(timezone.utc).timestamp())
                if now_ts > share.expires_at:
                    continue
            for view_id in (share.view_ids or []):
                wanted.add(str(view_id))
    
        return [view for view in views if str(view.id) in wanted]
    
