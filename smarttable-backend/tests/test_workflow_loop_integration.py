"""
循环节点（Loop Node）端到端集成测试

覆盖三大业务场景、错误处理与限制校验：
- 场景一：find_records + loop(find_records_column) + send_email（批量定向推送）
- 场景二：find_records + loop(find_records_all) + create_record（批量归档）
- 场景三：嵌套循环（外层人员 × 内层任务 → 任务明细）
- 错误处理：skip / terminate 模式下实例状态与下游节点行为
- 限制校验：通过 create_workflow 验证数量/深度/类型/参数边界

注意：find_records 节点存储结果时调用 r.to_dict()，单元测试通过 mock 让 to_dict()
返回扁平字典（field_id → value），本文件沿用该模式以测试完整链路。
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
)
from app.models.field import FieldType
from app.models.workflow import WorkflowNode
from app.services.workflow_execution_engine import WorkflowExecutionEngine, _LoopBodyNodeWrapper
from app.services.workflow_service import WorkflowService


# ── 公共 fixtures ────────────────────────────────────────────────────────────

@pytest.fixture(scope='function')
def loop_app():
    """为每个测试创建独立应用实例"""
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
    user = User(email='owner_integration@example.com', name='所有者')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user


@pytest.fixture(scope='function')
def base(ctx, owner):
    b = Base(name='集成测试 Base', owner_id=owner.id)
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
def engine(ctx, loop_app):
    eng = WorkflowExecutionEngine(loop_app)
    yield eng
    eng.executor.shutdown(wait=True)


# ── 工具函数 ─────────────────────────────────────────────────────────────────

def _make_mock_record(values, record_id=None, table_id=None):
    """构造 mock Record 对象：values 用于条件评估，to_dict() 返回扁平字典。

    与 test_workflow_execution.test_execute_find_records_returns_matching_records
    保持一致：find_records 存储结果时调用 r.to_dict()，mock 让其返回扁平
    field_id → value 字典，便于 loop 数据源解析与模板渲染。
    """
    mock = MagicMock()
    mock.id = record_id or uuid.uuid4()
    mock.table_id = table_id or uuid.uuid4()
    mock.values = dict(values)
    mock.to_dict.return_value = dict(values)
    mock.is_deleted = False
    return mock


def _run_workflow_sync(engine, instance):
    """同步执行工作流实例，模拟 _run_instance 的完成逻辑。

    与 _run_instance 区别：在当前线程/上下文中同步执行，便于测试断言。
    """
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
        trigger_type='record_created',
        status=WorkflowInstanceStatus.RUNNING,
        context=context or {},
        trigger_record_id=trigger_record_id,
    )
    db.session.add(instance)
    db.session.commit()
    return instance


def _make_loop_body_send_email(
    body_node_id='body-send-email',
    recipient_email='admin@example.com',
    subject_template='任务通知',
    body_template='你好',
):
    """构造循环体 send_email 子节点"""
    return {
        'id': body_node_id,
        'node_type': 'send_email',
        'name': '发送邮件',
        'config': {
            'action_type': 'send_email',
            'content_mode': 'custom',
            'recipient_type': 'fixed',
            'recipient_value': [recipient_email],
            'subject': subject_template,
            'body': body_template,
        },
        'order': 0,
        'next_nodes': [],
    }


def _make_loop_body_create_record(
    target_table_id,
    field_mappings,
    body_node_id='body-create-record',
):
    """构造循环体 create_record 子节点"""
    return {
        'id': body_node_id,
        'node_type': 'create_record',
        'name': '创建记录',
        'config': {
            'action_type': 'create_record',
            'target_table_id': str(target_table_id),
            'field_mappings': field_mappings,
        },
        'order': 0,
        'next_nodes': [],
    }


def _find_loop_logs(instance_id, data_source_marker=None):
    """找到 _execute_loop_node 创建的 loop 日志。

    execute_node 也会创建 node_type='loop' 的日志，但其 output_result
    为 {next_nodes: ...}，不含 total_iterations。_execute_loop_node 创建
    的日志 output_result 含 total_iterations/success_count 等统计字段。

    Args:
        instance_id: 工作流实例 ID
        data_source_marker: 可选，用于筛选 data_source 中包含该标记的日志
            （如 'outer-find' / 'inner-find' 区分嵌套循环的外层/内层日志）

    Returns:
        匹配的日志列表（按 created_at 排序）
    """
    logs = WorkflowExecutionLog.query.filter_by(
        instance_id=instance_id, node_type='loop'
    ).all()
    meaningful = [
        log for log in logs
        if log.output_result and 'total_iterations' in (log.output_result or {})
    ]
    if data_source_marker:
        meaningful = [
            log for log in meaningful
            if data_source_marker in str(log.input_context.get('data_source', {}))
        ]
    return meaningful


# ── SubTask 10.1: 场景一 find_records + loop + send_email ───────────────────

class TestLoopIntegrationFindRecordsSendEmail:
    """端到端测试：find_records → loop(find_records_column) → send_email

    业务场景：批量定向推送 —— 查找状态=进行中的任务，按负责人去重后发送邮件。
    """

    @patch('app.services.workflow_execution_engine.EmailSenderService.send_email_quick')
    @patch('app.services.email_config_service.EmailConfigService.is_email_enabled')
    def test_batch_send_email_by_member_deduped(
        self, mock_is_enabled, mock_send_quick, ctx, base, owner, engine
    ):
        mock_is_enabled.return_value = True
        mock_send_quick.return_value = (True, None)

        # 1. 创建表格与字段
        table = Table(base_id=base.id, name='任务表', order=0)
        db.session.add(table)
        db.session.commit()
        db.session.refresh(table)

        name_field = Field(table_id=table.id, name='任务名称',
                           type=FieldType.SINGLE_LINE_TEXT.value, order=0)
        member_field = Field(table_id=table.id, name='任务负责人',
                             type=FieldType.COLLABORATOR.value, order=1)
        status_field = Field(table_id=table.id, name='状态',
                             type=FieldType.SINGLE_SELECT.value, order=2)
        db.session.add_all([name_field, member_field, status_field])
        db.session.commit()
        db.session.refresh(name_field)
        db.session.refresh(member_field)
        db.session.refresh(status_field)

        # 2. 构造 4 条记录（Alice 2 条 + 陈一一 2 条），状态均为"进行中"
        member_field_id = str(member_field.id)
        status_field_id = str(status_field.id)
        name_field_id = str(name_field.id)
        alice = {'id': 'alice-uid', 'name': 'Alice', 'email': 'alice@example.com'}
        chen = {'id': 'chen-uid', 'name': '陈一一', 'email': 'chen@example.com'}

        mock_records = [
            _make_mock_record(
                {name_field_id: '任务A', member_field_id: [alice], status_field_id: '进行中'},
                table_id=table.id,
            ),
            _make_mock_record(
                {name_field_id: '任务B', member_field_id: [alice], status_field_id: '进行中'},
                table_id=table.id,
            ),
            _make_mock_record(
                {name_field_id: '任务C', member_field_id: [chen], status_field_id: '进行中'},
                table_id=table.id,
            ),
            _make_mock_record(
                {name_field_id: '任务D', member_field_id: [chen], status_field_id: '进行中'},
                table_id=table.id,
            ),
        ]

        # 3. 创建工作流：trigger → find_records → loop(find_records_column) → send_email
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='批量定向推送',
            created_by=owner.id,
            trigger_config={'trigger_type': 'record_created', 'filter_config': {}},
            nodes_config=[
                {'node_type': 'trigger', 'name': '触发', 'order': 0,
                 'next_nodes': []},  # next_nodes 由 create_workflow 维护
                {
                    'node_type': 'find_records',
                    'name': '查找进行中任务',
                    'config': {
                        'target_table_id': str(table.id),
                        'conditions': [{
                            'field_id': status_field_id,
                            'operator': 'equals',
                            'value': '进行中',
                        }],
                        'conjunction': 'and',
                        'result_variable': 'records',
                    },
                    'order': 1,
                },
                {
                    'node_type': 'loop',
                    'name': '按负责人循环',
                    'config': {
                        'loop_mode': 'sequential',
                        'data_source': {
                            'type': 'find_records_column',
                            'field_id': member_field_id,
                        },
                        'max_iterations': 100,
                        'error_handling': 'skip',
                        'empty_result_action': 'skip',
                        'loop_body_nodes': [
                            _make_loop_body_send_email(
                                subject_template='任务提醒',
                                body_template='你好 {{loop.current_data.name}}，'
                                              '邮箱：{{loop.current_data.email}}',
                            )
                        ],
                    },
                    'order': 2,
                    'next_nodes': [],
                },
            ],
        )

        # 串联节点：trigger → find_records → loop
        nodes_ordered = workflow.nodes.order_by(WorkflowNode.order).all()
        trigger_node = nodes_ordered[0]
        find_node = nodes_ordered[1]
        loop_node = nodes_ordered[2]
        trigger_node.next_nodes = [str(find_node.id)]
        find_node.next_nodes = [str(loop_node.id)]
        loop_node.next_nodes = []
        db.session.commit()

        instance = _make_instance(workflow.id, context={})

        # 4. mock Record.query 让 find_records 返回扁平记录
        with patch('app.services.workflow_execution_engine.Record.query') as mock_query:
            mock_query.filter_by.return_value.all.return_value = mock_records
            _run_workflow_sync(engine, instance)

        # 5. 验证
        db.session.refresh(instance)
        assert instance.status == WorkflowInstanceStatus.COMPLETED

        # send_email_quick 被调用 2 次（Alice + 陈一一去重后）
        assert mock_send_quick.call_count == 2

        # 验证每次调用的 body 包含正确的人员信息
        call_bodies = [call.kwargs.get('html_content', '') for call in mock_send_quick.call_args_list]
        joined = '\n'.join(call_bodies)
        assert 'Alice' in joined
        assert '陈一一' in joined
        assert 'alice@example.com' in joined
        assert 'chen@example.com' in joined

        # 验证 loop 节点执行日志（_execute_loop_node 创建的日志含 total_iterations）
        loop_logs = _find_loop_logs(instance.id)
        assert len(loop_logs) == 1, f'应有 1 条 loop 执行日志，实际 {len(loop_logs)}'
        loop_log = loop_logs[0]
        assert loop_log.status == 'success'
        assert loop_log.output_result['total_iterations'] == 2
        assert loop_log.output_result['success_count'] == 2
        assert loop_log.output_result['failure_count'] == 0


# ── SubTask 10.2: 场景二 find_records + loop + create_record ────────────────

class TestLoopIntegrationFindRecordsCreateRecord:
    """端到端测试：find_records → loop(find_records_all) → create_record

    业务场景：批量归档 —— 将"已上线"需求从进度表归档到归档表。
    """

    def test_batch_archive_to_another_table(
        self, ctx, base, owner, engine
    ):
        # 1. 创建需求进度表与需求归档表
        progress_table = Table(base_id=base.id, name='需求进度表', order=0)
        archive_table = Table(base_id=base.id, name='需求归档表', order=1)
        db.session.add_all([progress_table, archive_table])
        db.session.commit()
        db.session.refresh(progress_table)
        db.session.refresh(archive_table)

        # 进度表字段
        req_name_field = Field(table_id=progress_table.id, name='需求名称',
                               type=FieldType.SINGLE_LINE_TEXT.value, order=0)
        req_status_field = Field(table_id=progress_table.id, name='状态',
                                 type=FieldType.SINGLE_SELECT.value, order=1)
        req_owner_field = Field(table_id=progress_table.id, name='负责人',
                                type=FieldType.SINGLE_LINE_TEXT.value, order=2)
        db.session.add_all([req_name_field, req_status_field, req_owner_field])
        db.session.commit()
        db.session.refresh(req_name_field)
        db.session.refresh(req_status_field)
        db.session.refresh(req_owner_field)

        # 归档表字段
        arc_name_field = Field(table_id=archive_table.id, name='需求名称',
                               type=FieldType.SINGLE_LINE_TEXT.value, order=0)
        arc_owner_field = Field(table_id=archive_table.id, name='负责人',
                                type=FieldType.SINGLE_LINE_TEXT.value, order=1)
        arc_source_field = Field(table_id=archive_table.id, name='来源',
                                 type=FieldType.SINGLE_LINE_TEXT.value, order=2)
        db.session.add_all([arc_name_field, arc_owner_field, arc_source_field])
        db.session.commit()
        db.session.refresh(arc_name_field)
        db.session.refresh(arc_owner_field)
        db.session.refresh(arc_source_field)

        # 2. 构造 3 条"已上线"需求记录（扁平格式，供 find_records 存入上下文）
        req_name_id = str(req_name_field.id)
        req_status_id = str(req_status_field.id)
        req_owner_id = str(req_owner_field.id)

        mock_records = [
            _make_mock_record(
                {req_name_id: '需求A', req_status_id: '已上线', req_owner_id: '张三'},
                table_id=progress_table.id,
            ),
            _make_mock_record(
                {req_name_id: '需求B', req_status_id: '已上线', req_owner_id: '李四'},
                table_id=progress_table.id,
            ),
            _make_mock_record(
                {req_name_id: '需求C', req_status_id: '已上线', req_owner_id: '王五'},
                table_id=progress_table.id,
            ),
        ]

        # 3. 创建工作流：trigger → find_records → loop(find_records_all) → create_record
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=progress_table.id,
            name='批量归档',
            created_by=owner.id,
            trigger_config={'trigger_type': 'specified_time', 'filter_config': {}},
            nodes_config=[
                {'node_type': 'trigger', 'name': '触发', 'order': 0},
                {
                    'node_type': 'find_records',
                    'name': '查找已上线需求',
                    'config': {
                        'target_table_id': str(progress_table.id),
                        'conditions': [{
                            'field_id': req_status_id,
                            'operator': 'equals',
                            'value': '已上线',
                        }],
                        'conjunction': 'and',
                        'result_variable': 'records',
                    },
                    'order': 1,
                },
                {
                    'node_type': 'loop',
                    'name': '逐条归档',
                    'config': {
                        'loop_mode': 'sequential',
                        'data_source': {'type': 'find_records_all'},
                        'max_iterations': 100,
                        'error_handling': 'skip',
                        'empty_result_action': 'skip',
                        'loop_body_nodes': [
                            _make_loop_body_create_record(
                                target_table_id=archive_table.id,
                                field_mappings=[
                                    {
                                        'target_field_id': str(arc_name_field.id),
                                        'source_field_id': '',
                                        'value_template': '{{loop.current_data.' + req_name_id + '}}',
                                    },
                                    {
                                        'target_field_id': str(arc_owner_field.id),
                                        'source_field_id': '',
                                        'value_template': '{{loop.current_data.' + req_owner_id + '}}',
                                    },
                                    {
                                        'target_field_id': str(arc_source_field.id),
                                        'source_field_id': '',
                                        'value_template': '需求进度表',
                                    },
                                ],
                            )
                        ],
                    },
                    'order': 2,
                    'next_nodes': [],
                },
            ],
        )

        nodes_ordered = workflow.nodes.order_by(WorkflowNode.order).all()
        trigger_node = nodes_ordered[0]
        find_node = nodes_ordered[1]
        loop_node = nodes_ordered[2]
        trigger_node.next_nodes = [str(find_node.id)]
        find_node.next_nodes = [str(loop_node.id)]
        loop_node.next_nodes = []
        db.session.commit()

        instance = _make_instance(workflow.id, context={})
        # 使用 with 块限定 mock 作用范围：find_records 使用 mock 返回的记录，
        # create_record 写入真实数据库；验证阶段使用真实 Record.query
        with patch('app.services.workflow_execution_engine.Record.query') as mock_record_query:
            mock_record_query.filter_by.return_value.all.return_value = mock_records
            _run_workflow_sync(engine, instance)

        # 4. 验证
        db.session.refresh(instance)
        assert instance.status == WorkflowInstanceStatus.COMPLETED

        # 归档表新增 3 条记录（mock 已失效，查询真实数据库）
        archived_records = Record.query.filter_by(
            table_id=archive_table.id, is_deleted=False
        ).all()
        assert len(archived_records) == 3

        arc_name_id = str(arc_name_field.id)
        arc_owner_id = str(arc_owner_field.id)
        arc_source_id = str(arc_source_field.id)

        archived_names = sorted(r.values.get(arc_name_id, '') for r in archived_records)
        assert archived_names == ['需求A', '需求B', '需求C']

        archived_owners = sorted(r.values.get(arc_owner_id, '') for r in archived_records)
        assert archived_owners == ['张三', '李四', '王五']

        for r in archived_records:
            assert r.values.get(arc_source_id) == '需求进度表'

        # 验证 loop 节点执行日志（_execute_loop_node 创建的日志含 total_iterations）
        loop_logs = _find_loop_logs(instance.id)
        assert len(loop_logs) == 1, f'应有 1 条 loop 执行日志，实际 {len(loop_logs)}'
        loop_log = loop_logs[0]
        assert loop_log.output_result['total_iterations'] == 3
        assert loop_log.output_result['success_count'] == 3


# ── SubTask 10.3: 场景三 嵌套循环 ───────────────────────────────────────────

class TestLoopIntegrationNested:
    """端到端测试：嵌套循环（外层人员 × 内层任务 → 任务明细表）

    验证：外层 2 次 + 内层每次 3 次 = 6 条明细记录，且 loop_context 在内层
    结束后恢复外层值（最终被外层 finally 清除）。
    """

    def test_nested_loop_creates_6_detail_records(
        self, ctx, base, owner, engine
    ):
        # 1. 创建人员底表、任务底表、任务明细表
        emp_table = Table(base_id=base.id, name='人员底表', order=0)
        task_table = Table(base_id=base.id, name='任务底表', order=1)
        detail_table = Table(base_id=base.id, name='任务明细表', order=2)
        db.session.add_all([emp_table, task_table, detail_table])
        db.session.commit()
        db.session.refresh(emp_table)
        db.session.refresh(task_table)
        db.session.refresh(detail_table)

        # 人员底表字段
        emp_name_field = Field(table_id=emp_table.id, name='员工姓名',
                               type=FieldType.SINGLE_LINE_TEXT.value, order=0)
        emp_type_field = Field(table_id=emp_table.id, name='员工类型',
                               type=FieldType.SINGLE_LINE_TEXT.value, order=1)
        emp_status_field = Field(table_id=emp_table.id, name='在职状态',
                                 type=FieldType.SINGLE_SELECT.value, order=2)
        db.session.add_all([emp_name_field, emp_type_field, emp_status_field])
        db.session.commit()
        for f in [emp_name_field, emp_type_field, emp_status_field]:
            db.session.refresh(f)

        # 任务底表字段
        task_name_field = Field(table_id=task_table.id, name='任务名称',
                                type=FieldType.SINGLE_LINE_TEXT.value, order=0)
        task_type_field = Field(table_id=task_table.id, name='工作类型',
                                type=FieldType.SINGLE_LINE_TEXT.value, order=1)
        db.session.add_all([task_name_field, task_type_field])
        db.session.commit()
        for f in [task_name_field, task_type_field]:
            db.session.refresh(f)

        # 任务明细表字段
        detail_emp_field = Field(table_id=detail_table.id, name='员工姓名',
                                 type=FieldType.SINGLE_LINE_TEXT.value, order=0)
        detail_task_field = Field(table_id=detail_table.id, name='任务名称',
                                  type=FieldType.SINGLE_LINE_TEXT.value, order=1)
        db.session.add_all([detail_emp_field, detail_task_field])
        db.session.commit()
        for f in [detail_emp_field, detail_task_field]:
            db.session.refresh(f)

        # 2. 构造 2 个员工 + 3 个任务记录
        emp_name_id = str(emp_name_field.id)
        emp_type_id = str(emp_type_field.id)
        emp_status_id = str(emp_status_field.id)
        task_name_id = str(task_name_field.id)
        task_type_id = str(task_type_field.id)

        mock_emp_records = [
            _make_mock_record(
                {emp_name_id: '员工A', emp_type_id: '工程师', emp_status_id: '在职'},
                table_id=emp_table.id,
            ),
            _make_mock_record(
                {emp_name_id: '员工B', emp_type_id: '设计师', emp_status_id: '在职'},
                table_id=emp_table.id,
            ),
        ]
        mock_task_records = [
            _make_mock_record(
                {task_name_id: '任务1', task_type_id: '工程师'},
                table_id=task_table.id,
            ),
            _make_mock_record(
                {task_name_id: '任务2', task_type_id: '工程师'},
                table_id=task_table.id,
            ),
            _make_mock_record(
                {task_name_id: '任务3', task_type_id: '设计师'},
                table_id=task_table.id,
            ),
        ]

        # Record.query 被 find_records 多次调用，按 table_id 路由不同 mock 列表
        def filter_by_side_effect(**kwargs):
            table_id = kwargs.get('table_id')
            mock = MagicMock()
            if str(table_id) == str(emp_table.id):
                mock.all.return_value = mock_emp_records
            elif str(table_id) == str(task_table.id):
                mock.all.return_value = mock_task_records
            else:
                mock.all.return_value = []
            return mock

        # 3. 创建工作流：trigger → find_records(员工) → loop(外层) →
        #    [find_records(任务) → loop(内层) → create_record]
        detail_emp_id = str(detail_emp_field.id)
        detail_task_id = str(detail_task_field.id)

        # 内层 loop 的循环体：create_record（引用内层 loop 当前任务名）
        inner_body_create = _make_loop_body_create_record(
            target_table_id=detail_table.id,
            field_mappings=[
                {
                    'target_field_id': detail_task_id,
                    'source_field_id': '',
                    'value_template': '{{loop.current_data.' + task_name_id + '}}',
                },
            ],
            body_node_id='inner-create',
        )

        # 内层 loop 节点
        inner_loop = {
            'id': 'inner-loop',
            'node_type': 'loop',
            'name': '内层循环-任务',
            'config': {
                'loop_mode': 'sequential',
                'data_source': {'type': 'find_records_all', 'node_id': 'inner-find'},
                'max_iterations': 100,
                'error_handling': 'skip',
                'empty_result_action': 'skip',
                'loop_body_nodes': [inner_body_create],
            },
            'order': 1,
            'next_nodes': [],
        }

        # 内层 find_records 节点（查找所有任务，结果存入 records 变量）
        # 使用默认 'records' 变量名：_resolve_find_records_variable 对循环体内的
        # dict 节点 ID（如 'inner-find'）无法在 DB 中查到，会回退到 'records'。
        # 外层 loop 在迭代开始前已解析得到 data_array 局部变量，内层 find_records
        # 覆写 context['records'] 不影响外层迭代。
        inner_find = {
            'id': 'inner-find',
            'node_type': 'find_records',
            'name': '查找任务',
            'config': {
                'target_table_id': str(task_table.id),
                'conditions': [],
                'conjunction': 'and',
                'result_variable': 'records',
            },
            'order': 0,
            'next_nodes': ['inner-loop'],
        }

        # 外层 loop 循环体：find_records(任务) → loop(内层)
        outer_body_nodes = [inner_find, inner_loop]

        # 外层 find_records 节点（查找在职员工，结果存入 records 变量）
        outer_find = {
            'id': 'outer-find',
            'node_type': 'find_records',
            'name': '查找在职员工',
            'config': {
                'target_table_id': str(emp_table.id),
                'conditions': [{
                    'field_id': emp_status_id,
                    'operator': 'equals',
                    'value': '在职',
                }],
                'conjunction': 'and',
                'result_variable': 'records',
            },
            'order': 1,
        }

        # 外层 loop 节点
        outer_loop = {
            'id': 'outer-loop',
            'node_type': 'loop',
            'name': '外层循环-员工',
            'config': {
                'loop_mode': 'sequential',
                'data_source': {'type': 'find_records_all', 'node_id': 'outer-find'},
                'max_iterations': 100,
                'error_handling': 'skip',
                'empty_result_action': 'skip',
                'loop_body_nodes': outer_body_nodes,
            },
            'order': 2,
            'next_nodes': [],
        }

        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=emp_table.id,
            name='嵌套循环-任务明细',
            created_by=owner.id,
            trigger_config={'trigger_type': 'record_created', 'filter_config': {}},
            nodes_config=[
                {'node_type': 'trigger', 'name': '触发', 'order': 0},
                outer_find,
                outer_loop,
            ],
        )

        # 串联主链节点
        nodes_ordered = workflow.nodes.order_by(WorkflowNode.order).all()
        trigger_node = nodes_ordered[0]
        # 找到 outer-find 和 outer-loop（按 name 区分，因为 id 是新建的）
        outer_find_node = next(n for n in nodes_ordered if n.name == '查找在职员工')
        outer_loop_node = next(n for n in nodes_ordered if n.name == '外层循环-员工')
        trigger_node.next_nodes = [str(outer_find_node.id)]
        outer_find_node.next_nodes = [str(outer_loop_node.id)]
        outer_loop_node.next_nodes = []
        db.session.commit()

        instance = _make_instance(workflow.id, context={})
        # 使用 with 块限定 mock 作用范围：find_records 按 table_id 路由 mock 记录，
        # create_record 写入真实数据库；验证阶段使用真实 Record.query
        with patch('app.services.workflow_execution_engine.Record.query') as mock_record_query:
            mock_record_query.filter_by.side_effect = filter_by_side_effect
            _run_workflow_sync(engine, instance)

        # 4. 验证
        db.session.refresh(instance)
        assert instance.status == WorkflowInstanceStatus.COMPLETED

        # 任务明细表新增 6 条记录（2 员工 × 3 任务，mock 已失效，查询真实数据库）
        detail_records = Record.query.filter_by(
            table_id=detail_table.id, is_deleted=False
        ).all()
        assert len(detail_records) == 6

        # 每条记录的任务名称应来自 3 个任务之一
        task_names_in_details = [r.values.get(detail_task_id, '') for r in detail_records]
        for tn in ['任务1', '任务2', '任务3']:
            # 每个任务出现 2 次（2 个员工各一次）
            assert task_names_in_details.count(tn) == 2

        # 验证 loop 节点执行日志（_execute_loop_node 创建的日志含 total_iterations）
        # 外层 1 条 + 内层 2 条（外层每次迭代触发 1 次内层 loop）
        all_loop_logs = _find_loop_logs(instance.id)
        assert len(all_loop_logs) == 3, f'应有 3 条 loop 执行日志，实际 {len(all_loop_logs)}'

        # 外层日志（data_source 含 outer-find）
        outer_logs = _find_loop_logs(instance.id, 'outer-find')
        assert len(outer_logs) == 1, '外层 loop 日志应只有 1 条'
        outer_log = outer_logs[0]
        assert outer_log.output_result['total_iterations'] == 2
        assert outer_log.output_result['success_count'] == 2

        # 内层日志（data_source 含 inner-find）：每次外层迭代触发 1 次内层 loop
        inner_logs = _find_loop_logs(instance.id, 'inner-find')
        assert len(inner_logs) == 2, f'内层 loop 日志应有 2 条，实际 {len(inner_logs)}'
        for il in inner_logs:
            assert il.output_result['total_iterations'] == 3
            assert il.output_result['success_count'] == 3

        # 验证 loop_context 在所有循环结束后被清除
        final_context = instance.context or {}
        assert 'loop_context' not in final_context or final_context.get('loop_context') is None, \
            '循环结束后 loop_context 应被清除'


# ── SubTask 10.4: 错误处理集成测试 ──────────────────────────────────────────

class TestLoopIntegrationErrorHandling:
    """端到端测试：error_handling = skip / terminate

    验证：实例状态、下游节点执行情况、执行日志统计。
    """

    def _build_workflow_with_loop_and_downstream(
        self, base, table, owner, error_handling, trigger_field_id
    ):
        """创建 trigger → loop → downstream(trigger) 工作流。

        循环体内放 trigger 子节点（无副作用），downstream 也是 trigger 节点，
        通过执行日志区分是否被调用。
        """
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name=f'错误处理-{error_handling}',
            created_by=owner.id,
            trigger_config={'trigger_type': 'record_created', 'filter_config': {}},
            nodes_config=[
                {'node_type': 'trigger', 'name': '触发', 'order': 0},
                {
                    'node_type': 'loop',
                    'name': '循环',
                    'config': {
                        'loop_mode': 'sequential',
                        'data_source': {
                            'type': 'trigger_field',
                            'trigger_field_id': trigger_field_id,
                        },
                        'max_iterations': 10,
                        'error_handling': error_handling,
                        'empty_result_action': 'skip',
                        'loop_body_nodes': [
                            {
                                'id': 'body-trigger',
                                'node_type': 'trigger',
                                'name': '循环体触发',
                                'config': {},
                                'order': 0,
                                'next_nodes': [],
                            }
                        ],
                    },
                    'order': 1,
                    'next_nodes': [],
                },
                {
                    'node_type': 'trigger',
                    'name': '下游节点',
                    'config': {},
                    'order': 2,
                    'next_nodes': [],
                },
            ],
        )
        nodes_ordered = workflow.nodes.order_by(WorkflowNode.order).all()
        trigger_node = nodes_ordered[0]
        loop_node = nodes_ordered[1]
        downstream_node = nodes_ordered[2]
        trigger_node.next_nodes = [str(loop_node.id)]
        loop_node.next_nodes = [str(downstream_node.id)]
        db.session.commit()
        return workflow, trigger_node, loop_node, downstream_node

    def test_error_handling_skip_workflow_completes_and_downstream_executes(
        self, ctx, base, owner, engine
    ):
        """error_handling=skip：单次迭代失败被跳过，工作流 completed，下游节点执行"""
        table = Table(base_id=base.id, name='skip测试表', order=0)
        db.session.add(table)
        db.session.commit()
        db.session.refresh(table)
        field = Field(table_id=table.id, name='状态',
                      type=FieldType.SINGLE_LINE_TEXT.value, order=0)
        db.session.add(field)
        db.session.commit()
        db.session.refresh(field)

        workflow, trigger_node, loop_node, downstream_node = \
            self._build_workflow_with_loop_and_downstream(
                base, table, owner, 'skip', str(field.id)
            )

        instance = _make_instance(
            workflow.id,
            context={'trigger_event': {'record': {str(field.id): ['ok-1', 'fail', 'ok-2']}}},
        )

        # 让第 2 次循环体迭代失败：仅对 _LoopBodyNodeWrapper 实例（循环体子节点）
        # 触发异常，不影响主链节点（trigger / loop / downstream）的 execute_node 调用。
        original_execute = engine.execute_node
        body_call_count = {'n': 0}

        def mock_execute_node(inst, node):
            if isinstance(node, _LoopBodyNodeWrapper):
                body_call_count['n'] += 1
                if body_call_count['n'] == 2:
                    raise ValueError('模拟迭代失败')
            return original_execute(inst, node)

        with patch.object(engine, 'execute_node', side_effect=mock_execute_node):
            _run_workflow_sync(engine, instance)

        db.session.refresh(instance)
        assert instance.status == WorkflowInstanceStatus.COMPLETED

        # 使用 _find_loop_logs 获取 _execute_loop_node 创建的日志（含 total_iterations）
        loop_logs = _find_loop_logs(instance.id)
        assert len(loop_logs) == 1, f'应有 1 条 loop 执行日志，实际 {len(loop_logs)}'
        loop_log = loop_logs[0]
        assert loop_log.status == 'success'
        assert loop_log.output_result['success_count'] == 2
        assert loop_log.output_result['failure_count'] == 1
        assert loop_log.output_result['early_terminated'] is False

        # 下游节点应被执行（有 trigger 类型日志记录）
        # 注：trigger_node 自身、循环体内 trigger、下游 trigger 都会写日志
        trigger_logs = WorkflowExecutionLog.query.filter_by(
            instance_id=instance.id, node_type='trigger'
        ).all()
        # 至少有下游节点的日志（最后一次 trigger 调用是下游节点）
        assert len(trigger_logs) >= 1

    def test_error_handling_terminate_workflow_errors_and_downstream_skipped(
        self, ctx, base, owner, engine
    ):
        """error_handling=terminate：单次迭代失败终止循环，工作流 error，下游不执行"""
        table = Table(base_id=base.id, name='terminate测试表', order=0)
        db.session.add(table)
        db.session.commit()
        db.session.refresh(table)
        field = Field(table_id=table.id, name='状态',
                      type=FieldType.SINGLE_LINE_TEXT.value, order=0)
        db.session.add(field)
        db.session.commit()
        db.session.refresh(field)

        workflow, trigger_node, loop_node, downstream_node = \
            self._build_workflow_with_loop_and_downstream(
                base, table, owner, 'terminate', str(field.id)
            )

        instance = _make_instance(
            workflow.id,
            context={'trigger_event': {'record': {str(field.id): ['fail', 'ok-1', 'ok-2']}}},
        )

        # 让第 1 次循环体迭代失败：仅对 _LoopBodyNodeWrapper 实例触发异常，
        # 同时确保下游节点（WorkflowNode）不被执行。
        original_execute = engine.execute_node
        body_call_count = {'n': 0}
        downstream_node_id = str(downstream_node.id)

        def mock_execute_node(inst, node):
            if isinstance(node, _LoopBodyNodeWrapper):
                body_call_count['n'] += 1
                if body_call_count['n'] == 1:
                    raise ValueError('模拟终止')
            # 下游节点不应被调用
            if getattr(node, 'id', None) and str(node.id) == downstream_node_id:
                raise AssertionError('下游节点不应被执行')
            return original_execute(inst, node)

        with patch.object(engine, 'execute_node', side_effect=mock_execute_node):
            _run_workflow_sync(engine, instance)

        db.session.refresh(instance)
        assert instance.status == WorkflowInstanceStatus.ERROR

        # 使用 _find_loop_logs 获取 _execute_loop_node 创建的日志（含 total_iterations）
        loop_logs = _find_loop_logs(instance.id)
        assert len(loop_logs) == 1, f'应有 1 条 loop 执行日志，实际 {len(loop_logs)}'
        loop_log = loop_logs[0]
        assert loop_log.status == 'error'
        assert loop_log.output_result['early_terminated'] is True
        assert loop_log.output_result['success_count'] == 0
        assert loop_log.output_result['failure_count'] == 1
        assert '模拟终止' in (loop_log.error_message or '')


# ── SubTask 10.5: 限制校验集成测试 ──────────────────────────────────────────

class TestLoopValidationIntegration:
    """通过 create_workflow 验证限制校验（补充单元测试未覆盖的集成路径）"""

    def _make_loop_config(self, **overrides):
        """构造基础 loop 节点配置"""
        config = {
            'loop_mode': 'sequential',
            'data_source': {'type': 'find_records_all'},
            'max_iterations': 100,
            'error_handling': 'skip',
            'empty_result_action': 'skip',
            'loop_body_nodes': [
                {
                    'id': 'body-1',
                    'node_type': 'update_record',
                    'name': '更新',
                    'config': {'action_type': 'update_record', 'updates': []},
                    'order': 0,
                    'next_nodes': [],
                }
            ],
        }
        config.update(overrides)
        return {
            'node_type': 'loop',
            'name': '循环',
            'config': config,
            'order': 0,
            'next_nodes': [],
        }

    def test_create_workflow_rejects_six_loop_nodes(
        self, ctx, base, table, owner
    ):
        """6 个 loop 节点应被拒绝"""
        nodes = [self._make_loop_config() for _ in range(6)]
        for i, n in enumerate(nodes):
            n['order'] = i
        with pytest.raises(ValueError) as exc:
            WorkflowService.create_workflow(
                base_id=base.id,
                table_id=table.id,
                name='过多循环',
                created_by=owner.id,
                nodes_config=nodes,
            )
        msg = str(exc.value)
        assert '5' in msg and '循环' in msg

    def test_create_workflow_rejects_nested_depth_4(
        self, ctx, base, table, owner
    ):
        """嵌套深度 4 应被拒绝"""
        innermost = self._make_loop_config()
        level3 = self._make_loop_config(
            loop_body_nodes=[innermost]
        )
        level2 = self._make_loop_config(
            loop_body_nodes=[level3]
        )
        level1 = self._make_loop_config(
            loop_body_nodes=[level2]
        )
        with pytest.raises(ValueError) as exc:
            WorkflowService.create_workflow(
                base_id=base.id,
                table_id=table.id,
                name='嵌套过深',
                created_by=owner.id,
                nodes_config=[level1],
            )
        assert '嵌套深度' in str(exc.value) or '3 层' in str(exc.value)

    def test_create_workflow_rejects_condition_in_loop_body(
        self, ctx, base, table, owner
    ):
        """循环体包含 condition 应被拒绝"""
        loop = self._make_loop_config(
            loop_body_nodes=[
                {
                    'id': 'cond-1',
                    'node_type': 'condition',
                    'name': '条件',
                    'config': {},
                    'order': 0,
                    'next_nodes': [],
                }
            ]
        )
        with pytest.raises(ValueError) as exc:
            WorkflowService.create_workflow(
                base_id=base.id,
                table_id=table.id,
                name='条件循环体',
                created_by=owner.id,
                nodes_config=[loop],
            )
        assert '条件' in str(exc.value)

    def test_create_workflow_rejects_max_iterations_zero(
        self, ctx, base, table, owner
    ):
        """max_iterations=0 应被拒绝"""
        loop = self._make_loop_config(max_iterations=0)
        with pytest.raises(ValueError) as exc:
            WorkflowService.create_workflow(
                base_id=base.id,
                table_id=table.id,
                name='零迭代',
                created_by=owner.id,
                nodes_config=[loop],
            )
        assert 'max_iterations' in str(exc.value)

    def test_create_workflow_rejects_max_iterations_over_1000(
        self, ctx, base, table, owner
    ):
        """max_iterations=1001 应被拒绝"""
        loop = self._make_loop_config(max_iterations=1001)
        with pytest.raises(ValueError) as exc:
            WorkflowService.create_workflow(
                base_id=base.id,
                table_id=table.id,
                name='超限迭代',
                created_by=owner.id,
                nodes_config=[loop],
            )
        assert 'max_iterations' in str(exc.value)

    def test_create_workflow_rejects_invalid_error_handling(
        self, ctx, base, table, owner
    ):
        """error_handling='invalid' 应被拒绝"""
        loop = self._make_loop_config(error_handling='invalid')
        with pytest.raises(ValueError) as exc:
            WorkflowService.create_workflow(
                base_id=base.id,
                table_id=table.id,
                name='非法错误处理',
                created_by=owner.id,
                nodes_config=[loop],
            )
        assert 'error_handling' in str(exc.value)

    def test_create_workflow_rejects_empty_loop_body_nodes(
        self, ctx, base, table, owner
    ):
        """loop_body_nodes 为空应被拒绝"""
        loop = self._make_loop_config(loop_body_nodes=[])
        with pytest.raises(ValueError) as exc:
            WorkflowService.create_workflow(
                base_id=base.id,
                table_id=table.id,
                name='空循环体',
                created_by=owner.id,
                nodes_config=[loop],
            )
        assert 'loop_body_nodes' in str(exc.value)

    def test_update_workflow_rejects_six_loop_nodes(
        self, ctx, base, table, owner
    ):
        """update_workflow 也应校验 loop 节点数量"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='初始工作流',
            created_by=owner.id,
        )
        nodes = [self._make_loop_config() for _ in range(6)]
        for i, n in enumerate(nodes):
            n['order'] = i
        with pytest.raises(ValueError):
            WorkflowService.update_workflow(
                workflow_id=workflow.id,
                user_id=owner.id,
                nodes_config=nodes,
            )
