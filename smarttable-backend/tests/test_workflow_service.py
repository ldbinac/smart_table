"""
WorkflowService 单元测试
测试工作流 CRUD、状态管理与触发匹配能力。
"""
import uuid
from datetime import datetime, timezone

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
    BaseMember,
    MemberRole,
)
from app.models.field import FieldType
from app.models.workflow import WorkflowNode, WorkflowTrigger, WorkflowVersion
from app.services.workflow_service import WorkflowService


@pytest.fixture(scope='function')
def workflow_app():
    """为每个工作流测试创建独立应用实例"""
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
def ctx(workflow_app):
    """每次测试提供应用上下文"""
    with workflow_app.app_context():
        yield


@pytest.fixture(scope='function')
def owner(ctx):
    """创建所有者用户"""
    user = User(email='owner@example.com', name='所有者')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user


@pytest.fixture(scope='function')
def base(ctx, owner):
    """创建测试 Base"""
    b = Base(
        name='测试 Base',
        description='测试',
        owner_id=owner.id
    )
    db.session.add(b)
    db.session.commit()
    db.session.refresh(b)
    return b


@pytest.fixture(scope='function')
def table(ctx, base):
    """创建测试表格"""
    t = Table(base_id=base.id, name='测试表格', order=0)
    db.session.add(t)
    db.session.commit()
    db.session.refresh(t)
    return t


@pytest.fixture(scope='function')
def field(ctx, table):
    """创建测试字段"""
    from app.models.field import FieldType
    f = Field(
        table_id=table.id,
        name='状态',
        type=FieldType.SINGLE_LINE_TEXT.value,
        order=0
    )
    db.session.add(f)
    db.session.commit()
    db.session.refresh(f)
    return f


@pytest.fixture(scope='function')
def record(ctx, table, field, owner):
    """创建测试记录"""
    r = Record(
        table_id=table.id,
        values={str(field.id): '待审批'},
        created_by=owner.id,
        updated_by=owner.id
    )
    db.session.add(r)
    db.session.commit()
    db.session.refresh(r)
    return r


class TestWorkflowCRUD:
    """测试工作流 CRUD"""

    def test_create_workflow(self, ctx, base, table, owner):
        """测试创建工作流"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='测试工作流',
            description='用于测试',
            created_by=owner.id,
            trigger_config={
                'trigger_type': 'record_created',
                'filter_config': {},
                'field_ids': []
            },
            nodes_config=[
                {
                    'node_type': 'trigger',
                    'name': '记录创建',
                    'config': {},
                    'order': 0,
                    'next_nodes': []
                }
            ]
        )

        assert workflow is not None
        assert workflow.name == '测试工作流'
        assert workflow.status == WorkflowStatus.DRAFT
        assert workflow.base_id == base.id
        assert workflow.table_id == table.id

    def test_get_workflow(self, ctx, base, table, owner):
        """测试获取工作流详情"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='获取测试',
            created_by=owner.id
        )

        result = WorkflowService.get_workflow(workflow.id)
        assert result is not None
        assert result['workflow']['id'] == str(workflow.id)
        assert result['workflow']['name'] == '获取测试'

    def test_update_workflow_only_draft(self, ctx, base, table, owner):
        """测试仅草稿状态可编辑"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='原名称',
            created_by=owner.id
        )

        updated = WorkflowService.update_workflow(
            workflow_id=workflow.id,
            user_id=owner.id,
            name='新名称'
        )
        assert updated is not None
        assert updated.name == '新名称'

        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)
        updated_after_publish = WorkflowService.update_workflow(
            workflow_id=workflow.id,
            user_id=owner.id,
            name='再改名'
        )
        assert updated_after_publish is None

    def test_delete_workflow_soft_delete(self, ctx, base, table, owner):
        """测试软删除工作流并取消运行中实例"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='待删除',
            created_by=owner.id
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

        success = WorkflowService.delete_workflow(workflow.id, user_id=owner.id)
        assert success is True

        deleted = Workflow.query.get(workflow.id)
        assert deleted.is_deleted is True

        db.session.refresh(instance)
        assert instance.status == WorkflowInstanceStatus.CANCELLED

    def test_list_workflows_filter(self, ctx, base, table, owner):
        """测试工作流列表过滤"""
        WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='草稿工作流',
            created_by=owner.id
        )
        active_wf = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='活动工作流',
            created_by=owner.id
        )
        WorkflowService.publish_workflow(active_wf.id, created_by=owner.id)

        all_list = WorkflowService.list_workflows(base_id=base.id, user_id=owner.id)
        assert len(all_list) == 2

        active_list = WorkflowService.list_workflows(
            base_id=base.id,
            status='active',
            user_id=owner.id
        )
        assert len(active_list) == 1
        assert active_list[0].status == WorkflowStatus.ACTIVE


