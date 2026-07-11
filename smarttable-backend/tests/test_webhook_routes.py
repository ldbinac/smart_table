"""
Webhook 路由集成测试
测试 Webhook 引用查询与删除拦截逻辑。
"""
import pytest

from app.extensions import db
from app.models import (
    User,
    Base,
    WebhookConfig,
    WebhookMethod,
)
from app.models.workflow import (
    Workflow,
    WorkflowStatus,
    WorkflowNode,
    WorkflowNodeType,
)


@pytest.fixture(scope='function')
def webhook_config(test_base, test_user):
    """创建测试 Webhook 配置"""
    config = WebhookConfig(
        base_id=test_base.id,
        name='测试 Webhook',
        url='https://example.com/webhook',
        method=WebhookMethod.POST,
        headers={'X-Custom': 'test'},
        body_template='{"event": "{{event.event_type}}"}',
        secret='test-secret',
        created_by=test_user.id
    )
    db.session.add(config)
    db.session.commit()
    db.session.refresh(config)
    return config


@pytest.fixture(scope='function')
def workflow_with_webhook_node(test_base, test_table, test_user, webhook_config):
    """创建含 WEBHOOK 节点的工作流（引用 webhook_config）"""
    workflow = Workflow(
        base_id=test_base.id,
        table_id=test_table.id,
        name='引用 Webhook 工作流',
        status=WorkflowStatus.DRAFT,
        current_version=0,
        created_by=test_user.id,
    )
    db.session.add(workflow)
    db.session.commit()

    node = WorkflowNode(
        workflow_id=workflow.id,
        node_type=WorkflowNodeType.WEBHOOK,
        name='Webhook 节点',
        config={'webhook_id': str(webhook_config.id)},
        order=0,
        next_nodes=[],
    )
    db.session.add(node)
    db.session.commit()
    return workflow


class TestGetWebhookReferences:
    """测试 GET /webhooks/<id>/references"""

    def test_get_webhook_references_empty(self, client, auth_headers, webhook_config):
        """Webhook 未被引用时返回空列表"""
        response = client.get(
            f'/api/webhooks/{webhook_config.id}/references',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['count'] == 0
        assert data['data']['references'] == []

    def test_get_webhook_references_with_nodes(
        self, client, auth_headers, webhook_config, workflow_with_webhook_node
    ):
        """创建带 WEBHOOK 节点的工作流后能查到引用"""
        response = client.get(
            f'/api/webhooks/{webhook_config.id}/references',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['count'] == 1
        ref = data['data']['references'][0]
        assert ref['workflow_name'] == '引用 Webhook 工作流'
        assert ref['node_name'] == 'Webhook 节点'
        assert ref['workflow_status'] == 'draft'

    def test_get_webhook_references_excludes_deleted_workflows(
        self, client, auth_headers, webhook_config, test_base, test_table, test_user
    ):
        """已软删除工作流中的引用不计入"""
        workflow = Workflow(
            base_id=test_base.id,
            table_id=test_table.id,
            name='软删除工作流',
            status=WorkflowStatus.DRAFT,
            current_version=0,
            created_by=test_user.id,
            is_deleted=True,
        )
        db.session.add(workflow)
        db.session.commit()

        node = WorkflowNode(
            workflow_id=workflow.id,
            node_type=WorkflowNodeType.WEBHOOK,
            name='已删除工作流的节点',
            config={'webhook_id': str(webhook_config.id)},
            order=0,
            next_nodes=[],
        )
        db.session.add(node)
        db.session.commit()

        response = client.get(
            f'/api/webhooks/{webhook_config.id}/references',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['count'] == 0

    def test_get_webhook_references_not_found(self, client, auth_headers):
        """Webhook 不存在时返回 404"""
        response = client.get(
            '/api/webhooks/00000000-0000-0000-0000-000000000000/references',
            headers=auth_headers
        )
        assert response.status_code == 404


class TestDeleteWebhookReferenceCheck:
    """测试 DELETE /webhooks/<id> 的引用拦截"""

    def test_delete_webhook_blocked_when_referenced(
        self, client, auth_headers, webhook_config, workflow_with_webhook_node
    ):
        """被引用时 DELETE 返回 409 且不执行删除"""
        response = client.delete(
            f'/api/webhooks/{webhook_config.id}',
            headers=auth_headers
        )
        assert response.status_code == 409
        data = response.get_json()
        assert data['success'] is False
        assert data['error'] == 'webhook_in_use'
        assert '1' in data['message']
        assert len(data['details']) == 1
        assert data['details'][0]['workflow_name'] == '引用 Webhook 工作流'

        # Webhook 仍存在
        still_exists = WebhookConfig.query.get(webhook_config.id)
        assert still_exists is not None

    def test_delete_webhook_succeeds_when_not_referenced(
        self, client, auth_headers, webhook_config
    ):
        """无引用时 DELETE 成功"""
        response = client.delete(
            f'/api/webhooks/{webhook_config.id}',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Webhook 已被删除
        deleted = WebhookConfig.query.get(webhook_config.id)
        assert deleted is None

    def test_delete_webhook_after_reference_removed(
        self, client, auth_headers, webhook_config, workflow_with_webhook_node
    ):
        """解除引用后 DELETE 成功"""
        # 先确认被拦截
        blocked_resp = client.delete(
            f'/api/webhooks/{webhook_config.id}',
            headers=auth_headers
        )
        assert blocked_resp.status_code == 409

        # 删除引用节点
        WorkflowNode.query.filter_by(
            workflow_id=workflow_with_webhook_node.id
        ).delete()
        workflow_with_webhook_node.is_deleted = True
        db.session.commit()

        # 再次 DELETE 应成功
        response = client.delete(
            f'/api/webhooks/{webhook_config.id}',
            headers=auth_headers
        )
        assert response.status_code == 200
        assert WebhookConfig.query.get(webhook_config.id) is None
