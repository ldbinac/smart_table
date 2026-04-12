"""
管理员服务模块
处理管理员用户管理系统的所有业务逻辑，包括用户管理、操作日志、系统配置等功能
"""
import csv
import io
import json
import logging
import secrets
import string
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List
from uuid import UUID

from sqlalchemy import or_, and_

from app.extensions import db
from app.models.user import User, UserRole, UserStatus
from app.models.log import OperationLog, AdminActionType, EntityType
from app.models.config import SystemConfig

logger = logging.getLogger(__name__)


class AdminService:
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
        
        # 搜索过滤（邮箱或姓名）
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    User.email.ilike(search_pattern),
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
        must_change_password: bool = True
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        创建新用户
        
        Args:
            email: 邮箱地址
            password: 明文密码
            name: 用户姓名
            role: 用户角色，默认 'editor'
            must_change_password: 是否必须修改密码，默认 True
            
        Returns:
            (用户信息字典，错误信息) - 成功时错误信息为 None
        """
        # 验证邮箱格式
        if not email or '@' not in email:
            return None, '邮箱地址格式不正确'
        
        # 检查邮箱是否已存在
        existing_user = User.query.filter_by(email=email.lower()).first()
        if existing_user:
            return None, '该邮箱已被注册'
        
        # 验证角色有效性
        try:
            role_enum = UserRole(role.lower())
        except ValueError:
            return None, f'无效的角色：{role}'
        
        # 验证密码强度
        if len(password) < 8:
            return None, '密码长度至少为 8 位'
        
        try:
            # 创建新用户
            user = User(
                email=email.lower(),
                password=password,
                name=name.strip(),
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
            return None, f'创建用户失败：{str(e)}'
    
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
                return None, '用户不存在'
            
            # 更新邮箱
            if 'email' in data:
                new_email = data['email'].lower()
                if new_email != user.email:
                    # 检查邮箱是否已被其他用户使用
                    existing = User.query.filter_by(email=new_email).first()
                    if existing and existing.id != user.id:
                        return None, '该邮箱已被其他用户使用'
                    user.email = new_email
            
            # 更新姓名
            if 'name' in data:
                user.name = data['name'].strip()
            
            # 更新角色
            if 'role' in data:
                try:
                    user.role = UserRole(data['role'].lower())
                except ValueError:
                    return None, f'无效的角色：{data["role"]}'
            
            # 更新状态
            if 'status' in data:
                try:
                    new_status = UserStatus(data['status'].lower())
                    # 不允许直接设置为 DELETED 状态
                    if new_status == UserStatus.DELETED:
                        return None, '不能直接设置用户状态为已删除'
                    user.status = new_status
                except ValueError:
                    return None, f'无效的状态：{data["status"]}'
            
            user.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            logger.info(f"更新用户成功：{user.email}")
            
            return user.to_dict(include_email=True), None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"更新用户失败：{str(e)}")
            return None, f'更新用户失败：{str(e)}'
    
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
                return False, '用户不存在'
            
            # 软删除：设置状态为 DELETED
            user.status = UserStatus.DELETED
            user.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            logger.info(f"删除用户成功：{user.email}")
            
            return True, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"删除用户失败：{str(e)}")
            return False, f'删除用户失败：{str(e)}'
    
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
                return None, '用户不存在'
            
            if user.status == UserStatus.SUSPENDED:
                return None, '用户已被暂停'
            
            user.status = UserStatus.SUSPENDED
            user.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            logger.info(f"暂停用户成功：{user.email}")
            
            return user.to_dict(include_email=True), None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"暂停用户失败：{str(e)}")
            return None, f'暂停用户失败：{str(e)}'
    
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
                return None, '用户不存在'
            
            if user.status == UserStatus.ACTIVE:
                return None, '用户已是激活状态'
            
            user.status = UserStatus.ACTIVE
            user.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            logger.info(f"激活用户成功：{user.email}")
            
            return user.to_dict(include_email=True), None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"激活用户失败：{str(e)}")
            return None, f'激活用户失败：{str(e)}'
    
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
                return None, '用户不存在'
            
            # 如果没有提供临时密码，则生成随机密码
            if not temporary_password:
                temporary_password = AdminService._generate_temporary_password()
            
            # 验证密码强度
            if len(temporary_password) < 8:
                return None, '密码长度至少为 8 位'
            
            # 设置新密码
            user.set_password(temporary_password)
            user.must_change_password = True
            user.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            logger.info(f"重置用户密码成功：{user.email}")
            
            return temporary_password, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"重置用户密码失败：{str(e)}")
            return None, f'重置密码失败：{str(e)}'
    
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
    
    @staticmethod
    def get_operation_logs(
        page: int = 1,
        per_page: int = 20,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取分页操作日志
        
        Args:
            page: 页码，从 1 开始
            per_page: 每页数量，默认 20
            user_id: 用户 ID 过滤
            action: 操作类型过滤
            entity_type: 实体类型过滤
            start_date: 开始时间
            end_date: 结束时间
            
        Returns:
            包含日志列表和分页信息的字典
        """
        query = OperationLog.query
        
        # 用户 ID 过滤
        if user_id:
            try:
                uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id
                query = query.filter(OperationLog.user_id == uuid_id)
            except Exception:
                logger.warning(f"无效的用户 ID：{user_id}")
        
        # 操作类型过滤
        if action:
            query = query.filter(OperationLog.action == action)
        
        # 实体类型过滤
        if entity_type:
            query = query.filter(OperationLog.entity_type == entity_type)
        
        # 时间范围过滤
        if start_date:
            query = query.filter(OperationLog.created_at >= start_date)
        if end_date:
            query = query.filter(OperationLog.created_at <= end_date)
        
        # 分页
        pagination = query.order_by(OperationLog.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # 序列化日志数据
        logs_data = [log.to_dict() for log in pagination.items]
        
        return {
            'logs': logs_data,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    
    @staticmethod
    def export_operation_logs(
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """
        导出操作日志为 CSV 格式
        
        Args:
            user_id: 用户 ID 过滤
            action: 操作类型过滤
            entity_type: 实体类型过滤
            start_date: 开始时间
            end_date: 结束时间
            
        Returns:
            CSV 文件内容字符串
        """
        # 构建查询条件
        query = OperationLog.query
        
        if user_id:
            try:
                uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id
                query = query.filter(OperationLog.user_id == uuid_id)
            except Exception:
                logger.warning(f"无效的用户 ID：{user_id}")
        
        if action:
            query = query.filter(OperationLog.action == action)
        
        if entity_type:
            query = query.filter(OperationLog.entity_type == entity_type)
        
        if start_date:
            query = query.filter(OperationLog.created_at >= start_date)
        if end_date:
            query = query.filter(OperationLog.created_at <= end_date)
        
        # 获取所有日志
        logs = query.order_by(OperationLog.created_at.desc()).all()
        
        # 创建 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow([
            '日志 ID',
            '用户 ID',
            '用户姓名',
            '操作类型',
            '实体类型',
            '实体 ID',
            '旧值',
            '新值',
            'IP 地址',
            '创建时间'
        ])
        
        # 写入数据行
        for log in logs:
            writer.writerow([
                str(log.id),
                str(log.user_id) if log.user_id else '',
                log.user.name if log.user else '',
                log.action,
                log.entity_type,
                str(log.entity_id) if log.entity_id else '',
                log.old_value or '',
                log.new_value or '',
                log.ip_address or '',
                log.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return output.getvalue()
    
    @staticmethod
    def get_all_configs() -> Dict[str, Dict[str, Any]]:
        """
        获取所有系统配置，按配置分组
        
        Returns:
            按分组组织的配置字典：{group: {key: value}}
        """
        configs = SystemConfig.query.all()
        
        result = {}
        for config in configs:
            group = config.config_group
            if group not in result:
                result[group] = {}
            result[group][config.config_key] = config.config_value
        
        return result
    
    @staticmethod
    def get_config(key: str) -> Optional[Any]:
        """
        获取配置值
        
        Args:
            key: 配置键
            
        Returns:
            配置值，如果不存在则返回 None
        """
        config = SystemConfig.query.filter_by(config_key=key).first()
        
        if config:
            return config.config_value
        return None
    
    @staticmethod
    def update_config(
        key: str,
        value: Any,
        group: str = 'basic',
        description: Optional[str] = None
    ) -> SystemConfig:
        """
        创建或更新配置
        
        Args:
            key: 配置键
            value: 配置值
            group: 配置分组，默认 'basic'
            description: 配置描述，可选
            
        Returns:
            SystemConfig 配置对象
        """
        config = SystemConfig.query.filter_by(config_key=key).first()
        
        if config:
            # 更新现有配置
            config.config_value = value
            if group:
                config.config_group = group
            if description:
                config.description = description
            config.updated_at = datetime.now(timezone.utc)
        else:
            # 创建新配置
            config = SystemConfig(
                config_key=key,
                config_value=value,
                config_group=group,
                description=description
            )
            db.session.add(config)
        
        db.session.commit()
        
        logger.info(f"更新配置成功：{key}")
        
        return config
    
    @staticmethod
    def delete_config(key: str) -> Tuple[bool, Optional[str]]:
        """
        删除配置
        
        Args:
            key: 配置键
            
        Returns:
            (是否成功，错误信息) - 成功时错误信息为 None
        """
        try:
            config = SystemConfig.query.filter_by(config_key=key).first()
            
            if not config:
                return False, '配置不存在'
            
            db.session.delete(config)
            db.session.commit()
            
            logger.info(f"删除配置成功：{key}")
            
            return True, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"删除配置失败：{str(e)}")
            return False, f'删除配置失败：{str(e)}'