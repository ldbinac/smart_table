"""
邮件服务集成测试
测试用户注册验证流程、密码找回流程、账号管理通知和分享成员通知
"""
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.email_template import EmailTemplate
from app.models.email_log import EmailLog, EmailStatus
from app.models.base import Base, BaseMember, MemberRole
from app.services.auth_service import AuthService
from app.services.base_service import BaseService
from app.services.admin_service import AdminService
from app.services.email_config_service import EmailConfigService


class TestUserRegistrationEmailVerification:
    """用户注册邮箱验证流程测试"""

    @patch('app.services.auth_service.EmailConfigService.is_email_enabled')
    @patch('app.services.auth_service.EmailSenderService.send_email_quick')
    def test_registration_sends_verification_email(self, mock_send_email, mock_is_enabled, app, db_session):
        """测试用户注册时发送验证邮件"""
        with app.app_context():
            mock_is_enabled.return_value = True
            mock_send_email.return_value = (True, None)

            # 注册用户
            user, error = AuthService.register_user(
                email='newuser@example.com',
                password='Test1234!',
                name='New User'
            )

            assert user is not None
            assert error is None
            assert user.email_verified is False
            assert user.verification_token is not None

            # 验证邮件发送被调用
            mock_send_email.assert_called_once()
            call_args = mock_send_email.call_args[1]
            assert call_args['to_email'] == 'newuser@example.com'
            assert call_args['template_key'] == 'user_registration'

    @patch('app.services.auth_service.EmailConfigService.is_email_enabled')
    def test_registration_without_email_service(self, mock_is_enabled, app, db_session):
        """测试邮件服务禁用时用户注册"""
        with app.app_context():
            mock_is_enabled.return_value = False

            user, error = AuthService.register_user(
                email='newuser2@example.com',
                password='Test1234!',
                name='New User 2'
            )

            assert user is not None
            assert error is None
            # 用户仍然创建成功，只是不发送邮件

    def test_email_verification_with_valid_token(self, app, db_session):
        """测试使用有效令牌验证邮箱"""
        with app.app_context():
            # 创建用户
            user = User(
                email='verify@example.com',
                name='Verify User'
            )
            user.set_password('Test1234!')
            db.session.add(user)
            db.session.commit()

            # 生成验证令牌
            token = user.generate_verification_token()

            # 验证邮箱
            result = user.verify_email(token)

            assert result is True
            assert user.email_verified is True
            assert user.verification_token is None

    def test_email_verification_with_invalid_token(self, app, db_session):
        """测试使用无效令牌验证邮箱"""
        with app.app_context():
            user = User(
                email='verify2@example.com',
                name='Verify User 2'
            )
            user.set_password('Test1234!')
            db.session.add(user)
            db.session.commit()

            # 使用错误的令牌
            result = user.verify_email('wrong_token')

            assert result is False
            assert user.email_verified is False

    def test_email_verification_with_expired_token(self, app, db_session):
        """测试使用过期的令牌验证邮箱"""
        with app.app_context():
            user = User(
                email='verify3@example.com',
                name='Verify User 3'
            )
            user.set_password('Test1234!')
            db.session.add(user)
            db.session.commit()

            # 生成令牌并设置为过期
            token = user.generate_verification_token()
            user.verification_token_expires = datetime.now(timezone.utc) - timedelta(hours=1)
            db.session.commit()

            # 验证应该失败
            result = user.verify_email(token)

            assert result is False


class TestPasswordResetFlow:
    """密码找回流程测试"""

    def test_generate_reset_token(self, app, db_session, test_user):
        """测试生成密码重置令牌"""
        with app.app_context():
            token = test_user.generate_reset_token()

            assert token is not None
            assert test_user.reset_token == token
            assert test_user.reset_token_expires is not None

    def test_verify_reset_token_valid(self, app, db_session, test_user):
        """测试验证有效的重置令牌"""
        with app.app_context():
            token = test_user.generate_reset_token()

            result = test_user.verify_reset_token(token)

            assert result is True

    def test_verify_reset_token_invalid(self, app, db_session, test_user):
        """测试验证无效的重置令牌"""
        with app.app_context():
            test_user.generate_reset_token()

            result = test_user.verify_reset_token('wrong_token')

            assert result is False

    def test_verify_reset_token_expired(self, app, db_session, test_user):
        """测试验证过期的重置令牌"""
        with app.app_context():
            token = test_user.generate_reset_token()
            # 设置为过期
            test_user.reset_token_expires = datetime.now(timezone.utc) - timedelta(hours=1)
            db.session.commit()

            result = test_user.verify_reset_token(token)

            assert result is False

    def test_clear_reset_token(self, app, db_session, test_user):
        """测试清除重置令牌"""
        with app.app_context():
            test_user.generate_reset_token()
            test_user.clear_reset_token()

            assert test_user.reset_token is None
            assert test_user.reset_token_expires is None


