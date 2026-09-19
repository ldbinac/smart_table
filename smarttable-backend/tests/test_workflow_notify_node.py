"""
工作流「站内信通知」节点（node_type = notify）测试

覆盖：
- 五种接收人来源（指定成员 / 成员字段 / 流程触发人 / 记录创建人 / 空间全部成员）
- 多来源叠加去重
- 标题与正文的 {{变量}} 渲染
- 仅写站内信、不触发邮件通道
- 无接收人时跳过而非中断流程
- 配置校验（_validate_notify_node）
"""
import uuid

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
from app.models.base import BaseMember, MemberRole
from app.models.field import FieldType
from app.models.notification import Notification
from app.models.workflow import WorkflowNode, WorkflowNodeType
from app.services.workflow_execution_engine import WorkflowExecutionEngine
from app.services.workflow_service import WorkflowService


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope='function')
def exec_app():
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
def member_field(ctx, table):
    f = Field(table_id=table.id, name='负责人', type=FieldType.COLLABORATOR.value, order=0)
    db.session.add(f)
    db.session.commit()
    db.session.refresh(f)
    return f


@pytest.fixture(scope='function')
def name_field(ctx, table):
    f = Field(table_id=table.id, name='标题', type=FieldType.SINGLE_LINE_TEXT.value, order=1)
    db.session.add(f)
    db.session.commit()
    db.session.refresh(f)
    return f


@pytest.fixture(scope='function')
def engine(ctx, exec_app):
    engine = WorkflowExecutionEngine(exec_app)
    yield engine
    engine.executor.shutdown(wait=True)


def _create_user(email, name):
    user = User(email=email, name=name)
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user


def _make_notify_node(base_id, table_id, owner_id, config, context=None, record_id=None):
    """创建 notify 节点及对应工作流 + 实例"""
    workflow = WorkflowService.create_workflow(
        base_id=base_id,
        table_id=table_id,
        name='站内信节点测试',
        created_by=owner_id,
        trigger_config={'trigger_type': 'record_created', 'filter_config': {}},
        nodes_config=[
            {'node_type': 'trigger', 'name': '触发', 'order': 0},
        ],
    )

    node = WorkflowNode(
        workflow_id=workflow.id,
        node_type=WorkflowNodeType.NOTIFY,
        name='站内信通知',
        order=1,
        config=config,
    )
    db.session.add(node)
    db.session.commit()
    db.session.refresh(node)

    instance = WorkflowInstance(
        workflow_id=workflow.id,
        version_number=1,
        trigger_type='record_created',
        status=WorkflowInstanceStatus.RUNNING,
        context=context or {},
        trigger_record_id=record_id,
    )
    db.session.add(instance)
    db.session.commit()
    db.session.refresh(instance)

    return workflow, node, instance


# ── 各接收人来源 ───────────────────────────────────────────────────────────────

class TestNotifyFixedSource:
    """指定成员"""

    def test_sends_to_fixed_members(self, ctx, base, table, owner, engine):
        target = _create_user('fixed@example.com', '指定成员')

        workflow, node, instance = _make_notify_node(base.id, table.id, owner.id, {
            'recipient_sources': ['fixed'],
            'recipient_user_ids': [str(target.id)],
            'subject': '站内信标题',
            'body': '站内信正文',
        })

        result = engine._execute_notify(instance, node)

        assert result['status'] == 'sent'
        assert result['recipient_count'] == 1
        assert len(result['notification_ids']) == 1

        notification = Notification.query.get(uuid.UUID(result['notification_ids'][0]))
        assert notification.recipient_user_id == target.id
        assert notification.title == '站内信标题'
        assert notification.content == '站内信正文'
        assert notification.content_text == '站内信正文'
        assert notification.source == 'workflow'
        assert notification.is_read is False

    def test_ignores_unknown_user_ids(self, ctx, base, table, owner, engine):
        workflow, node, instance = _make_notify_node(base.id, table.id, owner.id, {
            'recipient_sources': ['fixed'],
            'recipient_user_ids': [str(uuid.uuid4())],
            'subject': '标题',
            'body': '正文',
        })

        # 用户不存在 → 无有效接收人 → 跳过
        result = engine._execute_notify(instance, node)
        assert result['status'] == 'skipped'
        assert result['reason'] == 'no_recipients'


