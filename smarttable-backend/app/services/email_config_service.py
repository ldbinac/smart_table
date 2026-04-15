"""
邮件配置服务模块
处理邮件配置的读取、解密和管理
"""
import base64
import hashlib
import logging
from typing import Optional, Dict, Any

from cryptography.fernet import Fernet
from flask import current_app

from app.extensions import db
from app.models.config import SystemConfig

logger = logging.getLogger(__name__)


class EmailConfigService:
    """
    邮件配置服务类
    提供邮件配置的读取、解密和验证功能
    """

    # 邮件配置相关的配置键
    CONFIG_EMAIL_ENABLED = 'email_enabled'
    CONFIG_SMTP_HOST = 'smtp_host'
    CONFIG_SMTP_PORT = 'smtp_port'
    CONFIG_SMTP_USERNAME = 'smtp_username'
    CONFIG_SMTP_PASSWORD = 'smtp_password'
    CONFIG_SMTP_USE_TLS = 'smtp_use_tls'
    CONFIG_SMTP_USE_SSL = 'smtp_use_ssl'
    CONFIG_FROM_EMAIL = 'sender_email'  # 前端使用 sender_email
    CONFIG_FROM_NAME = 'sender_name'    # 前端使用 sender_name

    # 默认配置值
    DEFAULT_CONFIG = {
        CONFIG_EMAIL_ENABLED: False,
        CONFIG_SMTP_PORT: 587,
        CONFIG_SMTP_USE_TLS: True,
        CONFIG_SMTP_USE_SSL: False,
        CONFIG_FROM_NAME: 'SmartTable'
    }

    @staticmethod
    def _get_encryption_key(secret_key: str) -> bytes:
        """
        从应用密钥生成 Fernet 加密密钥

        Args:
            secret_key: 应用密钥

        Returns:
            Fernet 加密密钥
        """
        key_hash = hashlib.sha256(secret_key.encode()).digest()
        return base64.urlsafe_b64encode(key_hash)

    @staticmethod
    def decrypt_password(encrypted_password: str, secret_key: Optional[str] = None) -> str:
        """
        解密 SMTP 密码

        Args:
            encrypted_password: 加密后的密码
            secret_key: 应用密钥，如果不提供则从 Flask 配置获取

        Returns:
            明文密码

        Raises:
            ValueError: 解密失败
        """
        try:
            if not secret_key:
                secret_key = current_app.config.get('SECRET_KEY')
                if not secret_key:
                    raise ValueError('未配置 SECRET_KEY')

            key = EmailConfigService._get_encryption_key(secret_key)
            f = Fernet(key)
            decrypted = f.decrypt(encrypted_password.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f'解密 SMTP 密码失败：{str(e)}')
            raise ValueError(f'解密密码失败：{str(e)}')

    @staticmethod
    def encrypt_password(password: str, secret_key: Optional[str] = None) -> str:
        """
        加密 SMTP 密码

        Args:
            password: 明文密码
            secret_key: 应用密钥，如果不提供则从 Flask 配置获取

        Returns:
            加密后的密码字符串

        Raises:
            ValueError: 加密失败
        """
        try:
            if not secret_key:
                secret_key = current_app.config.get('SECRET_KEY')
                if not secret_key:
                    raise ValueError('未配置 SECRET_KEY')

            key = EmailConfigService._get_encryption_key(secret_key)
            f = Fernet(key)
            encrypted = f.encrypt(password.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f'加密 SMTP 密码失败：{str(e)}')
            raise ValueError(f'加密密码失败：{str(e)}')

    @staticmethod
    def get_email_config() -> Dict[str, Any]:
        """
        从 SystemConfig 读取邮件配置并解密密码

        Returns:
            包含邮件配置的字典，包含以下字段：
            - email_enabled: 是否启用邮件服务
            - smtp_host: SMTP 服务器地址
            - smtp_port: SMTP 端口
            - smtp_username: SMTP 用户名
            - smtp_password: 解密后的 SMTP 密码
            - smtp_use_tls: 是否使用 TLS
            - smtp_use_ssl: 是否使用 SSL
            - from_email: 发件人邮箱（映射自 sender_email）
            - from_name: 发件人名称（映射自 sender_name）
        """
        config = EmailConfigService.DEFAULT_CONFIG.copy()

        # 从数据库读取配置
        email_configs = SystemConfig.get_group_configs('email')

        # 更新配置值
        for key, value in email_configs.items():
            config_key = key.replace('email_', '') if key.startswith('email_') else key
            config[config_key] = value

        # 映射前端字段到内部字段
        if 'sender_email' in config:
            config['from_email'] = config['sender_email']
        if 'sender_name' in config:
            config['from_name'] = config['sender_name']

        # 映射 encryption_type 到 smtp_use_tls/smtp_use_ssl
        encryption_type = config.get('encryption_type', 'tls')
        if encryption_type == 'ssl':
            config['smtp_use_ssl'] = True
            config['smtp_use_tls'] = False
        elif encryption_type == 'tls':
            config['smtp_use_ssl'] = False
            config['smtp_use_tls'] = True
        else:  # 'none'
            config['smtp_use_ssl'] = False
            config['smtp_use_tls'] = False

        # 解密密码
        encrypted_password = email_configs.get(EmailConfigService.CONFIG_SMTP_PASSWORD)
        if encrypted_password:
            try:
                config['smtp_password'] = EmailConfigService.decrypt_password(encrypted_password)
            except ValueError:
                # 如果解密失败，可能是明文密码，直接使用
                config['smtp_password'] = encrypted_password
                logger.warning('SMTP 密码解密失败，可能为明文存储')

        # 确保端口为整数
        if 'smtp_port' in config and config['smtp_port']:
            try:
                config['smtp_port'] = int(config['smtp_port'])
            except (ValueError, TypeError):
                config['smtp_port'] = EmailConfigService.DEFAULT_CONFIG[EmailConfigService.CONFIG_SMTP_PORT]

        return config

    @staticmethod
    def is_email_enabled() -> bool:
        """
        检查邮件服务是否启用

        Returns:
            邮件服务是否已启用且配置完整
        """
        enabled = SystemConfig.get_config(EmailConfigService.CONFIG_EMAIL_ENABLED, False)
        if not enabled:
            return False

        # 检查必要的配置是否已设置
        required_configs = [
            EmailConfigService.CONFIG_SMTP_HOST,
            EmailConfigService.CONFIG_SMTP_USERNAME,
            EmailConfigService.CONFIG_SMTP_PASSWORD,
            EmailConfigService.CONFIG_FROM_EMAIL
        ]

        for config_key in required_configs:
            value = SystemConfig.get_config(config_key)
            if not value:
                logger.warning(f'邮件服务配置不完整：缺少 {config_key}')
                return False

        return True

    @staticmethod
    def get_smtp_config() -> Dict[str, Any]:
        """
        获取 SMTP 连接配置

        Returns:
            包含 SMTP 连接配置的字典，包含以下字段：
            - host: SMTP 服务器地址
            - port: SMTP 端口
            - username: SMTP 用户名
            - password: SMTP 密码（已解密）
            - use_tls: 是否使用 TLS
            - use_ssl: 是否使用 SSL
            - timeout: 连接超时时间（秒）
        """
        config = EmailConfigService.get_email_config()

        return {
            'host': config.get('smtp_host', ''),
            'port': config.get('smtp_port', 587),
            'username': config.get('smtp_username', ''),
            'password': config.get('smtp_password', ''),
            'use_tls': config.get('smtp_use_tls', True),
            'use_ssl': config.get('smtp_use_ssl', False),
            'timeout': 30
        }

    @staticmethod
    def get_sender_config() -> Dict[str, str]:
        """
        获取发件人配置

        Returns:
            包含发件人配置的字典，包含以下字段：
            - email: 发件人邮箱
            - name: 发件人名称
        """
        config = EmailConfigService.get_email_config()

        return {
            'email': config.get('from_email', ''),
            'name': config.get('from_name', 'SmartTable')
        }

    @staticmethod
    def get_frontend_url() -> str:
        """
        获取前端应用 URL

        Returns:
            前端应用的基础 URL
        """
        # 优先从配置读取
        frontend_url = SystemConfig.get_config('frontend_url')
        if frontend_url:
            return frontend_url.rstrip('/')
        
        # 默认返回本地开发地址
        return 'http://localhost:5173'

    @staticmethod
    def save_email_config(config_data: Dict[str, Any], secret_key: Optional[str] = None) -> Dict[str, Any]:
        """
        保存邮件配置

        Args:
            config_data: 邮件配置数据
            secret_key: 应用密钥

        Returns:
            包含操作结果的字典
        """
        try:
            # 加密密码
            if 'smtp_password' in config_data and config_data['smtp_password']:
                config_data['smtp_password'] = EmailConfigService.encrypt_password(
                    config_data['smtp_password'],
                    secret_key
                )

            # 保存配置到数据库
            for key, value in config_data.items():
                config_key = f'email_{key}' if not key.startswith('email_') else key
                SystemConfig.set_config(
                    key=config_key,
                    value=value,
                    group='email',
                    description=f'邮件配置: {key}'
                )

            db.session.commit()
            logger.info('邮件配置保存成功')

            return {'success': True, 'message': '配置保存成功'}

        except Exception as e:
            db.session.rollback()
            logger.error(f'保存邮件配置失败：{str(e)}')
            return {'success': False, 'error': f'保存配置失败：{str(e)}'}

    @staticmethod
    def test_config() -> Dict[str, Any]:
        """
        测试当前邮件配置是否有效

        Returns:
            包含测试结果的字典
        """
        if not EmailConfigService.is_email_enabled():
            return {'success': False, 'error': '邮件服务未启用或配置不完整'}

        smtp_config = EmailConfigService.get_smtp_config()

        try:
            import smtplib
            import ssl

            context = ssl.create_default_context()

            if smtp_config['use_ssl']:
                server = smtplib.SMTP_SSL(
                    smtp_config['host'],
                    smtp_config['port'],
                    context=context,
                    timeout=smtp_config['timeout']
                )
            else:
                server = smtplib.SMTP(
                    smtp_config['host'],
                    smtp_config['port'],
                    timeout=smtp_config['timeout']
                )

            with server:
                if not smtp_config['use_ssl'] and smtp_config['use_tls']:
                    server.starttls(context=context)

                server.login(smtp_config['username'], smtp_config['password'])

            logger.info('邮件配置测试成功')
            return {'success': True, 'message': 'SMTP 连接测试成功'}

        except smtplib.SMTPAuthenticationError:
            return {'success': False, 'error': 'SMTP 认证失败，请检查用户名和密码'}
        except smtplib.SMTPConnectError:
            return {'success': False, 'error': '无法连接到 SMTP 服务器，请检查服务器地址和端口'}
        except smtplib.SMTPException as e:
            return {'success': False, 'error': f'SMTP 错误：{str(e)}'}
        except Exception as e:
            logger.error(f'测试邮件配置失败：{str(e)}')
            return {'success': False, 'error': f'测试失败：{str(e)}'}
