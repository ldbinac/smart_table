"""
WorkflowExecutionEngine 单元测试
测试实例启动、节点执行、循环防护与失败隔离。
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
    WorkflowStatus,
    WorkflowNodeType,
    WorkflowTriggerType,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowExecutionLog,
)
from app.models.workflow import WorkflowNode, WorkflowTrigger
from app.services.workflow_execution_engine import WorkflowExecutionEngine
from app.services.workflow_event_bus import WorkflowEvent
from app.services.workflow_service import WorkflowService


@pytest.fixture(scope='function')
def exec_app():
    """为每个执行引擎测试创建独立应用实例"""
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
def field(ctx, table):
    from app.models.field import FieldType
    f = Field(table_id=table.id, name='状态', type=FieldType.SINGLE_LINE_TEXT.value, order=0)
    db.session.add(f)
    db.session.commit()
    db.session.refresh(f)
    return f


@pytest.fixture(scope='function')
def record(ctx, table, field, owner):
    r = Record(table_id=table.id, values={str(field.id): '初始值'}, created_by=owner.id)
    db.session.add(r)
    db.session.commit()
    db.session.refresh(r)
    return r


@pytest.fixture(scope='function')
def engine(ctx, exec_app):
    """创建使用当前应用的执行引擎"""
    return WorkflowExecutionEngine(exec_app)


class TestStartInstance:
    """测试实例启动"""

    def test_start_instance_creates_record(self, ctx, base, table, owner, engine):
        """测试启动实例会创建 WorkflowInstance"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='启动测试',
            created_by=owner.id
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        event = WorkflowEvent(
            event_type='record_created',
            table_id=str(table.id),
            record_id=None,
            actor_id=str(owner.id)
        )

        instance = engine.start_instance(workflow, event)
        assert instance is not None
        assert instance.workflow_id == workflow.id
        assert instance.status == WorkflowInstanceStatus.RUNNING
        assert instance.version_number == 1

    def test_start_instance_exceeds_max_depth(self, ctx, base, table, owner, engine):
        """测试触发链深度超过上限时拒绝启动"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='深度测试',
            created_by=owner.id
        )

        event = WorkflowEvent(
            event_type='record_created',
            table_id=str(table.id),
            record_id=None,
            actor_id=str(owner.id),
            metadata={'trigger_chain': [str(uuid.uuid4()) for _ in range(3)]}
        )

        instance = engine.start_instance(workflow, event)
        assert instance is None


class TestExecuteTriggerNode:
    """测试触发节点执行"""

    def test_execute_trigger_node(self, ctx, base, table, owner, engine):
        """测试触发节点返回成功"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='触发节点测试',
            created_by=owner.id,
            nodes_config=[
                {'node_type': 'trigger', 'name': '触发', 'order': 0}
            ]
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        instance = WorkflowInstance(
            workflow_id=workflow.id,
            version_number=1,
            trigger_type='record_created',
            status=WorkflowInstanceStatus.RUNNING
        )
        db.session.add(instance)
        db.session.commit()

        trigger_node = workflow.nodes.first()
        result = engine.execute_node(instance, trigger_node)

        assert isinstance(result, dict)
        assert result['status'] == 'success'

        log = WorkflowExecutionLog.query.filter_by(instance_id=instance.id).first()
        assert log is not None
        assert log.status == 'success'


class TestExecuteConditionNode:
    """测试条件分支节点"""

    def test_condition_node_true_branch(self, ctx, base, table, owner, engine):
        """测试条件为真时走 true 分支"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='条件分支测试',
            created_by=owner.id,
            nodes_config=[
                {
                    'node_type': 'condition',
                    'name': '条件',
                    'config': {
                        'condition': {
                            'operator': 'eq',
                            'field_id': 'status',
                            'value': 'active'
                        },
                        'true_next_nodes': [],
                        'false_next_nodes': []
                    },
                    'order': 0
                }
            ]
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        instance = WorkflowInstance(
            workflow_id=workflow.id,
            version_number=1,
            trigger_type='record_created',
            status=WorkflowInstanceStatus.RUNNING,
            context={'record': {'status': 'active'}}
        )
        db.session.add(instance)
        db.session.commit()

        condition_node = workflow.nodes.first()
        result = engine.execute_node(instance, condition_node)

        assert result['result'] is True

    def test_condition_node_false_branch(self, ctx, base, table, owner, engine):
        """测试条件为假时走 false 分支"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='条件分支测试',
            created_by=owner.id,
            nodes_config=[
                {
                    'node_type': 'condition',
                    'name': '条件',
                    'config': {
                        'condition': {
                            'operator': 'eq',
                            'field_id': 'status',
                            'value': 'active'
                        },
                        'true_next_nodes': [],
                        'false_next_nodes': []
                    },
                    'order': 0
                }
            ]
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        instance = WorkflowInstance(
            workflow_id=workflow.id,
            version_number=1,
            trigger_type='record_created',
            status=WorkflowInstanceStatus.RUNNING,
            context={'record': {'status': 'inactive'}}
        )
        db.session.add(instance)
        db.session.commit()

        condition_node = workflow.nodes.first()
        result = engine.execute_node(instance, condition_node)

        assert result['result'] is False