class TestWorkflowStatus:
    """测试工作流状态管理"""

    def test_publish_workflow(self, ctx, base, table, owner):
        """测试发布工作流生成版本快照"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='发布测试',
            created_by=owner.id,
            nodes_config=[
                {'node_type': 'trigger', 'name': '触发', 'order': 0}
            ]
        )

        published = WorkflowService.publish_workflow(workflow.id, created_by=owner.id)
        assert published is not None
        assert published.status == WorkflowStatus.ACTIVE
        assert published.current_version == 1

        result = WorkflowService.get_workflow(workflow.id)
        assert result['current_version'] is not None
        assert result['current_version']['version_number'] == 1

    def test_pause_and_resume_workflow(self, ctx, base, table, owner):
        """测试暂停与恢复工作流"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='状态测试',
            created_by=owner.id
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        paused = WorkflowService.pause_workflow(workflow.id, user_id=owner.id)
        assert paused.status == WorkflowStatus.PAUSED

        resumed = WorkflowService.resume_workflow(workflow.id, user_id=owner.id)
        assert resumed.status == WorkflowStatus.ACTIVE


class TestMatchTriggers:
    """测试触发器匹配逻辑"""

    def test_match_record_created_without_filter(self, ctx, base, table, owner, record):
        """测试无条件记录创建触发"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='无条件触发',
            created_by=owner.id,
            trigger_config={
                'trigger_type': 'record_created',
                'filter_config': {}
            }
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        matched = WorkflowService.match_triggers(
            table_id=table.id,
            event_type='record_created',
            record=record
        )
        assert len(matched) == 1
        assert matched[0].id == workflow.id

    def test_match_with_eq_filter(self, ctx, base, table, owner, field):
        """测试等于过滤条件"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='条件触发',
            created_by=owner.id,
            trigger_config={
                'trigger_type': 'record_created',
                'filter_config': {
                    'conjunction': 'and',
                    'conditions': [
                        {
                            'field_id': str(field.id),
                            'operator': 'equals',
                            'value': '待审批'
                        }
                    ]
                }
            }
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        record_match = Record(
            table_id=table.id,
            values={str(field.id): '待审批'},
            created_by=owner.id
        )
        record_no_match = Record(
            table_id=table.id,
            values={str(field.id): '已完成'},
            created_by=owner.id
        )
        db.session.add_all([record_match, record_no_match])
        db.session.commit()

        matched = WorkflowService.match_triggers(
            table_id=table.id,
            event_type='record_created',
            record=record_match
        )
        assert len(matched) == 1

        not_matched = WorkflowService.match_triggers(
            table_id=table.id,
            event_type='record_created',
            record=record_no_match
        )
        assert len(not_matched) == 0

    def test_match_with_contains_filter(self, ctx, base, table, owner, field):
        """测试包含过滤条件"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='包含触发',
            created_by=owner.id,
            trigger_config={
                'trigger_type': 'record_created',
                'filter_config': {
                    'conjunction': 'and',
                    'conditions': [
                        {
                            'field_id': str(field.id),
                            'operator': 'contains',
                            'value': '审批'
                        }
                    ]
                }
            }
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        record = Record(
            table_id=table.id,
            values={str(field.id): '待审批事项'},
            created_by=owner.id
        )
        db.session.add(record)
        db.session.commit()

        matched = WorkflowService.match_triggers(
            table_id=table.id,
            event_type='record_created',
            record=record
        )
        assert len(matched) == 1

    def test_match_draft_workflow_not_triggered(self, ctx, base, table, owner, record):
        """测试草稿状态工作流不会被触发"""
        WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='草稿不触发',
            created_by=owner.id,
            trigger_config={
                'trigger_type': 'record_created',
                'filter_config': {}
            }
        )

        matched = WorkflowService.match_triggers(
            table_id=table.id,
            event_type='record_created',
            record=record
        )
        assert len(matched) == 0

    def test_match_unknown_event_type(self, ctx, base, table, record):
        """测试未知事件类型返回空列表"""
        matched = WorkflowService.match_triggers(
            table_id=table.id,
            event_type='unknown_event',
            record=record
        )
        assert matched == []

    def test_match_record_updated_with_field_ids_and_is_not_empty(self, ctx, base, table, owner, field):
        """测试 record_updated 监听指定字段且字段不为空时触发"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='record_updated 标题字段触发',
            created_by=owner.id,
            trigger_config={
                'trigger_type': 'record_updated',
                'field_ids': [str(field.id)],
                'filter_config': {
                    'conjunction': 'and',
                    'conditions': [
                        {
                            'field_id': str(field.id),
                            'operator': 'isNotEmpty'
                        }
                    ]
                }
            }
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        # 标题字段已更新为不为空（模拟 RecordService 更新后的记录状态）
        record = Record(
            table_id=table.id,
            values={str(field.id): '新标题'},
            created_by=owner.id
        )
        db.session.add(record)
        db.session.commit()

        matched = WorkflowService.match_triggers(
            table_id=table.id,
            event_type='record_updated',
            record=record,
            changes={
                str(field.id): {'old_value': '', 'new_value': '新标题'}
            }
        )
        assert len(matched) == 1
        assert matched[0].id == workflow.id

    def test_match_record_updated_ignores_unlistened_fields(self, ctx, base, table, owner, field):
        """测试 record_updated 未更新监听字段时不触发"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='record_updated 未监听字段不触发',
            created_by=owner.id,
            trigger_config={
                'trigger_type': 'record_updated',
                'field_ids': [str(field.id)],
                'filter_config': {}
            }
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        other_field = Field(
            table_id=table.id,
            name='其他字段',
            type=FieldType.SINGLE_LINE_TEXT.value,
            order=1
        )
        db.session.add(other_field)
        db.session.commit()

        record = Record(
            table_id=table.id,
            values={str(field.id): '标题', str(other_field.id): '旧值'},
            created_by=owner.id
        )
        db.session.add(record)
        db.session.commit()

        matched = WorkflowService.match_triggers(
            table_id=table.id,
            event_type='record_updated',
            record=record,
            changes={
                str(other_field.id): {'old_value': '旧值', 'new_value': '新值'}
            }
        )
        assert len(matched) == 0

    def test_update_workflow_preserves_frontend_operator(self, ctx, base, table, owner, field):
        """测试 update_workflow 保存触发器时保留前端操作符（不做转换）"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='操作符保留测试',
            created_by=owner.id,
            trigger_config={
                'trigger_type': 'record_updated',
                'field_ids': [str(field.id)],
                'filter_config': {
                    'conjunction': 'and',
                    'conditions': [
                        {'field_id': str(field.id), 'operator': 'isNotEmpty'}
                    ]
                }
            }
        )

        WorkflowService.update_workflow(
            workflow_id=workflow.id,
            user_id=owner.id,
            trigger_config={
                'trigger_type': 'record_updated',
                'field_ids': [str(field.id)],
                'filter_config': {
                    'conjunction': 'and',
                    'conditions': [
                        {'field_id': str(field.id), 'operator': 'isNotEmpty'}
                    ]
                }
            }
        )

        trigger = workflow.triggers.first()
        assert trigger is not None
        # 验证 conjunction 字段被保留
        assert trigger.filter_config['conjunction'] == 'and'
        # 验证前端操作符原样入库，不做任何转换
        assert trigger.filter_config['conditions'][0]['operator'] == 'isNotEmpty'


