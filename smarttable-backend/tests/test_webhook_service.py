"""
WebhookService 单元测试
测试 Webhook 投递、签名、重试与模板渲染。
"""
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

from app import create_app
from app.extensions import db
from app.models import (
    User,
    Base,
    WebhookConfig,
    WebhookDeliveryLog,
    WebhookDeliveryStatus,
    WebhookMethod,
)
from app.services.webhook_service import WebhookService


@pytest.fixture(scope='function')
def webhook_app():
    """为每个 Webhook 测试创建独立应用实例"""
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def ctx(webhook_app):
    with webhook_app.app_context():
        yield


@pytest.fixture(scope='function')
def owner(ctx):
    user = User(email='owner@example.com', name='所有者')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user


@pytest.fixture(scope='function')
def base(ctx, owner):
    b = Base(name='测试 Base', owner_id=owner.id)
    db.session.add(b)
    db.session.commit()
    db.session.refresh(b)
    return b


@pytest.fixture(scope='function')
def webhook_config(ctx, base, owner):
    """创建测试 Webhook 配置"""
    config = WebhookConfig(
        base_id=base.id,
        name='测试 Webhook',
        url='https://example.com/webhook',
        method=WebhookMethod.POST,
        headers={'X-Custom': 'test'},
        body_template='{"event": "{{event.event_type}}", "record": "{{record.name}}"}',
        secret='test-secret',
        created_by=owner.id
    )
    db.session.add(config)
    db.session.commit()
    db.session.refresh(config)
    return config


class TestComputeSignature:
    """测试签名计算"""

    def test_compute_signature(self):
        """测试 HMAC-SHA256 签名一致"""
        secret = 'my-secret'
        payload = '{"event": "test"}'
        signature = WebhookService._compute_signature(secret, payload)
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex 长度为 64

    def test_same_payload_same_signature(self):
        """测试相同 payload 生成相同签名"""
        secret = 'my-secret'
        payload = '{"event": "test"}'
        sig1 = WebhookService._compute_signature(secret, payload)
        sig2 = WebhookService._compute_signature(secret, payload)
        assert sig1 == sig2


class TestBuildPayload:
    """测试请求体构建"""

    def test_build_payload_with_template(self, webhook_config):
        """测试使用模板渲染 payload"""
        event_data = {'event_type': 'record_created', 'record': {'name': 'SmartTable'}}

        payload = WebhookService._build_payload(webhook_config, None, event_data)
        data = json.loads(payload)
        assert data['event'] == 'record_created'
        assert data['record'] == 'SmartTable'

    def test_build_payload_default(self, base, owner):
        """测试无模板时使用默认 JSON payload"""
        config = WebhookConfig(
            base_id=base.id,
            name='默认 Payload',
            url='https://example.com/webhook',
            method=WebhookMethod.POST,
            body_template=None,
            created_by=owner.id
        )
        db.session.add(config)
        db.session.commit()

        event_data = {'event_type': 'test'}
        payload = WebhookService._build_payload(config, None, event_data)
        data = json.loads(payload)
        assert data['event'] == event_data


class TestBuildHeaders:
    """测试请求头构建"""

    def test_build_headers_includes_signature(self, webhook_config):
        """测试请求头包含签名与事件头"""
        payload = '{"event": "test"}'
        event_data = {'event_type': 'record_created'}
        headers = WebhookService._build_headers(webhook_config, event_data, payload)

        assert headers['Content-Type'] == 'application/json'
        assert headers['X-Custom'] == 'test'
        assert headers['X-SmartTable-Event'] == 'record_created'
        assert 'X-SmartTable-Signature' in headers
        assert headers['X-SmartTable-Signature'].startswith('sha256=')


class TestDeliver:
    """测试 Webhook 投递"""

    @patch('app.services.webhook_service.requests.request')
    def test_deliver_success(self, mock_request, webhook_config):
        """测试 HTTP 200 响应标记为成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'OK'
        mock_request.return_value = mock_response

        event_data = {'event_type': 'record_created', 'record': {'name': 'Test'}}
        result = WebhookService.deliver(webhook_config, None, event_data)

        assert result['success'] is True
        assert result['status'] == 'success'

        log = WebhookDeliveryLog.query.first()
        assert log is not None
        assert log.status == WebhookDeliveryStatus.SUCCESS
        assert log.response_status == 200

    @patch('app.services.webhook_service.requests.request')
    def test_deliver_failure_schedules_retry(self, mock_request, webhook_config):
        """测试 HTTP 500 响应标记为失败并安排重试"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_request.return_value = mock_response

        event_data = {'event_type': 'record_created'}
        result = WebhookService.deliver(webhook_config, None, event_data)

        assert result['success'] is False
        assert result['status'] == 'failed'

        log = WebhookDeliveryLog.query.first()
        assert log.status == WebhookDeliveryStatus.FAILED
        assert log.retry_count == 1
        assert log.next_retry_at is not None

    @patch('app.services.webhook_service.requests.request')
    def test_deliver_request_exception_schedules_retry(self, mock_request, webhook_config):
        """测试请求异常时安排重试"""
        from requests.exceptions import RequestException
        mock_request.side_effect = RequestException('Connection error')

        event_data = {'event_type': 'record_created'}
        result = WebhookService.deliver(webhook_config, None, event_data)

        assert result['success'] is False

        log = WebhookDeliveryLog.query.first()
        assert log.status == WebhookDeliveryStatus.FAILED
        assert log.retry_count == 1
        assert '请求异常' in log.error_message


class TestRetryPending:
    """测试失败重试扫描"""

    @patch('app.services.webhook_service.requests.request')
    def test_retry_pending_succeeds_on_second_attempt(self, mock_request, webhook_config):
        """测试 retry_pending 在下次重试时间到达后重新投递并成功"""
        failed_response = MagicMock()
        failed_response.status_code = 500
        failed_response.text = 'Error'
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.text = 'OK'
        mock_request.side_effect = [failed_response, success_response]

        event_data = {'event_type': 'record_created'}
        WebhookService.deliver(webhook_config, None, event_data)

        log = WebhookDeliveryLog.query.first()
        log.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()

        result = WebhookService.retry_pending()
        assert result['success'] is True
        assert result['results']['processed'] == 1
        assert result['results']['succeeded'] == 1

        db.session.refresh(log)
        assert log.status == WebhookDeliveryStatus.SUCCESS


class TestRenderTemplate:
    """测试 Webhook 模板渲染"""

    def test_render_template(self):
        """测试变量替换"""
        template = 'event={{event.type}}, record={{record.id}}'
        context = {'event': {'type': 'created'}, 'record': {'id': '123'}}
        result = WebhookService._render_template(template, context)
        assert result == 'event=created, record=123'

    def test_resolve_path_nested(self):
        """测试嵌套路径解析"""
        context = {'data': {'items': [{'name': 'first'}]}}
        assert WebhookService._resolve_path('data.items.0.name', context) == 'first'
