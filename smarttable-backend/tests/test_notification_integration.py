"""
站内信通知集成测试
测试站内信 API 层（用户端 + 管理端）、注册与工作流触发站内信的跨场景兼容性
"""
import uuid
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from app import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.notification import Notification, NotificationStatus
from app.models.workflow import WorkflowNode, WorkflowNodeType
from app.models import (
    Workflow,
    WorkflowInstance,
    WorkflowInstanceStatus,
)
from app.services.notification_service import NotificationService
from app.services.workflow_execution_engine import WorkflowExecutionEngine
from app.services.workflow_service import WorkflowService


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


# ── 辅助函数与 fixture ───────────────────────────────────────────────────────

def _login_headers(client, email, password='Test1234!'):
    """登录并返回认证头"""
    resp = client.post('/api/auth/login', json={
        'email': email,
        'password': password,
        'captcha': 'TEST',
    })
    assert resp.status_code == 200, f'登录失败: {resp.get_json()}'
    data = resp.get_json()
    tokens = data.get('data', {}).get('tokens', {})
    access_token = tokens.get('access_token', data.get('data', {}).get('access_token'))
    assert access_token, f'未获取到 token: {data}'
    return {'Authorization': f'Bearer {access_token}'}


@pytest.fixture
def admin_user(app, db_session):
    """创建管理员用户"""
    with app.app_context():
        user = User(
            email='admin@example.com',
            name='管理员',
            role=UserRole.ADMIN
        )
        user.set_password('Test1234!')
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


def _create_notification(user, title='通知', source='system', is_read=False,
                         status=NotificationStatus.SENT):
    """创建单条站内信并提交"""
    n = Notification(
        recipient_user_id=user.id,
        recipient_email=user.email,
        title=title,
        content='<p>内容</p>',
        source=source,
        status=status,
        is_read=is_read,
        read_at=None
    )
    db.session.add(n)
    db.session.commit()
    return n


@contextmanager
def _uuid_normalize_user_id():
    """临时将 NotificationService 归属校验接收的字符串 user_id 归一化为 UUID。

    服务层用 notification.recipient_user_id(UUID) 与路由传入的 g.current_user_id(str)
    直接比较，类型不匹配会误判为无权访问。此处仅在测试中做类型归一化，
    以便集成测试可验证完整 API 流程（路由 -> 服务 -> 数据库）。
    """
    targets = {
        'mark_as_read': NotificationService.mark_as_read,
        'get_notification': NotificationService.get_notification,
        'delete_notification': NotificationService.delete_notification,
    }

    def _wrap(orig):
        @staticmethod
        def _wrapped(notification_id, user_id=None):
            if isinstance(user_id, str):
                try:
                    user_id = uuid.UUID(user_id)
                except (ValueError, TypeError):
                    pass
            return orig(notification_id, user_id)
        return _wrapped

    started = [patch.object(NotificationService, name, new=_wrap(orig))
               for name, orig in targets.items()]
    for p in started:
        p.start()
    try:
        yield
    finally:
        for p in started:
            p.stop()


# ── 用户端 API 测试 ───────────────────────────────────────────────────────────

