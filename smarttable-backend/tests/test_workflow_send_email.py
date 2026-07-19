"""
工作流发送邮件动作测试
测试 _execute_send_email 自定义内容模式、收件人字段解析、
邮件服务禁用场景以及邮件模板列表 API
"""
import uuid
from unittest.mock import patch, MagicMock

import pytest

from app import create_app
from app.extensions import db
from app.models import (
    User,
    Base,
    Table,
    Field,
    Record,
    Workflow,
    WorkflowInstance,
    WorkflowInstanceStatus,
)
from app.models.field import FieldType
from app.models.workflow import WorkflowNode, WorkflowNodeType
from app.services.workflow_execution_engine import WorkflowExecutionEngine
from app.services.workflow_service import WorkflowService


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope='function')
def exec_app():
    """为每个测试创建独立应用实例"""
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def ctx(exec_app):
    """每次测试提供应用上下文"""
    with exec_app.app_context():
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
def table(ctx, base):
    t = Table(base_id=base.id, name='测试表格', order=0)
    db.session.add(t)
    db.session.commit()
    db.session.refresh(t)
    return t


@pytest.fixture(scope='function')
def email_field(ctx, table):
    """创建邮件类型字段"""
    f = Field(table_id=table.id, name='邮箱', type=FieldType.EMAIL.value, order=0)
    db.session.add(f)
    db.session.commit()
    db.session.refresh(f)
    return f


@pytest.fixture(scope='function')
def name_field(ctx, table):
    """创建文本字段"""
    f = Field(table_id=table.id, name='姓名', type=FieldType.SINGLE_LINE_TEXT.value, order=1)
    db.session.add(f)
    db.session.commit()
    db.session.refresh(f)
    return f


@pytest.fixture(scope='function')
def record_with_email(ctx, table, email_field, name_field, owner):
    """创建包含邮箱字段值的记录"""
    r = Record(
        table_id=table.id,
        values={
            str(email_field.id): 'user@example.com',
            str(name_field.id): '张三',
        },
        created_by=owner.id,
    )
    db.session.add(r)
    db.session.commit()
    db.session.refresh(r)
    return r


@pytest.fixture(scope='function')
def engine(ctx, exec_app):
    """创建使用当前应用的执行引擎"""
    engine = WorkflowExecutionEngine(exec_app)
    yield engine
    engine.executor.shutdown(wait=True)


