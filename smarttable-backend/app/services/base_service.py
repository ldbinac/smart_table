"""
基础数据服务模块
处理 Base（工作区/数据库）的 CRUD 操作和成员管理
"""
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone

from flask import current_app
from sqlalchemy import or_

from app.extensions import db
from app.models.base import Base, BaseMember, MemberRole
from app.models.base_share import BaseShare, SharePermission
from app.models.user import User
from app.models.table import Table
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
            return {'success': False, 'error': '分享令牌不存在'}
        
        # 检查分享是否激活
        if not share.is_active:
            current_app.logger.error(f'[BaseService] 分享链接已失效')
            return {'success': False, 'error': '分享链接已失效'}
        
        # 检查是否过期
        if share.expires_at is not None:
            if int(datetime.now(timezone.utc).timestamp()) > share.expires_at:
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

    @staticmethod
    def copy_base(base_id: str, user_id: str, new_name: str = None) -> Dict[str, Any]:
        """
        复制基础数据（多维表格）
        
        复制内容包括：
        - Base 基本信息
        - 所有数据表结构及字段配置
        - 所有数据记录
        - 所有视图配置
        - 所有仪表盘配置
        
        排除内容：
        - 分享设置
        - 访问权限设置
        - 评论及协作历史记录
        
        Args:
            base_id: 源基础数据 ID
            user_id: 复制操作的用户 ID
            new_name: 新基础数据名称（可选，默认为"原名称+副本"）
            
        Returns:
            包含操作结果的字典
        """
        from app.services.table_service import TableService
        from app.services.field_service import FieldService
        from app.services.record_service import RecordService
        from app.services.view_service import ViewService
        from app.services.dashboard_service import DashboardService
        from app.services.link_service import LinkService
        from app.models.field import Field
        from app.models.record import Record
        from app.models.view import View
        from app.models.dashboard import Dashboard
        from app.models.link_relation import LinkValue, LinkRelation
        
        try:
            # 1. 获取源 Base
            source_base = Base.query.get(base_id)
            if not source_base:
                return {'success': False, 'error': '源基础数据不存在'}
            
            # 2. 生成新名称
            if not new_name:
                new_name = f"{source_base.name} 副本"
            
            # 检查同名冲突，自动添加序号后缀
            existing_names = [b.name for b in Base.query.filter(
                Base.name.like(f"{new_name}%")
            ).all()]
            
            if new_name in existing_names:
                counter = 2
                original_name = new_name
                while f"{original_name}({counter})" in existing_names:
                    counter += 1
                new_name = f"{original_name}({counter})"
            
            # 3. 创建新 Base
            new_base = Base(
                name=new_name,
                owner_id=user_id,
                description=source_base.description,
                icon=source_base.icon,
                color=source_base.color,
                is_personal=source_base.is_personal
            )
            db.session.add(new_base)
            db.session.flush()  # 获取 new_base.id
            
            current_app.logger.info(f'[BaseService] 创建副本 Base: {new_base.id}, 源: {base_id}')
            
            # 4. 创建成员关系（复制者成为所有者）
            membership = BaseMember(
                base_id=new_base.id,
                user_id=user_id,
                role=MemberRole.OWNER,
                is_starred=False
            )
            db.session.add(membership)
            
            # 5. 复制数据表
            source_tables = Table.query.filter_by(base_id=base_id).all()
            table_id_map = {}  # 源表ID -> 新表ID 映射
            field_id_map = {}  # 源字段ID -> 新字段ID 映射
            record_id_map = {}  # 源记录ID -> 新记录ID 映射
            link_field_map = {}  # 源关联字段ID -> (新关联字段ID, 目标表ID, link_relation_id) 映射
            
            for source_table in source_tables:
                # 创建新表
                new_table = Table(
                    base_id=new_base.id,
                    name=source_table.name,
                    description=source_table.description,
                    order=source_table.order
                )
                db.session.add(new_table)
                db.session.flush()
                
                table_id_map[str(source_table.id)] = str(new_table.id)
                
                # 复制字段
                source_fields = Field.query.filter_by(table_id=source_table.id).all()
                for source_field in source_fields:
                    # 处理关联字段 - 使用 LinkService 创建
                    # 关联字段类型可能是 'link' 或 'link_to_record'
                    if source_field.type in ['link', 'link_to_record']:
                        import copy
                        new_options = copy.deepcopy(source_field.options) if source_field.options else {}
                        
                        # 映射 linkedTableId
                        target_table_id = None
                        if isinstance(new_options, dict) and 'linkedTableId' in new_options:
                            old_linked_table_id = new_options['linkedTableId']
                            if old_linked_table_id in table_id_map:
                                target_table_id = table_id_map[old_linked_table_id]
                            else:
                                target_table_id = old_linked_table_id
                        
                        # 如果没有找到 target_table_id，尝试从 config 中获取
                        if not target_table_id and source_field.config:
                            config = source_field.config if isinstance(source_field.config, dict) else {}
                            linked_table_id = config.get('linkedTableId')
                            if linked_table_id:
                                if linked_table_id in table_id_map:
                                    target_table_id = table_id_map[linked_table_id]
                                else:
                                    target_table_id = linked_table_id
                        
                        # 使用 LinkService 创建关联字段
                        if target_table_id:
                            link_result = LinkService.create_link_field(
                                str(new_table.id),
                                {
                                    'name': source_field.name,
                                    'target_table_id': target_table_id,
                                    'relationship_type': new_options.get('relationshipType', 'many_to_one'),
                                    'bidirectional': new_options.get('bidirectional', False),
                                    'description': source_field.description or ''
                                }
                            )
                            
                            if link_result['success']:
                                # link_result['field'] 是字典，需要获取 id
                                new_field_id = str(link_result['field']['id'])
                                field_id_map[str(source_field.id)] = new_field_id
                                
                                # 获取 link_relation_id
                                link_relation_id = None
                                if 'link_relation' in link_result and link_result['link_relation']:
                                    link_relation_id = link_result['link_relation'].get('id')
                                
                                # 记录关联字段映射，用于后续复制关联值
                                link_field_map[str(source_field.id)] = (new_field_id, target_table_id, link_relation_id)
                                current_app.logger.info(f'[BaseService] 关联字段创建成功：{source_field.id} -> {new_field_id}, target_table={target_table_id}, link_relation_id={link_relation_id}')
                                
                                # 验证 config 中的 linkedTableId 是否正确
                                new_field_config = link_result['field'].get('config', {})
                                config_linked_table_id = new_field_config.get('linkedTableId')
                                current_app.logger.info(f'[BaseService] 新字段 config.linkedTableId: {config_linked_table_id}, 期望: {target_table_id}')
                                
                                # 验证 link_relations 是否创建
                                if link_relation_id:
                                    current_app.logger.info(f'[BaseService] link_relations 创建成功：{link_relation_id}')
                                else:
                                    current_app.logger.warning(f'[BaseService] link_relations 未创建')
                                
                                # 如果有反向字段，也记录映射
                                if 'inverse_field' in link_result and link_result['inverse_field']:
                                    inverse_field = link_result['inverse_field']
                                    # 反向字段的目标表是当前新表
                                    # 获取反向字段的 link_relation_id
                                    inverse_link_relation_id = None
                                    if 'link_relation' in link_result and link_result['link_relation']:
                                        # 双向关联使用同一个 link_relation
                                        inverse_link_relation_id = link_relation_id
                                    link_field_map[str(inverse_field['id'])] = (str(inverse_field['id']), str(new_table.id), inverse_link_relation_id)
                                    current_app.logger.info(f'[BaseService] 反向关联字段创建成功：{inverse_field["id"]}, link_relation_id={inverse_link_relation_id}')
                            else:
                                current_app.logger.error(f"[BaseService] 创建关联字段失败：{link_result.get('error')}")
                                # 如果创建失败，使用普通字段创建作为降级方案
                                # 更新 config 中的 linkedTableId 指向新表
                                fallback_config = copy.deepcopy(source_field.config) if source_field.config else {}
                                if isinstance(fallback_config, dict) and target_table_id:
                                    fallback_config['linkedTableId'] = target_table_id
                                new_field = Field(
                                    table_id=new_table.id,
                                    name=source_field.name,
                                    type=source_field.type,
                                    options=new_options,
                                    config=fallback_config,
                                    order=source_field.order,
                                    is_primary=source_field.is_primary,
                                    is_required=source_field.is_required,
                                    description=source_field.description
                                )
                                db.session.add(new_field)
                                db.session.flush()
                                field_id_map[str(source_field.id)] = str(new_field.id)
                                current_app.logger.warning(f'[BaseService] 使用降级方案创建关联字段：{new_field.id}，config.linkedTableId={fallback_config.get("linkedTableId") if isinstance(fallback_config, dict) else None}')
                        else:
                            # 没有目标表ID，使用普通字段创建
                            # 更新 config 中的 linkedTableId 指向新表（如果可能）
                            fallback_config = copy.deepcopy(source_field.config) if source_field.config else {}
                            if isinstance(fallback_config, dict):
                                # 尝试从 options 或原 config 中获取并映射 linkedTableId
                                old_linked_id = fallback_config.get('linkedTableId')
                                if old_linked_id and old_linked_id in table_id_map:
                                    fallback_config['linkedTableId'] = table_id_map[old_linked_id]
                            new_field = Field(
                                table_id=new_table.id,
                                name=source_field.name,
                                type=source_field.type,
                                options=new_options,
                                config=fallback_config,
                                order=source_field.order,
                                is_primary=source_field.is_primary,
                                is_required=source_field.is_required,
                                description=source_field.description
                            )
                            db.session.add(new_field)
                            db.session.flush()
                            field_id_map[str(source_field.id)] = str(new_field.id)
                            current_app.logger.warning(f'[BaseService] 无目标表ID，使用降级方案创建关联字段：{new_field.id}')
                    else:
                        # 普通字段直接复制
                        new_field = Field(
                            table_id=new_table.id,
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
                
                # 更新主字段引用
                if source_table.primary_field_id:
                    new_primary_field_id = field_id_map.get(str(source_table.primary_field_id))
                    if new_primary_field_id:
                        new_table.primary_field_id = new_primary_field_id
                
                # 复制记录
                source_records = Record.query.filter_by(table_id=source_table.id).all()
                for source_record in source_records:
                    # 转换字段值中的字段ID
                    new_values = {}
                    for field_id, value in source_record.values.items():
                        new_field_id = field_id_map.get(field_id, field_id)
                        new_values[new_field_id] = value
                    
                    new_record = Record(
                        table_id=new_table.id,
                        values=new_values
                    )
                    db.session.add(new_record)
                    db.session.flush()
                    
                    # 建立记录ID映射
                    record_id_map[str(source_record.id)] = str(new_record.id)
                
                # 6. 复制关联关系（LinkValue）
                # 查找当前表的所有关联字段（类型可能是 'link' 或 'link_to_record'）
                source_link_fields = Field.query.filter(
                    Field.table_id == source_table.id,
                    Field.type.in_(['link', 'link_to_record'])
                ).all()
                current_app.logger.info(f'[BaseService] 复制关联关系：表 {source_table.id} 有 {len(source_link_fields)} 个关联字段')
                current_app.logger.info(f'[BaseService] link_field_map 内容：{link_field_map}')
                current_app.logger.info(f'[BaseService] record_id_map 内容：{record_id_map}')
                
                for source_link_field in source_link_fields:
                    source_field_id = str(source_link_field.id)
                    current_app.logger.info(f'[BaseService] 处理关联字段：{source_field_id}，在映射中：{source_field_id in link_field_map}')

                    if source_field_id not in link_field_map:
                        current_app.logger.warning(f'[BaseService] 字段 {source_field_id} 不在 link_field_map 中，跳过')
                        continue

                    new_field_id, target_table_id, link_relation_id = link_field_map[source_field_id]
                    current_app.logger.info(f'[BaseService] 新字段ID：{new_field_id}，目标表ID：{target_table_id}，link_relation_id：{link_relation_id}')

                    # 检查是否有 link_relation_id，如果没有则跳过
                    if not link_relation_id:
                        current_app.logger.warning(f'[BaseService] 字段 {source_field_id} 没有 link_relation_id，无法复制关联值')
                        continue

                    # 查找源字段对应的 link_relation
                    source_link_relation = LinkRelation.query.filter_by(source_field_id=source_field_id).first()
                    if not source_link_relation:
                        current_app.logger.warning(f'[BaseService] 找不到源字段 {source_field_id} 的 link_relation')
                        continue

                    # 查找该 link_relation 的所有关联值
                    source_link_values = LinkValue.query.filter_by(link_relation_id=str(source_link_relation.id)).all()
                    current_app.logger.info(f'[BaseService] 找到 {len(source_link_values)} 个关联值 (link_relation_id={source_link_relation.id})')

                    for link_value in source_link_values:
                        # 映射源记录ID
                        source_record_id = str(link_value.source_record_id)
                        if source_record_id not in record_id_map:
                            current_app.logger.warning(f'[BaseService] 源记录 {source_record_id} 不在映射中')
                            continue
                        new_source_record_id = record_id_map[source_record_id]

                        # 映射目标记录ID（如果目标记录也在复制范围内）
                        target_record_id = str(link_value.target_record_id)
                        new_target_record_id = record_id_map.get(target_record_id, target_record_id)

                        # 创建新的关联值 - 必须包含 link_relation_id
                        new_link_value = LinkValue(
                            link_relation_id=link_relation_id,
                            source_record_id=new_source_record_id,
                            target_record_id=new_target_record_id
                        )
                        db.session.add(new_link_value)
                        current_app.logger.info(f'[BaseService] 创建新关联值：link_relation_id={link_relation_id}, source={new_source_record_id}, target={new_target_record_id}')
                
                # 复制视图
                source_views = View.query.filter_by(table_id=source_table.id).all()
                for source_view in source_views:
                    # 转换筛选条件中的字段ID
                    new_filters = []
                    for filter_item in (source_view.filters or []):
                        new_filter = filter_item.copy()
                        if 'field_id' in new_filter and new_filter['field_id'] in field_id_map:
                            new_filter['field_id'] = field_id_map[new_filter['field_id']]
                        new_filters.append(new_filter)
                    
                    # 转换排序配置中的字段ID
                    new_sorts = []
                    for sort_item in (source_view.sort_config or []):
                        new_sort = sort_item.copy()
                        if 'field_id' in new_sort and new_sort['field_id'] in field_id_map:
                            new_sort['field_id'] = field_id_map[new_sort['field_id']]
                        new_sorts.append(new_sort)
                    
                    # 转换分组配置中的字段ID
                    new_group_config = source_view.group_config or {}
                    if isinstance(new_group_config, dict) and 'group_bys' in new_group_config:
                        new_group_bys = []
                        for field_id in new_group_config['group_bys']:
                            new_group_bys.append(field_id_map.get(field_id, field_id))
                        new_group_config['group_bys'] = new_group_bys
                    
                    # 转换字段可见性配置中的字段ID
                    new_field_visibility = {}
                    for field_id, visible in (source_view.field_visibility or {}).items():
                        new_field_id = field_id_map.get(field_id, field_id)
                        new_field_visibility[new_field_id] = visible
                    
                    # 转换隐藏字段列表中的字段ID
                    new_hidden_fields = []
                    for field_id in (source_view.hidden_fields or []):
                        new_hidden_fields.append(field_id_map.get(field_id, field_id))
                    
                    # 转换冻结字段列表中的字段ID
                    new_frozen_fields = []
                    for field_id in (source_view.frozen_fields or []):
                        new_frozen_fields.append(field_id_map.get(field_id, field_id))
                    
                    # 转换字段宽度配置中的字段ID
                    new_field_widths = {}
                    for field_id, width in (source_view.field_widths or {}).items():
                        new_field_id = field_id_map.get(field_id, field_id)
                        new_field_widths[new_field_id] = width
                    
                    # 转换表单配置中的字段ID
                    new_form_config = source_view.form_config or {}
                    if isinstance(new_form_config, dict):
                        if 'fields' in new_form_config:
                            new_form_fields = []
                            for field_id in new_form_config['fields']:
                                new_form_fields.append(field_id_map.get(field_id, field_id))
                            new_form_config['fields'] = new_form_fields
                    
                    new_view = View(
                        table_id=new_table.id,
                        name=source_view.name,
                        type=source_view.type,
                        description=source_view.description,
                        order=source_view.order,
                        is_default=source_view.is_default,
                        is_public=source_view.is_public,
                        filters=new_filters,
                        sort_config=new_sorts,
                        group_config=new_group_config,
                        field_visibility=new_field_visibility,
                        hidden_fields=new_hidden_fields,
                        frozen_fields=new_frozen_fields,
                        row_height=source_view.row_height,
                        field_widths=new_field_widths,
                        form_config=new_form_config
                    )
                    db.session.add(new_view)
            
            # 6. 复制仪表盘
            source_dashboards = Dashboard.query.filter_by(base_id=base_id).all()
            for source_dashboard in source_dashboards:
                # 转换仪表盘布局中的表ID和字段ID
                new_layout = source_dashboard.layout or {}
                if isinstance(new_layout, dict):
                    # 处理布局中的表ID引用
                    if 'table_id' in new_layout and new_layout['table_id'] in table_id_map:
                        new_layout['table_id'] = table_id_map[new_layout['table_id']]
                
                # 转换 widgets 中的表ID和字段ID
                new_widgets = []
                for widget in (source_dashboard.widgets or []):
                    new_widget = widget.copy()
                    if 'table_id' in new_widget and new_widget['table_id'] in table_id_map:
                        new_widget['table_id'] = table_id_map[new_widget['table_id']]
                    if 'field_id' in new_widget and new_widget['field_id'] in field_id_map:
                        new_widget['field_id'] = field_id_map[new_widget['field_id']]
                    new_widgets.append(new_widget)
                
                new_dashboard = Dashboard(
                    base_id=new_base.id,
                    user_id=user_id,
                    name=source_dashboard.name,
                    description=source_dashboard.description,
                    is_default=source_dashboard.is_default,
                    layout=new_layout,
                    widgets=new_widgets
                )
                db.session.add(new_dashboard)
            
            # 7. 提交所有更改
            db.session.commit()

            # 8. 验证并修复关联字段的 config
            from sqlalchemy.orm.attributes import flag_modified
            for source_field_id, (new_field_id, target_table_id, link_relation_id) in link_field_map.items():
                if link_relation_id:
                    new_field = Field.query.get(new_field_id)
                    if new_field:
                        # 检查 config 中的 linkedTableId 是否正确
                        if new_field.config is None:
                            new_field.config = {}
                        current_linked_table_id = new_field.config.get('linkedTableId')
                        if str(current_linked_table_id) != str(target_table_id):
                            current_app.logger.warning(f'[BaseService] 修复字段 {new_field_id} 的 config.linkedTableId: {current_linked_table_id} -> {target_table_id}')
                            new_field.config['linkedTableId'] = target_table_id
                            flag_modified(new_field, 'config')
            
            if link_field_map:
                db.session.commit()
                current_app.logger.info(f'[BaseService] 已验证并修复 {len(link_field_map)} 个关联字段的 config')

            current_app.logger.info(f'[BaseService] Base 复制完成：{new_base.id}')
            
            return {
                'success': True,
                'base': new_base.to_dict(),
                'message': '复制成功'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[BaseService] 复制 Base 失败：{base_id}, 错误：{str(e)}')
            return {'success': False, 'error': f'复制失败：{str(e)}'}