class TestWorkflowPermission:
    """测试工作流权限控制"""

    def test_viewer_cannot_create_workflow(self, ctx, base, table, owner):
        """测试 VIEWER 无法创建工作流"""
        viewer = User(email='viewer_perm@example.com', name='浏览者权限')
        viewer.set_password('Test1234!')
        db.session.add(viewer)
        db.session.commit()

        member = BaseMember(base_id=base.id, user_id=viewer.id, role=MemberRole.VIEWER)
        db.session.add(member)
        db.session.commit()

        with pytest.raises(Exception):
            WorkflowService.create_workflow(
                base_id=base.id,
                table_id=table.id,
                name='viewer 创建',
                created_by=viewer.id
            )


class TestWorkflowVersion:
    """测试 WorkflowVersion 模型"""

    def test_to_dict_includes_creator_name(self, ctx, owner, base, table):
        """测试 WorkflowVersion.to_dict 包含创建者名称"""
        workflow = Workflow(
            id=uuid.uuid4(),
            base_id=base.id,
            table_id=table.id,
            name='测试工作流',
            status=WorkflowStatus.ACTIVE,
            current_version=1,
            created_by=owner.id
        )
        version = WorkflowVersion(
            id=uuid.uuid4(),
            workflow_id=workflow.id,
            version_number=1,
            config_snapshot={'nodes': [], 'triggers': []},
            created_by=owner.id,
            created_at=datetime.now(timezone.utc)
        )
        version.creator = owner

        data = version.to_dict()

        assert data['created_by'] == str(owner.id)
        assert data['created_by_name'] == owner.name

    def test_to_dict_without_creator(self, ctx):
        """测试 WorkflowVersion.to_dict 在无创建者时返回 None"""
        version = WorkflowVersion(
            id=uuid.uuid4(),
            workflow_id=uuid.uuid4(),
            version_number=1,
            config_snapshot={'nodes': [], 'triggers': []},
            created_by=None,
            created_at=datetime.now(timezone.utc)
        )

        data = version.to_dict()

        assert data['created_by'] is None
        assert data['created_by_name'] is None


