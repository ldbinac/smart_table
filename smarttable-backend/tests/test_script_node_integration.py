"""
自定义脚本节点集成测试
测试执行引擎的 _resolve_script_input、_resolve_script_branch 纯逻辑，
以及 _execute_script_node / execute_node 端到端执行（写入 ctx[result_variable] 与 node_outputs）。
"""
import sys
import os
import uuid
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.extensions import db
from app.models import (
    User,
    Base,
    Workflow,
    WorkflowStatus,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowExecutionLog,
)
from app.models.workflow import WorkflowNode, WorkflowNodeType
from app.services.workflow_execution_engine import WorkflowExecutionEngine


@pytest.fixture
def engine(app):
    """创建绑定当前 app 的执行引擎，测试后关闭线程池"""
    eng = WorkflowExecutionEngine(app)
    yield eng
    eng.executor.shutdown(wait=True)


def _create_user_base_workflow():
    """创建用户、Base、工作流并返回（满足外键约束）"""
    user = User(email=f'script-{uuid.uuid4().hex[:8]}@example.com', name='脚本测试用户')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)

    base = Base(name='脚本测试 Base', owner_id=user.id)
    db.session.add(base)
    db.session.commit()
    db.session.refresh(base)

    workflow = Workflow(
        base_id=base.id,
        name='脚本测试工作流',
        status=WorkflowStatus.DRAFT,
        current_version=0,
    )
    db.session.add(workflow)
    db.session.commit()
    db.session.refresh(workflow)
    return workflow


def _make_instance(workflow, context=None):
    instance = WorkflowInstance(
        workflow_id=workflow.id,
        version_number=1,
        trigger_type='manual',
        status=WorkflowInstanceStatus.RUNNING,
        context=context or {},
    )
    db.session.add(instance)
    db.session.commit()
    db.session.refresh(instance)
    return instance


def _add_node(workflow, node_type, name, order, next_nodes=None, config=None):
    node = WorkflowNode(
        workflow_id=workflow.id,
        node_type=node_type,
        name=name,
        config=config or {},
        order=order,
        next_nodes=next_nodes or [],
    )
    db.session.add(node)
    db.session.commit()
    db.session.refresh(node)
    return node


class TestResolveScriptBranch:
    """测试 _resolve_script_branch 分支路由纯逻辑"""

    def test_known_label_routes_to_target(self, engine):
        node = SimpleNamespace(next_nodes=['default_next'])
        branches = [{'label': 'high', 'target_node_id': 'node_high'}]
        result = engine._resolve_script_branch(node, branches, 'high')
        assert result == ['node_high']

    def test_unknown_label_falls_back_to_default(self, engine):
        node = SimpleNamespace(next_nodes=['default_next'])
        branches = [{'label': 'high', 'target_node_id': 'node_high'}]
        result = engine._resolve_script_branch(node, branches, 'unknown_label')
        assert result == ['default_next']

    def test_no_label_uses_default(self, engine):
        node = SimpleNamespace(next_nodes=['default_next'])
        branches = [{'label': 'high', 'target_node_id': 'node_high'}]
        result = engine._resolve_script_branch(node, branches, None)
        assert result == ['default_next']

    def test_empty_branches_uses_default_next_nodes(self, engine):
        node = SimpleNamespace(next_nodes=['n1', 'n2'])
        result = engine._resolve_script_branch(node, [], 'anything')
        assert result == ['n1', 'n2']


class TestResolveScriptInput:
    """测试 _resolve_script_input 输入解析"""

    def test_single_predecessor_returns_its_output(self, engine):
        workflow = _create_user_base_workflow()
        script_node = _add_node(workflow, WorkflowNodeType.SCRIPT, '脚本', order=10, next_nodes=[])
        pred = _add_node(workflow, WorkflowNodeType.FIND_RECORDS, '前驱', order=0, next_nodes=[str(script_node.id)])

        instance = _make_instance(workflow, context={
            'node_outputs': {str(pred.id): {'result': 'pred_data'}}
        })
        result = engine._resolve_script_input(instance, script_node, None)
        assert result == 'pred_data'

    def test_multiple_predecessors_returns_dict(self, engine):
        workflow = _create_user_base_workflow()
        script_node = _add_node(workflow, WorkflowNodeType.SCRIPT, '脚本', order=10, next_nodes=[])
        pred_a = _add_node(workflow, WorkflowNodeType.FIND_RECORDS, 'A', order=0, next_nodes=[str(script_node.id)])
        pred_b = _add_node(workflow, WorkflowNodeType.FIND_RECORDS, 'B', order=1, next_nodes=[str(script_node.id)])

        instance = _make_instance(workflow, context={
            'node_outputs': {
                str(pred_a.id): {'result': 'data_a'},
                str(pred_b.id): {'result': 'data_b'},
            }
        })
        result = engine._resolve_script_input(instance, script_node, None)
        assert isinstance(result, dict)
        assert result[str(pred_a.id)] == 'data_a'
        assert result[str(pred_b.id)] == 'data_b'

    def test_no_predecessor_returns_none(self, engine):
        workflow = _create_user_base_workflow()
        script_node = _add_node(workflow, WorkflowNodeType.SCRIPT, '脚本', order=0, next_nodes=[])

        instance = _make_instance(workflow, context={})
        result = engine._resolve_script_input(instance, script_node, None)
        assert result is None

    def test_specified_input_node_id(self, engine):
        workflow = _create_user_base_workflow()
        script_node = _add_node(workflow, WorkflowNodeType.SCRIPT, '脚本', order=10, next_nodes=[])
        pred = _add_node(workflow, WorkflowNodeType.FIND_RECORDS, '前驱', order=0, next_nodes=[str(script_node.id)])

        instance = _make_instance(workflow, context={
            'node_outputs': {str(pred.id): {'result': 'specified_data'}}
        })
        result = engine._resolve_script_input(instance, script_node, str(pred.id))
        assert result == 'specified_data'


