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

class TableShareServiceGroup02Mixin:
    """Mixin auto-split"""
    
    """数据表分享服务类"""
    
    VALID_PERMISSIONS = ('editor', 'commenter', 'viewer')
    
    VALID_VIEW_SCOPES = ('all', 'specified')
    
    PERMISSION_RANK = {'viewer': 0, 'commenter': 1, 'editor': 2}
    
    
    @staticmethod
    def get_shared_tables_for_user(user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户通过表分享加入的数据表列表（首页/「分享给我的」列表数据源）
    
        规则：
        - 仅统计有效分享（is_active 且未过期）
        - 同一数据表命中多条分享时，取权限最高的一条作为代表（share_id/share_token/permission/view_scope）
        - 排序：按表格更新时间倒序（与首页列表排序规则一致）
    
        Args:
            user_id: 用户 ID
    
        Returns:
            列表项含 share_id, share_token, permission, view_scope, view_count,
            joined_at, table, base
        """
        rows = (
            db.session.query(TableShareMember, TableShare, Table)
            .join(TableShare, TableShareMember.share_id == TableShare.id)
            .join(Table, Table.id == TableShare.table_id)
            .filter(
                TableShareMember.user_id == str(user_id),
                TableShare.is_active.is_(True),
            )
            .all()
        )
    
        now_ts = int(datetime.now(timezone.utc).timestamp())
        best_by_table: Dict[str, Dict[str, Any]] = {}
        for member, share, table in rows:
            if share.expires_at is not None and now_ts > share.expires_at:
                continue
            base = table.base
            if base is None:
                continue
            permission = TableShareService._permission_value(share)
            rank = TableShareService.PERMISSION_RANK.get(permission, -1)
            item = {
                'share_id': str(share.id),
                'share_token': str(share.share_token),
                'permission': permission,
                'view_scope': share.view_scope,
                'view_count': len(share.view_ids or []) if share.view_scope == 'specified' else None,
                'joined_at': member.joined_at.isoformat() if member.joined_at else None,
                'table': {
                    'id': str(table.id),
                    'name': table.name,
                    'description': table.description,
                    'updated_at': table.updated_at.isoformat() if table.updated_at else None,
                },
                'base': {
                    'id': str(base.id),
                    'name': base.name,
                    'color': base.color,
                    'icon': base.icon,
                },
            }
            existing = best_by_table.get(str(table.id))
            if existing is None or rank > TableShareService.PERMISSION_RANK.get(
                existing['permission'], -1
            ):
                best_by_table[str(table.id)] = item
    
        result = list(best_by_table.values())
        result.sort(
            key=lambda item: item['table']['updated_at'] or '',
            reverse=True,
        )
        return result
    
    @staticmethod
    def remove_view_from_shares(table_id: str, view_id: str) -> None:
        """
        从该表所有表分享的 view_ids 中移除指定视图；
        若移除后 specified 范围为空，则将 view_scope 回退为 all（避免空范围）
        """
        shares = TableShare.query.filter_by(
            table_id=str(table_id), view_scope='specified'
        ).all()
    
        changed = False
        for share in shares:
            ids = [str(v) for v in (share.view_ids or [])]
            if str(view_id) not in ids:
                continue
            remaining = [v for v in ids if v != str(view_id)]
            if remaining:
                share.view_ids = remaining
            else:
                share.view_scope = 'all'
                share.view_ids = None
            changed = True
    
        if changed:
            db.session.commit()
            current_app.logger.info(
                f'[TableShareService] 视图删除后清理表分享可见范围：table={table_id}, view={view_id}'
            )
    
