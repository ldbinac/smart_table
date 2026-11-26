"""
管理员服务模块
处理管理员用户管理系统的所有业务逻辑，包括用户管理、操作日志、系统配置等功能
"""
import csv
import io
import json
import logging
import secrets
import smtplib
import ssl
import string
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Optional, Tuple, Dict, Any, List
from uuid import UUID

from sqlalchemy import or_, and_

from app.extensions import db
try:
    from app.utils.crypto import decrypt_secret, encrypt_secret
except ImportError:
    decrypt_secret = None
    encrypt_secret = None
from app.models.user import User, UserRole, UserStatus
from app.models.log import OperationLog, AdminActionType, EntityType
from app.models.config import SystemConfig
from app.services.email_config_service import EmailConfigService
from app.services.email_sender_service import EmailSenderService
from app.services.notification_service import NotificationService
from app.services.security_config_service import SecurityConfigService
from app.services.config_cache_service import ConfigCacheService
from app.i18n import translate

logger = logging.getLogger(__name__)

class AdminServiceGroup01Mixin:
    """Mixin auto-split"""
    
    """
    管理员服务类
    提供用户管理、操作日志记录、系统配置管理等所有管理员相关功能
    """
    
    
    @staticmethod
    def _generate_temporary_password(length: int = 12) -> str:
        """
        生成安全的随机临时密码
    
        Args:
            length: 密码长度，默认 12 位
    
        Returns:
            生成的随机密码
        """
        # 确保密码包含大小写字母、数字和特殊字符
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            password = ''.join(secrets.choice(alphabet) for _ in range(length))
            # 确保密码至少包含一个大写字母、一个小写字母、一个数字和一个特殊字符
            if (any(c.isupper() for c in password)
                and any(c.islower() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*" for c in password)):
                return password
    
    @staticmethod
    def _get_user_query():
        """
        获取用户基础查询对象
    
        Returns:
            SQLAlchemy Query 对象
        """
        return User.query.filter(User.status != UserStatus.DELETED)
    
    @staticmethod
    def get_all_users(
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取分页用户列表
    
        Args:
            page: 页码，从 1 开始
            per_page: 每页数量，默认 20
            search: 搜索关键词（支持邮箱和姓名）
            role: 角色过滤（owner, admin, workspace_admin, editor, commenter, viewer）
            status: 状态过滤（active, inactive, suspended）
    
        Returns:
            包含用户列表和分页信息的字典：
            {
                'users': 用户列表,
                'total': 总数,
                'page': 当前页码,
                'per_page': 每页数量,
                'pages': 总页数
            }
        """
        query = AdminService._get_user_query()
    
        # 搜索过滤（邮箱、用户名或姓名）
        if search:
            from app.utils.validators import escape_like_pattern
            escaped = escape_like_pattern(search)
            search_pattern = f"%{escaped}%"
            query = query.filter(
                or_(
                    User.email.ilike(search_pattern),
                    User.username.ilike(search_pattern),
                    User.name.ilike(search_pattern)
                )
            )
    
        # 角色过滤
        if role:
            try:
                role_enum = UserRole(role.lower())
                query = query.filter(User.role == role_enum)
            except ValueError:
                logger.warning(f"无效的角色值：{role}")
    
        # 状态过滤（排除 DELETED 状态）
        if status:
            try:
                status_enum = UserStatus(status.lower())
                if status_enum != UserStatus.DELETED:
                    query = query.filter(User.status == status_enum)
            except ValueError:
                logger.warning(f"无效的状态值：{status}")
    
        # 分页
        pagination = query.order_by(User.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
    
        # 序列化用户数据
        users_data = [user.to_dict(include_email=True) for user in pagination.items]
    
        return {
            'users': users_data,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    
    @staticmethod
    def get_user(user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户详情
    
        Args:
            user_id: 用户 ID
    
        Returns:
            用户信息字典，如果不存在则返回 None
        """
        try:
            uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id
            user = User.query.filter_by(id=uuid_id).first()
    
            if not user or user.status == UserStatus.DELETED:
                return None
    
            return user.to_dict(include_email=True)
        except Exception as e:
            logger.error(f"获取用户失败：{str(e)}")
            return None
    
    @staticmethod
    def create_user(
        email: str,
        password: str,
        name: str,
        role: str = 'editor',
        must_change_password: bool = True,
        username: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        创建新用户
    
        Args:
            email: 邮箱地址
            password: 明文密码
            name: 用户姓名
            role: 用户角色，默认 'editor'
            must_change_password: 是否必须修改密码，默认 True
            username: 用户名（用于登录，不传则使用 name 自动生成）
    
        Returns:
            (用户信息字典，错误信息) - 成功时错误信息为 None
        """
        # 验证邮箱格式
        if not email or '@' not in email:
            return None, 'invalid_email_address_format'
    
        # 检查邮箱是否已存在
        existing_user = User.query.filter_by(email=email.lower()).first()
        if existing_user:
            return None, 'email_already_registered'
    
        # 处理 username：去空格 + 小写 + 唯一性校验
        final_username = (username or name or '').strip().lower() or None
        if final_username:
            if User.check_username_exists(final_username):
                return None, 'username_already_exists'
    
        # 验证角色有效性
        try:
            role_enum = UserRole(role.lower())
        except ValueError:
            return None, translate('invalid_role', role)
    
        # 验证密码强度（使用安全配置）
        valid, error_msg = SecurityConfigService.validate_password_strength(password)
        if not valid:
            return None, error_msg
    
        try:
            # 创建新用户
            user = User(
                email=email.lower(),
                password=password,
                name=name.strip(),
                username=final_username,
                role=role_enum,
                must_change_password=must_change_password
            )
    
            db.session.add(user)
            db.session.commit()
    
            logger.info(f"创建用户成功：{user.email}")
    
            return user.to_dict(include_email=True), None
    
        except Exception as e:
            db.session.rollback()
            logger.error(f"创建用户失败：{str(e)}")
            return None, 'failed_create_user_try_again_later'
    
    @staticmethod
    def update_user(
        user_id: str,
        data: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        更新用户信息
    
        Args:
            user_id: 用户 ID
            data: 包含更新字段的字典，可包含：
                - email: 邮箱地址
                - username: 用户名
                - name: 用户姓名
                - role: 用户角色
                - status: 用户状态
    
        Returns:
            (用户信息字典，错误信息) - 成功时错误信息为 None
        """
        try:
            uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id
            user = User.query.filter_by(id=uuid_id).first()
    
            if not user or user.status == UserStatus.DELETED:
                return None, 'user_does_not_exist'
    
            # 更新邮箱
            if 'email' in data:
                new_email = data['email'].lower()
                if new_email != user.email:
                    # 检查邮箱是否已被其他用户使用
                    existing = User.query.filter_by(email=new_email).first()
                    if existing and existing.id != user.id:
                        return None, 'email_already_used_another_user'
                    user.email = new_email
    
            # 更新用户名
            if 'username' in data:
                new_username = (data['username'] or '').strip().lower() or None
                if new_username != (user.username or '').lower():
                    # 检查是否已被其他用户使用
                    if User.check_username_exists(new_username, exclude_user_id=user.id):
                        return None, 'username_already_exists'
                    user.username = new_username
    
            # 更新姓名
            if 'name' in data:
                user.name = data['name'].strip()
    
            # 更新角色
            if 'role' in data:
                try:
                    user.role = UserRole(data['role'].lower())
                except ValueError:
                    return None, translate('invalid_role', data["role"])
    
            # 更新状态
            if 'status' in data:
                try:
                    new_status = UserStatus(data['status'].lower())
                    # 不允许直接设置为 DELETED 状态
                    if new_status == UserStatus.DELETED:
                        return None, 'directly_set_user_status_deleted'
                    user.status = new_status
                except ValueError:
                    return None, translate('invalid_status', data["status"])
    
            user.updated_at = datetime.now(timezone.utc)
            db.session.commit()
    
            logger.info(f"更新用户成功：{user.email}")
    
            return user.to_dict(include_email=True), None
    
        except Exception as e:
            db.session.rollback()
            logger.error(f"更新用户失败：{str(e)}")
            return None, 'failed_update_user_try_again_later'
    
    @staticmethod
    def delete_user(user_id: str) -> Tuple[bool, Optional[str]]:
        """
        删除用户（软删除，设置状态为 DELETED）
    
        Args:
            user_id: 用户 ID
    
        Returns:
            (是否成功，错误信息) - 成功时错误信息为 None
        """
        try:
            uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id
            user = User.query.filter_by(id=uuid_id).first()
    
            if not user or user.status == UserStatus.DELETED:
                return False, 'user_does_not_exist'
    
            # 发送账号删除通知（站内信先于邮件，邮件不可用时站内信仍独立工作）
            try:
                NotificationService.send_notification(
                    recipient_email=user.email,
                    recipient_user_id=user.id,
                    template_key='account_deleted',
                    template_data={
                        'user_name': user.name,
                        'operation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'admin_name': '系统管理员'
                    },
                    source='admin'
                )
            except Exception as e:
                logger.error(f'发送账号删除通知邮件失败: {str(e)}')
    
            # 软删除：设置状态为 DELETED
            user.status = UserStatus.DELETED
            user.updated_at = datetime.now(timezone.utc)
            db.session.commit()
    
            logger.info(f"删除用户成功：{user.email}")
    
            return True, None
    
        except Exception as e:
            db.session.rollback()
            logger.error(f"删除用户失败：{str(e)}")
            return False, 'failed_delete_user_try_again_later'
    
    @staticmethod
    def suspend_user(user_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        暂停用户（设置状态为 SUSPENDED，被暂停的用户无法登录）
    
        Args:
            user_id: 用户 ID
    
        Returns:
            (用户信息字典，错误信息) - 成功时错误信息为 None
        """
        try:
            uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id
            user = User.query.filter_by(id=uuid_id).first()
    
            if not user or user.status == UserStatus.DELETED:
                return None, 'user_does_not_exist'
    
            if user.status == UserStatus.SUSPENDED:
                return None, 'user_been_suspended'
    
            user.status = UserStatus.SUSPENDED
            user.updated_at = datetime.now(timezone.utc)
            db.session.commit()
    
            logger.info(f"暂停用户成功：{user.email}")
    
            # 发送账号停用通知（站内信先于邮件，邮件不可用时站内信仍独立工作）
            try:
                NotificationService.send_notification(
                    recipient_email=user.email,
                    recipient_user_id=user.id,
                    template_key='account_suspended',
                    template_data={
                        'user_name': user.name,
                        'operation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'reason': '账号已被管理员暂停使用',
                        'admin_name': '系统管理员'
                    },
                    source='admin'
                )
            except Exception as e:
                logger.error(f'发送账号停用通知邮件失败: {str(e)}')
    
            return user.to_dict(include_email=True), None
    
        except Exception as e:
            db.session.rollback()
            logger.error(f"暂停用户失败：{str(e)}")
            return None, 'failed_suspend_user_try_again_later'
    
    @staticmethod
    def activate_user(user_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        激活用户（设置状态为 ACTIVE）
    
        Args:
            user_id: 用户 ID
    
        Returns:
            (用户信息字典，错误信息) - 成功时错误信息为 None
        """
        try:
            uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id
            user = User.query.filter_by(id=uuid_id).first()
    
            if not user or user.status == UserStatus.DELETED:
                return None, 'user_does_not_exist'
    
            if user.status == UserStatus.ACTIVE:
                return None, 'user_already_active'
    
            user.status = UserStatus.ACTIVE
            user.updated_at = datetime.now(timezone.utc)
            db.session.commit()
    
            logger.info(f"激活用户成功：{user.email}")
    
            # 发送账号启用通知（站内信先于邮件，邮件不可用时站内信仍独立工作）
            try:
                login_link = f"{EmailConfigService.get_frontend_url()}/login"
                NotificationService.send_notification(
                    recipient_email=user.email,
                    recipient_user_id=user.id,
                    template_key='account_activated',
                    template_data={
                        'user_name': user.name,
                        'operation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'login_link': login_link
                    },
                    source='admin'
                )
            except Exception as e:
                logger.error(f'发送账号启用通知邮件失败: {str(e)}')
    
            return user.to_dict(include_email=True), None
    
        except Exception as e:
            db.session.rollback()
            logger.error(f"激活用户失败：{str(e)}")
            return None, 'failed_activate_user_try_again_later'
    
    @staticmethod
    def reset_password(
        user_id: str,
        temporary_password: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        重置用户密码
    
        Args:
            user_id: 用户 ID
            temporary_password: 临时密码，如果不提供则自动生成
    
        Returns:
            (临时密码，错误信息) - 成功时错误信息为 None
        """
        try:
            uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id
            user = User.query.filter_by(id=uuid_id).first()
    
            if not user or user.status == UserStatus.DELETED:
                return None, 'user_does_not_exist'
    
            # 如果没有提供临时密码，则生成随机密码
            if not temporary_password:
                temporary_password = AdminService._generate_temporary_password()
    
            # 验证密码强度（使用安全配置）
            valid, error_msg = SecurityConfigService.validate_password_strength(temporary_password)
            if not valid:
                return None, error_msg
    
            # 设置新密码
            user.set_password(temporary_password)
            user.must_change_password = True
            user.updated_at = datetime.now(timezone.utc)
            db.session.commit()
    
            logger.info(f"重置用户密码成功：{user.email}")
    
            # 发送密码重置通知（站内信先于邮件，邮件不可用时站内信仍独立工作）
            try:
                NotificationService.send_notification(
                    recipient_email=user.email,
                    recipient_user_id=user.id,
                    template_key='password_changed',
                    template_data={
                        'user_name': user.name,
                        'operation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    },
                    source='admin'
                )
            except Exception as e:
                logger.error(f'发送密码重置通知邮件失败: {str(e)}')
    
            return temporary_password, None
    
        except Exception as e:
            db.session.rollback()
            logger.error(f"重置用户密码失败：{str(e)}")
            return None, 'failed_reset_password_try_again_later_2'
    
    @staticmethod
    def log_operation(
        user_id: str,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> OperationLog:
        """
        记录操作日志
    
        Args:
            user_id: 操作用户 ID
            action: 操作类型（create, update, delete, suspend, activate, reset_password 等）
            entity_type: 实体类型（user, config 等）
            entity_id: 实体 ID（可选）
            old_value: 旧值字典（可选）
            new_value: 新值字典（可选）
            ip_address: IP 地址（可选）
            user_agent: 用户代理（可选）
    
        Returns:
            创建的操作日志对象
        """
        try:
            uuid_user_id = UUID(user_id) if isinstance(user_id, str) else user_id
            uuid_entity_id = UUID(entity_id) if entity_id and isinstance(entity_id, str) else entity_id
    
            log = OperationLog.log(
                user_id=uuid_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=uuid_entity_id,
                old_value=old_value,
                new_value=new_value,
                ip_address=ip_address or '',
                user_agent=user_agent
            )
    
            db.session.commit()
    
            return log
    
        except Exception as e:
            db.session.rollback()
            logger.error(f"记录操作日志失败：{str(e)}")
            raise
    
