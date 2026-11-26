"""
基础数据服务模块
处理 Base（工作区/数据库）的 CRUD 操作和成员管理
"""
from typing import List, Optional, Dict, Any
import uuid

# 用于区分"未传递 role_id"和"明确将 role_id 设为 None"
_UNSET = object()
import threading
from datetime import datetime, timezone

from flask import current_app
from sqlalchemy import or_

from app.extensions import db
from app.models.base import Base, BaseMember, MemberRole
from app.models.base_share import BaseShare, SharePermission
from app.models.user import User
from app.models.table import Table
from app.models.field import Field
from app.models.record import Record
from app.models.view import View
from app.models.dashboard import Dashboard
from app.utils.constants import ROLE_LEVELS
from app.services.email_config_service import EmailConfigService
from app.services.email_sender_service import EmailSenderService
from app.services.notification_service import NotificationService

class BaseServiceGroup01Mixin:
    """Mixin auto-split"""
    
    """基础数据服务类"""
    
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
    
        base.updated_at = datetime.now(timezone.utc)
        db.session.commit()
    
        return base
    
    @staticmethod
    def delete_base(base_id: str) -> bool:
        """
        删除基础数据（级联删除关联的表格、字段、记录、关联关系等）
    
        Args:
            base_id: 基础数据 ID
    
        Returns:
            是否删除成功
        """
        base = Base.query.get(base_id)
        if not base:
            return False
    
        try:
            # 获取该 Base 下的所有表格 ID
            table_ids = [str(t.id) for t in base.tables]
    
            # 删除这些表格相关的 LinkValue（关联值）
            if table_ids:
                from app.models.link_relation import LinkValue, LinkRelation
                from app.models.record import Record
    
                # 获取该 Base 下所有记录的 ID
                record_ids = []
                for table in base.tables:
                    for record in table.records:
                        record_ids.append(str(record.id))
    
                # 删除这些记录相关的 LinkValue
                if record_ids:
                    LinkValue.query.filter(
                        db.or_(
                            LinkValue.source_record_id.in_(record_ids),
                            LinkValue.target_record_id.in_(record_ids)
                        )
                    ).delete(synchronize_session=False)
    
                # 删除该 Base 下表格之间的 LinkRelation（关联关系）
                LinkRelation.query.filter(
                    db.or_(
                        LinkRelation.source_table_id.in_(table_ids),
                        LinkRelation.target_table_id.in_(table_ids)
                    )
                ).delete(synchronize_session=False)
    
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
            return {'success': False, 'error': 'user_does_not_exist'}
    
        # 检查是否已经是成员
        existing = BaseMember.query.filter_by(
            base_id=base_id,
            user_id=user.id
        ).first()
    
        if existing:
            return {'success': False, 'error': 'user_already_member'}
    
        # 检查是否是基础数据所有者
        base = Base.query.get(base_id)
        if base and str(base.owner_id) == str(user.id):
            return {'success': False, 'error': 'owner_owner_base_added_member'}
    
        # 验证角色
        try:
            member_role = MemberRole(role.lower())
        except ValueError:
            return {'success': False, 'error': 'invalid_role_type'}
    
        # 创建成员关系
        membership = BaseMember(
            base_id=base_id,
            user_id=user.id,
            role=member_role,
            invited_by=invited_by
        )
    
        db.session.add(membership)
        db.session.commit()
    
        # 发送分享邀请通知（站内信先于邮件，邮件不可用时站内信仍独立工作）
        try:
            inviter = User.query.get(invited_by)
            base_link = f"{EmailConfigService.get_frontend_url()}/base/{base_id}"
            permission_map = {
                'owner': '所有者',
                'admin': '管理员',
                'editor': '编辑者',
                'commenter': '评论者',
                'viewer': '查看者'
            }
            NotificationService.send_notification(
                recipient_email=user.email,
                recipient_user_id=user.id,
                template_key='share_invitation',
                template_data={
                    'sharer_name': inviter.name if inviter else '系统管理员',
                    'base_name': base.name if base else '未命名多维表',
                    'base_description': base.description or '暂无描述',
                    'permission': permission_map.get(member_role.value, member_role.value),
                    'base_link': base_link
                },
                source='system'
            )
        except Exception as e:
            current_app.logger.error(f'发送分享邀请邮件失败: {str(e)}')
    
        return {
            'success': True,
            'member': membership.to_dict(include_user=True)
        }
    
    @staticmethod
    def remove_member(base_id: str, user_id: str, removed_by: str = None) -> bool:
        """
        从基础数据中移除成员
    
        Args:
            base_id: 基础数据 ID
            user_id: 要移除的用户 ID
            removed_by: 执行移除操作的用户 ID（可选）
    
        Returns:
            是否移除成功
        """
        membership = BaseMember.query.filter_by(
            base_id=base_id,
            user_id=user_id
        ).first()
    
        if not membership:
            return False
    
        # 获取用户信息用于发送邮件
        user = User.query.get(user_id)
        base = Base.query.get(base_id)
    
        try:
            db.session.delete(membership)
            db.session.commit()
    
            # 发送分享移除通知（站内信先于邮件，邮件不可用时站内信仍独立工作）
            if user and base:
                try:
                    operator = User.query.get(removed_by) if removed_by else None
                    NotificationService.send_notification(
                        recipient_email=user.email,
                        recipient_user_id=user.id,
                        template_key='share_removed',
                        template_data={
                            'user_name': user.name,
                            'base_name': base.name,
                            'operation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'operator_name': operator.name if operator else '系统管理员'
                        },
                        source='system'
                    )
                except Exception as e:
                    current_app.logger.error(f'发送分享移除通知邮件失败: {str(e)}')
    
            return True
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def update_member_role(base_id: str, user_id: str, new_role: str = None, role_id: str = _UNSET, updated_by: str = None) -> Dict[str, Any]:
        """
        更新成员角色
    
        Args:
            base_id: 基础数据 ID
            user_id: 用户 ID
            new_role: 新基础角色（可选）
            role_id: 自定义角色 ID（可选，传入 None 表示移除自定义角色）
            updated_by: 执行更新操作的用户 ID（可选）
    
        Returns:
            包含操作结果的字典
        """
        membership = BaseMember.query.filter_by(
            base_id=base_id,
            user_id=user_id
        ).first()
    
        if not membership:
            return {'success': False, 'error': 'member_does_not_exist'}
    
        # 保存旧角色用于邮件通知
        old_role = membership.role
    
        try:
            if new_role:
                member_role = MemberRole(new_role.lower())
                membership.role = member_role
    
            if role_id is not _UNSET:
                try:
                    from app.models.permission import Role
                except ImportError:
                    Role = None
                if role_id:
                    role = Role.query.get(role_id)
                    if not role:
                        return {'success': False, 'error': '自定义角色不存在'}
                    if str(role.base_id) != str(base_id):
                        return {'success': False, 'error': '自定义角色不属于当前 Base'}
                membership.role_id = role_id if role_id else None
    
            db.session.commit()
        except ValueError:
            return {'success': False, 'error': 'invalid_role_type'}
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'更新成员角色失败: {str(e)}')
            return {'success': False, 'error': '更新成员角色失败'}
    
        # 发送权限变更通知（站内信先于邮件，邮件不可用时站内信仍独立工作）
        try:
            user = User.query.get(user_id)
            base = Base.query.get(base_id)
    
            if user and base:
                operator = User.query.get(updated_by) if updated_by else None
                permission_map = {
                    'owner': '所有者',
                    'admin': '管理员',
                    'editor': '编辑者',
                    'commenter': '评论者',
                    'viewer': '查看者'
                }
                base_link = f"{EmailConfigService.get_frontend_url()}/base/{base_id}"
    
                # 构建通知模板数据
                template_data = {
                    'user_name': user.name,
                    'base_name': base.name,
                    'old_permission': permission_map.get(old_role.value, old_role.value),
                    'new_permission': permission_map.get(
                        membership.role.value, membership.role.value
                    ) if new_role else old_role.value,
                    'operation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'operator_name': operator.name if operator else '系统管理员',
                    'base_link': base_link
                }
    
                NotificationService.send_notification(
                    recipient_email=user.email,
                    recipient_user_id=user.id,
                    template_key='permission_changed',
                    template_data=template_data,
                    source='system'
                )
        except Exception as e:
            current_app.logger.error(f'发送权限变更通知邮件失败: {str(e)}')
    
        return {
            'success': True,
            'member': membership.to_dict(include_user=True)
        }
    
