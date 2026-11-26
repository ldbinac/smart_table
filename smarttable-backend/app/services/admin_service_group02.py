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

class AdminServiceGroup02Mixin:
    """Mixin auto-split"""
    
    """
    管理员服务类
    提供用户管理、操作日志记录、系统配置管理等所有管理员相关功能
    """
    
    
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
        获取所有系统配置，按配置分组（优先缓存）
    
        Returns:
            按分组组织的配置字典：{group: {key: value}}
        """
        return ConfigCacheService.get_all_configs()
    
    @staticmethod
    def get_config(key: str) -> Optional[Any]:
        """
        获取配置值（优先缓存）
    
        Args:
            key: 配置键
    
        Returns:
            配置值，如果不存在则返回 None
        """
        return ConfigCacheService.get_config(key)
    
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
    
        # 失效配置缓存
        ConfigCacheService.invalidate_config_cache(key)
    
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
                return False, 'configuration_does_not_exist'
    
            db.session.delete(config)
            db.session.commit()
    
            logger.info(f"删除配置成功：{key}")
    
            # 失效配置缓存
            ConfigCacheService.invalidate_config_cache(key)
    
            return True, None
    
        except Exception as e:
            db.session.rollback()
            logger.error(f"删除配置失败：{str(e)}")
            return False, 'failed_delete_configuration_try_again_later'
    
    @staticmethod
    def encrypt_smtp_password(password: str, secret_key: str) -> str:
        """
        使用应用密钥加密 SMTP 密码
    
        Args:
            password: 明文密码
            secret_key: 应用密钥
    
        Returns:
            加密后的密码字符串
        """
        try:
            return encrypt_secret(password, secret_key)
        except Exception as e:
            logger.error(f"加密 SMTP 密码失败：{str(e)}")
            raise
    
    @staticmethod
    def decrypt_smtp_password(encrypted_password: str, secret_key: str) -> str:
        """
        解密 SMTP 密码
    
        Args:
            encrypted_password: 加密后的密码
            secret_key: 应用密钥
    
        Returns:
            明文密码
        """
        try:
            return decrypt_secret(encrypted_password, secret_key)
        except Exception as e:
            logger.error(f"解密 SMTP 密码失败：{str(e)}")
            raise
    
    @staticmethod
    def verify_email_config(config_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        验证 SMTP 配置是否有效
    
        Args:
            config_data: 邮件配置数据，包含：
                - smtp_host: SMTP 服务器地址
                - smtp_port: SMTP 端口
                - smtp_username: SMTP 用户名
                - smtp_password: SMTP 密码（明文或加密）
                - smtp_use_tls: 是否使用 TLS（可选，默认 True）
                - smtp_use_ssl: 是否使用 SSL（可选，默认 False）
                - from_email: 发件人邮箱
    
        Returns:
            (是否有效，错误信息) - 有效时错误信息为 None
        """
        required_fields = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'from_email']
    
        for field in required_fields:
            if field not in config_data or not config_data[field]:
                return False, translate('missing_required_field', field)
    
        try:
            smtp_host = config_data['smtp_host']
            smtp_port = int(config_data['smtp_port'])
            smtp_username = config_data['smtp_username']
            smtp_password = config_data['smtp_password']
            smtp_use_tls = config_data.get('smtp_use_tls', True)
            smtp_use_ssl = config_data.get('smtp_use_ssl', False)
    
            if smtp_port < 1 or smtp_port > 65535:
                return False, 'smtp_port_between'
    
            context = ssl.create_default_context()
    
            if smtp_use_ssl:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=10)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
    
            with server:
                if not smtp_use_ssl and smtp_use_tls:
                    server.starttls(context=context)
    
                server.login(smtp_username, smtp_password)
    
            logger.info(f"SMTP 配置验证成功：{smtp_host}:{smtp_port}")
            return True, None
        except smtplib.SMTPConnectError:
            return False, 'connect_smtp_server_check_server_address_port'
        except smtplib.SMTPException:
            return False, 'smtp_connection_error_check_configuration'
        except ValueError:
            return False, 'invalid_smtp_port_format'
        except Exception as e:
            logger.error(f"验证 SMTP 配置失败：{str(e)}")
            return False, 'verification_failed_try_again_later'
    
    @staticmethod
    def send_test_email(config_data: Dict[str, Any], test_email: str, secret_key: str) -> Tuple[bool, Optional[str]]:
        """
        发送测试邮件
    
        Args:
            config_data: 邮件配置数据，包含：
                - smtp_host: SMTP 服务器地址
                - smtp_port: SMTP 端口
                - smtp_username: SMTP 用户名
                - smtp_password: SMTP 密码（明文或加密）
                - smtp_use_tls: 是否使用 TLS（可选，默认 True）
                - smtp_use_ssl: 是否使用 SSL（可选，默认 False）
                - from_email: 发件人邮箱
                - from_name: 发件人名称（可选）
            test_email: 测试邮件接收地址
            secret_key: 应用密钥（用于解密密码）
    
        Returns:
            (是否成功，错误信息) - 成功时错误信息为 None
        """
        required_fields = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'from_email']
    
        for field in required_fields:
            if field not in config_data or not config_data[field]:
                return False, translate('missing_required_field', field)
    
        if not test_email or '@' not in test_email:
            return False, 'invalid_test_email_address_format'
    
        try:
            smtp_host = config_data['smtp_host']
            smtp_port = int(config_data['smtp_port'])
            smtp_username = config_data['smtp_username']
            smtp_password = config_data['smtp_password']
            smtp_use_tls = config_data.get('smtp_use_tls', True)
            smtp_use_ssl = config_data.get('smtp_use_ssl', False)
            from_email = config_data['from_email']
            from_name = config_data.get('from_name', 'SmartTable')
    
            # 尝试解密密码（如果已加密）
            try:
                decrypted_password = AdminService.decrypt_smtp_password(smtp_password, secret_key)
            except Exception:
                decrypted_password = smtp_password
    
            subject = 'SmartTable 邮件配置测试'
            body = f'''
您好！
    
这是一封测试邮件，用于验证 SmartTable 系统的邮件配置是否正确。
    
配置信息：
- SMTP 服务器：{smtp_host}:{smtp_port}
- 发件人：{from_email}
- 发送时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
    
如果您收到此邮件，说明邮件配置已成功生效。
    
此邮件由系统自动发送，请勿回复。
            '''.strip()
    
            msg = MIMEText(body, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = f'{from_name} <{from_email}>'
            msg['To'] = test_email
    
            context = ssl.create_default_context()
    
            if smtp_use_ssl:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=10)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
    
            with server:
                if not smtp_use_ssl and smtp_use_tls:
                    server.starttls(context=context)
    
                server.login(smtp_username, decrypted_password)
                server.sendmail(from_email, [test_email], msg.as_string())
    
            logger.info(f"测试邮件发送成功：{test_email}")
            return True, None
        except smtplib.SMTPConnectError:
            return False, 'connect_smtp_server_check_server_address_port'
        except smtplib.SMTPRecipientsRefused:
            return False, 'recipient_address_was_rejected'
        except smtplib.SMTPException:
            return False, 'smtp_connection_error_check_configuration'
        except Exception as e:
            logger.error(f"发送测试邮件失败：{str(e)}")
            return False, 'sending_failed_try_again_later'
    
