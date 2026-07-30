"""
循环节点（Loop Node）单元测试

覆盖：
- WorkflowService._validate_loop_node 配置校验
- WorkflowService._count_loop_nodes 递归统计
- WorkflowService.create_workflow / update_workflow 中 loop 节点的保存与校验路径
- WorkflowExecutionEngine._resolve_loop_data_source 四种数据源解析
- WorkflowExecutionEngine._execute_loop_node 基本执行流程与执行日志
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
from app.services.workflow_execution_engine import (
    WorkflowExecutionEngine,
    _LoopBodyNodeWrapper,
)
from app.services.workflow_service import WorkflowService


@pytest.fixture(scope='function')
def loop_app():
    """为每个循环节点测试创建独立应用实例"""
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
    user = User(email='owner_loop@example.com', name='所有者')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user


@pytest.fixture(scope='function')
def base(ctx, owner):
    b = Base(name='循环测试 Base', owner_id=owner.id)
    db.session.add(b)
    db.session.commit()
    db.session.refresh(b)
    return b


@pytest.fixture(scope='function')
def table(ctx, base):
    t = Table(base_id=base.id, name='循环测试表格', order=0)
    db.session.add(t)
    db.session.commit()
    db.session.refresh(t)
    return t


@pytest.fixture(scope='function')
def field(ctx, table):
    f = Field(
        table_id=table.id,
        name='状态',
        type=FieldType.SINGLE_LINE_TEXT.value,
        order=0,
    )
    db.session.add(f)
    db.session.commit()
    db.session.refresh(f)
    return f


@pytest.fixture(scope='function')
def record(ctx, table, field, owner):
    r = Record(
        table_id=table.id,
        values={str(field.id): '初始值'},
        created_by=owner.id,
    )
    db.session.add(r)
    db.session.commit()
    db.session.refresh(r)
    return r


@pytest.fixture(scope='function')
def engine(ctx, loop_app):
    eng = WorkflowExecutionEngine(loop_app)
    yield eng
    eng.executor.shutdown(wait=True)


def _make_loop_node_config(
    loop_body_nodes=None,
    max_iterations=100,
    error_handling='skip',
    empty_result_action='skip',
    data_source=None,
):
    """构造 loop 节点配置（用于校验测试）"""
    if loop_body_nodes is None:
        loop_body_nodes = [
            {
                'id': 'body-1',
                'node_type': 'update_record',
                'name': '更新记录',
                'config': {
                    'action_type': 'update_record',
                    'updates': [{'field_id': 'f1', 'value_template': '{{loop.current_data}}'}],
                },
                'order': 0,
                'next_nodes': [],
            }
        ]
    if data_source is None:
        data_source = {'type': 'trigger_field', 'trigger_field_id': 'f1'}
    return {
        'node_type': 'loop',
        'name': '循环',
        'config': {
            'loop_mode': 'sequential',
            'data_source': data_source,
            'max_iterations': max_iterations,
            'error_handling': error_handling,
            'empty_result_action': empty_result_action,
            'loop_body_nodes': loop_body_nodes,
        },
        'order': 0,
        'next_nodes': [],
    }


class TestValidateLoopNode:
    """测试 _validate_loop_node 静态方法"""

    def test_valid_loop_node_passes_validation(self):
        """合法配置应通过校验"""
        node_data = _make_loop_node_config()
        # 不抛异常即通过
        WorkflowService._validate_loop_node(node_data)

    def test_missing_loop_body_nodes_raises(self):
        """loop_body_nodes 缺失时抛出 ValueError"""
        node_data = _make_loop_node_config(loop_body_nodes=[])
        with pytest.raises(ValueError) as exc:
            WorkflowService._validate_loop_node(node_data)
        assert 'loop_body_nodes' in str(exc.value)

    def test_loop_body_nodes_not_list_raises(self):
        """loop_body_nodes 非 list 时抛出 ValueError"""
        node_data = _make_loop_node_config(loop_body_nodes={'invalid': True})
        node_data['config']['loop_body_nodes'] = {'invalid': True}
        with pytest.raises(ValueError):
            WorkflowService._validate_loop_node(node_data)

    def test_condition_in_loop_body_raises(self):
        """循环体包含 condition 节点时抛出 ValueError"""
        body_with_condition = [
            {
                'id': 'cond-1',
                'node_type': 'condition',
                'name': '条件',
                'config': {},
                'order': 0,
                'next_nodes': [],
            }
        ]
        node_data = _make_loop_node_config(loop_body_nodes=body_with_condition)
        with pytest.raises(ValueError) as exc:
            WorkflowService._validate_loop_node(node_data)
        assert '条件分支' in str(exc.value) or 'condition' in str(exc.value)

    def test_invalid_max_iterations_raises(self):
        """max_iterations 非 1-1000 正整数时抛出 ValueError"""
        for invalid in [0, -1, 1001, 'abc', 1.5, True]:
            node_data = _make_loop_node_config(max_iterations=invalid)
            with pytest.raises(ValueError) as exc:
                WorkflowService._validate_loop_node(node_data)
            assert 'max_iterations' in str(exc.value)

    def test_invalid_error_handling_raises(self):
        """error_handling 非 skip/terminate 时抛出 ValueError"""
        node_data = _make_loop_node_config(error_handling='continue')
        with pytest.raises(ValueError) as exc:
            WorkflowService._validate_loop_node(node_data)
        assert 'error_handling' in str(exc.value)

    def test_invalid_empty_result_action_raises(self):
        """empty_result_action 非 skip/error 时抛出 ValueError"""
        node_data = _make_loop_node_config(empty_result_action='continue')
        with pytest.raises(ValueError) as exc:
            WorkflowService._validate_loop_node(node_data)
        assert 'empty_result_action' in str(exc.value)

    def test_nested_loop_exceeding_depth_3_raises(self):
        """嵌套深度超过 3 层时抛出 ValueError"""
        # 构造 4 层嵌套循环
        innermost = _make_loop_node_config()
        innermost['config']['loop_body_nodes'] = [
            {
                'id': 'leaf',
                'node_type': 'update_record',
                'name': '叶子',
                'config': {},
                'order': 0,
                'next_nodes': [],
            }
        ]
        # 第 3 层
        level3 = _make_loop_node_config(loop_body_nodes=[innermost])
        # 第 2 层
        level2 = _make_loop_node_config(loop_body_nodes=[level3])
        # 第 1 层（顶层）—— 校验时应递归到 depth=4 抛错
        level1 = _make_loop_node_config(loop_body_nodes=[level2])

        with pytest.raises(ValueError) as exc:
            WorkflowService._validate_loop_node(level1)
        assert '嵌套深度' in str(exc.value) or '3 层' in str(exc.value)

    def test_nested_loop_depth_3_passes(self):
        """嵌套深度为 3 层时应通过校验"""
        innermost = _make_loop_node_config()
        level3 = _make_loop_node_config(loop_body_nodes=[innermost])
        level2 = _make_loop_node_config(loop_body_nodes=[level3])
        # 顶层 + level2 + level3 = 3 层，应通过
        WorkflowService._validate_loop_node(level2)


class TestCountLoopNodes:
    """测试 _count_loop_nodes 静态方法"""

    def test_no_loop_nodes(self):
        """无 loop 节点时返回 0"""
        nodes = [
            {'node_type': 'trigger', 'config': {}},
            {'node_type': 'action', 'config': {'action_type': 'create_record'}},
        ]
        assert WorkflowService._count_loop_nodes(nodes) == 0

    def test_single_loop_node(self):
        """单个顶层 loop 节点返回 1"""
        nodes = [_make_loop_node_config()]
        assert WorkflowService._count_loop_nodes(nodes) == 1

    def test_nested_loop_nodes(self):
        """嵌套 loop 节点应递归统计"""
        inner = _make_loop_node_config()
        inner['config']['loop_body_nodes'] = [
            {
                'id': 'inner-loop',
                'node_type': 'loop',
                'name': '内层循环',
                'config': {
                    'loop_body_nodes': [],
                    'max_iterations': 10,
                    'error_handling': 'skip',
                    'empty_result_action': 'skip',
                },
                'order': 0,
                'next_nodes': [],
            }
        ]
        # 外层 1 + 内层 1 = 2
        nodes = [inner]
        assert WorkflowService._count_loop_nodes(nodes) == 2

    def test_non_list_input_returns_zero(self):
        """非 list 输入返回 0"""
        assert WorkflowService._count_loop_nodes(None) == 0
        assert WorkflowService._count_loop_nodes('invalid') == 0

    def test_more_than_5_loops_in_create_workflow_raises(self, ctx, base, table, owner):
        """单个工作流超过 5 个循环节点时 create_workflow 抛出 ValueError"""
        nodes = [_make_loop_node_config() for _ in range(6)]
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
        assert '5 个' in str(exc.value) or '5个' in str(exc.value)


class TestCreateWorkflowWithLoop:
    """测试 create_workflow 保存 loop 节点"""

    def test_create_workflow_persists_loop_node_type(self, ctx, base, table, owner):
        """loop 节点应原样保存为 LOOP 类型（不走 action_type 转换）"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='循环节点保存测试',
            created_by=owner.id,
            nodes_config=[_make_loop_node_config()],
        )

        node = workflow.nodes.first()
        assert node is not None
        assert node.node_type == WorkflowNodeType.LOOP
        # config 中不应被追加 action_type 字段
        assert 'action_type' not in (node.config or {})
        assert 'loop_body_nodes' in node.config
        assert len(node.config['loop_body_nodes']) == 1

    def test_create_workflow_invalid_loop_raises(self, ctx, base, table, owner):
        """create_workflow 中 loop 节点校验失败时抛出 ValueError"""
        invalid_loop = _make_loop_node_config(loop_body_nodes=[])
        with pytest.raises(ValueError):
            WorkflowService.create_workflow(
                base_id=base.id,
                table_id=table.id,
                name='非法循环',
                created_by=owner.id,
                nodes_config=[invalid_loop],
            )

    def test_update_workflow_persists_loop_node_type(self, ctx, base, table, owner):
        """update_workflow 应正确保存 loop 节点类型"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='循环更新测试',
            created_by=owner.id,
        )

        WorkflowService.update_workflow(
            workflow_id=workflow.id,
            user_id=owner.id,
            nodes_config=[_make_loop_node_config()],
        )

        node = WorkflowNode.query.filter_by(workflow_id=workflow.id).first()
        assert node is not None
        assert node.node_type == WorkflowNodeType.LOOP

    def test_update_workflow_invalid_loop_raises(self, ctx, base, table, owner):
        """update_workflow 中 loop 节点校验失败时抛出 ValueError"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='循环更新非法测试',
            created_by=owner.id,
        )

        invalid_loop = _make_loop_node_config(loop_body_nodes=[])
        with pytest.raises(ValueError):
            WorkflowService.update_workflow(
                workflow_id=workflow.id,
                user_id=owner.id,
                nodes_config=[invalid_loop],
            )


