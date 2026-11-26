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

class BaseServiceGroup02Mixin:
    """Mixin auto-split"""
    
    """基础数据服务类"""
    
    ROLE_LEVELS = ROLE_LEVELS
    
    
    @staticmethod
    def transfer_ownership(base_id: str, current_user_id: str,
                           target_user_id: str,
                           former_owner_role: Optional[str] = None) -> Dict[str, Any]:
        """
        转移基础数据所有权
    
        将 Base 所有权转移给目标用户，并按 former_owner_role 处理原所有者的权限：
        - 指定角色（admin/editor/commenter/viewer）：原所有者降级为该角色成员
        - None：移除原所有者的协作权限（删除成员关系）
    
        Args:
            base_id: 基础数据 ID
            current_user_id: 当前操作用户 ID（必须为所有者）
            target_user_id: 目标用户 ID
            former_owner_role: 原所有者转移后的角色，None 表示不保留协作权限
    
        Returns:
            包含操作结果的字典
        """
        base = Base.query.get(base_id)
        if not base:
            return {'success': False, 'error': 'base_not_exist'}
    
        # 仅所有者可以转移
        if str(base.owner_id) != str(current_user_id):
            return {'success': False, 'error': 'only_owner_can_transfer'}
    
        # 不能转移给自己
        if str(target_user_id) == str(current_user_id):
            return {'success': False, 'error': 'cannot_transfer_to_self'}
    
        # 目标用户必须存在
        target_user = User.query.get(target_user_id)
        if not target_user:
            return {'success': False, 'error': 'user_does_not_exist'}
    
        # 校验原所有者保留角色
        keep_role = None
        if former_owner_role is not None and str(former_owner_role).strip() != '':
            try:
                keep_role = MemberRole(str(former_owner_role).strip().lower())
            except ValueError:
                return {'success': False, 'error': 'invalid_role_type'}
            if keep_role == MemberRole.OWNER:
                return {'success': False, 'error': 'invalid_role_type'}
    
        old_owner = User.query.get(current_user_id)
    
        try:
            # 1. 变更所有者
            base.owner_id = target_user_id
    
            # 2. 目标用户成员行 upsert（非成员时自动创建 owner 行）
            target_membership = BaseMember.query.filter_by(
                base_id=base_id,
                user_id=target_user_id
            ).first()
            if target_membership:
                target_membership.role = MemberRole.OWNER
            else:
                db.session.add(BaseMember(
                    base_id=base_id,
                    user_id=target_user_id,
                    role=MemberRole.OWNER,
                    invited_by=current_user_id
                ))
    
            # 3. 原所有者成员行处理
            old_membership = BaseMember.query.filter_by(
                base_id=base_id,
                user_id=current_user_id
            ).first()
            if keep_role is not None:
                if old_membership:
                    old_membership.role = keep_role
                else:
                    db.session.add(BaseMember(
                        base_id=base_id,
                        user_id=current_user_id,
                        role=keep_role,
                        invited_by=target_user_id
                    ))
            else:
                if old_membership:
                    db.session.delete(old_membership)
    
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[BaseService] 转移所有权失败: {str(e)}')
            return {'success': False, 'error': 'transfer_ownership_failed'}
    
        current_app.logger.info(
            f'[BaseService] 所有权转移成功: base={base_id}, '
            f'{current_user_id} -> {target_user_id}, keep_role={keep_role.value if keep_role else None}'
        )
    
        # 4. 后台线程发送通知（站内信先于邮件，邮件不可用时站内信仍独立工作）；
        # SMTP 同步发送可能耗时数秒到数十秒，异步化避免阻塞转移接口响应
        base_link = f"{EmailConfigService.get_frontend_url()}/base/{base_id}"
        permission_map = {
            'owner': '所有者',
            'admin': '管理员',
            'editor': '编辑者',
            'commenter': '评论者',
            'viewer': '查看者'
        }
        operation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        old_owner_name = old_owner.name if old_owner else '原所有者'
        target_user_name = target_user.name
        notify_app = current_app._get_current_object()
        notify_base_name = base.name
    
        def _send_transfer_notifications():
            try:
                with notify_app.app_context():
                    try:
                        NotificationService.send_notification(
                            recipient_user_id=target_user_id,
                            template_key='base_ownership_transferred',
                            template_data={
                                'user_name': target_user_name,
                                'base_name': notify_base_name,
                                'old_owner_name': old_owner_name,
                                'operation_time': operation_time,
                                'base_link': base_link
                            },
                            source='system'
                        )
                    except Exception as e:
                        notify_app.logger.error(f'发送所有权转移通知失败: {str(e)}')
    
                    try:
                        if keep_role is not None:
                            NotificationService.send_notification(
                                recipient_user_id=current_user_id,
                                template_key='permission_changed',
                                template_data={
                                    'user_name': old_owner_name,
                                    'base_name': notify_base_name,
                                    'old_permission': permission_map.get('owner', 'owner'),
                                    'new_permission': permission_map.get(keep_role.value, keep_role.value),
                                    'operation_time': operation_time,
                                    'operator_name': old_owner_name,
                                    'base_link': base_link
                                },
                                source='system'
                            )
                        else:
                            NotificationService.send_notification(
                                recipient_user_id=current_user_id,
                                template_key='share_removed',
                                template_data={
                                    'user_name': old_owner_name,
                                    'base_name': notify_base_name,
                                    'operation_time': operation_time,
                                    'operator_name': old_owner_name
                                },
                                source='system'
                            )
                    except Exception as e:
                        notify_app.logger.error(f'发送原所有者权限变更通知失败: {str(e)}')
            except Exception as e:
                import logging
                logging.error(f'所有权转移通知后台任务异常: {str(e)}')
    
        threading.Thread(
            target=_send_transfer_notifications,
            name='base-transfer-ownership-notify',
            daemon=True
        ).start()
    
        return {
            'success': True,
            'base': base.to_dict()
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
        current_app.logger.info(f'[BaseService] 验证分享令牌：base={base_id}, user={user_id}')
    
        # 查找分享记录
        share = BaseShare.query.filter_by(share_token=share_token, base_id=base_id).first()
    
        if not share:
            current_app.logger.error(f'[BaseService] 分享令牌不存在')
            return {'success': False, 'error': 'share_token_does_not_exist'}
    
        # 检查分享是否激活
        if not share.is_active:
            current_app.logger.error(f'[BaseService] 分享链接已失效')
            return {'success': False, 'error': 'share_link_no_longer_active'}
    
        # 检查是否过期
        if share.expires_at is not None:
            if int(datetime.now(timezone.utc).timestamp()) > share.expires_at:
                current_app.logger.error(f'[BaseService] 分享链接已过期')
                return {'success': False, 'error': 'share_link_expired'}
    
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
    
    @staticmethod
    def _copy_base_info(source_base: 'Base', user_id: str, new_name: str = None) -> 'Base':
        """
        复制 Base 基本信息
    
        Args:
            source_base: 源 Base 对象
            user_id: 复制操作的用户 ID
            new_name: 新名称（可选）
    
        Returns:
            新创建的 Base 对象
        """
        if not new_name:
            new_name = f"{source_base.name} 副本"
    
        existing_names = [b.name for b in Base.query.filter(
            Base.name.like(f"{new_name}%")
        ).all()]
    
        if new_name in existing_names:
            counter = 2
            original_name = new_name
            while f"{original_name}({counter})" in existing_names:
                counter += 1
            new_name = f"{original_name}({counter})"
    
        new_base = Base(
            name=new_name,
            owner_id=user_id,
            description=source_base.description,
            icon=source_base.icon,
            color=source_base.color,
            is_personal=source_base.is_personal
        )
        db.session.add(new_base)
        db.session.flush()
    
        membership = BaseMember(
            base_id=new_base.id,
            user_id=user_id,
            role=MemberRole.OWNER,
            is_starred=False
        )
        db.session.add(membership)
    
        current_app.logger.info(f'[BaseService] 创建副本 Base: {new_base.id}, 源: {source_base.id}')
        return new_base
    
    @staticmethod
    def _copy_field(source_field: 'Field', new_table_id: str, field_id_map: dict, 
                    table_id_map: dict, link_field_map: dict) -> None:
        """
        复制单个字段
    
        Args:
            source_field: 源字段对象
            new_table_id: 新表 ID
            field_id_map: 字段 ID 映射字典
            table_id_map: 表 ID 映射字典
            link_field_map: 关联字段映射字典
        """
        from app.services.link_service import LinkService
        import copy
    
        if source_field.type in ['link', 'link_to_record']:
            BaseService._copy_link_field(source_field, new_table_id, field_id_map, 
                                         table_id_map, link_field_map)
        else:
            new_field = Field(
                table_id=new_table_id,
                name=source_field.name,
                type=source_field.type,
                options=source_field.options,
                config=source_field.config,
                order=source_field.order,
                is_primary=source_field.is_primary,
                is_required=source_field.is_required,
                description=source_field.description
            )
            db.session.add(new_field)
            db.session.flush()
            field_id_map[str(source_field.id)] = str(new_field.id)
    
    @staticmethod
    def _copy_link_field(source_field: 'Field', new_table_id: str, field_id_map: dict,
                         table_id_map: dict, link_field_map: dict) -> None:
        """
        复制关联字段
    
        Args:
            source_field: 源关联字段对象
            new_table_id: 新表 ID
            field_id_map: 字段 ID 映射字典
            table_id_map: 表 ID 映射字典
            link_field_map: 关联字段映射字典
        """
        from app.services.link_service import LinkService
        import copy
    
        new_options = copy.deepcopy(source_field.options) if source_field.options else {}
    
        config = source_field.config if isinstance(source_field.config, dict) else {}
    
        target_table_id = None
        if isinstance(new_options, dict) and 'linkedTableId' in new_options:
            old_linked_table_id = new_options['linkedTableId']
            target_table_id = table_id_map.get(old_linked_table_id, old_linked_table_id)
    
        if not target_table_id and config.get('linkedTableId'):
            linked_table_id = config.get('linkedTableId')
            if linked_table_id:
                target_table_id = table_id_map.get(linked_table_id, linked_table_id)
    
        relationship_type = config.get('relationshipType') or new_options.get('relationshipType', 'many_to_one')
        bidirectional = config.get('bidirectional', new_options.get('bidirectional', False))
    
        if target_table_id:
            link_result = LinkService.create_link_field(
                new_table_id,
                {
                    'name': source_field.name,
                    'target_table_id': target_table_id,
                    'relationship_type': relationship_type,
                    'bidirectional': bidirectional,
                    'description': source_field.description or ''
                }
            )
    
            if link_result['success']:
                new_field_id = str(link_result['field']['id'])
                field_id_map[str(source_field.id)] = new_field_id
    
                link_relation_id = None
                if 'link_relation' in link_result and link_result['link_relation']:
                    link_relation_id = link_result['link_relation'].get('id')
    
                link_field_map[str(source_field.id)] = (new_field_id, target_table_id, link_relation_id)
                current_app.logger.info(f'[BaseService] 关联字段创建成功：{source_field.id} -> {new_field_id}')
    
                if 'inverse_field' in link_result and link_result['inverse_field']:
                    inverse_field = link_result['inverse_field']
                    inverse_link_relation_id = link_relation_id
                    link_field_map[str(inverse_field['id'])] = (str(inverse_field['id']), new_table_id, inverse_link_relation_id)
            else:
                BaseService._create_fallback_link_field(source_field, new_table_id, field_id_map, 
                                                        table_id_map, new_options, target_table_id)
        else:
            BaseService._create_fallback_link_field(source_field, new_table_id, field_id_map,
                                                    table_id_map, new_options, None)
    
