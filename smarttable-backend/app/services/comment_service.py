"""
评论服务模块
提供记录评论的列表、创建、编辑、删除、关注，以及 @提及解析与三类通知触发。
"""
import re
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any, Union

from app.extensions import db
from app.models.record import Record, RecordComment
from app.models.comment import CommentMention, RecordFollower
from app.models.user import User
from app.models.base import BaseMember, MemberRole
from app.models.table_share import TableShare
from app.services.permission_service import PermissionService
from app.services.table_share_service import TableShareService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

# 评论内容长度上限
COMMENT_MAX_LENGTH = 2000
# 回复树最大递归深度（用于列表组装）
REPLY_TREE_MAX_DEPTH = 5
# 列表每页最大条数
MAX_PER_PAGE = 100
# @提及正则：匹配 @ 后连续非空白、非 @ 字符（长度 1-32）
_MENTION_PATTERN = re.compile(r'@([^\s@]{1,32})')

# 服务方法返回结果：(成功标志, 数据/错误键, HTTP 状态码)
ServiceResult = Tuple[bool, Union[Dict[str, Any], str], int]


class CommentService:
    """记录评论服务"""

    # ------------------------------------------------------------------ #
    # 权限辅助
    # ------------------------------------------------------------------ #
    @staticmethod
    def _get_record_or_error(record_id: str) -> Optional[Record]:
        record = Record.query.get(record_id)
        if record is None or record.is_deleted:
            return None
        return record

    @staticmethod
    def _can_read(record: Record, user_id: str) -> bool:
        base_id = str(record.table.base_id) if record.table else None
        if base_id and PermissionService.check_permission(base_id, user_id, MemberRole.VIEWER):
            return True
        return TableShareService.get_members_role(str(record.table_id), user_id) is not None

    @staticmethod
    def _can_comment(record: Record, user_id: str) -> bool:
        base_id = str(record.table.base_id) if record.table else None
        if base_id and PermissionService.check_permission(base_id, user_id, MemberRole.COMMENTER):
            return True
        role = TableShareService.get_members_role(str(record.table_id), user_id)
        return role in ('commenter', 'editor')

    @staticmethod
    def _can_delete_any_comment(record: Record, user_id: str) -> bool:
        """Editor+（Base editor/admin/owner，或表分享 editor）可删除任意评论"""
        base_id = str(record.table.base_id) if record.table else None
        if base_id and PermissionService.check_permission(base_id, user_id, MemberRole.EDITOR):
            return True
        return TableShareService.get_members_role(str(record.table_id), user_id) == 'editor'

    # ------------------------------------------------------------------ #
    # @提及解析
    # ------------------------------------------------------------------ #
    @staticmethod
    def _accessible_users(base_id: str, table_id: str) -> List[User]:
        """获取可访问该记录的人员集合（Base 成员 ∪ 表分享成员）"""
        user_ids = set()
        for m in BaseMember.query.filter_by(base_id=base_id).all():
            user_ids.add(m.user_id)
        shares = TableShare.query.filter_by(table_id=table_id).all()
        for share in shares:
            if not getattr(share, 'is_active', True):
                continue
            for mem in share.members:
                user_ids.add(mem.user_id)
        if not user_ids:
            return []
        return User.query.filter(User.id.in_(user_ids)).all()

    @classmethod
    def _parse_mentions(cls, content: str, users: List[User]) -> List[User]:
        """从评论正文中解析被 @ 的成员（按显示名精确匹配，去重）"""
        if not content:
            return []
        tokens = _MENTION_PATTERN.findall(content)
        name_map = {}
        for u in users:
            name_map.setdefault(u.name, []).append(u)
        mentioned: List[User] = []
        seen = set()
        for tok in tokens:
            for u in name_map.get(tok, []):
                if u.id in seen:
                    continue
                seen.add(u.id)
                mentioned.append(u)
        return mentioned

    # ------------------------------------------------------------------ #
    # 通知辅助
    # ------------------------------------------------------------------ #
    @staticmethod
    def _pref_enabled(user: User, key: str) -> bool:
        prefs = user.notification_prefs or {}
        return bool(prefs.get(key, True))

    @classmethod
    def _send_notification(
        cls,
        recipient: User,
        pref_key: str,
        template_key: str,
        template_data: Dict[str, Any],
    ) -> None:
        if not cls._pref_enabled(recipient, pref_key):
            return
        try:
            # 不传 title：由邮件模板主题渲染（含 actor/base 等信息）作为
            # 站内信标题与邮件主题的统一来源，避免在服务层硬编码语言文本
            NotificationService.send_notification(
                recipient_user_id=recipient.id,
                template_key=template_key,
                source='comment',
                template_data=template_data,
                send_email=True,
            )
        except Exception as exc:  # 通知失败不影响评论写入
            logger.error(f'[Comment] 发送通知失败：{exc}')

    @classmethod
    def _build_template_data(cls, actor: User, record: Record, comment: RecordComment) -> Dict[str, Any]:
        base_id = str(record.table.base_id) if record.table else ''
        table_id = str(record.table_id)
        base_name = record.table.base.name if record.table and record.table.base else ''
        table_name = record.table.name if record.table else ''
        # 记录标题：取第一个非空字段值，否则用记录 ID
        record_title = str(record.id)
        for value in (record.values or {}).values():
            if value:
                record_title = str(value)
                break
        snippet = (comment.content or '')[:200]
        record_url = f'/base/{base_id}/table/{table_id}/record/{record.id}'
        return {
            'actor_name': actor.name,
            'base_name': base_name,
            'table_name': table_name,
            'record_title': record_title,
            'comment_snippet': snippet,
            'record_url': record_url,
        }

    # ------------------------------------------------------------------ #
    # 列表
    # ------------------------------------------------------------------ #
    @classmethod
    def list(
        cls,
        record_id: str,
        user_id: str,
        page: int = 1,
        per_page: int = 20,
    ) -> ServiceResult:
        record = cls._get_record_or_error(record_id)
        if record is None:
            return False, 'record_does_not_exist', 404
        if not cls._can_read(record, user_id):
            return False, 'no_permission_access_record', 403

        page = max(1, page)
        per_page = max(1, min(per_page, MAX_PER_PAGE))
        top_query = RecordComment.query.filter_by(
            record_id=record.id, parent_id=None
        ).filter(RecordComment.is_deleted == False)  # noqa: E712
        total = top_query.count()
        items = (
            top_query.order_by(RecordComment.created_at.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        data = [cls._serialize(comment, depth=1) for comment in items]
        return True, {
            'items': data,
            'total': total,
            'page': page,
            'per_page': per_page,
        }, 200

    @classmethod
    def _serialize(cls, comment: RecordComment, depth: int) -> Dict[str, Any]:
        data = comment.to_dict(include_user=True)
        if depth < REPLY_TREE_MAX_DEPTH:
            replies = (
                comment.replies.filter(RecordComment.is_deleted == False)  # noqa: E712
                .order_by(RecordComment.created_at.asc())
                .all()
            )
            data['replies'] = [cls._serialize(r, depth + 1) for r in replies]
        else:
            data['replies'] = []
        # @提及列表（仅显式 @，回复指向的父作者不含入展示）
        data['mentions'] = [
            {'user_id': str(m.mentioned_user_id), 'type': m.mention_type}
            for m in comment.mentions
            if m.mention_type == 'mention'
        ]
        return data

    # ------------------------------------------------------------------ #
    # 创建 / 回复
    # ------------------------------------------------------------------ #
    @classmethod
    def create(
        cls,
        record_id: str,
        user_id: str,
        content: str,
        parent_id: Optional[str] = None,
    ) -> ServiceResult:
        record = cls._get_record_or_error(record_id)
        if record is None:
            return False, 'record_does_not_exist', 404
        if not cls._can_comment(record, user_id):
            return False, 'no_permission_comment', 403

        if not content or not content.strip():
            return False, 'comment_content_empty', 400
        if len(content) > COMMENT_MAX_LENGTH:
            return False, 'comment_content_too_long', 400

        parent = None
        if parent_id:
            parent = RecordComment.query.get(parent_id)
            if parent is None or parent.is_deleted or str(parent.record_id) != str(record.id):
                return False, 'comment_parent_invalid', 400

        actor = User.query.get(user_id)
        comment = RecordComment(
            record_id=record.id,
            user_id=actor.id if actor else user_id,
            content=content.strip(),
            parent_id=parent.id if parent else None,
        )
        db.session.add(comment)
        db.session.flush()

        base_id = str(record.table.base_id) if record.table else None
        table_id = str(record.table_id)
        accessible = cls._accessible_users(base_id, table_id) if base_id else []

        # @提及（去重、排除自身）
        mentioned_users = [
            u for u in cls._parse_mentions(content, accessible)
            if str(u.id) != str(user_id)
        ]
        for u in mentioned_users:
            db.session.add(CommentMention(
                comment_id=comment.id,
                mentioned_user_id=u.id,
                mention_type='mention',
            ))

        # 回复：记录父评论作者（用于回复通知）
        parent_author = None
        if parent is not None and parent.user_id and str(parent.user_id) != str(user_id):
            db.session.add(CommentMention(
                comment_id=comment.id,
                mentioned_user_id=parent.user_id,
                mention_type='reply_parent',
            ))
            parent_author = User.query.get(parent.user_id)

        # 记录关注者（仅顶层评论）
        followers: List[User] = []
        if parent is None:
            for f in RecordFollower.query.filter_by(record_id=record.id).all():
                if str(f.user_id) == str(user_id):
                    continue
                fu = User.query.get(f.user_id)
                if fu:
                    followers.append(fu)

        # 通知模板数据（在提交前基于已加载对象构建）
        tpl = cls._build_template_data(actor, record, comment)

        # 先持久化评论与提及，再发送通知：通知失败不影响评论已写入
        db.session.commit()

        for u in mentioned_users:
            cls._send_notification(u, 'notify_on_mention', 'comment_mention', tpl)
        if parent_author:
            cls._send_notification(parent_author, 'notify_on_reply', 'comment_reply', tpl)
        for fu in followers:
            cls._send_notification(fu, 'notify_on_record_comment', 'record_comment', tpl)

        return True, cls._serialize(comment, depth=1), 201

    # ------------------------------------------------------------------ #
    # 编辑
    # ------------------------------------------------------------------ #
    @classmethod
    def update(
        cls,
        comment_id: str,
        user_id: str,
        content: str,
    ) -> ServiceResult:
        comment = RecordComment.query.get(comment_id)
        if comment is None or comment.is_deleted:
            return False, 'comment_not_found', 404
        if str(comment.user_id) != str(user_id):
            return False, 'comment_edit_forbidden', 403
        if not content or not content.strip():
            return False, 'comment_content_empty', 400
        if len(content) > COMMENT_MAX_LENGTH:
            return False, 'comment_content_too_long', 400

        comment.content = content.strip()
        comment.updated_at = datetime.now(timezone.utc)

        # 重新解析 @提及，仅对新增提及补充通知（不撤回已移除）
        record = comment.record
        base_id = str(record.table.base_id) if record.table else None
        table_id = str(record.table_id)
        accessible = cls._accessible_users(base_id, table_id) if base_id else []
        existing = {str(m.mentioned_user_id) for m in comment.mentions}
        new_mentions: List[User] = []
        for u in cls._parse_mentions(content, accessible):
            if str(u.id) == str(user_id) or str(u.id) in existing:
                continue
            db.session.add(CommentMention(
                comment_id=comment.id,
                mentioned_user_id=u.id,
                mention_type='mention',
            ))
            new_mentions.append(u)

        actor = User.query.get(user_id)
        tpl = cls._build_template_data(actor, record, comment)
        db.session.commit()

        for u in new_mentions:
            cls._send_notification(u, 'notify_on_mention', 'comment_mention', tpl)

        return True, cls._serialize(comment, depth=1), 200

    # ------------------------------------------------------------------ #
    # 删除（软删除，保留回复树）
    # ------------------------------------------------------------------ #
    @classmethod
    def delete(
        cls,
        comment_id: str,
        user_id: str,
    ) -> ServiceResult:
        comment = RecordComment.query.get(comment_id)
        if comment is None or comment.is_deleted:
            return False, 'comment_not_found', 404

        is_author = str(comment.user_id) == str(user_id)
        record = comment.record
        if not is_author and not cls._can_delete_any_comment(record, user_id):
            return False, 'no_permission_delete_comment', 403

        has_replies = comment.replies.filter(RecordComment.is_deleted == False).count() > 0  # noqa: E712
        if has_replies:
            # 含回复：软删除占位，保留回复树
            comment.is_deleted = True
            comment.deleted_at = datetime.now(timezone.utc)
            comment.content = ''
            # 清除 @提及关联（通知历史保留）
            CommentMention.query.filter_by(comment_id=comment.id).delete(
                synchronize_session=False
            )
        else:
            # 无回复：硬删
            CommentMention.query.filter_by(comment_id=comment.id).delete(
                synchronize_session=False
            )
            db.session.delete(comment)

        db.session.commit()
        return True, {'success': True}, 200

    # ------------------------------------------------------------------ #
    # 关注 / 取关
    # ------------------------------------------------------------------ #
    @classmethod
    def toggle_follow(
        cls,
        record_id: str,
        user_id: str,
    ) -> ServiceResult:
        record = cls._get_record_or_error(record_id)
        if record is None:
            return False, 'record_does_not_exist', 404
        if not cls._can_read(record, user_id):
            return False, 'no_permission_access_record', 403

        existing = RecordFollower.query.filter_by(
            record_id=record.id, user_id=user_id
        ).first()
        if existing:
            db.session.delete(existing)
            following = False
        else:
            db.session.add(RecordFollower(record_id=record.id, user_id=user_id))
            following = True
        db.session.commit()
        return True, {'following': following}, 200