class TestResolveLoopDataSource:
    """测试 _resolve_loop_data_source 方法"""

    def _make_instance(self, workflow_id, context=None):
        instance = WorkflowInstance(
            workflow_id=workflow_id,
            version_number=1,
            trigger_type='record_created',
            status=WorkflowInstanceStatus.RUNNING,
            context=context or {},
        )
        db.session.add(instance)
        db.session.commit()
        return instance

    def test_find_records_all_returns_records_array(self, ctx, base, table, owner, engine):
        """find_records_all 数据源返回 records 数组"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='find_records_all 测试',
            created_by=owner.id,
        )
        instance = self._make_instance(
            workflow.id,
            context={
                'records': {
                    'count': 2,
                    'records': [{'id': 'r1'}, {'id': 'r2'}],
                }
            },
        )

        result = engine._resolve_loop_data_source(
            instance, {'type': 'find_records_all'}
        )
        assert result == [{'id': 'r1'}, {'id': 'r2'}]

    def test_find_records_all_with_custom_result_variable(
        self, ctx, base, table, owner, engine
    ):
        """find_records_all 数据源使用 node_id 查找 result_variable"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='find_records_all 自定义变量测试',
            created_by=owner.id,
            nodes_config=[
                {
                    'node_type': 'find_records',
                    'name': '查找记录',
                    'config': {
                        'target_table_id': str(table.id),
                        'result_variable': 'my_records',
                    },
                    'order': 0,
                }
            ],
        )

        find_node = workflow.nodes.first()
        instance = self._make_instance(
            workflow.id,
            context={
                'my_records': {
                    'count': 1,
                    'records': [{'id': 'custom-r1'}],
                }
            },
        )

        result = engine._resolve_loop_data_source(
            instance, {'type': 'find_records_all', 'node_id': str(find_node.id)}
        )
        assert result == [{'id': 'custom-r1'}]

    def test_find_records_all_empty_returns_empty_list(
        self, ctx, base, table, owner, engine
    ):
        """find_records_all 数据源为空时返回空列表"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='find_records_all 空测试',
            created_by=owner.id,
        )
        instance = self._make_instance(workflow.id, context={})

        result = engine._resolve_loop_data_source(
            instance, {'type': 'find_records_all'}
        )
        assert result == []

    def test_find_records_column_flattens_field_values(
        self, ctx, base, table, owner, engine
    ):
        """find_records_column 数据源扁平化字段值"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='find_records_column 测试',
            created_by=owner.id,
        )
        instance = self._make_instance(
            workflow.id,
            context={
                'records': {
                    'count': 3,
                    'records': [
                        {'f_id': 'a'},
                        {'f_id': 'b'},
                        {'f_id': 'c'},
                    ],
                }
            },
        )

        result = engine._resolve_loop_data_source(
            instance, {'type': 'find_records_column', 'field_id': 'f_id'}
        )
        assert result == ['a', 'b', 'c']

    def test_find_records_column_dedupes_person_field(
        self, ctx, base, table, owner, engine
    ):
        """find_records_column 对人员/群组/附件字段（list of dict with id）自动去重"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='find_records_column 去重测试',
            created_by=owner.id,
        )
        instance = self._make_instance(
            workflow.id,
            context={
                'records': {
                    'count': 2,
                    'records': [
                        {'members': [{'id': 'u1', 'name': 'Alice'}, {'id': 'u2', 'name': 'Bob'}]},
                        {'members': [{'id': 'u2', 'name': 'Bob'}, {'id': 'u3', 'name': 'Carol'}]},
                    ],
                }
            },
        )

        result = engine._resolve_loop_data_source(
            instance, {'type': 'find_records_column', 'field_id': 'members'}
        )
        # u2 出现两次但只保留一次
        ids = [item['id'] for item in result]
        assert ids == ['u1', 'u2', 'u3']
        assert len(result) == 3

    def test_trigger_field_returns_list_directly(
        self, ctx, base, table, owner, engine
    ):
        """trigger_field 数据源：字段值为列表时直接返回"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='trigger_field 列表测试',
            created_by=owner.id,
        )
        instance = self._make_instance(
            workflow.id,
            context={
                'trigger_event': {
                    'record': {'tags': ['t1', 't2', 't3']}
                }
            },
        )

        result = engine._resolve_loop_data_source(
            instance, {'type': 'trigger_field', 'trigger_field_id': 'tags'}
        )
        assert result == ['t1', 't2', 't3']

    def test_trigger_field_wraps_scalar_as_single_element_list(
        self, ctx, base, table, owner, engine
    ):
        """trigger_field 数据源：字段值为标量时包装为单元素列表"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='trigger_field 标量测试',
            created_by=owner.id,
        )
        instance = self._make_instance(
            workflow.id,
            context={
                'trigger_event': {
                    'record': {'status': 'active'}
                }
            },
        )

        result = engine._resolve_loop_data_source(
            instance, {'type': 'trigger_field', 'trigger_field_id': 'status'}
        )
        assert result == ['active']

    def test_trigger_field_empty_returns_empty_list(
        self, ctx, base, table, owner, engine
    ):
        """trigger_field 数据源：字段值为 None 时返回空列表"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='trigger_field 空测试',
            created_by=owner.id,
        )
        instance = self._make_instance(
            workflow.id,
            context={'trigger_event': {'record': {}}}
        )

        result = engine._resolve_loop_data_source(
            instance, {'type': 'trigger_field', 'trigger_field_id': 'missing'}
        )
        assert result == []

    def test_webhook_array_returns_json_array(
        self, ctx, base, table, owner, engine
    ):
        """webhook_array 数据源返回 json.array"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='webhook_array 测试',
            created_by=owner.id,
        )
        instance = self._make_instance(
            workflow.id,
            context={
                'wh-node-1_result': {
                    'json': {'array': [{'id': 'w1'}, {'id': 'w2'}]}
                }
            },
        )

        result = engine._resolve_loop_data_source(
            instance, {'type': 'webhook_array', 'node_id': 'wh-node-1'}
        )
        assert result == [{'id': 'w1'}, {'id': 'w2'}]

    def test_webhook_array_missing_returns_empty_list(
        self, ctx, base, table, owner, engine
    ):
        """webhook_array 数据源不存在时返回空列表"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='webhook_array 缺失测试',
            created_by=owner.id,
        )
        instance = self._make_instance(workflow.id, context={})

        result = engine._resolve_loop_data_source(
            instance, {'type': 'webhook_array', 'node_id': 'missing'}
        )
        assert result == []

    def test_unknown_type_returns_empty_list(
        self, ctx, base, table, owner, engine
    ):
        """未知数据源类型返回空列表"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='未知数据源测试',
            created_by=owner.id,
        )
        instance = self._make_instance(workflow.id, context={})

        result = engine._resolve_loop_data_source(
            instance, {'type': 'unknown_type'}
        )
        assert result == []


class TestExecuteLoopNode:
    """测试 _execute_loop_node 方法"""

    def _make_instance(self, workflow_id, context=None, trigger_record_id=None):
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

    def test_loop_node_empty_result_skip_returns_next_nodes(
        self, ctx, base, table, owner, engine
    ):
        """空数据源且 empty_result_action=skip 时返回 next_nodes（跳过循环）"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='空结果跳过测试',
            created_by=owner.id,
            nodes_config=[
                {
                    'node_type': 'loop',
                    'name': '循环',
                    'config': {
                        'data_source': {'type': 'trigger_field', 'trigger_field_id': 'missing'},
                        'max_iterations': 10,
                        'error_handling': 'skip',
                        'empty_result_action': 'skip',
                        'loop_body_nodes': [
                            {
                                'id': 'body-1',
                                'node_type': 'update_record',
                                'name': '更新',
                                'config': {},
                                'order': 0,
                                'next_nodes': [],
                            }
                        ],
                    },
                    'order': 0,
                    'next_nodes': ['next-node-id'],
                }
            ],
        )

        loop_node = workflow.nodes.first()
        instance = self._make_instance(
            workflow.id,
            context={'trigger_event': {'record': {}}}
        )

        result = engine._execute_loop_node(instance, loop_node)
        assert result == {'next_nodes': ['next-node-id']}

    def test_loop_node_empty_result_error_raises(
        self, ctx, base, table, owner, engine
    ):
        """空数据源且 empty_result_action=error 时抛出 ValueError"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='空结果报错测试',
            created_by=owner.id,
            nodes_config=[
                {
                    'node_type': 'loop',
                    'name': '循环',
                    'config': {
                        'data_source': {'type': 'trigger_field', 'trigger_field_id': 'missing'},
                        'max_iterations': 10,
                        'error_handling': 'skip',
                        'empty_result_action': 'error',
                        'loop_body_nodes': [
                            {
                                'id': 'body-1',
                                'node_type': 'update_record',
                                'name': '更新',
                                'config': {},
                                'order': 0,
                                'next_nodes': [],
                            }
                        ],
                    },
                    'order': 0,
                    'next_nodes': [],
                }
            ],
        )

        loop_node = workflow.nodes.first()
        instance = self._make_instance(
            workflow.id,
            context={'trigger_event': {'record': {}}}
        )

        with pytest.raises(ValueError) as exc:
            engine._execute_loop_node(instance, loop_node)
        assert '空' in str(exc.value)

    def test_loop_node_executes_iterations_and_writes_log(
        self, ctx, base, table, owner, field, record, engine
    ):
        """loop 节点应执行所有迭代并写入执行日志"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='循环执行测试',
            created_by=owner.id,
            nodes_config=[
                {
                    'node_type': 'loop',
                    'name': '循环',
                    'config': {
                        'data_source': {'type': 'trigger_field', 'trigger_field_id': str(field.id)},
                        'max_iterations': 10,
                        'error_handling': 'skip',
                        'empty_result_action': 'skip',
                        'loop_body_nodes': [
                            {
                                'id': 'body-trigger',
                                'node_type': 'trigger',
                                'name': '触发',
                                'config': {},
                                'order': 0,
                                'next_nodes': [],
                            }
                        ],
                    },
                    'order': 0,
                    'next_nodes': [],
                }
            ],
        )

        loop_node = workflow.nodes.first()
        instance = self._make_instance(
            workflow.id,
            context={
                'trigger_event': {
                    'record': {str(field.id): ['item-1', 'item-2', 'item-3']}
                }
            },
        )

        result = engine._execute_loop_node(instance, loop_node)
        assert result == {'next_nodes': []}

        # 验证 loop 节点执行日志
        loop_logs = WorkflowExecutionLog.query.filter_by(
            instance_id=instance.id, node_type='loop'
        ).all()
        assert len(loop_logs) == 1
        loop_log = loop_logs[0]
        assert loop_log.status == 'success'
        assert loop_log.output_result['total_iterations'] == 3
        assert loop_log.output_result['success_count'] == 3
        assert loop_log.output_result['failure_count'] == 0
        assert loop_log.output_result['early_terminated'] is False

        # 验证循环体子节点执行日志（每轮迭代一条 trigger 子节点日志）
        body_logs = WorkflowExecutionLog.query.filter_by(
            instance_id=instance.id, node_type='trigger'
        ).all()
        # execute_node 在 _execute_loop_body_chain 中调用，每轮一条
        assert len(body_logs) == 3
        # 每条日志的 input_context 应包含 iteration_index
        for idx, blog in enumerate(body_logs):
            assert blog.input_context.get('iteration_index') == idx
            assert blog.input_context.get('loop_context') is not None

    def test_loop_node_max_iterations_caps_total(
        self, ctx, base, table, owner, field, engine
    ):
        """max_iterations 应限制实际迭代次数"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='循环上限测试',
            created_by=owner.id,
            nodes_config=[
                {
                    'node_type': 'loop',
                    'name': '循环',
                    'config': {
                        'data_source': {'type': 'trigger_field', 'trigger_field_id': str(field.id)},
                        'max_iterations': 2,
                        'error_handling': 'skip',
                        'empty_result_action': 'skip',
                        'loop_body_nodes': [
                            {
                                'id': 'body-trigger',
                                'node_type': 'trigger',
                                'name': '触发',
                                'config': {},
                                'order': 0,
                                'next_nodes': [],
                            }
                        ],
                    },
                    'order': 0,
                    'next_nodes': [],
                }
            ],
        )

        loop_node = workflow.nodes.first()
        instance = self._make_instance(
            workflow.id,
            context={
                'trigger_event': {
                    'record': {str(field.id): ['a', 'b', 'c', 'd', 'e']}
                }
            },
        )

        result = engine._execute_loop_node(instance, loop_node)
        assert result == {'next_nodes': []}

        loop_log = WorkflowExecutionLog.query.filter_by(
            instance_id=instance.id, node_type='loop'
        ).first()
        # max_iterations=2 限制了迭代次数
        assert loop_log.output_result['total_iterations'] == 2
        assert loop_log.input_context['total'] == 2
        assert loop_log.input_context['array_length'] == 5

    def test_loop_node_error_handling_skip_continues(
        self, ctx, base, table, owner, field, engine
    ):
        """error_handling=skip 时单轮失败不影响其他迭代"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='循环 skip 模式测试',
            created_by=owner.id,
            nodes_config=[
                {
                    'node_type': 'loop',
                    'name': '循环',
                    'config': {
                        'data_source': {'type': 'trigger_field', 'trigger_field_id': str(field.id)},
                        'max_iterations': 10,
                        'error_handling': 'skip',
                        'empty_result_action': 'skip',
                        'loop_body_nodes': [
                            {
                                'id': 'body-trigger',
                                'node_type': 'trigger',
                                'name': '触发',
                                'config': {},
                                'order': 0,
                                'next_nodes': [],
                            }
                        ],
                    },
                    'order': 0,
                    'next_nodes': [],
                }
            ],
        )

        loop_node = workflow.nodes.first()
        instance = self._make_instance(
            workflow.id,
            context={
                'trigger_event': {
                    'record': {str(field.id): ['ok-1', 'fail', 'ok-2']}
                }
            },
        )

        # 模拟第二轮失败
        original_execute = engine.execute_node
        call_count = {'n': 0}

        def mock_execute_node(inst, node):
            call_count['n'] += 1
            if call_count['n'] == 2:
                raise ValueError('模拟失败')
            return original_execute(inst, node)

        with patch.object(engine, 'execute_node', side_effect=mock_execute_node):
            result = engine._execute_loop_node(instance, loop_node)

        assert result == {'next_nodes': []}
        loop_log = WorkflowExecutionLog.query.filter_by(
            instance_id=instance.id, node_type='loop'
        ).first()
        # 第二轮失败被跳过，循环继续执行第三轮
        assert loop_log.output_result['success_count'] == 2
        assert loop_log.output_result['failure_count'] == 1
        assert loop_log.output_result['early_terminated'] is False
        assert loop_log.status == 'success'

    def test_loop_node_error_handling_terminate_raises(
        self, ctx, base, table, owner, field, engine
    ):
        """error_handling=terminate 时单轮失败终止循环并抛出异常"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='循环 terminate 模式测试',
            created_by=owner.id,
            nodes_config=[
                {
                    'node_type': 'loop',
                    'name': '循环',
                    'config': {
                        'data_source': {'type': 'trigger_field', 'trigger_field_id': str(field.id)},
                        'max_iterations': 10,
                        'error_handling': 'terminate',
                        'empty_result_action': 'skip',
                        'loop_body_nodes': [
                            {
                                'id': 'body-trigger',
                                'node_type': 'trigger',
                                'name': '触发',
                                'config': {},
                                'order': 0,
                                'next_nodes': [],
                            }
                        ],
                    },
                    'order': 0,
                    'next_nodes': [],
                }
            ],
        )

        loop_node = workflow.nodes.first()
        instance = self._make_instance(
            workflow.id,
            context={
                'trigger_event': {
                    'record': {str(field.id): ['ok-1', 'fail', 'ok-2']}
                }
            },
        )

        original_execute = engine.execute_node
        call_count = {'n': 0}

        def mock_execute_node(inst, node):
            call_count['n'] += 1
            if call_count['n'] == 2:
                raise ValueError('模拟失败')
            return original_execute(inst, node)

        with patch.object(engine, 'execute_node', side_effect=mock_execute_node):
            with pytest.raises(ValueError) as exc:
                engine._execute_loop_node(instance, loop_node)
            assert '模拟失败' in str(exc.value)

        # 异常抛出前，日志应被更新（finally 块）
        loop_log = WorkflowExecutionLog.query.filter_by(
            instance_id=instance.id, node_type='loop'
        ).first()
        assert loop_log.status == 'error'
        assert loop_log.output_result['early_terminated'] is True
        assert loop_log.output_result['success_count'] == 1
        assert loop_log.output_result['failure_count'] == 1
        assert '模拟失败' in (loop_log.error_message or '')


class TestLoopBodyNodeWrapper:
    """测试 _LoopBodyNodeWrapper 包装类"""

    def test_wrapper_exposes_attributes(self):
        """包装类应正确暴露 id/node_type/config/next_nodes/order/name 属性"""
        node_dict = {
            'id': 'wrapper-1',
            'node_type': 'update_record',
            'name': '更新记录',
            'config': {'action_type': 'update_record', 'updates': []},
            'order': 5,
            'next_nodes': ['next-1', 'next-2'],
        }
        wrapper = _LoopBodyNodeWrapper(node_dict)
        # id 强制为 None（避免 FK 冲突）
        assert wrapper.id is None
        assert wrapper.node_type == 'update_record'
        assert wrapper.name == '更新记录'
        assert wrapper.config == {'action_type': 'update_record', 'updates': []}
        assert wrapper.order == 5
        assert wrapper.next_nodes == ['next-1', 'next-2']

    def test_wrapper_handles_empty_dict(self):
        """包装类应优雅处理空 dict"""
        wrapper = _LoopBodyNodeWrapper({})
        assert wrapper.id is None
        assert wrapper.node_type == 'action'
        assert wrapper.name == ''
        assert wrapper.config == {}
        assert wrapper.next_nodes == []
        assert wrapper.order == 0

    def test_wrapper_handles_none(self):
        """包装类应优雅处理 None"""
        wrapper = _LoopBodyNodeWrapper(None)
        assert wrapper.id is None
        assert wrapper.node_type == 'action'


class TestBuildRenderContextWithLoop:
    """测试 _build_render_context 注入 loop 变量"""

    def test_render_context_loop_is_none_outside_loop(
        self, ctx, base, table, owner, engine
    ):
        """循环体外 loop_context 为 None"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='渲染上下文测试',
            created_by=owner.id,
        )
        instance = WorkflowInstance(
            workflow_id=workflow.id,
            version_number=1,
            trigger_type='record_created',
            status=WorkflowInstanceStatus.RUNNING,
            context={},
        )
        db.session.add(instance)
        db.session.commit()

        render_context = engine._build_render_context(instance)
        assert render_context['loop'] is None

    def test_render_context_loop_includes_loop_context(
        self, ctx, base, table, owner, engine
    ):
        """循环体内 loop_context 应注入到 loop 变量"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='渲染上下文循环内测试',
            created_by=owner.id,
        )
        loop_ctx = {
            'current_data': 'item-1',
            'index': 0,
            'round': 1,
            'total': 3,
        }
        instance = WorkflowInstance(
            workflow_id=workflow.id,
            version_number=1,
            trigger_type='record_created',
            status=WorkflowInstanceStatus.RUNNING,
            context={'loop_context': loop_ctx},
        )
        db.session.add(instance)
        db.session.commit()

        render_context = engine._build_render_context(instance)
        assert render_context['loop'] == loop_ctx
        assert render_context['loop']['current_data'] == 'item-1'
        assert render_context['loop']['round'] == 1