class TestNotifyFieldSource:
    """成员字段动态取值"""

    def test_resolves_member_field(self, ctx, base, table, owner, member_field, engine):
        target = _create_user('field@example.com', '字段成员')
        record = Record(
            table_id=table.id,
            values={str(member_field.id): [str(target.id)]},
            created_by=owner.id,
        )
        db.session.add(record)
        db.session.commit()

        workflow, node, instance = _make_notify_node(
            base.id, table.id, owner.id,
            {
                'recipient_sources': ['field'],
                'recipient_field_ids': [str(member_field.id)],
                'subject': '标题',
                'body': '正文',
            },
            record_id=record.id,
        )

        result = engine._execute_notify(instance, node)

        assert result['status'] == 'sent'
        assert result['recipient_count'] == 1
        notification = Notification.query.get(uuid.UUID(result['notification_ids'][0]))
        assert notification.recipient_user_id == target.id


class TestNotifyTriggerUserSource:
    """流程触发人"""

    def test_resolves_trigger_actor(self, ctx, base, table, owner, engine):
        actor = _create_user('actor@example.com', '触发人')

        workflow, node, instance = _make_notify_node(
            base.id, table.id, owner.id,
            {
                'recipient_sources': ['trigger_user'],
                'subject': '标题',
                'body': '正文',
            },
            context={'trigger_event': {'actor_id': str(actor.id), 'event_type': 'record_created'}},
        )

        result = engine._execute_notify(instance, node)

        assert result['status'] == 'sent'
        notification = Notification.query.get(uuid.UUID(result['notification_ids'][0]))
        assert notification.recipient_user_id == actor.id

    def test_skips_system_user(self, ctx, base, table, owner, engine):
        workflow, node, instance = _make_notify_node(
            base.id, table.id, owner.id,
            {
                'recipient_sources': ['trigger_user'],
                'subject': '标题',
                'body': '正文',
            },
            context={'trigger_event': {
                'actor_id': WorkflowExecutionEngine.SYSTEM_USER_ID,
                'event_type': 'record_created',
            }},
        )

        result = engine._execute_notify(instance, node)
        assert result['status'] == 'skipped'


class TestNotifyRecordCreatorSource:
    """记录创建人"""

    def test_resolves_record_creator(self, ctx, base, table, owner, name_field, engine):
        creator = _create_user('creator@example.com', '创建人')
        record = Record(
            table_id=table.id,
            values={str(name_field.id): '任务 A'},
            created_by=creator.id,
        )
        db.session.add(record)
        db.session.commit()

        workflow, node, instance = _make_notify_node(
            base.id, table.id, owner.id,
            {
                'recipient_sources': ['record_creator'],
                'subject': '标题',
                'body': '正文',
            },
            record_id=record.id,
        )

        result = engine._execute_notify(instance, node)

        assert result['status'] == 'sent'
        notification = Notification.query.get(uuid.UUID(result['notification_ids'][0]))
        assert notification.recipient_user_id == creator.id


class TestNotifyBaseMembersSource:
    """空间全部成员"""

    def test_fans_out_to_base_members(self, ctx, base, table, owner, engine):
        member = _create_user('basemember@example.com', '空间成员')
        db.session.add(BaseMember(
            base_id=base.id,
            user_id=member.id,
            role=MemberRole.EDITOR,
            invited_by=owner.id,
        ))
        db.session.commit()

        workflow, node, instance = _make_notify_node(base.id, table.id, owner.id, {
            'recipient_sources': ['base_members'],
            'subject': '标题',
            'body': '正文',
        })

        result = engine._execute_notify(instance, node)

        assert result['status'] == 'sent'
        assert result['recipient_count'] == 1
        notification = Notification.query.get(uuid.UUID(result['notification_ids'][0]))
        assert notification.recipient_user_id == member.id


