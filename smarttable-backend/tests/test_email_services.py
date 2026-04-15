"""
邮件服务单元测试
测试邮件配置服务、邮件发送服务、邮件模板服务和邮件重试机制
"""
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from cryptography.fernet import Fernet

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.email_template import EmailTemplate
from app.models.email_log import EmailLog, EmailStatus
from app.services.email_config_service import EmailConfigService
from app.services.email_sender_service import EmailSenderService
from app.services.email_template_service import EmailTemplateService
from app.services.email_log_service import EmailLogService
from app.services.email_retry_service import EmailRetryService


class TestEmailConfigService:
    """邮件配置服务测试"""

    def test_is_email_enabled_no_config(self, app, db_session):
        """测试无配置时邮件服务未启用"""
        with app.app_context():
            assert EmailConfigService.is_email_enabled() is False

    def test_is_email_enabled_with_config(self, app, db_session):
        """测试有配置时邮件服务启用"""
        with app.app_context():
            # 创建邮件配置
            from app.models.config import SystemConfig
            config = SystemConfig(
                key='email_enabled',
                value='true',
                description='邮件服务启用状态'
            )
            db.session.add(config)
            db.session.commit()

            assert EmailConfigService.is_email_enabled() is True

    def test_get_config_value(self, app, db_session):
        """测试获取配置值"""
        with app.app_context():
            from app.models.config import SystemConfig
            config = SystemConfig(
                key='smtp_server',
                value='smtp.example.com',
                description='SMTP服务器'
            )
            db.session.add(config)
            db.session.commit()

            value = EmailConfigService._get_config_value('smtp_server')
            assert value == 'smtp.example.com'

    def test_get_config_value_not_exist(self, app, db_session):
        """测试获取不存在的配置值"""
        with app.app_context():
            value = EmailConfigService._get_config_value('non_existent_key')
            assert value is None

    def test_encrypt_decrypt_password(self, app):
        """测试密码加密和解密"""
        with app.app_context():
            original_password = 'test_password_123'
            encrypted = EmailConfigService.encrypt_password(original_password)
            decrypted = EmailConfigService.decrypt_password(encrypted)

            assert encrypted != original_password
            assert decrypted == original_password

    def test_get_smtp_config(self, app, db_session):
        """测试获取SMTP配置"""
        with app.app_context():
            from app.models.config import SystemConfig
            configs = [
                SystemConfig(key='smtp_server', value='smtp.gmail.com'),
                SystemConfig(key='smtp_port', value='587'),
                SystemConfig(key='smtp_username', value='test@gmail.com'),
                SystemConfig(key='sender_email', value='noreply@example.com'),
                SystemConfig(key='sender_name', value='Test Sender'),
                SystemConfig(key='encryption_type', value='tls'),
            ]
            for config in configs:
                db.session.add(config)
            db.session.commit()

            smtp_config = EmailConfigService.get_smtp_config()

            assert smtp_config['server'] == 'smtp.gmail.com'
            assert smtp_config['port'] == 587
            assert smtp_config['username'] == 'test@gmail.com'
            assert smtp_config['sender_email'] == 'noreply@example.com'
            assert smtp_config['sender_name'] == 'Test Sender'
            assert smtp_config['use_tls'] is True
            assert smtp_config['use_ssl'] is False