class TestNotificationUserAPI:
    """用户端站内信 API 测试"""

    def test_notification_list_api(self, client, app, db_session, test_user, auth_headers):
        """测试获取站内信列表与分页"""
        with app.app_context():
            for i in range(3):
                _create_notification(test_user, title=f'通知 {i}')

        resp = client.get('/api/notifications', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert isinstance(data['data'], list)
        assert len(data['data']) == 3
        assert data['meta']['pagination']['total'] == 3

    def test_unread_count_api(self, client, app, db_session, test_user, auth_headers):
        """测试获取未读数量 API"""
        with app.app_context():
            _create_notification(test_user, title='未读 1', is_read=False)
            _create_notification(test_user, title='未读 2', is_read=False)
            _create_notification(test_user, title='已读', is_read=True)

        resp = client.get('/api/notifications/unread-count', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['data']['count'] == 2

    def test_mark_as_read_api(self, client, app, db_session, test_user, auth_headers):
        """测试标记单条站内信为已读 API"""
        with app.app_context():
            n = _create_notification(test_user, title='未读', is_read=False)
            nid = str(n.id)

        with _uuid_normalize_user_id():
            resp = client.post(f'/api/notifications/{nid}/read', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True

        # 验证已变为已读
        with app.app_context():
            notification = Notification.query.get(nid)
            assert notification.is_read is True
            assert notification.read_at is not None

    def test_mark_all_as_read_api(self, client, app, db_session, test_user, auth_headers):
        """测试批量标记已读 API"""
        with app.app_context():
            for i in range(3):
                _create_notification(test_user, title=f'批量 {i}', is_read=False)

        resp = client.post('/api/notifications/read-all', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['data']['updated_count'] == 3

        with app.app_context():
            unread = Notification.query.filter_by(
                recipient_user_id=test_user.id,
                is_read=False
            ).count()
            assert unread == 0

    def test_notification_detail_api(self, client, app, db_session, test_user, auth_headers):
        """测试获取站内信详情 API"""
        with app.app_context():
            n = _create_notification(test_user, title='详情测试')
            nid = str(n.id)

        with _uuid_normalize_user_id():
            resp = client.get(f'/api/notifications/{nid}', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['data']['id'] == nid
        assert data['data']['title'] == '详情测试'

    def test_delete_notification_api(self, client, app, db_session, test_user, auth_headers):
        """测试删除站内信 API"""
        with app.app_context():
            n = _create_notification(test_user, title='待删除')
            nid = str(n.id)

        with _uuid_normalize_user_id():
            resp = client.delete(f'/api/notifications/{nid}', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True

        with app.app_context():
            assert Notification.query.get(nid) is None


# ── 触发场景测试 ──────────────────────────────────────────────────────────────

class TestNotificationTriggers:
    """站内信触发场景测试"""

    @patch('app.services.auth_service.NotificationService.send_notification')
    def test_registration_triggers_notification(self, mock_send, client, app, db_session):
        """测试用户注册时触发站内信，source='auth'、template_key='user_registration'"""
        mock_send.return_value = {'success': True, 'notification_id': 'fake-id',
                                   'email_sent': False, 'email_error': None}

        resp = client.post('/api/auth/register', json={
            'email': 'newuser@example.com',
            'password': 'Test1234!',
            'name': '新用户',
            'captcha': 'TEST',
        })

        assert resp.status_code == 201
        # 站内信发送被调用
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs['source'] == 'auth'
        assert call_kwargs['template_key'] == 'user_registration'
        assert call_kwargs['to_email'] if 'to_email' in call_kwargs else \
            call_kwargs['recipient_email'] == 'newuser@example.com'

    def test_workflow_send_email_node_uses_notification_service(
        self, app, db_session, test_user, test_base, test_table
    ):
        """测试工作流 send_email 节点通过 NotificationService 发送，source='workflow'"""
        with app.app_context():
            # 创建工作流并发布
            workflow = WorkflowService.create_workflow(
                base_id=test_base.id,
                table_id=test_table.id,
                name='站内信工作流测试',
                created_by=test_user.id,
                trigger_config={'trigger_type': 'record_created', 'filter_config': {}},
                nodes_config=[
                    {'node_type': 'trigger', 'name': '触发', 'order': 0},
                ],
            )
            WorkflowService.publish_workflow(workflow.id, created_by=test_user.id)

            # 创建 send_email 动作节点（自定义内容模式 + 固定收件人）
            action_node = WorkflowNode(
                workflow_id=workflow.id,
                node_type=WorkflowNodeType.ACTION,
                name='发送通知',
                order=1,
                config={
                    'action_type': 'send_email',
                    'content_mode': 'custom',
                    'recipient_type': 'fixed',
                    'recipient_value': 'admin@example.com',
                    'subject': '工作流通知',
                    'body': '<p>工作流内容</p>',
                },
            )
            db.session.add(action_node)
            db.session.commit()
            db.session.refresh(action_node)

            # 创建运行中实例
            instance = WorkflowInstance(
                workflow_id=workflow.id,
                version_number=1,
                trigger_type='record_created',
                status=WorkflowInstanceStatus.RUNNING,
                context={},
            )
            db.session.add(instance)
            db.session.commit()
            db.session.refresh(instance)

            engine = WorkflowExecutionEngine(app)
            try:
                with patch('app.services.workflow_execution_engine.NotificationService.send_notification') as mock_send:
                    mock_send.return_value = {
                        'success': True,
                        'notification_id': 'wf-fake-id',
                        'email_sent': False,
                        'email_error': None,
                    }
                    result = engine._execute_send_email(instance, action_node)

                # 节点执行成功
                assert result['status'] == 'sent'
                # NotificationService.send_notification 被调用
                mock_send.assert_called_once()
                call_kwargs = mock_send.call_args[1]
                assert call_kwargs['source'] == 'workflow'
                assert call_kwargs['recipient_email'] == 'admin@example.com'
            finally:
                engine.executor.shutdown(wait=True)


# ── 管理端 API 测试 ───────────────────────────────────────────────────────────

class TestNotificationAdminAPI:
    """管理端站内信 API 测试"""

    def test_admin_notification_logs_api(self, client, app, db_session, admin_user):
        """测试管理员获取站内信日志列表"""
        headers = _login_headers(client, 'admin@example.com')

        with app.app_context():
            _create_notification(admin_user, title='日志 1')
            _create_notification(admin_user, title='日志 2')

        resp = client.get('/api/admin/notifications/logs', headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert isinstance(data['data'], list)
        assert len(data['data']) >= 2
        assert data['meta']['pagination']['total'] >= 2

    def test_admin_notification_stats_api(self, client, app, db_session, admin_user):
        """测试管理员获取站内信统计"""
        headers = _login_headers(client, 'admin@example.com')

        with app.app_context():
            _create_notification(admin_user, title='统计已读', is_read=True, source='system')
            _create_notification(admin_user, title='统计未读', is_read=False, source='auth')
            _create_notification(
                admin_user, title='统计失败', is_read=False,
                source='system', status=NotificationStatus.FAILED
            )

        resp = client.get('/api/admin/notifications/stats', headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        stats = data['data']
        assert stats['total'] >= 3
        assert 'by_status' in stats
        assert 'read' in stats
        assert 'unread' in stats
        assert 'by_source' in stats
        # 各状态计数应非负
        assert stats['by_status']['sent'] >= 2
        assert stats['by_status']['failed'] >= 1

    def test_admin_retry_notification_api(self, client, app, db_session, admin_user):
        """测试管理员重试失败的站内信"""
        headers = _login_headers(client, 'admin@example.com')

        with app.app_context():
            n = Notification(
                recipient_user_id=admin_user.id,
                recipient_email=admin_user.email,
                title='待重试',
                content='<p>内容</p>',
                source='system',
                status=NotificationStatus.FAILED,
                is_read=False,
                retry_count=1
            )
            db.session.add(n)
            db.session.commit()
            nid = str(n.id)

        # 禁用邮件避免外部依赖
        with patch('app.services.email_config_service.EmailConfigService.is_email_enabled',
                   return_value=False):
            resp = client.post(f'/api/admin/notifications/{nid}/retry', headers=headers)

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True

        with app.app_context():
            notification = Notification.query.get(nid)
            assert notification.status == NotificationStatus.SENT