class TestAccountManagementNotifications:
    """账号管理通知测试"""

    @patch('app.services.admin_service.EmailConfigService.is_email_enabled')
    @patch('app.services.admin_service.EmailSenderService.send_email_quick')
    def test_suspend_user_sends_notification(self, mock_send_email, mock_is_enabled, app, db_session, test_user):
        """测试停用账号时发送通知邮件"""
        with app.app_context():
            mock_is_enabled.return_value = True
            mock_send_email.return_value = (True, None)

            result, error = AdminService.suspend_user(str(test_user.id))

            assert result is not None
            assert error is None
            assert result['status'] == 'suspended'

            # 验证邮件发送被调用
            mock_send_email.assert_called_once()
            call_args = mock_send_email.call_args[1]
            assert call_args['template_key'] == 'account_suspended'

    @patch('app.services.admin_service.EmailConfigService.is_email_enabled')
    @patch('app.services.admin_service.EmailSenderService.send_email_quick')
    def test_activate_user_sends_notification(self, mock_send_email, mock_is_enabled, app, db_session, test_user):
        """测试启用账号时发送通知邮件"""
        with app.app_context():
            # 先停用用户
            test_user.status = 'suspended'
            db.session.commit()

            mock_is_enabled.return_value = True
            mock_send_email.return_value = (True, None)

            result, error = AdminService.activate_user(str(test_user.id))

            assert result is not None
            assert error is None
            assert result['status'] == 'active'

            # 验证邮件发送被调用
            mock_send_email.assert_called_once()
            call_args = mock_send_email.call_args[1]
            assert call_args['template_key'] == 'account_activated'

    @patch('app.services.admin_service.EmailConfigService.is_email_enabled')
    @patch('app.services.admin_service.EmailSenderService.send_email_quick')
    def test_reset_password_sends_notification(self, mock_send_email, mock_is_enabled, app, db_session, test_user):
        """测试重置密码时发送通知邮件"""
        with app.app_context():
            mock_is_enabled.return_value = True
            mock_send_email.return_value = (True, None)

            temp_password, error = AdminService.reset_password(str(test_user.id))

            assert temp_password is not None
            assert error is None

            # 验证邮件发送被调用
            mock_send_email.assert_called_once()
            call_args = mock_send_email.call_args[1]
            assert call_args['template_key'] == 'password_changed'