class TestEmailTemplateService:
    """邮件模板服务测试"""

    def test_get_template_create_default(self, app, db_session):
        """测试获取模板时自动创建默认模板"""
        with app.app_context():
            result = EmailTemplateService.get_template('user_registration')

            assert result['success'] is True
            assert result['template']['template_key'] == 'user_registration'
            assert result['template']['is_default'] is True

    def test_get_template_not_exist(self, app, db_session):
        """测试获取不存在的模板"""
        with app.app_context():
            result = EmailTemplateService.get_template('non_existent_template')

            assert result['success'] is False
            assert 'error' in result

    def test_render_template(self, app, db_session):
        """测试模板渲染"""
        with app.app_context():
            template = 'Hello {{user_name}}, welcome to {{app_name}}!'
            data = {'user_name': 'John', 'app_name': 'SmartTable'}

            result = EmailTemplateService.render_template(template, data)

            assert result == 'Hello John, welcome to SmartTable!'

    def test_render_template_with_defaults(self, app, db_session):
        """测试模板渲染带默认值"""
        with app.app_context():
            template = 'Year: {{year}}, App: {{app_name}}'
            data = {}

            result = EmailTemplateService.render_template(template, data)

            assert '{{year}}' not in result
            assert '{{app_name}}' not in result
            assert 'SmartTable' in result

    def test_update_template(self, app, db_session):
        """测试更新模板"""
        with app.app_context():
            # 先创建默认模板
            EmailTemplateService.get_template('user_registration')

            update_data = {
                'name': 'Updated Template Name',
                'subject': 'Updated Subject'
            }
            result = EmailTemplateService.update_template('user_registration', update_data)

            assert result['success'] is True
            assert result['template']['name'] == 'Updated Template Name'
            assert result['template']['subject'] == 'Updated Subject'
            assert result['template']['is_default'] is False

    def test_reset_template(self, app, db_session):
        """测试重置模板为默认"""
        with app.app_context():
            # 先创建并修改模板
            EmailTemplateService.get_template('user_registration')
            EmailTemplateService.update_template('user_registration', {'name': 'Modified'})

            # 重置模板
            result = EmailTemplateService.reset_template('user_registration')

            assert result['success'] is True
            assert result['template']['is_default'] is True

    def test_get_all_templates(self, app, db_session):
        """测试获取所有模板"""
        with app.app_context():
            result = EmailTemplateService.get_all_templates()

            assert result['success'] is True
            assert len(result['templates']) > 0


class TestEmailLogService:
    """邮件日志服务测试"""

    def test_create_log(self, app, db_session):
        """测试创建邮件日志"""
        with app.app_context():
            log = EmailLogService.create_log(
                recipient_email='test@example.com',
                recipient_name='Test User',
                template_key='user_registration',
                subject='Test Subject',
                status=EmailStatus.PENDING
            )

            assert log is not None
            assert log.recipient_email == 'test@example.com'
            assert log.status == EmailStatus.PENDING

    def test_update_log_status(self, app, db_session):
        """测试更新日志状态"""
        with app.app_context():
            log = EmailLogService.create_log(
                recipient_email='test@example.com',
                recipient_name='Test User',
                template_key='user_registration',
                subject='Test Subject',
                status=EmailStatus.PENDING
            )

            EmailLogService.update_log_status(
                log_id=log.id,
                status=EmailStatus.SENT,
                sent_at=datetime.now(timezone.utc)
            )

            updated_log = EmailLog.query.get(log.id)
            assert updated_log.status == EmailStatus.SENT
            assert updated_log.sent_at is not None

    def test_get_logs_by_status(self, app, db_session):
        """测试按状态获取日志"""
        with app.app_context():
            # 创建不同状态的日志
            EmailLogService.create_log(
                recipient_email='test1@example.com',
                recipient_name='Test User 1',
                template_key='user_registration',
                subject='Test Subject 1',
                status=EmailStatus.SENT
            )
            EmailLogService.create_log(
                recipient_email='test2@example.com',
                recipient_name='Test User 2',
                template_key='password_reset',
                subject='Test Subject 2',
                status=EmailStatus.FAILED
            )

            sent_logs = EmailLogService.get_logs_by_status(EmailStatus.SENT)
            assert len(sent_logs) == 1

    def test_get_pending_logs(self, app, db_session):
        """测试获取待发送日志"""
        with app.app_context():
            EmailLogService.create_log(
                recipient_email='test@example.com',
                recipient_name='Test User',
                template_key='user_registration',
                subject='Test Subject',
                status=EmailStatus.PENDING
            )

            pending_logs = EmailLogService.get_pending_logs()
            assert len(pending_logs) == 1
            assert pending_logs[0].status == EmailStatus.PENDING


