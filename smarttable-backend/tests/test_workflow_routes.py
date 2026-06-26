"""
工作流相关 API 路由集成测试
测试 workflows、approvals、webhooks、workflow_templates 端点。
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from app.extensions import db
from app.models import (
    User,
    Base,
    BaseMember,
    MemberRole,
    Table,
    Field,
    Record,
    Workflow,
    WorkflowStatus,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowTask,
    WorkflowTaskStatus,
    WebhookConfig,
    WebhookMethod,
)
from app.models.workflow import WorkflowNode, WorkflowTrigger
from app.services.workflow_service import WorkflowService
from app.services.approval_service import ApprovalService


@pytest.fixture(scope='function')
def workflow_table(test_base):
    """在工作流测试中创建表格"""
    table = Table(base_id=test_base.id, name='测试表格', order=0)
    db.session.add(table)
    db.session.commit()
    db.session.refresh(table)
    return table


@pytest.fixture(scope='function')
def workflow_field(workflow_table):
    """在工作流测试中创建字段"""
    from app.models.field import FieldType
    field = Field(
        table_id=workflow_table.id,
        name='状态',
        type=FieldType.SINGLE_LINE_TEXT.value,
        order=0
    )
    db.session.add(field)
    db.session.commit()
    db.session.refresh(field)
    return field


@pytest.fixture(scope='function')
def viewer_member(test_base, test_viewer_user):
    """将 viewer 用户添加为 Base 的 VIEWER 成员"""
    member = BaseMember(
        base_id=test_base.id,
        user_id=test_viewer_user.id,
        role=MemberRole.VIEWER
    )
    db.session.add(member)
    db.session.commit()
    return member


@pytest.fixture(scope='function')
def editor_member(test_base, test_editor_user):
    """将 editor 用户添加为 Base 的 EDITOR 成员"""
    member = BaseMember(
        base_id=test_base.id,
        user_id=test_editor_user.id,
        role=MemberRole.EDITOR
    )
    db.session.add(member)
    db.session.commit()
    return member


@pytest.fixture(scope='function')
def created_workflow(test_base, workflow_table, test_user):
    """创建并返回一个草稿工作流"""
    workflow = WorkflowService.create_workflow(
        base_id=test_base.id,
        table_id=workflow_table.id,
        name='路由测试工作流',
        description='用于路由测试',
        created_by=test_user.id,
        trigger_config={
            'trigger_type': 'record_created',
            'filter_config': {}
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
    return workflow


class TestWorkflowRoutes:
    """测试工作流路由"""

    def test_get_workflows_list(self, client, auth_headers, test_base, created_workflow):
        """测试获取 Base 下工作流列表"""
        response = client.get(
            f'/api/bases/{test_base.id}/workflows',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']) >= 1

    def test_create_workflow(self, client, auth_headers, test_base, workflow_table):
        """测试创建工作流"""
        response = client.post(
            f'/api/bases/{test_base.id}/workflows',
            json={
                'name': '新建工作流',
                'table_id': str(workflow_table.id),
                'trigger_config': {
                    'trigger_type': 'record_created',
                    'filter_config': {}
                },
                'nodes_config': [
                    {
                        'node_type': 'trigger',
                        'name': '记录创建',
                        'order': 0
                    }
                ]
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['name'] == '新建工作流'

    def test_viewer_cannot_create_workflow(
        self, client, viewer_auth_headers, test_base, workflow_table, viewer_member
    ):
        """测试 VIEWER 无法通过 API 创建工作流"""
        response = client.post(
            f'/api/bases/{test_base.id}/workflows',
            json={
                'name': 'viewer 创建',
                'table_id': str(workflow_table.id)
            },
            headers=viewer_auth_headers
        )
        assert response.status_code == 403

    def test_update_workflow(self, client, auth_headers, created_workflow):
        """测试更新草稿工作流"""
        response = client.put(
            f'/api/workflows/{created_workflow.id}',
            json={'name': '已更新名称'},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['workflow']['name'] == '已更新名称'

    def test_publish_workflow(self, client, auth_headers, created_workflow):
        """测试发布工作流"""
        response = client.post(
            f'/api/workflows/{created_workflow.id}/publish',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['workflow']['status'] == 'active'

    def test_pause_and_resume_workflow(self, client, auth_headers, created_workflow):
        """测试暂停与恢复工作流"""
        client.post(
            f'/api/workflows/{created_workflow.id}/publish',
            headers=auth_headers
        )

        response = client.post(
            f'/api/workflows/{created_workflow.id}/pause',
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.get_json()['data']['workflow']['status'] == 'paused'

        response = client.post(
            f'/api/workflows/{created_workflow.id}/resume',
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.get_json()['data']['workflow']['status'] == 'active'

    def test_delete_workflow(self, client, auth_headers, created_workflow):
        """测试删除工作流"""
        response = client.delete(
            f'/api/workflows/{created_workflow.id}',
            headers=auth_headers
        )
        assert response.status_code == 200

        get_response = client.get(
            f'/api/workflows/{created_workflow.id}',
            headers=auth_headers
        )
        assert get_response.status_code == 404

    def test_get_workflow_instances(self, client, auth_headers, created_workflow):
        """测试获取工作流实例列表"""
        WorkflowService.publish_workflow(created_workflow.id, created_by=created_workflow.created_by)
        instance = WorkflowInstance(
            workflow_id=created_workflow.id,
            version_number=1,
            trigger_type='record_created',
            status=WorkflowInstanceStatus.RUNNING
        )
        db.session.add(instance)
        db.session.commit()

        response = client.get(
            f'/api/workflows/{created_workflow.id}/instances',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['meta']['pagination']['total'] == 1


class TestApprovalRoutes:
    """测试审批路由"""

    def test_get_approvals_list(self, client, auth_headers, test_base, created_workflow, workflow_field):
        """测试获取我的审批列表"""
        WorkflowService.publish_workflow(created_workflow.id, created_by=created_workflow.created_by)
        record = Record(
            table_id=created_workflow.table_id,
            values={str(workflow_field.id): '测试'},
            created_by=created_workflow.created_by
        )
        db.session.add(record)
        db.session.commit()

        instance = WorkflowInstance(
            workflow_id=created_workflow.id,
            version_number=1,
            trigger_type='record_created',
            status=WorkflowInstanceStatus.RUNNING,
            trigger_record_id=record.id
        )
        db.session.add(instance)
        db.session.commit()

        # 创建审批节点和任务
        node = WorkflowNode(
            workflow_id=created_workflow.id,
            node_type='approval',
            name='审批',
            config={
                'mode': 'any',
                'approvers': {
                    'source': 'fixed_users',
                    'user_ids': [str(created_workflow.created_by)]
                }
            },
            order=1
        )
        db.session.add(node)
        db.session.commit()

        task = WorkflowTask(
            instance_id=instance.id,
            node_id=node.id,
            assignee_id=created_workflow.created_by,
            status=WorkflowTaskStatus.PENDING
        )
        db.session.add(task)
        db.session.commit()

        response = client.get(
            f'/api/bases/{test_base.id}/approvals?status=pending',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)
        assert data['success'] is True

    def test_approve_task(self, client, auth_headers, test_base, created_workflow, workflow_field):
        """测试通过 API 同意审批"""
        WorkflowService.publish_workflow(created_workflow.id, created_by=created_workflow.created_by)
        record = Record(
            table_id=created_workflow.table_id,
            values={str(workflow_field.id): '测试'},
            created_by=created_workflow.created_by
        )
        db.session.add(record)
        db.session.commit()

        instance = WorkflowInstance(
            workflow_id=created_workflow.id,
            version_number=1,
            trigger_type='record_created',
            status=WorkflowInstanceStatus.RUNNING,
            trigger_record_id=record.id
        )
        db.session.add(instance)
        db.session.commit()

        node = WorkflowNode(
            workflow_id=created_workflow.id,
            node_type='approval',
            name='审批',
            config={
                'mode': 'any',
                'approvers': {
                    'source': 'fixed_users',
                    'user_ids': [str(created_workflow.created_by)]
                }
            },
            order=1
        )
        db.session.add(node)
        db.session.commit()

        with patch.object(ApprovalService, '_send_notification'):
            with patch.object(ApprovalService, '_emit_if_enabled'):
                task = WorkflowTask(
                    instance_id=instance.id,
                    node_id=node.id,
                    assignee_id=created_workflow.created_by,
                    status=WorkflowTaskStatus.PENDING
                )
                db.session.add(task)
                db.session.commit()

                response = client.post(
                    f'/api/approvals/{task.id}/approve',
                    json={'comment': '同意'},
                    headers=auth_headers
                )
                assert response.status_code == 200
                data = response.get_json()
                assert data['success'] is True

    def test_non_assignee_cannot_approve(
        self, client, editor_auth_headers, test_base, created_workflow,
        workflow_field, editor_member, test_user
    ):
        """测试非审批人无法通过 API 同意"""
        WorkflowService.publish_workflow(created_workflow.id, created_by=test_user.id)
        record = Record(
            table_id=created_workflow.table_id,
            values={str(workflow_field.id): '测试'},
            created_by=test_user.id
        )
        db.session.add(record)
        db.session.commit()

        instance = WorkflowInstance(
            workflow_id=created_workflow.id,
            version_number=1,
            trigger_type='record_created',
            status=WorkflowInstanceStatus.RUNNING,
            trigger_record_id=record.id
        )
        db.session.add(instance)
        db.session.commit()

        node = WorkflowNode(
            workflow_id=created_workflow.id,
            node_type='approval',
            name='审批',
            config={
                'mode': 'any',
                'approvers': {
                    'source': 'fixed_users',
                    'user_ids': [str(test_user.id)]
                }
            },
            order=1
        )
        db.session.add(node)
        db.session.commit()

        task = WorkflowTask(
            instance_id=instance.id,
            node_id=node.id,
            assignee_id=test_user.id,
            status=WorkflowTaskStatus.PENDING
        )
        db.session.add(task)
        db.session.commit()

        response = client.post(
            f'/api/approvals/{task.id}/approve',
            headers=editor_auth_headers
        )
        assert response.status_code == 403


class TestWebhookRoutes:
    """测试 Webhook 路由"""

    def test_create_webhook(self, client, auth_headers, test_base):
        """测试创建 Webhook"""
        response = client.post(
            f'/api/bases/{test_base.id}/webhooks',
            json={
                'name': '测试 Webhook',
                'url': 'https://example.com/webhook',
                'method': 'POST',
                'headers': {'X-Custom': 'value'}
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['name'] == '测试 Webhook'

    def test_viewer_cannot_create_webhook(
        self, client, viewer_auth_headers, test_base, viewer_member
    ):
        """测试 VIEWER 无法创建 Webhook"""
        response = client.post(
            f'/api/bases/{test_base.id}/webhooks',
            json={
                'name': 'viewer webhook',
                'url': 'https://example.com/webhook'
            },
            headers=viewer_auth_headers
        )
        assert response.status_code == 403

    def test_get_webhooks_list(self, client, auth_headers, test_base, test_user):
        """测试获取 Webhook 列表"""
        webhook = WebhookConfig(
            base_id=test_base.id,
            name='列表 Webhook',
            url='https://example.com/list',
            method=WebhookMethod.POST,
            created_by=test_user.id
        )
        db.session.add(webhook)
        db.session.commit()

        response = client.get(
            f'/api/bases/{test_base.id}/webhooks',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) >= 1


class TestWorkflowTemplateRoutes:
    """测试工作流模板路由"""

    def test_list_templates(self, client, auth_headers):
        """测试获取模板列表"""
        response = client.get(
            '/api/workflow-templates',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_save_as_template(self, client, auth_headers, created_workflow):
        """测试将工作流保存为模板"""
        response = client.post(
            '/api/workflow-templates',
            json={
                'workflow_id': str(created_workflow.id),
                'name': '我的模板',
                'category': 'test'
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert 'template_id' in data['data']