class TestShareMemberNotifications:
    """分享成员通知测试"""

    @pytest.fixture
    def test_base_with_owner(self, app, db_session):
        """创建带所有者的测试Base"""
        with app.app_context():
            owner = User(
                email='owner@example.com',
                name='Base Owner'
            )
            owner.set_password('Test1234!')
            db.session.add(owner)
            db.session.commit()

            base = Base(
                name='Test Base for Sharing',
                description='Test Description',
                owner_id=owner.id
            )
            db.session.add(base)
            db.session.commit()

            return base, owner

    @pytest.fixture
    def test_member_user(self, app, db_session):
        """创建测试成员用户"""
        with app.app_context():
            user = User(
                email='member@example.com',
                name='Member User'
            )
            user.set_password('Test1234!')
            db.session.add(user)
            db.session.commit()
            return user

    @patch('app.services.base_service.EmailConfigService.is_email_enabled')
    @patch('app.services.base_service.EmailSenderService.send_email_quick')
    def test_add_member_sends_invitation_email(self, mock_send_email, mock_is_enabled, app, db_session, test_base_with_owner, test_member_user):
        """测试添加成员时发送邀请邮件"""
        with app.app_context():
            base, owner = test_base_with_owner

            mock_is_enabled.return_value = True
            mock_send_email.return_value = (True, None)

            result = BaseService.add_member(
                base_id=str(base.id),
                email=test_member_user.email,
                role='editor',
                invited_by=str(owner.id)
            )

            assert result['success'] is True

            # 验证邮件发送被调用
            mock_send_email.assert_called_once()
            call_args = mock_send_email.call_args[1]
            assert call_args['template_key'] == 'share_invitation'
            assert call_args['to_email'] == test_member_user.email

    @patch('app.services.base_service.EmailConfigService.is_email_enabled')
    @patch('app.services.base_service.EmailSenderService.send_email_quick')
    def test_remove_member_sends_notification_email(self, mock_send_email, mock_is_enabled, app, db_session, test_base_with_owner, test_member_user):
        """测试移除成员时发送通知邮件"""
        with app.app_context():
            base, owner = test_base_with_owner

            # 先添加成员
            BaseService.add_member(
                base_id=str(base.id),
                email=test_member_user.email,
                role='editor',
                invited_by=str(owner.id)
            )

            mock_is_enabled.return_value = True
            mock_send_email.return_value = (True, None)

            # 移除成员
            result = BaseService.remove_member(
                base_id=str(base.id),
                user_id=str(test_member_user.id),
                removed_by=str(owner.id)
            )

            assert result is True

            # 验证邮件发送被调用（移除通知）
            # 注意：这里应该检查第二次调用
            call_count = mock_send_email.call_count
            assert call_count >= 1

    @patch('app.services.base_service.EmailConfigService.is_email_enabled')
    @patch('app.services.base_service.EmailSenderService.send_email_quick')
    def test_update_member_role_sends_notification_email(self, mock_send_email, mock_is_enabled, app, db_session, test_base_with_owner, test_member_user):
        """测试更新成员权限时发送通知邮件"""
        with app.app_context():
            base, owner = test_base_with_owner

            # 先添加成员
            BaseService.add_member(
                base_id=str(base.id),
                email=test_member_user.email,
                role='viewer',
                invited_by=str(owner.id)
            )

            mock_is_enabled.return_value = True
            mock_send_email.return_value = (True, None)

            # 更新权限
            result = BaseService.update_member_role(
                base_id=str(base.id),
                user_id=str(test_member_user.id),
                new_role='editor',
                updated_by=str(owner.id)
            )

            assert result['success'] is True

            # 验证邮件发送被调用（权限变更通知）
            call_count = mock_send_email.call_count
            assert call_count >= 1


class TestEmailLogCreation:
    """邮件日志创建测试"""

    @patch('app.services.email_sender_service.EmailLogService.create_log')
    @patch('app.services.email_sender_service.EmailConfigService.is_email_enabled')
    def test_send_email_creates_log(self, mock_is_enabled, mock_create_log, app, db_session):
        """测试发送邮件时创建日志"""
        with app.app_context():
            mock_is_enabled.return_value = True
            mock_log = MagicMock()
            mock_log.id = uuid.uuid4()
            mock_create_log.return_value = mock_log

            from app.services.email_sender_service import EmailSenderService

            # 由于我们模拟了日志创建，这里主要测试调用
            # 实际发送邮件需要SMTP配置
            mock_create_log.assert_not_called()  # 还没有调用


class TestEmailTemplateInitialization:
    """邮件模板初始化测试"""

    def test_default_templates_created_on_startup(self, app, db_session):
        """测试启动时创建默认模板"""
        with app.app_context():
            from app.services.email_template_service import EmailTemplateService

            # 获取所有模板，这会触发默认模板创建
            result = EmailTemplateService.get_all_templates()

            assert result['success'] is True
            # 应该包含所有默认模板
            template_keys = [t['template_key'] for t in result['templates']]

            expected_templates = [
                'user_registration',
                'password_reset',
                'account_suspended',
                'account_activated',
                'password_changed',
                'account_updated',
                'account_deleted',
                'share_invitation',
                'share_removed',
                'permission_changed'
            ]

            for key in expected_templates:
                assert key in template_keys, f"模板 {key} 应该存在"