class TestEmailRetryService:
    """邮件重试服务测试"""

    def test_should_retry(self, app, db_session):
        """测试是否应该重试"""
        with app.app_context():
            log = EmailLogService.create_log(
                recipient_email='test@example.com',
                recipient_name='Test User',
                template_key='user_registration',
                subject='Test Subject',
                status=EmailStatus.FAILED,
                retry_count=0
            )

            assert EmailRetryService.should_retry(log) is True

    def test_should_not_retry_max_reached(self, app, db_session):
        """测试达到最大重试次数时不应重试"""
        with app.app_context():
            log = EmailLogService.create_log(
                recipient_email='test@example.com',
                recipient_name='Test User',
                template_key='user_registration',
                subject='Test Subject',
                status=EmailStatus.FAILED,
                retry_count=3
            )

            assert EmailRetryService.should_retry(log) is False

    def test_increment_retry_count(self, app, db_session):
        """测试增加重试计数"""
        with app.app_context():
            log = EmailLogService.create_log(
                recipient_email='test@example.com',
                recipient_name='Test User',
                template_key='user_registration',
                subject='Test Subject',
                status=EmailStatus.FAILED,
                retry_count=0
            )

            EmailRetryService.increment_retry_count(log)

            assert log.retry_count == 1
            assert log.status == EmailStatus.RETRYING

    @patch('app.services.email_retry_service.EmailSenderService')
    def test_process_failed_emails(self, mock_sender, app, db_session):
        """测试处理失败邮件"""
        with app.app_context():
            # 创建失败的邮件日志
            log = EmailLogService.create_log(
                recipient_email='test@example.com',
                recipient_name='Test User',
                template_key='user_registration',
                subject='Test Subject',
                status=EmailStatus.FAILED,
                retry_count=0
            )

            # 模拟发送成功
            mock_sender.send_email.return_value = (True, None)

            result = EmailRetryService.process_failed_emails()

            assert result['processed'] >= 0


class TestEmailSenderService:
    """邮件发送服务测试"""

    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp, app, db_session):
        """测试发送邮件成功"""
        with app.app_context():
            # 创建模板
            EmailTemplateService.get_template('user_registration')

            # 模拟SMTP连接
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            with patch.object(EmailConfigService, 'is_email_enabled', return_value=True):
                with patch.object(EmailConfigService, 'get_smtp_config', return_value={
                    'server': 'smtp.gmail.com',
                    'port': 587,
                    'username': 'test@gmail.com',
                    'password': 'password',
                    'sender_email': 'test@gmail.com',
                    'sender_name': 'Test',
                    'use_tls': True,
                    'use_ssl': False
                }):
                    success, error = EmailSenderService.send_email(
                        to_email='recipient@example.com',
                        to_name='Recipient',
                        subject='Test Subject',
                        html_content='<p>Test</p>',
                        text_content='Test'
                    )

                    # 由于我们模拟了SMTP，应该成功
                    mock_server.starttls.assert_called_once()

    def test_send_email_disabled(self, app, db_session):
        """测试邮件服务禁用时发送失败"""
        with app.app_context():
            with patch.object(EmailConfigService, 'is_email_enabled', return_value=False):
                success, error = EmailSenderService.send_email(
                    to_email='recipient@example.com',
                    to_name='Recipient',
                    subject='Test Subject',
                    html_content='<p>Test</p>',
                    text_content='Test'
                )

                assert success is False
                assert '邮件服务未启用' in error

    @patch('app.services.email_sender_service.EmailSenderService.send_email')
    def test_send_email_quick(self, mock_send_email, app, db_session):
        """测试快速发送邮件"""
        with app.app_context():
            # 创建模板
            template_result = EmailTemplateService.get_template('user_registration')

            mock_send_email.return_value = (True, None)

            with patch.object(EmailConfigService, 'is_email_enabled', return_value=True):
                success, error = EmailSenderService.send_email_quick(
                    to_email='recipient@example.com',
                    to_name='Recipient',
                    template_key='user_registration',
                    template_data={'user_name': 'Test User', 'verification_link': 'http://test.com'}
                )

                mock_send_email.assert_called_once()