class TestEvalOperator:
    """测试操作符评估"""

    def test_is_not_empty_with_value(self):
        """测试 is_not_empty：有值时返回 True"""
        assert WorkflowService._eval_operator('hello', 'isNotEmpty', None) is True

    def test_is_not_empty_with_empty_string(self):
        """测试 is_not_empty：空字符串返回 False"""
        assert WorkflowService._eval_operator('', 'isNotEmpty', None) is False

    def test_is_not_empty_with_none(self):
        """测试 is_not_empty：None 返回 False"""
        assert WorkflowService._eval_operator(None, 'isNotEmpty', None) is False

    def test_is_empty_with_none(self):
        """测试 is_empty：None 返回 True"""
        assert WorkflowService._eval_operator(None, 'isEmpty', None) is True

    def test_is_empty_with_empty_string(self):
        """测试 is_empty：空字符串返回 True"""
        assert WorkflowService._eval_operator('', 'isEmpty', None) is True

    def test_is_empty_with_value(self):
        """测试 is_empty：有值返回 False"""
        assert WorkflowService._eval_operator('hello', 'isEmpty', None) is False

    def test_not_equals_operator(self):
        """测试 notEquals 不等于操作符"""
        assert WorkflowService._eval_operator('a', 'notEquals', 'b') is True
        assert WorkflowService._eval_operator('a', 'notEquals', 'a') is False

    def test_gte_lte_operators(self):
        """测试 greaterThanOrEqual/lessThanOrEqual 操作符"""
        assert WorkflowService._eval_operator(5, 'greaterThanOrEqual', 5) is True
        assert WorkflowService._eval_operator(5, 'greaterThanOrEqual', 6) is False
        assert WorkflowService._eval_operator(5, 'lessThanOrEqual', 5) is True
        assert WorkflowService._eval_operator(5, 'lessThanOrEqual', 4) is False

    def test_startswith_endswith(self):
        """测试 startsWith/endsWith 操作符"""
        assert WorkflowService._eval_operator('hello world', 'startsWith', 'hello') is True
        assert WorkflowService._eval_operator('hello world', 'endsWith', 'world') is True
        assert WorkflowService._eval_operator('hello world', 'startsWith', 'world') is False

    def test_isAnyOf_isNoneOf_operators(self):
        """测试 isAnyOf/isNoneOf 操作符"""
        assert WorkflowService._eval_operator('a', 'isAnyOf', ['a', 'b']) is True
        assert WorkflowService._eval_operator('c', 'isAnyOf', ['a', 'b']) is False
        assert WorkflowService._eval_operator('c', 'isNoneOf', ['a', 'b']) is True

    def test_match_triggers_with_is_not_empty_filter(self, ctx, base, table, owner, field):
        """测试 is_not_empty 触发条件实际匹配"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='is_not_empty 触发',
            created_by=owner.id,
            trigger_config={
                'trigger_type': 'record_created',
                'filter_config': {
                    'conjunction': 'and',
                    'conditions': [
                        {
                            'field_id': str(field.id),
                            'operator': 'isNotEmpty'
                        }
                    ]
                }
            }
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        record_with_value = Record(
            table_id=table.id,
            values={str(field.id): '有值'},
            created_by=owner.id
        )
        record_empty = Record(
            table_id=table.id,
            values={str(field.id): ''},
            created_by=owner.id
        )
        db.session.add_all([record_with_value, record_empty])
        db.session.commit()

        # 有值时应触发
        matched = WorkflowService.match_triggers(
            table_id=table.id,
            event_type='record_created',
            record=record_with_value
        )
        assert len(matched) == 1
        assert matched[0].id == workflow.id

        # 空值时不应触发
        not_matched = WorkflowService.match_triggers(
            table_id=table.id,
            event_type='record_created',
            record=record_empty
        )
        assert len(not_matched) == 0

    def test_match_triggers_with_frontend_isNotEmpty_operator(self, ctx, base, table, owner, field):
        """测试前端操作符 isNotEmpty 能正确匹配"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='isNotEmpty 前端操作符测试',
            created_by=owner.id,
            trigger_config={
                'trigger_type': 'record_created',
                'filter_config': {
                    'conjunction': 'and',
                    'conditions': [
                        {
                            'field_id': str(field.id),
                            'operator': 'isNotEmpty'
                        }
                    ]
                }
            }
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)

        record_with_value = Record(
            table_id=table.id,
            values={str(field.id): '有值'},
            created_by=owner.id
        )
        record_empty = Record(
            table_id=table.id,
            values={str(field.id): ''},
            created_by=owner.id
        )
        db.session.add_all([record_with_value, record_empty])
        db.session.commit()

        # 有值时应触发
        matched = WorkflowService.match_triggers(
            table_id=table.id,
            event_type='record_created',
            record=record_with_value
        )
        assert len(matched) == 1
        assert matched[0].id == workflow.id

        # 空值时不应触发
        not_matched = WorkflowService.match_triggers(
            table_id=table.id,
            event_type='record_created',
            record=record_empty
        )
        assert len(not_matched) == 0


    def test_evaluate_filter_condition_with_frontend_operator(self):
        """测试 _evaluate_filter_condition 接收前端操作符"""
        condition = {'field_id': 'f1', 'operator': 'isNotEmpty'}
        record_values = {'f1': '有值'}
        assert WorkflowService._evaluate_filter_condition(condition, record_values, None) is True

        condition_empty = {'field_id': 'f1', 'operator': 'isEmpty'}
        assert WorkflowService._evaluate_filter_condition(condition_empty, {'f1': ''}, None) is True

        condition_eq = {'field_id': 'f1', 'operator': 'equals', 'value': 'hello'}
        assert WorkflowService._evaluate_filter_condition(condition_eq, {'f1': 'hello'}, None) is True


