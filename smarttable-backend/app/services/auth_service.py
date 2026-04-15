"""
认证服务模块
处理用户认证相关的业务逻辑，包括注册、登录、令牌管理、密码修改等功能
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any
from uuid import UUID

from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt_identity
)

from app.extensions import db, cache
from app.models.user import User, TokenBlocklist, UserStatus
from app.services.email_config_service import EmailConfigService
from app.services.email_sender_service import EmailSenderService
from app.services.email_template_service import EmailTemplateService


class AuthService:
    """
    认证服务类
    提供用户认证相关的所有业务逻辑
    """
    
    # 访问令牌过期时间（秒）
    ACCESS_TOKEN_EXPIRES = 86400  # 24 小时
    # 刷新令牌过期时间（秒）
    REFRESH_TOKEN_EXPIRES = 2592000  # 30 天
    
    @staticmethod
    def register_user(email: str, password: str, name: str) -> Tuple[Optional[User], Optional[str]]:
        """
        用户注册
        
        Args:
            email: 邮箱地址
            password: 明文密码
            name: 用户姓名
            
        Returns:
            (用户对象, 错误信息) - 成功时错误信息为 None
        """
        # 检查邮箱是否已存在
        existing_user = User.query.filter_by(email=email.lower()).first()
        if existing_user:
            return None, '该邮箱已被注册'
        
        try:
            # 创建新用户
            user = User(
                email=email.lower(),
                password=password,
                name=name.strip()
            )
            
            db.session.add(user)
            db.session.commit()
            
            # 生成验证令牌
            verification_token = user.generate_verification_token()
            
            # 如果邮件服务启用，发送验证邮件
            if EmailConfigService.is_email_enabled():
                try:
                    verification_link = f"{EmailConfigService.get_frontend_url()}/verify-email?token={verification_token}"
                    EmailSenderService.send_email_quick(
                        to_email=user.email,
                        to_name=user.name,
                        template_key='user_registration',
                        template_data={
                            'user_name': user.name,
                            'verification_link': verification_link
                        }
                    )
                except Exception as e:
                    # 邮件发送失败不影响注册流程，记录错误即可
                    from flask import current_app
                    current_app.logger.error(f'发送验证邮件失败: {str(e)}')
            
            return user, None
            
        except Exception as e:
            db.session.rollback()
            return None, f'注册失败: {str(e)}'
    
    @staticmethod
    def authenticate_user(email: str, password: str) -> Tuple[Optional[User], Optional[str]]:
        """
        验证用户凭据
        
        Args:
            email: 邮箱地址
            password: 密码
            
        Returns:
            (用户对象, 错误信息) - 成功时错误信息为 None
        """
        user = User.query.filter_by(email=email.lower()).first()
        
        if not user:
            return None, '邮箱或密码错误'
        
        if not user.check_password(password):
            return None, '邮箱或密码错误'
        
        if not user.is_active():
            return None, '账号已被禁用，请联系管理员'
        
        return user, None
    
    @staticmethod
    def generate_tokens(user_id: str) -> Dict[str, Any]:
        """
        生成访问令牌和刷新令牌
        
        Args:
            user_id: 用户 ID
            
        Returns:
            包含令牌信息的字典
        """
        # 获取当前令牌版本号
        cache_key = f"user_token_version:{user_id}"
        token_version = cache.get(cache_key) or 0
        
        # 创建访问令牌（短期有效），包含版本号
        access_token = create_access_token(
            identity=user_id,
            expires_delta=timedelta(seconds=AuthService.ACCESS_TOKEN_EXPIRES),
            additional_claims={'token_version': token_version}
        )
        
        # 创建刷新令牌（长期有效），包含版本号
        refresh_token = create_refresh_token(
            identity=user_id,
            expires_delta=timedelta(seconds=AuthService.REFRESH_TOKEN_EXPIRES),
            additional_claims={'token_version': token_version}
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': AuthService.ACCESS_TOKEN_EXPIRES
        }
    
    @staticmethod
    def refresh_access_token(user_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        刷新访问令牌
        
        Args:
            user_id: 用户 ID
            
        Returns:
            (新的访问令牌, 错误信息) - 成功时错误信息为 None
        """
        # 验证用户是否存在且状态正常
        user = User.query.get(user_id)
        
        if not user:
            return None, '用户不存在'
        
        if not user.is_active():
            return None, '用户账号已被禁用'
        
        # 生成新的访问令牌
        access_token = create_access_token(
            identity=user_id,
            expires_delta=timedelta(seconds=AuthService.ACCESS_TOKEN_EXPIRES)
        )
        
        return access_token, None
    
    @staticmethod
    def revoke_token(jti: str, user_id: str, token_type: str = 'access', 
                     expires_at: Optional[datetime] = None) -> bool:
        """
        撤销令牌（加入黑名单）
        
        Args:
            jti: 令牌唯一标识
            user_id: 用户 ID
            token_type: 令牌类型（access 或 refresh）
            expires_at: 令牌过期时间
            
        Returns:
            是否成功撤销
        """
        try:
            # 如果没有提供过期时间，使用默认时间
            if expires_at is None:
                expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            
            # 创建黑名单记录
            token_block = TokenBlocklist(
                jti=jti,
                token_type=token_type,
                user_id=user_id,
                expires_at=expires_at
            )
            
            db.session.add(token_block)
            db.session.commit()
            
            # 同时缓存到 Redis 以提高检查效率
            cache_key = f"token_blacklist:{jti}"
            cache.set(cache_key, True, timeout=int((expires_at - datetime.now(timezone.utc)).total_seconds()))
            
            return True
            
        except Exception as e:
            db.session.rollback()
            return False
    
    @staticmethod
    def revoke_all_user_tokens(user_id: str) -> bool:
        """
        撤销用户的所有令牌（用于密码修改等安全场景）
        
        Args:
            user_id: 用户 ID
            
        Returns:
            是否成功
        """
        try:
            # 这里可以记录一个用户级别的令牌版本号
            # 所有令牌验证时都需要检查版本号
            cache_key = f"user_token_version:{user_id}"
            current_version = cache.get(cache_key) or 0
            cache.set(cache_key, current_version + 1, timeout=2592000)  # 30 天
            
            return True
            
        except Exception as e:
            return False
    
    @staticmethod
    def is_token_revoked(jti: str) -> bool:
        """
        检查令牌是否已被撤销
        
        Args:
            jti: 令牌唯一标识
            
        Returns:
            是否已被撤销
        """
        # 先检查缓存
        cache_key = f"token_blacklist:{jti}"
        if cache.get(cache_key):
            return True
        
        # 再检查数据库
        token = TokenBlocklist.query.filter_by(jti=jti).first()
        return token is not None
    
    @staticmethod
    def change_password(user_id: str, old_password: str, new_password: str, ip_address: str = None, user_agent: str = None) -> Tuple[bool, Optional[str]]:
        """
        修改用户密码

        Args:
            user_id: 用户 ID
            old_password: 旧密码
            new_password: 新密码
            ip_address: 客户端IP地址（用于日志记录）
            user_agent: 客户端User-Agent（用于日志记录）

        Returns:
            (是否成功, 错误信息)
        """
        from app.models.operation_history import OperationHistory

        user = User.query.get(user_id)

        if not user:
            # 记录操作日志 - 用户不存在
            OperationHistory.log(
                user_id=user_id,
                resource_type='user',
                resource_id=user_id,
                operation_type='password_change_failed',
                detail={'reason': 'user_not_found', 'ip': ip_address},
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.session.commit()
            return False, '用户不存在'

        # 验证旧密码
        if not user.check_password(old_password):
            # 记录操作日志 - 旧密码错误
            OperationHistory.log(
                user_id=user.id,
                resource_type='user',
                resource_id=str(user.id),
                operation_type='password_change_failed',
                detail={'reason': 'invalid_old_password', 'email': user.email, 'ip': ip_address},
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.session.commit()
            return False, '旧密码错误'

        try:
            # 设置新密码
            user.set_password(new_password)

            # 撤销用户的所有令牌，强制重新登录
            AuthService.revoke_all_user_tokens(user_id)

            # 记录操作日志 - 密码修改成功
            OperationHistory.log(
                user_id=user.id,
                resource_type='user',
                resource_id=str(user.id),
                operation_type='password_changed',
                detail={'email': user.email, 'ip': ip_address},
                ip_address=ip_address,
                user_agent=user_agent
            )

            db.session.commit()

            # 发送密码修改通知邮件
            from app.services.email_config_service import EmailConfigService
            from app.services.email_sender_service import EmailSenderService

            if EmailConfigService.is_email_enabled():
                try:
                    EmailSenderService.send_email_quick(
                        to_email=user.email,
                        to_name=user.name,
                        template_key='password_changed',
                        template_data={
                            'user_name': user.name,
                            'operation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                    )
                except Exception as e:
                    logger.error(f'发送密码修改通知邮件失败: {str(e)}')

            return True, None

        except Exception as e:
            db.session.rollback()

            # 记录操作日志 - 系统错误
            OperationHistory.log(
                user_id=user.id,
                resource_type='user',
                resource_id=str(user.id),
                operation_type='password_change_error',
                detail={'error': str(e), 'email': user.email, 'ip': ip_address},
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.session.commit()

            return False, f'密码修改失败: {str(e)}'
    
    @staticmethod
    def get_current_user(user_id: str) -> Optional[User]:
        """
        获取当前用户信息
        
        Args:
            user_id: 用户 ID
            
        Returns:
            用户对象，如果不存在则返回 None
        """
        try:
            # 将字符串ID转换为UUID对象
            uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id
            return User.query.get(uuid_id)
        except Exception:
            return None
    
    @staticmethod
    def update_last_login(user_id: str) -> bool:
        """
        更新用户最后登录时间

        Args:
            user_id: 用户 ID

        Returns:
            是否成功
        """
        try:
            # 将字符串ID转换为UUID对象
            uuid_id = UUID(user_id) if isinstance(user_id, str) else user_id

            # 使用 filter_by 而不是 get，避免 SQLAlchemy 2.0 的兼容性问题
            user = User.query.filter_by(id=uuid_id).first()

            if not user:
                return False

            # 直接更新字段并提交，避免嵌套事务问题
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False
    
    @staticmethod
    def check_email_exists(email: str) -> bool:
        """
        检查邮箱是否已存在
        
        Args:
            email: 邮箱地址
            
        Returns:
            是否存在
        """
        return User.query.filter_by(email=email.lower()).first() is not None
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """
        通过邮箱获取用户
        
        Args:
            email: 邮箱地址
            
        Returns:
            用户对象，如果不存在则返回 None
        """
        return User.query.filter_by(email=email.lower()).first()
    
    @staticmethod
    def logout_user(jti: str, user_id: str, token_type: str = 'access') -> Tuple[bool, Optional[str]]:
        """
        用户登出，撤销当前令牌
        
        Args:
            jti: 令牌唯一标识
            user_id: 用户 ID
            token_type: 令牌类型
            
        Returns:
            (是否成功, 错误信息)
        """
        success = AuthService.revoke_token(jti, user_id, token_type)
        
        if success:
            return True, None
        else:
            return False, '登出失败，请稍后重试'
    
    @staticmethod
    def cleanup_expired_tokens() -> int:
        """
        清理过期的黑名单令牌记录
        
        Returns:
            清理的记录数
        """
        try:
            expired_tokens = TokenBlocklist.query.filter(
                TokenBlocklist.expires_at < datetime.now(timezone.utc)
            ).all()
            
            count = len(expired_tokens)
            
            for token in expired_tokens:
                db.session.delete(token)
            
            db.session.commit()
            
            return count
            
        except Exception as e:
            db.session.rollback()
            return 0
    
    @staticmethod
    def validate_token_version(user_id: str, token_version: int) -> bool:
        """
        验证令牌版本（用于检查令牌是否因密码修改等原因失效）
        
        Args:
            user_id: 用户 ID
            token_version: 令牌中的版本号
            
        Returns:
            是否有效
        """
        cache_key = f"user_token_version:{user_id}"
        current_version = cache.get(cache_key) or 0
        
        return token_version >= current_version