class TestExecuteUpdateRecord:
    """测试更新记录动作节点"""

    def test_execute_update_record(self, ctx, base, table, owner, field, record, engine):
        """测试更新记录动作会修改记录字段值"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='更新记录测试',
            created_by=owner.id,
            nodes_config=[
                {
                    'node_type': 'action',
                    'name': '更新状态',
                    'config': {
                        'action_type': 'update_record',
                        'values': {
                            str(field.id): '已更新'
                        }
                    },
                    'order': 0
                }
            ]
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        instance = WorkflowInstance(
            workflow_id=workflow.id,
            version_number=1,
            trigger_type='record_created',
            status=WorkflowInstanceStatus.RUNNING,
            trigger_record_id=record.id
        )
        db.session.add(instance)
        db.session.commit()

        action_node = workflow.nodes.first()
        result = engine.execute_node(instance, action_node)

        assert 'record_id' in result
        db.session.refresh(record)
        assert record.values[str(field.id)] == '已更新'


class TestRenderTemplate:
    """测试模板渲染"""

    def test_render_template_simple(self, engine):
        """测试简单模板替换"""
        context = {'record': {'name': 'SmartTable'}, 'workflow': {'name': '测试'}}
        assert engine.render_template('{{record.name}}', context) == 'SmartTable'

    def test_render_template_nested(self, engine):
        """测试嵌套路径解析"""
        context = {'trigger': {'record': {'status': 'active'}}}
        assert engine.render_template('{{trigger.record.status}}', context) == 'active'

    def test_render_template_mixed_text(self, engine):
        """测试混合文本中的模板替换"""
        context = {'record': {'name': 'SmartTable'}}
        result = engine.render_template('Hello {{record.name}}!', context)
        assert result == 'Hello SmartTable!'


class TestLoopProtection:
    """测试循环防护"""

    def test_node_cycle_detection(self, ctx, base, table, owner, engine):
        """测试检测到节点循环时停止执行"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='循环测试',
            created_by=owner.id,
            nodes_config=[
                {
                    'node_type': 'trigger',
                    'name': '触发',
                    'order': 0,
                    'next_nodes': []
                }
            ]
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        trigger_node = workflow.nodes.first()
        instance = WorkflowInstance(
            workflow_id=workflow.id,
            version_number=1,
            trigger_type='record_created',
            status=WorkflowInstanceStatus.RUNNING,
            context={'visited_node_ids': [str(trigger_node.id)]}
        )
        db.session.add(instance)
        db.session.commit()

        # 再次访问已访问节点应直接返回，不抛异常
        engine._execute_chain(instance, trigger_node)
        assert instance.status == WorkflowInstanceStatus.RUNNING


class TestFailureIsolation:
    """测试失败隔离"""

    def test_continue_on_error(self, ctx, base, table, owner, engine):
        """测试节点配置 continue_on_error 时不会中断"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='失败隔离测试',
            created_by=owner.id,
            nodes_config=[
                {
                    'node_type': 'action',
                    'name': '错误动作',
                    'config': {
                        'action_type': 'unknown_action',
                        'continue_on_error': True
                    },
                    'order': 0,
                    'max_retries': 0
                }
            ]
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        instance = WorkflowInstance(
            workflow_id=workflow.id,
            version_number=1,
            trigger_type='record_created',
            status=WorkflowInstanceStatus.RUNNING
        )
        db.session.add(instance)
        db.session.commit()

        action_node = workflow.nodes.first()
        result = engine.execute_node(instance, action_node)

        assert result['status'] == 'error'
        assert result.get('continued') is True

    def test_max_retries(self, ctx, base, table, owner, engine):
        """测试节点失败会按 max_retries 重试"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='重试测试',
            created_by=owner.id,
            nodes_config=[
                {
                    'node_type': 'action',
                    'name': '总是失败',
                    'config': {
                        'action_type': 'unknown_action'
                    },
                    'order': 0,
                    'max_retries': 2
                }
            ]
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        instance = WorkflowInstance(
            workflow_id=workflow.id,
            version_number=1,
            trigger_type='record_created',
            status=WorkflowInstanceStatus.RUNNING
        )
        db.session.add(instance)
        db.session.commit()

        action_node = workflow.nodes.first()
        with pytest.raises(Exception):
            engine.execute_node(instance, action_node)

        logs = WorkflowExecutionLog.query.filter_by(instance_id=instance.id).all()
        assert len(logs) == 1
        assert logs[0].status == 'error'