class TestCleanFilterConfig:
    """测试空条件清理"""

    def test_clean_empty_conditions(self):
        """测试空 conditions 数组被清理为空 dict"""
        result = WorkflowService._clean_filter_config({'conjunction': 'and', 'conditions': []})
        assert result == {}

    def test_clean_non_empty_conditions(self):
        """测试非空 conditions 不被清理"""
        config = {'conjunction': 'and', 'conditions': [{'field_id': 'f1', 'operator': 'equals', 'value': 'v1'}]}
        result = WorkflowService._clean_filter_config(config)
        assert result == config

    def test_clean_empty_dict(self):
        """测试空 dict 保持不变"""
        result = WorkflowService._clean_filter_config({})
        assert result == {}

    def test_clean_none(self):
        """测试 None 返回空 dict"""
        result = WorkflowService._clean_filter_config(None)
        assert result == {}

    def test_create_workflow_cleans_empty_conditions(self, ctx, base, table, owner):
        """测试创建工作流时清理空条件"""
        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='空条件测试',
            created_by=owner.id,
            trigger_config={
                'trigger_type': 'record_created',
                'filter_config': {'conjunction': 'and', 'conditions': []}
            }
        )
        trigger = workflow.triggers.first()
        assert trigger is not None
        assert trigger.filter_config == {}