def _make_send_email_node(base_id, table_id, owner_id, config):
    """创建 send_email 动作节点及对应工作流 + 实例"""
    workflow = WorkflowService.create_workflow(
        base_id=base_id,
        table_id=table_id,
        name='邮件动作测试',
        created_by=owner_id,
        trigger_config={'trigger_type': 'record_created', 'filter_config': {}},
        nodes_config=[
            {'node_type': 'trigger', 'name': '触发', 'order': 0},
        ],
    )
    WorkflowService.publish_workflow(workflow.id, created_by=owner_id)

    # 创建 send_email 动作节点
    action_node = WorkflowNode(
        workflow_id=workflow.id,
        node_type=WorkflowNodeType.ACTION,
        name='发送邮件',
        order=1,
        config=config,
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

    return workflow, action_node, instance


# ── Test 1: Custom content mode ───────────────────────────────────────────────

class TestExecuteSendEmailCustomContent:
    """测试 _execute_send_email 自定义内容模式"""

    @patch('app.services.workflow_execution_engine.EmailSenderService.send_email_quick')
    @patch('app.services.email_config_service.EmailConfigService.is_email_enabled')
    def test_custom_mode_renders_and_sends(
        self, mock_is_enabled, mock_send_quick, ctx, base, table, record_with_email, owner, engine,
    ):
        """content_mode == 'custom' 时渲染模板后直接发送邮件"""
        mock_is_enabled.return_value = True
        mock_send_quick.return_value = (True, None)

        email_field = Field.query.filter_by(table_id=table.id, name='邮箱').first()
        name_field = Field.query.filter_by(table_id=table.id, name='姓名').first()

        config = {
            'action_type': 'send_email',
            'content_mode': 'custom',
            'recipient_type': 'fixed',
            'recipient_value': 'admin@example.com',
            'subject': '通知：{{record.' + str(name_field.id) + '}}',
            'body': '<p>你好 {{record.' + str(name_field.id) + '}}</p>',
        }

        workflow, action_node, instance = _make_send_email_node(
            base.id, table.id, owner.id, config,
        )
        # 让实例关联触发记录
        instance.trigger_record_id = record_with_email.id
        db.session.commit()

        result = engine._execute_send_email(instance, action_node)

        # 返回值正确
        assert result['status'] == 'sent'
        assert result['to_email'] == 'admin@example.com'

        # send_email_quick 被调用一次
        mock_send_quick.assert_called_once()
        call_kwargs = mock_send_quick.call_args[1]

        # 主题和正文包含实际记录数据（"张三"）
        assert '张三' in call_kwargs['subject']
        assert '张三' in call_kwargs['html_content']

        # 参数传递正确
        assert call_kwargs['to_email'] == 'admin@example.com'


# ── Test 2: Recipient field resolution ────────────────────────────────────────

class TestResolveEmailRecipients:
    """测试 _resolve_email_recipients 收件人字段解析"""

    def test_field_type_string_value(self, ctx, engine):
        """字符串值直接作为邮箱"""
        config = {
            'recipient_type': 'field',
            'recipient_value': ['field_001'],
        }
        context = {
            'record': {'field_001': 'alice@example.com'},
        }
        result = engine._resolve_email_recipients(config, context)
        assert result == 'alice@example.com'

    def test_field_type_list_of_strings(self, ctx, engine):
        """列表中的字符串均被提取"""
        config = {
            'recipient_type': 'field',
            'recipient_value': ['field_001'],
        }
        context = {
            'record': {'field_001': ['a@example.com', 'b@example.com']},
        }
        result = engine._resolve_email_recipients(config, context)
        assert result == 'a@example.com,b@example.com'

    def test_field_type_list_of_objects_with_email_key(self, ctx, engine):
        """列表中包含 email 键的对象，提取邮箱地址"""
        config = {
            'recipient_type': 'field',
            'recipient_value': ['collaborator_field'],
        }
        context = {
            'record': {
                'collaborator_field': [
                    {'email': 'x@example.com', 'name': 'X'},
                    {'email': 'y@example.com', 'name': 'Y'},
                ],
            },
        }
        result = engine._resolve_email_recipients(config, context)
        assert result == 'x@example.com,y@example.com'

    def test_field_type_comma_separated_string(self, ctx, engine):
        """逗号分隔的邮箱字符串被正确拆分"""
        config = {
            'recipient_type': 'field',
            'recipient_value': ['field_001'],
        }
        context = {
            'record': {'field_001': 'a@example.com, b@example.com'},
        }
        result = engine._resolve_email_recipients(config, context)
        assert result == 'a@example.com,b@example.com'

    def test_field_type_missing_field_returns_empty(self, ctx, engine):
        """记录中不存在对应字段时返回空字符串"""
        config = {
            'recipient_type': 'field',
            'recipient_value': ['nonexistent_field'],
        }
        context = {
            'record': {},
        }
        result = engine._resolve_email_recipients(config, context)
        assert result == ''

    def test_field_type_uuid_member_id_resolves_to_email(self, ctx, engine, owner):
        """成员字段的 UUID 值应查询用户表获取邮箱地址"""
        # 创建一个成员用户
        member = User(email='member@example.com', name='成员用户')
        member.set_password('Test1234!')
        db.session.add(member)
        db.session.commit()
        db.session.refresh(member)

        config = {
            'recipient_type': 'field',
            'recipient_value': ['member_field'],
        }
        context = {
            'record': {
                'member_field': str(member.id),  # 存储的是用户UUID
            },
        }
        result = engine._resolve_email_recipients(config, context)
        assert result == 'member@example.com'

    def test_field_type_list_of_uuid_member_ids(self, ctx, engine):
        """成员字段包含多个成员ID（UUID列表）时应全部解析为邮箱"""
        # 创建两个成员用户
        member1 = User(email='member1@example.com', name='成员1')
        member1.set_password('Test1234!')
        member2 = User(email='member2@example.com', name='成员2')
        member2.set_password('Test1234!')
        db.session.add_all([member1, member2])
        db.session.commit()
        db.session.refresh(member1)
        db.session.refresh(member2)

        config = {
            'recipient_type': 'field',
            'recipient_value': ['members_field'],
        }
        context = {
            'record': {
                'members_field': [str(member1.id), str(member2.id)],  # UUID列表
            },
        }
        result = engine._resolve_email_recipients(config, context)
        assert 'member1@example.com' in result
        assert 'member2@example.com' in result


# ── Test 3: Email service disabled ────────────────────────────────────────────

class TestExecuteSendEmailDisabled:
    """测试邮件服务未启用场景"""

    @patch('app.services.email_config_service.EmailConfigService.is_email_enabled')
    def test_raises_when_email_disabled(self, mock_is_enabled, ctx, base, table, owner, engine):
        """邮件服务未启用时 _execute_send_email 抛出 ValueError"""
        mock_is_enabled.return_value = False

        config = {
            'action_type': 'send_email',
            'content_mode': 'custom',
            'recipient_type': 'fixed',
            'recipient_value': 'admin@example.com',
            'subject': '测试',
            'body': '<p>内容</p>',
        }

        _workflow, action_node, instance = _make_send_email_node(
            base.id, table.id, owner.id, config,
        )

        with pytest.raises(ValueError, match='邮件服务未启用或配置不完整'):
            engine._execute_send_email(instance, action_node)


# ── Test 4: Template list API ─────────────────────────────────────────────────

class TestEmailTemplateListAPI:
    """测试邮件模板列表 API（工作流配置用）"""

    def test_returns_200_with_templates(self, ctx, exec_app, owner):
        """GET /api/admin/email/templates/list 返回 200 及模板列表"""
        client = exec_app.test_client()

        # 登录获取 token
        resp = client.post('/api/auth/login', json={
            'email': 'owner@example.com',
            'password': 'Test1234!',
            'captcha': 'TEST',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        tokens = data.get('data', {}).get('tokens', {})
        access_token = tokens.get('access_token', data.get('data', {}).get('access_token'))
        assert access_token, f'登录失败，无法获取 token: {data}'
        headers = {'Authorization': f'Bearer {access_token}'}

        # 请求模板列表
        resp = client.get('/api/admin/email/templates/list', headers=headers)
        assert resp.status_code == 200

        body = resp.get_json()
        assert body['success'] is True

        # 返回数据应是列表，且每项包含 id/name/template_key
        templates = body['data']
        assert isinstance(templates, list)
        if templates:
            assert 'id' in templates[0]
            assert 'name' in templates[0]
            assert 'template_key' in templates[0]

    def test_regular_user_can_access(self, ctx, exec_app):
        """普通用户（非管理员）也可访问模板列表接口"""
        # 创建普通用户
        user = User(email='regular@example.com', name='普通用户')
        user.set_password('Test1234!')
        db.session.add(user)
        db.session.commit()

        client = exec_app.test_client()

        # 以普通用户登录
        resp = client.post('/api/auth/login', json={
            'email': 'regular@example.com',
            'password': 'Test1234!',
            'captcha': 'TEST',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        tokens = data.get('data', {}).get('tokens', {})
        access_token = tokens.get('access_token', data.get('data', {}).get('access_token'))
        assert access_token, f'普通用户登录失败: {data}'
        headers = {'Authorization': f'Bearer {access_token}'}

        # 普通用户也能访问
        resp = client.get('/api/admin/email/templates/list', headers=headers)
        assert resp.status_code == 200

        body = resp.get_json()
        assert body['success'] is True
