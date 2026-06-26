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
                    'operator': 'and',
                    'conditions': [
                        {
                            'field_id': str(field.id),
                            'operator': 'eq',
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
                    'operator': 'and',
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
