"""
站内信通知服务单元测试
测试 NotificationService 与 NotificationRetryService 的核心功能：
站内信发送、邮件协同顺序、已读管理、查询过滤、统计与重试机制
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models.notification import Notification, NotificationStatus
from app.services.notification_service import NotificationService
from app.services.notification_retry_service import NotificationRetryService
from app.services.email_sender_service import EmailSenderService
from app.services.email_config_service import EmailConfigService


@pytest.fixture(scope='function')
def app():
    """覆盖 conftest 的 app fixture：去重 Notification 模型的重复索引定义。

    Notification 模型同时声明了列级 index=True 与 __table_args__ 中的显式 Index
    （同名），导致 SQLite create_all 时重复创建索引报错。此处按索引名去重。
    """
    table = Notification.__table__
    seen_names = set()
    deduped = set()
    for idx in list(table.indexes):
        if idx.name not in seen_names:
            seen_names.add(idx.name)
            deduped.add(idx)
    table.indexes = deduped

    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


class TestNotificationServiceSend:
    """站内信发送服务测试"""

    def test_send_notification_creates_in_app_message(self, app, db_session, test_user):
        """测试发送站内信创建记录，状态为 sent 且未读"""
        with app.app_context():
            # 禁用邮件以避免依赖外部服务
            with patch.object(EmailConfigService, 'is_email_enabled', return_value=False):
                result = NotificationService.send_notification(
                    recipient_email=test_user.email,
                    recipient_user_id=test_user.id,
                    title='测试',
                    content='<p>内容</p>',
                    source='system'
                )

            assert result['success'] is True
            assert result['notification_id'] is not None

            notification = Notification.query.filter_by(
                recipient_user_id=test_user.id
            ).first()
            assert notification is not None
            assert notification.status == NotificationStatus.SENT
            assert notification.is_read is False
            assert notification.sent_at is not None
            assert notification.title == '测试'
            assert notification.content == '<p>内容</p>'
            assert notification.source == 'system'

    def test_send_notification_in_app_before_email(self, app, db_session, test_user):
        """测试站内信先于邮件写入（通过 mock 记录邮件调用时站内信已存在及时间戳）"""
        with app.app_context():
            email_call_times = []
            email_call_notifications = []

            def mock_send_email(**kwargs):
                # 邮件发送时查询站内信是否已写入
                n = Notification.query.filter_by(
                    recipient_user_id=test_user.id
                ).first()
                email_call_notifications.append(n)
                email_call_times.append(datetime.now(timezone.utc))
                return (True, None)

            with patch.object(EmailConfigService, 'is_email_enabled', return_value=True):
                with patch.object(EmailSenderService, 'send_email_quick', side_effect=mock_send_email):
                    result = NotificationService.send_notification(
                        recipient_email=test_user.email,
                        recipient_user_id=test_user.id,
                        title='顺序测试',
                        content='<p>内容</p>',
                        source='system'
                    )

            assert result['success'] is True
            assert len(email_call_times) == 1

            # 邮件发送时站内信已写入
            assert email_call_notifications[0] is not None

            # 站内信创建时间应早于或等于邮件调用时间
            created_at = email_call_notifications[0].created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            assert created_at <= email_call_times[0]

    def test_send_notification_works_when_email_disabled(self, app, db_session, test_user):
        """测试邮件服务禁用时站内信仍可创建且邮件未发送"""
        with app.app_context():
            with patch.object(EmailConfigService, 'is_email_enabled', return_value=False):
                with patch.object(EmailSenderService, 'send_email_quick') as mock_send:
                    result = NotificationService.send_notification(
                        recipient_email=test_user.email,
                        recipient_user_id=test_user.id,
                        title='禁用邮件测试',
                        content='<p>内容</p>',
                        source='system'
                    )

            assert result['success'] is True
            assert result['email_sent'] is False
            # 邮件未被调用
            mock_send.assert_not_called()

            notification = Notification.query.filter_by(
                recipient_user_id=test_user.id
            ).first()
            assert notification is not None
            assert notification.status == NotificationStatus.SENT

    def test_send_notification_external_email_only_sends_email(self, app, db_session):
        """测试无对应用户时仅发送邮件，不写站内信"""
        with app.app_context():
            with patch.object(EmailConfigService, 'is_email_enabled', return_value=True):
                with patch.object(EmailSenderService, 'send_email_quick', return_value=(True, None)) as mock_send:
                    result = NotificationService.send_notification(
                        recipient_email='nonexistent@example.com',
                        title='外部邮件',
                        content='<p>内容</p>',
                        source='system'
                    )

            # 邮件被调用
            mock_send.assert_called_once()
            # 未创建站内信（user_id 为 None 不写站内信）
            assert result['notification_id'] is None
            assert Notification.query.count() == 0
            # 外部邮箱 success 取决于邮件结果
            assert result['success'] is True
            assert result['email_sent'] is True

    def test_send_notification_email_failure_does_not_affect_in_app(self, app, db_session, test_user):
        """测试邮件发送异常不影响站内信状态"""
        with app.app_context():
            with patch.object(EmailConfigService, 'is_email_enabled', return_value=True):
                with patch.object(EmailSenderService, 'send_email_quick', side_effect=Exception('SMTP 连接失败')):
                    result = NotificationService.send_notification(
                        recipient_email=test_user.email,
                        recipient_user_id=test_user.id,
                        title='邮件失败测试',
                        content='<p>内容</p>',
                        source='system'
                    )

            # 站内信仍成功
            assert result['success'] is True
            assert result['notification_id'] is not None
            assert result['email_sent'] is False
            assert result['email_error'] is not None

            notification = Notification.query.filter_by(
                recipient_user_id=test_user.id
            ).first()
            assert notification is not None
            assert notification.status == NotificationStatus.SENT


class TestNotificationServiceQuery:
    """站内信查询与已读管理测试"""

    def test_get_unread_count(self, app, db_session, test_user):
        """测试获取未读数量：2 未读 1 已读应返回 2"""
        with app.app_context():
            # 创建 2 条未读
            for i in range(2):
                db.session.add(Notification(
                    recipient_user_id=test_user.id,
                    recipient_email=test_user.email,
                    title=f'未读 {i}',
                    content='<p>内容</p>',
                    source='system',
                    status=NotificationStatus.SENT,
                    is_read=False
                ))
            # 创建 1 条已读
            db.session.add(Notification(
                recipient_user_id=test_user.id,
                recipient_email=test_user.email,
                title='已读',
                content='<p>内容</p>',
                source='system',
                status=NotificationStatus.SENT,
                is_read=True,
                read_at=datetime.now(timezone.utc)
            ))
            db.session.commit()

            result = NotificationService.get_unread_count(test_user.id)

            assert result['success'] is True
            assert result['count'] == 2

    def test_mark_as_read(self, app, db_session, test_user):
        """测试标记单条站内信为已读"""
        with app.app_context():
            notification = Notification(
                recipient_user_id=test_user.id,
                recipient_email=test_user.email,
                title='未读',
                content='<p>内容</p>',
                source='system',
                status=NotificationStatus.SENT,
                is_read=False
            )
            db.session.add(notification)
            db.session.commit()

            result = NotificationService.mark_as_read(notification.id, test_user.id)

            assert result['success'] is True

            db.session.refresh(notification)
            assert notification.is_read is True
            assert notification.read_at is not None

    def test_mark_all_as_read(self, app, db_session, test_user):
        """测试批量标记所有未读为已读，返回更新条数 3"""
        with app.app_context():
            for i in range(3):
                db.session.add(Notification(
                    recipient_user_id=test_user.id,
                    recipient_email=test_user.email,
                    title=f'批量 {i}',
                    content='<p>内容</p>',
                    source='system',
                    status=NotificationStatus.SENT,
                    is_read=False
                ))
            db.session.commit()

            result = NotificationService.mark_all_as_read(test_user.id)

            assert result['success'] is True
            assert result['updated_count'] == 3

            unread_count = Notification.query.filter_by(
                recipient_user_id=test_user.id,
                is_read=False
            ).count()
            assert unread_count == 0

    def test_get_notifications_with_filters(self, app, db_session, test_user):
        """测试按 is_read 与 source 过滤查询"""
        with app.app_context():
            notifications = [
                Notification(
                    recipient_user_id=test_user.id, recipient_email=test_user.email,
                    title='系统未读', content='<p>1</p>', source='system',
                    status=NotificationStatus.SENT, is_read=False
                ),
                Notification(
                    recipient_user_id=test_user.id, recipient_email=test_user.email,
                    title='系统已读', content='<p>2</p>', source='system',
                    status=NotificationStatus.SENT, is_read=True,
                    read_at=datetime.now(timezone.utc)
                ),
                Notification(
                    recipient_user_id=test_user.id, recipient_email=test_user.email,
                    title='认证未读', content='<p>3</p>', source='auth',
                    status=NotificationStatus.SENT, is_read=False
                ),
            ]
            for n in notifications:
                db.session.add(n)
            db.session.commit()

            # 过滤：未读
            result = NotificationService.get_notifications(
                test_user.id, page=1, per_page=20, filters={'is_read': False}
            )
            assert result['success'] is True
            assert result['pagination']['total'] == 2

            # 过滤：source='auth'
            result = NotificationService.get_notifications(
                test_user.id, page=1, per_page=20, filters={'source': 'auth'}
            )
            assert result['success'] is True
            assert result['pagination']['total'] == 1
            assert result['notifications'][0]['source'] == 'auth'

            # 过滤：source='auth' 且未读
            result = NotificationService.get_notifications(
                test_user.id, page=1, per_page=20,
                filters={'source': 'auth', 'is_read': False}
            )
            assert result['success'] is True
            assert result['pagination']['total'] == 1

    def test_delete_notification(self, app, db_session, test_user):
        """测试删除站内信"""
        with app.app_context():
            notification = Notification(
                recipient_user_id=test_user.id,
                recipient_email=test_user.email,
                title='待删除',
                content='<p>内容</p>',
                source='system',
                status=NotificationStatus.SENT,
                is_read=False
            )
            db.session.add(notification)
            db.session.commit()
            nid = notification.id

            result = NotificationService.delete_notification(nid, test_user.id)

            assert result['success'] is True
            assert Notification.query.get(nid) is None

    def test_get_stats(self, app, db_session, test_user):
        """测试统计信息：总量、各状态、已读/未读、按来源分组"""
        with app.app_context():
            notifications = [
                Notification(
                    recipient_user_id=test_user.id, recipient_email=test_user.email,
                    title='系统已发送已读', content='<p>1</p>', source='system',
                    status=NotificationStatus.SENT, is_read=True,
                    read_at=datetime.now(timezone.utc)
                ),
                Notification(
                    recipient_user_id=test_user.id, recipient_email=test_user.email,
                    title='系统已发送未读', content='<p>2</p>', source='system',
                    status=NotificationStatus.SENT, is_read=False
                ),
                Notification(
                    recipient_user_id=test_user.id, recipient_email=test_user.email,
                    title='认证失败', content='<p>3</p>', source='auth',
                    status=NotificationStatus.FAILED, is_read=False
                ),
            ]
            for n in notifications:
                db.session.add(n)
            db.session.commit()

            result = NotificationService.get_stats()

            assert result['success'] is True
            stats = result['stats']
            assert stats['total'] == 3
            assert stats['by_status']['sent'] == 2
            assert stats['by_status']['failed'] == 1
            assert stats['read'] == 1
            assert stats['unread'] == 2

            source_map = {item['source']: item['count'] for item in stats['by_source']}
            assert source_map['system'] == 2
            assert source_map['auth'] == 1


class TestNotificationRetryService:
    """站内信重试服务测试"""

    def test_retry_failed_notification(self, app, db_session, test_user):
        """测试重试失败的站内信，状态应变为 sent"""
        with app.app_context():
            notification = Notification(
                recipient_user_id=test_user.id,
                recipient_email=test_user.email,
                title='失败站内信',
                content='<p>内容</p>',
                source='system',
                status=NotificationStatus.FAILED,
                is_read=False,
                retry_count=1
            )
            db.session.add(notification)
            db.session.commit()

            # 禁用邮件避免外部依赖
            with patch.object(EmailConfigService, 'is_email_enabled', return_value=False):
                result = NotificationRetryService.retry_failed_notification(str(notification.id))

            assert result['success'] is True

            db.session.refresh(notification)
            assert notification.status == NotificationStatus.SENT

    def test_retry_max_count(self, app, db_session, test_user):
        """测试达到最大重试次数时重试应返回失败"""
        with app.app_context():
            notification = Notification(
                recipient_user_id=test_user.id,
                recipient_email=test_user.email,
                title='已达最大重试',
                content='<p>内容</p>',
                source='system',
                status=NotificationStatus.FAILED,
                is_read=False,
                retry_count=NotificationRetryService.MAX_RETRY_COUNT
            )
            db.session.add(notification)
            db.session.commit()

            result = NotificationRetryService.retry_failed_notification(str(notification.id))

            assert result['success'] is False
            assert '最大重试次数' in result['error']
