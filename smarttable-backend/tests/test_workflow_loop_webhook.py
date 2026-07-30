"""
循环节点 + Webhook 循环体集成测试

复现用户场景：指定时间触发 → 查找记录 → 循环节点(find_records_all) → Webhook 循环体
验证循环体内的 webhook 节点是否正确执行并记录执行日志。
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
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowExecutionLog,
    WorkflowNode,
)
from app.services.workflow_execution_engine import WorkflowExecutionEngine
from app.services.workflow_service import WorkflowService


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope='function')
def loop_app():
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    app.config['SECRET_KEY'] = 'test-secret-key'
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def ctx(loop_app):
    with loop_app.app_context():
        yield


@pytest.fixture(scope='function')
def owner(ctx):
    user = User(email='owner_webhook_loop@example.com', name='所有者')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user


@pytest.fixture(scope='function')
def base(ctx, owner):
    b = Base(name='Webhook循环测试 Base', owner_id=owner.id)
    db.session.add(b)
    db.session.commit()
    db.session.refresh(b)
    return b


@pytest.fixture(scope='function')
def table(ctx, base, owner):
    t = Table(base_id=base.id, name='测试表格', order=0)
    db.session.add(t)
    db.session.commit()
    db.session.refresh(t)
    return t


@pytest.fixture(scope='function')
def engine(ctx, loop_app):
    eng = WorkflowExecutionEngine(loop_app)
    yield eng
    eng.executor.shutdown(wait=True)


# ── 工具函数 ─────────────────────────────────────────────────────────────────

def _make_mock_record(values, record_id=None, table_id=None):
    mock = MagicMock()
    mock.id = record_id or uuid.uuid4()
    mock.table_id = table_id or uuid.uuid4()
    mock.values = dict(values)
    mock.to_dict.return_value = dict(values)
    mock.is_deleted = False
    return mock


def _run_workflow_sync(engine, instance):
    try:
        trigger_node = WorkflowNode.query.filter_by(
            workflow_id=instance.workflow_id,
            node_type=WorkflowNodeType.TRIGGER
        ).order_by(WorkflowNode.order).first()
        if not trigger_node:
            trigger_node = WorkflowNode.query.filter_by(
                workflow_id=instance.workflow_id
            ).order_by(WorkflowNode.order).first()
        if not trigger_node:
            engine._complete_instance(instance, WorkflowInstanceStatus.ERROR, '未找到触发节点')
            return instance
        engine._execute_chain(instance, trigger_node)
        if instance.status == WorkflowInstanceStatus.RUNNING:
            engine._complete_instance(instance, WorkflowInstanceStatus.COMPLETED)
    except Exception as e:
        engine._complete_instance(instance, WorkflowInstanceStatus.ERROR, str(e))
    return instance


def _make_instance(workflow_id, context=None, trigger_record_id=None):
    instance = WorkflowInstance(
        workflow_id=workflow_id,
        version_number=1,
        trigger_type='specified_time',
        status=WorkflowInstanceStatus.RUNNING,
        context=context or {},
        trigger_record_id=trigger_record_id,
    )
    db.session.add(instance)
    db.session.commit()
    return instance


# ── 测试 ─────────────────────────────────────────────────────────────────────

class TestLoopWithWebhookBody:
    """测试循环节点 + Webhook 循环体"""

    def test_find_records_all_loop_with_webhook_body_creates_logs(
        self, ctx, base, table, owner, engine
    ):
        """find_records(find_records_all) → loop → webhook(循环体)

        验证循环体 webhook 节点执行日志被正确创建。
        """
        field = Field(
            table_id=table.id,
            name='名称', type='single_line_text', order=0
        )
        db.session.add(field)
        db.session.commit()
        db.session.refresh(field)

        # 构造 2 条 mock 记录
        mock_records = [
            _make_mock_record({str(field.id): '记录A'}, table_id=table.id),
            _make_mock_record({str(field.id): '记录B'}, table_id=table.id),
        ]

        # 创建工作流：trigger → find_records → loop(find_records_all) → webhook(循环体)
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='Webhook循环测试',
            created_by=owner.id,
            trigger_config={'trigger_type': 'specified_time', 'filter_config': {}},
            nodes_config=[
                {'node_type': 'trigger', 'name': '触发', 'order': 0},
                {
                    'node_type': 'find_records',
                    'name': '查找记录',
                    'config': {
                        'target_table_id': str(table.id),
                        'conditions': [],
                        'conjunction': 'and',
                        'result_variable': 'records',
                        'limit': 100,
                    },
                    'order': 1,
                },
                {
                    'node_type': 'loop',
                    'name': '逐条Webhook',
                    'config': {
                        'loop_mode': 'sequential',
                        'data_source': {'type': 'find_records_all'},
                        'max_iterations': 100,
                        'error_handling': 'skip',
                        'empty_result_action': 'skip',
                        'loop_body_nodes': [
                            {
                                'id': 'body-webhook-1',
                                'node_type': 'webhook',
                                'name': '发送Webhook',
                                'config': {
                                    'webhook_id': None,
                                    'inline_webhook': {
                                        'url': 'https://example.com/hook',
                                        'method': 'POST',
                                        'headers': {},
                                        'body_template': '{"record": "{{loop.current_data}}"}',
                                    },
                                },
                                'order': 0,
                                'next_nodes': [],
                            }
                        ],
                    },
                    'order': 2,
                    'next_nodes': [],
                },
            ],
        )

        # 手动串联节点（create_workflow 不自动设置 next_nodes）
        nodes_ordered = workflow.nodes.order_by(WorkflowNode.order).all()
        assert len(nodes_ordered) == 3, f'应有 3 个节点，实际 {len(nodes_ordered)}'
        trigger_node = nodes_ordered[0]
        find_node = nodes_ordered[1]
        loop_node = nodes_ordered[2]
        trigger_node.next_nodes = [str(find_node.id)]
        find_node.next_nodes = [str(loop_node.id)]
        loop_node.next_nodes = []
        db.session.commit()

        instance = _make_instance(workflow.id, context={})

        # mock Record.query 让 find_records 返回 2 条记录
        with patch('app.services.workflow_execution_engine.Record.query') as mock_query:
            mock_query.filter_by.return_value.all.return_value = mock_records
            # mock WebhookService.deliver 避免真实 HTTP 调用
            with patch('app.services.workflow_execution_engine.WebhookService.deliver') as mock_deliver:
                mock_deliver.return_value = {'status': 'success', 'status_code': 200}
                _run_workflow_sync(engine, instance)

        # 验证
        db.session.refresh(instance)
        assert instance.status == WorkflowInstanceStatus.COMPLETED, (
            f'实例应为 COMPLETED，实际 {instance.status}'
        )

        # 验证 loop 节点执行日志（_execute_loop_node 创建的日志含 total_iterations）
        loop_logs = WorkflowExecutionLog.query.filter_by(
            instance_id=instance.id, node_type='loop'
        ).all()
        # 找到含 total_iterations 的日志
        detailed_loop_logs = [
            lg for lg in loop_logs
            if isinstance(lg.output_result, dict) and 'total_iterations' in lg.output_result
        ]
        assert len(detailed_loop_logs) == 1, (
            f'应有 1 条详细 loop 执行日志，实际 {len(detailed_loop_logs)}，'
            f'所有 loop 日志: {[(lg.output_result, lg.status) for lg in loop_logs]}'
        )
        loop_log = detailed_loop_logs[0]
        assert loop_log.status == 'success'
        assert loop_log.output_result['total_iterations'] == 2, (
            f'应迭代 2 次，实际 {loop_log.output_result["total_iterations"]}'
        )

        # ★ 关键验证：循环体 webhook 执行日志是否存在
        webhook_logs = WorkflowExecutionLog.query.filter_by(
            instance_id=instance.id
        ).filter(
            WorkflowExecutionLog.node_type.in_(['webhook', 'trigger_webhook'])
        ).all()
        assert len(webhook_logs) == 2, (
            f'应有 2 条 webhook 执行日志（每轮迭代一条），'
            f'实际 {len(webhook_logs)}，'
            f'所有日志 node_type: {WorkflowExecutionLog.query.filter_by(instance_id=instance.id).with_entities(WorkflowExecutionLog.node_type).all()}'
        )

        # 验证每条 webhook 日志的 input_context 包含 loop_context
        for wlog in webhook_logs:
            assert wlog.input_context.get('loop_context') is not None, (
                'webhook 执行日志应包含 loop_context'
            )