class TestExecuteScriptNode:
    """测试 _execute_script_node / execute_node 端到端执行"""

    def test_writes_result_variable_to_context(self, engine):
        workflow = _create_user_base_workflow()
        script_node = _add_node(
            workflow, WorkflowNodeType.SCRIPT, '脚本', order=0, next_nodes=[],
            config={
                'language': 'python',
                'script_source': 'set_result({"answer": 42})',
                'timeout': 5,
                'result_variable': 'script_result',
                'branches': [],
            },
        )

        instance = _make_instance(workflow, context={})
        result = engine._execute_script_node(instance, script_node)

        assert isinstance(result, dict)
        assert result['result']['result'] == {'answer': 42}
        # ctx[result_variable] 写入
        ctx = instance.context or {}
        assert ctx.get('script_result') == {'answer': 42}

    def test_branch_routing_to_target(self, engine):
        workflow = _create_user_base_workflow()
        target_node = _add_node(workflow, WorkflowNodeType.UPDATE_RECORD, '目标', order=10, next_nodes=[])
        script_node = _add_node(
            workflow, WorkflowNodeType.SCRIPT, '脚本', order=0, next_nodes=['default_next'],
            config={
                'language': 'python',
                'script_source': 'set_result(1)\nset_branch("high")',
                'timeout': 5,
                'result_variable': 'script_result',
                'branches': [{'label': 'high', 'target_node_id': str(target_node.id)}],
            },
        )

        instance = _make_instance(workflow, context={})
        result = engine._execute_script_node(instance, script_node)
        assert result['next_nodes'] == [str(target_node.id)]
        assert result['result']['branch'] == 'high'

    def test_execute_node_writes_node_outputs(self, engine):
        workflow = _create_user_base_workflow()
        script_node = _add_node(
            workflow, WorkflowNodeType.SCRIPT, '脚本', order=0, next_nodes=[],
            config={
                'language': 'python',
                'script_source': 'set_result(42)',
                'timeout': 5,
                'result_variable': 'script_result',
                'branches': [],
            },
        )

        instance = _make_instance(workflow, context={})
        result = engine.execute_node(instance, script_node)

        assert isinstance(result, dict)
        ctx = instance.context or {}
        node_outputs = ctx.get('node_outputs') or {}
        assert str(script_node.id) in node_outputs
        # node_outputs[id] 仅写入 dispatch_result 的 result 部分（output_result），
        # 使 {{node_outputs.<id>.result.field}} 模板路径可正确解析（无双重嵌套）
        assert node_outputs[str(script_node.id)]['result'] == 42

    def test_node_outputs_supports_template_path(self, engine):
        """node_outputs[id].result.field 模板路径可正确解析（dict 结果）"""
        workflow = _create_user_base_workflow()
        script_node = _add_node(
            workflow, WorkflowNodeType.SCRIPT, '脚本', order=0, next_nodes=[],
            config={
                'language': 'python',
                'script_source': 'set_result({"answer": 42, "name": "test"})',
                'timeout': 5,
                'result_variable': 'script_result',
                'branches': [],
            },
        )

        instance = _make_instance(workflow, context={})
        engine.execute_node(instance, script_node)

        ctx = instance.context or {}
        node_outputs = ctx.get('node_outputs') or {}
        assert str(script_node.id) in node_outputs
        assert node_outputs[str(script_node.id)]['result']['answer'] == 42
        assert node_outputs[str(script_node.id)]['result']['name'] == 'test'

    def test_render_context_exposes_script_result(self, engine):
        """脚本结果变量暴露到渲染上下文顶层，使 {{script_result.field}} 可直接引用"""
        workflow = _create_user_base_workflow()
        script_node = _add_node(
            workflow, WorkflowNodeType.SCRIPT, '脚本', order=0, next_nodes=[],
            config={
                'language': 'python',
                'script_source': 'set_result({"answer": 42})',
                'timeout': 5,
                'result_variable': 'script_result',
                'branches': [],
            },
        )

        instance = _make_instance(workflow, context={})
        engine._execute_script_node(instance, script_node)

        render_ctx = engine._build_render_context(instance)
        assert render_ctx['script_result']['answer'] == 42

    def test_execute_node_records_error_status(self, engine):
        """脚本执行失败时 execution_log.status=='error' 且 error_message 非空"""
        workflow = _create_user_base_workflow()
        script_node = _add_node(
            workflow, WorkflowNodeType.SCRIPT, '脚本', order=0, next_nodes=[],
            config={
                'language': 'python',
                'script_source': 'set_result(undefined_var)',
                'timeout': 5,
                'result_variable': 'script_result',
                'branches': [],
            },
        )

        instance = _make_instance(workflow, context={})
        # 脚本引用未定义变量 → NameError → execute_node 抛出 RuntimeError
        with pytest.raises(RuntimeError):
            engine.execute_node(instance, script_node)

        logs = (
            WorkflowExecutionLog.query
            .filter_by(instance_id=instance.id)
            .order_by(WorkflowExecutionLog.started_at.desc())
            .all()
        )
        assert len(logs) >= 1
        latest = logs[0]
        assert latest.status == 'error'
        assert latest.error_message