# ── 组合行为 ──────────────────────────────────────────────────────────────────

class TestNotifyCombinations:

    def test_multiple_sources_are_merged_and_deduplicated(self, ctx, base, table, owner, member_field, engine):
        """同一个人来自多个来源时只发一条"""
        shared = _create_user('shared@example.com', '重复成员')
        db.session.add(BaseMember(
            base_id=base.id,
            user_id=shared.id,
            role=MemberRole.EDITOR,
            invited_by=owner.id,
        ))
        record = Record(
            table_id=table.id,
            values={str(member_field.id): [str(shared.id)]},
            created_by=shared.id,
        )
        db.session.add(record)
        db.session.commit()

        workflow, node, instance = _make_notify_node(
            base.id, table.id, owner.id,
            {
                'recipient_sources': ['fixed', 'field', 'record_creator', 'base_members'],
                'recipient_user_ids': [str(shared.id)],
                'recipient_field_ids': [str(member_field.id)],
                'subject': '标题',
                'body': '正文',
            },
            record_id=record.id,
        )

        result = engine._execute_notify(instance, node)

        assert result['status'] == 'sent'
        assert result['recipient_count'] == 1
        assert len(result['notification_ids']) == 1

    def test_renders_template_variables(self, ctx, base, table, owner, name_field, engine):
        """标题与正文中的 {{record.<field_id>}} 被替换为真实值"""
        target = _create_user('render@example.com', '渲染成员')
        record = Record(
            table_id=table.id,
            values={str(name_field.id): '季度汇报'},
            created_by=owner.id,
        )
        db.session.add(record)
        db.session.commit()

        workflow, node, instance = _make_notify_node(
            base.id, table.id, owner.id,
            {
                'recipient_sources': ['fixed'],
                'recipient_user_ids': [str(target.id)],
                'subject': '任务 {{record.' + str(name_field.id) + '}} 已更新',
                'body': '你好，{{record.' + str(name_field.id) + '}} 有变更',
            },
            record_id=record.id,
        )

        result = engine._execute_notify(instance, node)

        notification = Notification.query.get(uuid.UUID(result['notification_ids'][0]))
        assert notification.title == '任务 季度汇报 已更新'
        assert notification.content == '你好，季度汇报 有变更'

    def test_escapes_html_in_body(self, ctx, base, table, owner, engine):
        """正文按纯文本转义，避免消息中心渲染 HTML 时产生 XSS"""
        target = _create_user('escape@example.com', '转义成员')

        workflow, node, instance = _make_notify_node(base.id, table.id, owner.id, {
            'recipient_sources': ['fixed'],
            'recipient_user_ids': [str(target.id)],
            'subject': '标题',
            'body': '<script>alert(1)</script>',
        })

        result = engine._execute_notify(instance, node)

        notification = Notification.query.get(uuid.UUID(result['notification_ids'][0]))
        assert '<script>' not in notification.content
        assert '&lt;script&gt;' in notification.content
        assert notification.content_text == '<script>alert(1)</script>'

    def test_does_not_send_email(self, ctx, base, table, owner, engine):
        """站内信节点不走邮件通道"""
        from unittest.mock import patch

        target = _create_user('nomail@example.com', '无邮件成员')

        workflow, node, instance = _make_notify_node(base.id, table.id, owner.id, {
            'recipient_sources': ['fixed'],
            'recipient_user_ids': [str(target.id)],
            'subject': '标题',
            'body': '正文',
        })

        with patch('app.services.workflow_execution_engine.EmailSenderService.send_email_quick') as mock_send:
            result = engine._execute_notify(instance, node)

        assert result['status'] == 'sent'
        assert mock_send.call_count == 0

    def test_truncates_overlong_title(self, ctx, base, table, owner, engine):
        target = _create_user('longtitle@example.com', '长标题成员')

        workflow, node, instance = _make_notify_node(base.id, table.id, owner.id, {
            'recipient_sources': ['fixed'],
            'recipient_user_ids': [str(target.id)],
            'subject': '标' * 600,
            'body': '正文',
        })

        result = engine._execute_notify(instance, node)

        notification = Notification.query.get(uuid.UUID(result['notification_ids'][0]))
        assert len(notification.title) == 500

    def test_missing_title_raises(self, ctx, base, table, owner, engine):
        target = _create_user('notitle@example.com', '无标题成员')

        workflow, node, instance = _make_notify_node(base.id, table.id, owner.id, {
            'recipient_sources': ['fixed'],
            'recipient_user_ids': [str(target.id)],
            'subject': '   ',
            'body': '正文',
        })

        with pytest.raises(ValueError):
            engine._execute_notify(instance, node)


