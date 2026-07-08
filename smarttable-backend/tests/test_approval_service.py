"""
ApprovalService 单元测试
测试审批任务创建、或签、会签、串行、转交、驳回与超时处理。
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

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
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowTask,
    WorkflowTaskStatus,
    WorkflowExecutionLog,
)
from app.models.workflow import WorkflowNode
from app.services.approval_service import ApprovalService
from app.services.workflow_service import WorkflowService


@pytest.fixture(scope='function')
def approval_app():
    """为每个审批服务测试创建独立应用实例"""
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def ctx(approval_app):
    with approval_app.app_context():
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
def approver_a(ctx):
    user = User(email='approver_a@example.com', name='审批人A')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user


@pytest.fixture(scope='function')
def approver_b(ctx):
    user = User(email='approver_b@example.com', name='审批人B')
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
    f = Field(table_id=table.id, name='标题', type=FieldType.SINGLE_LINE_TEXT.value, order=0)
    db.session.add(f)
    db.session.commit()
    db.session.refresh(f)
    return f


@pytest.fixture(scope='function')
def record(ctx, table, field, owner):
    r = Record(table_id=table.id, values={str(field.id): '测试记录'}, created_by=owner.id)
    db.session.add(r)
    db.session.commit()
    db.session.refresh(r)
    return r


def _create_workflow(ctx, base, table, owner, nodes_config):
    """辅助函数：创建并发布带审批节点的工作流"""
    workflow = WorkflowService.create_workflow(
        base_id=base.id,
        table_id=table.id,
        name='审批测试工作流',
        created_by=owner.id,
        nodes_config=nodes_config
    )
    WorkflowService.publish_workflow(workflow.id, created_by=owner.id)
    return workflow


def _create_instance(workflow, record, trigger_type='record_created'):
    """辅助函数：创建工作流实例"""
    instance = WorkflowInstance(
        workflow_id=workflow.id,
        version_number=1,
        trigger_type=trigger_type,
        status=WorkflowInstanceStatus.RUNNING,
        trigger_record_id=record.id,
        context={
            'trigger_event': {
                'actor_id': str(record.created_by)
            }
        }
    )
    db.session.add(instance)
    db.session.commit()
    db.session.refresh(instance)
    return instance


@pytest.fixture(autouse=True)
def disable_notifications():
    """禁用审批通知，避免测试发送邮件"""
    with patch.object(ApprovalService, '_send_notification'):
        with patch.object(ApprovalService, '_emit_if_enabled'):
            yield


class TestCreateTasks:
    """测试审批任务创建"""

    def test_create_tasks_any_mode(self, ctx, base, table, owner, approver_a, approver_b, record):
        """测试或签模式为每个审批人创建任务"""
        workflow = _create_workflow(ctx, base, table, owner, [
            {
                'node_type': 'approval',
                'name': '或签审批',
                'config': {
                    'mode': 'any',
                    'approvers': {
                        'source': 'fixed_users',
                        'user_ids': [str(approver_a.id), str(approver_b.id)]
                    }
                },
                'order': 0
            }
        ])

        instance = _create_instance(workflow, record)
        approval_node = workflow.nodes.first()

        result = ApprovalService.create_tasks(instance, approval_node)
        assert result['success'] is True
        assert result['mode'] == 'any'
        assert len(result['tasks']) == 2

        tasks = WorkflowTask.query.filter_by(instance_id=instance.id).all()
        assert len(tasks) == 2
        assert all(t.status == WorkflowTaskStatus.PENDING for t in tasks)

    def test_create_tasks_all_mode(self, ctx, base, table, owner, approver_a, approver_b, record):
        """测试会签模式为每个审批人创建任务"""
        workflow = _create_workflow(ctx, base, table, owner, [
            {
                'node_type': 'approval',
                'name': '会签审批',
                'config': {
                    'mode': 'all',
                    'approvers': {
                        'source': 'fixed_users',
                        'user_ids': [str(approver_a.id), str(approver_b.id)]
                    }
                },
                'order': 0
            }
        ])

        instance = _create_instance(workflow, record)
        approval_node = workflow.nodes.first()

        result = ApprovalService.create_tasks(instance, approval_node)
        assert result['success'] is True
        assert result['mode'] == 'all'
        assert len(result['tasks']) == 2

    def test_create_tasks_serial_mode(self, ctx, base, table, owner, approver_a, approver_b, record):
        """测试串行模式仅创建第一个任务"""
        workflow = _create_workflow(ctx, base, table, owner, [
            {
                'node_type': 'approval',
                'name': '串行审批',
                'config': {
                    'mode': 'serial',
                    'approvers': {
                        'source': 'fixed_users',
                        'user_ids': [str(approver_a.id), str(approver_b.id)]
                    }
                },
                'order': 0
            }
        ])

        instance = _create_instance(workflow, record)
        approval_node = workflow.nodes.first()

        result = ApprovalService.create_tasks(instance, approval_node)
        assert result['success'] is True
        assert result['mode'] == 'serial'
        assert len(result['tasks']) == 1
        assert result['tasks'][0]['assignee_id'] == str(approver_a.id)

    def test_create_tasks_no_approvers(self, ctx, base, table, owner, record):
        """测试未解析到审批人时返回失败"""
        workflow = _create_workflow(ctx, base, table, owner, [
            {
                'node_type': 'approval',
                'name': '无审批人',
                'config': {
                    'mode': 'any',
                    'approvers': {
                        'source': 'fixed_users',
                        'user_ids': []
                    }
                },
                'order': 0
            }
        ])

        instance = _create_instance(workflow, record)
        approval_node = workflow.nodes.first()

        result = ApprovalService.create_tasks(instance, approval_node)
        assert result['success'] is False
        assert '未解析到审批人' in result['error']


class TestApprove:
    """测试同意审批"""

    def test_approve_any_mode(self, ctx, base, table, owner, approver_a, approver_b, record):
        """测试或签模式下任一审批人同意即通过"""
        workflow = _create_workflow(ctx, base, table, owner, [
            {
                'node_type': 'approval',
                'name': '或签审批',
                'config': {
                    'mode': 'any',
                    'approvers': {
                        'source': 'fixed_users',
                        'user_ids': [str(approver_a.id), str(approver_b.id)]
                    }
                },
                'order': 0
            }
        ])

        instance = _create_instance(workflow, record)
        approval_node = workflow.nodes.first()
        ApprovalService.create_tasks(instance, approval_node)

        task = WorkflowTask.query.filter_by(assignee_id=approver_a.id).first()
        result = ApprovalService.approve(str(task.id), str(approver_a.id), '同意')

        assert result['success'] is True
        assert result['task']['status'] == 'approved'

        db.session.refresh(instance)
        assert instance.status == WorkflowInstanceStatus.COMPLETED

    def test_approve_all_mode(self, ctx, base, table, owner, approver_a, approver_b, record):
        """测试会签模式下需全部同意才通过"""
        workflow = _create_workflow(ctx, base, table, owner, [
            {
                'node_type': 'approval',
                'name': '会签审批',
                'config': {
                    'mode': 'all',
                    'approvers': {
                        'source': 'fixed_users',
                        'user_ids': [str(approver_a.id), str(approver_b.id)]
                    }
                },
                'order': 0
            }
        ])

        instance = _create_instance(workflow, record)
        approval_node = workflow.nodes.first()
        ApprovalService.create_tasks(instance, approval_node)

        task_a = WorkflowTask.query.filter_by(assignee_id=approver_a.id).first()
        ApprovalService.approve(str(task_a.id), str(approver_a.id))

        db.session.refresh(instance)
        assert instance.status == WorkflowInstanceStatus.RUNNING

        task_b = WorkflowTask.query.filter_by(assignee_id=approver_b.id).first()
        ApprovalService.approve(str(task_b.id), str(approver_b.id))

        db.session.refresh(instance)
        assert instance.status == WorkflowInstanceStatus.COMPLETED

    def test_approve_serial_mode(self, ctx, base, table, owner, approver_a, approver_b, record):
        """测试串行模式下第一个同意后创建第二个任务"""
        workflow = _create_workflow(ctx, base, table, owner, [
            {
                'node_type': 'approval',
                'name': '串行审批',
                'config': {
                    'mode': 'serial',
                    'approvers': {
                        'source': 'fixed_users',
                        'user_ids': [str(approver_a.id), str(approver_b.id)]
                    }
                },
                'order': 0
            }
        ])

        instance = _create_instance(workflow, record)
        approval_node = workflow.nodes.first()
        ApprovalService.create_tasks(instance, approval_node)

        task_a = WorkflowTask.query.filter_by(assignee_id=approver_a.id).first()
        ApprovalService.approve(str(task_a.id), str(approver_a.id))

        tasks = WorkflowTask.query.filter_by(instance_id=instance.id).all()
        assert len(tasks) == 2

        task_b = WorkflowTask.query.filter_by(assignee_id=approver_b.id).first()
        assert task_b is not None
        assert task_b.status == WorkflowTaskStatus.PENDING

    def test_non_assignee_cannot_approve(self, ctx, base, table, owner, approver_a, approver_b, record):
        """测试非审批人无法处理任务"""
        workflow = _create_workflow(ctx, base, table, owner, [
            {
                'node_type': 'approval',
                'name': '或签审批',
                'config': {
                    'mode': 'any',
                    'approvers': {
                        'source': 'fixed_users',
                        'user_ids': [str(approver_a.id)]
                    }
                },
                'order': 0
            }
        ])

        instance = _create_instance(workflow, record)
        approval_node = workflow.nodes.first()
        ApprovalService.create_tasks(instance, approval_node)

        task = WorkflowTask.query.filter_by(assignee_id=approver_a.id).first()
        result = ApprovalService.approve(str(task.id), str(approver_b.id))

        assert result['success'] is False
        assert '无权处理' in result['error']


class TestReject:
    """测试驳回审批"""

    def test_reject_terminates_instance(self, ctx, base, table, owner, approver_a, approver_b, record):
        """测试驳回撤回终止实例"""
        workflow = _create_workflow(ctx, base, table, owner, [
            {
                'node_type': 'approval',
                'name': '或签审批',
                'config': {
                    'mode': 'any',
                    'approvers': {
                        'source': 'fixed_users',
                        'user_ids': [str(approver_a.id), str(approver_b.id)]
                    }
                },
                'order': 0
            }
        ])

        instance = _create_instance(workflow, record)
        approval_node = workflow.nodes.first()
        ApprovalService.create_tasks(instance, approval_node)

        task = WorkflowTask.query.filter_by(assignee_id=approver_a.id).first()
        result = ApprovalService.reject(str(task.id), str(approver_a.id), '不符合要求')

        assert result['success'] is True

        db.session.refresh(instance)
        assert instance.status == WorkflowInstanceStatus.REJECTED


class TestTransfer:
    """测试转交审批"""

    def test_transfer_creates_new_task(self, ctx, base, table, owner, approver_a, approver_b, record):
        """测试转交会创建新任务"""
        workflow = _create_workflow(ctx, base, table, owner, [
            {
                'node_type': 'approval',
                'name': '或签审批',
                'config': {
                    'mode': 'any',
                    'approvers': {
                        'source': 'fixed_users',
                        'user_ids': [str(approver_a.id)]
                    }
                },
                'order': 0
            }
        ])

        instance = _create_instance(workflow, record)
        approval_node = workflow.nodes.first()
        ApprovalService.create_tasks(instance, approval_node)

        task = WorkflowTask.query.filter_by(assignee_id=approver_a.id).first()
        result = ApprovalService.transfer(
            str(task.id),
            str(approver_a.id),
            str(approver_b.id),
            '请 B 处理'
        )

        assert result['success'] is True
        assert result['task']['status'] == 'transferred'
        assert result['new_task']['assignee_id'] == str(approver_b.id)


class TestTimeout:
    """测试超时处理"""

    def test_auto_approve_timeout(self, ctx, base, table, owner, approver_a, record):
        """测试超时自动通过"""
        workflow = _create_workflow(ctx, base, table, owner, [
            {
                'node_type': 'approval',
                'name': '超时自动通过',
                'config': {
                    'mode': 'any',
                    'approvers': {
                        'source': 'fixed_users',
                        'user_ids': [str(approver_a.id)]
                    },
                    'timeout_hours': 1,
                    'timeout_action': 'auto_approve'
                },
                'order': 0
            }
        ])

        instance = _create_instance(workflow, record)
        approval_node = workflow.nodes.first()
        ApprovalService.create_tasks(instance, approval_node)

        # 伪造节点执行日志开始时间为 2 小时前
        log = WorkflowExecutionLog.query.filter_by(instance_id=instance.id).first()
        log.started_at = datetime.now(timezone.utc) - timedelta(hours=2)
        db.session.commit()

        ApprovalService.check_timeout()

        task = WorkflowTask.query.filter_by(assignee_id=approver_a.id).first()
        assert task.status == WorkflowTaskStatus.APPROVED

    def test_auto_reject_timeout(self, ctx, base, table, owner, approver_a, record):
        """测试超时自动驳回"""
        workflow = _create_workflow(ctx, base, table, owner, [
            {
                'node_type': 'approval',
                'name': '超时自动驳回',
                'config': {
                    'mode': 'any',
                    'approvers': {
                        'source': 'fixed_users',
                        'user_ids': [str(approver_a.id)]
                    },
                    'timeout_hours': 1,
                    'timeout_action': 'auto_reject'
                },
                'order': 0
            }
        ])

        instance = _create_instance(workflow, record)
        approval_node = workflow.nodes.first()
        ApprovalService.create_tasks(instance, approval_node)

        log = WorkflowExecutionLog.query.filter_by(instance_id=instance.id).first()
        log.started_at = datetime.now(timezone.utc) - timedelta(hours=2)
        db.session.commit()

        ApprovalService.check_timeout()

        db.session.refresh(instance)
        assert instance.status == WorkflowInstanceStatus.REJECTED