# ── 配置校验 ──────────────────────────────────────────────────────────────────

class TestValidateNotifyNode:

    def test_requires_recipient_source(self):
        with pytest.raises(ValueError):
            WorkflowService._validate_notify_node({'config': {'subject': '标题'}})

    def test_rejects_unknown_source(self):
        with pytest.raises(ValueError):
            WorkflowService._validate_notify_node({'config': {'recipient_sources': ['unknown']}})

    def test_requires_members_for_fixed_source(self):
        with pytest.raises(ValueError):
            WorkflowService._validate_notify_node({
                'config': {'recipient_sources': ['fixed'], 'recipient_user_ids': []},
            })

    def test_requires_fields_for_field_source(self):
        with pytest.raises(ValueError):
            WorkflowService._validate_notify_node({
                'config': {'recipient_sources': ['field'], 'recipient_field_ids': []},
            })

    def test_accepts_dynamic_sources_without_extra_values(self):
        """流程触发人 / 记录创建人 / 空间成员无需额外取值"""
        WorkflowService._validate_notify_node({
            'config': {
                'recipient_sources': ['trigger_user', 'record_creator', 'base_members'],
                'subject': '标题',
            },
        })

    def test_rejects_non_string_content(self):
        with pytest.raises(ValueError):
            WorkflowService._validate_notify_node({
                'config': {'recipient_sources': ['trigger_user'], 'subject': 123},
            })

    def test_rejects_empty_title(self):
        """标题为空在保存阶段即被拦截，避免运行时才中断流程"""
        for subject in (None, '', '   '):
            with pytest.raises(ValueError):
                WorkflowService._validate_notify_node({
                    'config': {
                        'recipient_sources': ['base_members'],
                        'subject': subject,
                        'body': '正文',
                    },
                })

    def test_create_workflow_with_notify_node(self, ctx, base, table, owner):
        """notify 节点可通过工作流创建接口保存"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='含站内信节点',
            created_by=owner.id,
            trigger_config={'trigger_type': 'record_created', 'filter_config': {}},
            nodes_config=[
                {'node_type': 'trigger', 'name': '触发', 'order': 0},
                {
                    'node_type': 'notify',
                    'name': '站内信通知',
                    'order': 1,
                    'config': {
                        'recipient_sources': ['base_members'],
                        'subject': '标题',
                        'body': '正文',
                    },
                },
            ],
        )
        node = workflow.nodes.filter_by(node_type='notify').first()
        assert node is not None
        assert node.config['recipient_sources'] == ['base_members']

    def test_create_workflow_rejects_invalid_notify_node(self, ctx, base, table, owner):
        with pytest.raises(ValueError):
            WorkflowService.create_workflow(
                base_id=base.id,
                table_id=table.id,
                name='站内信配置非法',
                created_by=owner.id,
                trigger_config={'trigger_type': 'record_created', 'filter_config': {}},
                nodes_config=[
                    {'node_type': 'trigger', 'name': '触发', 'order': 0},
                    {'node_type': 'notify', 'name': '站内信通知', 'order': 1, 'config': {}},
                ],
            )
