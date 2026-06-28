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
from app.models.workflow import WorkflowNode, WorkflowTrigger, WorkflowVersion
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

    def test_create_workflow_requires_table_id(self, client, auth_headers, test_base):
        """测试创建工作流时必须提供 table_id"""
        response = client.post(
            f'/api/bases/{test_base.id}/workflows',
            json={'name': '无表工作流'},
            headers=auth_headers
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert '请选择关联数据表' in data['message']

    def test_update_nodes_returns_action_subtype_as_node_type(
        self, client, auth_headers, created_workflow
    ):
        """测试保存 create_record/update_record/send_email 节点后，查询返回细粒度 node_type"""
        response = client.put(
            f'/api/workflows/{created_workflow.id}/nodes',
            json={
                'nodes': [
                    {
                        'node_type': 'trigger',
                        'name': '记录创建',
                        'config': {},
                        'order': 0,
                        'next_nodes': []
                    },
                    {
                        'node_type': 'create_record',
                        'name': '创建记录',
                        'config': {'target_table_id': 'table-1'},
                        'order': 1,
                        'next_nodes': []
                    },
                    {
                        'node_type': 'update_record',
                        'name': '更新记录',
                        'config': {},
                        'order': 2,
                        'next_nodes': []
                    },
                    {
                        'node_type': 'send_email',
                        'name': '发送邮件',
                        'config': {},
                        'order': 3,
                        'next_nodes': []
                    }
                ]
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        returned_types = {node['name']: node['node_type'] for node in data['data']}
        assert returned_types['创建记录'] == 'create_record'
        assert returned_types['更新记录'] == 'update_record'
        assert returned_types['发送邮件'] == 'send_email'

        # 再次 GET 确认 to_dict() 也返回细粒度类型
        get_response = client.get(
            f'/api/workflows/{created_workflow.id}/nodes',
            headers=auth_headers
        )
        assert get_response.status_code == 200
        get_data = get_response.get_json()
        returned_types = {node['name']: node['node_type'] for node in get_data['data']}
        assert returned_types['创建记录'] == 'create_record'
        assert returned_types['更新记录'] == 'update_record'
        assert returned_types['发送邮件'] == 'send_email'

    def test_publish_workflow_snapshot_preserves_create_record_node_type(
        self, client, auth_headers, created_workflow
    ):
        """测试发布后版本快照保留 create_record 细粒度类型与完整配置"""
        response = client.put(
            f'/api/workflows/{created_workflow.id}/nodes',
            json={
                'nodes': [
                    {
                        'node_type': 'trigger',
                        'name': '记录创建',
                        'config': {},
                        'order': 0,
                        'next_nodes': []
                    },
                    {
                        'node_type': 'create_record',
                        'name': '创建记录',
                        'config': {
                            'target_table_id': 'table-1',
                            'field_mappings': [
                                {
                                    'target_field_id': 'target-1',
                                    'source_field_id': 'source-1',
                                    'value_template': '{{trigger.record.source-1}}'
                                }
                            ]
                        },
                        'order': 1,
                        'next_nodes': []
                    }
                ]
            },
            headers=auth_headers
        )
        assert response.status_code == 200

        publish_response = client.post(
            f'/api/workflows/{created_workflow.id}/publish',
            headers=auth_headers
        )
        assert publish_response.status_code == 200

        versions_response = client.get(
            f'/api/workflows/{created_workflow.id}/versions',
            headers=auth_headers
        )
        assert versions_response.status_code == 200
        versions_data = versions_response.get_json()
        assert versions_data['success'] is True
        assert len(versions_data['data']) == 1

        snapshot = versions_data['data'][0]['config_snapshot']
        nodes = snapshot['nodes']
        assert len(nodes) == 2
        create_node = [n for n in nodes if n['name'] == '创建记录'][0]
        assert create_node['node_type'] == 'create_record'
        assert create_node['config']['target_table_id'] == 'table-1'
        assert create_node['config']['field_mappings'][0]['target_field_id'] == 'target-1'
        assert create_node['config']['field_mappings'][0]['value_template'] == '{{trigger.record.source-1}}'

    def test_version_snapshot_with_legacy_action_subtype_can_be_loaded(
        self, client, auth_headers, created_workflow, test_user
    ):
        """测试历史版本快照中以 action + action_type 存储的节点可被正确识别"""
        # 直接写入一个旧格式版本快照
        version = WorkflowVersion(
            workflow_id=created_workflow.id,
            version_number=created_workflow.current_version + 1,
            config_snapshot={
                'name': created_workflow.name,
                'nodes': [
                    {
                        'id': 'legacy-node-1',
                        'workflow_id': str(created_workflow.id),
                        'node_type': 'action',
                        'name': '旧版创建记录',
                        'config': {
                            'action_type': 'create_record',
                            'target_table_id': 'legacy-table',
                            'field_mappings': []
                        },
                        'order': 0,
                        'next_nodes': []
                    }
                ],
                'triggers': []
            },
            created_by=test_user.id
        )
        db.session.add(version)
        created_workflow.current_version += 1
        db.session.commit()

        versions_response = client.get(
            f'/api/workflows/{created_workflow.id}/versions',
            headers=auth_headers
        )
        assert versions_response.status_code == 200
        versions_data = versions_response.get_json()
        snapshot = versions_data['data'][0]['config_snapshot']
        legacy_node = [n for n in snapshot['nodes'] if n['name'] == '旧版创建记录'][0]
        # 后端快照直接返回原始数据，不经过 to_dict()，因此仍为 action；
        # 前端 getVersionNodes 会使用 normalizeWorkflowNodes 处理，这里仅校验快照完整保留
        assert legacy_node['node_type'] == 'action'
        assert legacy_node['config']['action_type'] == 'create_record'
        assert legacy_node['config']['target_table_id'] == 'legacy-table'

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

    def test_edit_nodes_when_paused(self, client, auth_headers, created_workflow):
        """测试暂停状态下可以编辑节点"""
        # 先发布
        client.post(
            f'/api/workflows/{created_workflow.id}/publish',
            headers=auth_headers
        )
        # 暂停
        client.post(
            f'/api/workflows/{created_workflow.id}/pause',
            headers=auth_headers
        )

        # 暂停状态下编辑节点
        response = client.put(
            f'/api/workflows/{created_workflow.id}/nodes',
            json={
                'nodes': [
                    {
                        'node_type': 'trigger',
                        'name': '记录创建',
                        'config': {},
                        'order': 0,
                        'next_nodes': []
                    },
                    {
                        'node_type': 'update_record',
                        'name': '更新记录',
                        'config': {
                            'action_type': 'update_record',
                            'updates': []
                        },
                        'order': 1,
                        'next_nodes': []
                    }
                ]
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']) == 2

    def test_edit_trigger_when_paused(self, client, auth_headers, created_workflow):
        """测试暂停状态下可以编辑触发器"""
        # 先发布
        client.post(
            f'/api/workflows/{created_workflow.id}/publish',
            headers=auth_headers
        )
        # 暂停
        client.post(
            f'/api/workflows/{created_workflow.id}/pause',
            headers=auth_headers
        )

        # 暂停状态下编辑触发器
        response = client.put(
            f'/api/workflows/{created_workflow.id}/trigger',
            json={
                'trigger_type': 'record_updated',
                'filter_config': {}
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_cannot_edit_nodes_when_active(self, client, auth_headers, created_workflow):
        """测试已发布(active)状态不能编辑节点"""
        client.post(
            f'/api/workflows/{created_workflow.id}/publish',
            headers=auth_headers
        )

        response = client.put(
            f'/api/workflows/{created_workflow.id}/nodes',
            json={
                'nodes': [
                    {
                        'node_type': 'trigger',
                        'name': '记录创建',
                        'config': {},
                        'order': 0,
                        'next_nodes': []
                    }
                ]
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        data = response.get_json()
        assert '暂停' in data.get('message', '') or '草稿' in data.get('message', '')

    def test_publish_from_paused_state(self, client, auth_headers, created_workflow):
        """测试从暂停状态发布工作流"""
        # 先发布
        client.post(
            f'/api/workflows/{created_workflow.id}/publish',
            headers=auth_headers
        )
        assert created_workflow.current_version == 1

        # 暂停
        client.post(
            f'/api/workflows/{created_workflow.id}/pause',
            headers=auth_headers
        )

        # 编辑节点
        client.put(
            f'/api/workflows/{created_workflow.id}/nodes',
            json={
                'nodes': [
                    {
                        'node_type': 'trigger',
                        'name': '记录创建',
                        'config': {},
                        'order': 0,
                        'next_nodes': []
                    }
                ]
            },
            headers=auth_headers
        )

        # 再次发布
        response = client.post(
            f'/api/workflows/{created_workflow.id}/publish',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['workflow']['status'] == 'active'
        # 版本号递增
        assert data['data']['workflow']['current_version'] == 2

    def test_publish_validates_missing_trigger(self, client, auth_headers, test_base, workflow_table):
        """测试发布时验证缺少触发器"""
        # 创建无触发器的工作流
        workflow = WorkflowService.create_workflow(
            base_id=test_base.id,
            table_id=workflow_table.id,
            name='无触发器工作流',
            created_by=test_base.owner_id,
            trigger_config=None,
            nodes_config=[
                {'node_type': 'trigger', 'name': '触发', 'config': {}, 'order': 0}
            ]
        )
        # 手动删除触发器
        WorkflowTrigger.query.filter_by(workflow_id=workflow.id).delete()
        db.session.commit()

        response = client.post(
            f'/api/workflows/{workflow.id}/publish',
            headers=auth_headers
        )
        assert response.status_code == 400
        data = response.get_json()
        assert '触发器' in data.get('message', '')

    def test_publish_validates_missing_nodes(self, client, auth_headers, test_base, workflow_table):
        """测试发布时验证缺少节点"""
        workflow = WorkflowService.create_workflow(
            base_id=test_base.id,
            table_id=workflow_table.id,
            name='无节点工作流',
            created_by=test_base.owner_id,
            trigger_config={'trigger_type': 'record_created', 'filter_config': {}},
            nodes_config=None
        )
        # 手动删除节点
        WorkflowNode.query.filter_by(workflow_id=workflow.id).delete()
        db.session.commit()

        response = client.post(
            f'/api/workflows/{workflow.id}/publish',
            headers=auth_headers
        )
        assert response.status_code == 400
        data = response.get_json()
        assert '节点' in data.get('message', '')

    def test_snapshot_creates_version_when_paused_with_changes(self, client, auth_headers, created_workflow):
        """测试暂停状态修改后保存快照会创建新版本"""
        # 先发布（v1）
        client.post(
            f'/api/workflows/{created_workflow.id}/publish',
            headers=auth_headers
        )
        assert created_workflow.current_version == 1

        # 暂停
        client.post(
            f'/api/workflows/{created_workflow.id}/pause',
            headers=auth_headers
        )

        # 修改节点
        client.put(
            f'/api/workflows/{created_workflow.id}/nodes',
            json={
                'nodes': [
                    {
                        'node_type': 'trigger',
                        'name': '记录创建',
                        'config': {},
                        'order': 0,
                        'next_nodes': []
                    },
                    {
                        'node_type': 'update_record',
                        'name': '更新记录',
                        'config': {
                            'action_type': 'update_record',
                            'updates': []
                        },
                        'order': 1,
                        'next_nodes': []
                    }
                ]
            },
            headers=auth_headers
        )

        # 保存快照
        response = client.post(
            f'/api/workflows/{created_workflow.id}/snapshot',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['version_number'] == 2

    def test_snapshot_skips_when_no_changes(self, client, auth_headers, created_workflow):
        """测试暂停状态无变更时保存快照不会创建新版本"""
        # 先发布（v1）
        client.post(
            f'/api/workflows/{created_workflow.id}/publish',
            headers=auth_headers
        )

        # 暂停（未做任何修改）
        client.post(
            f'/api/workflows/{created_workflow.id}/pause',
            headers=auth_headers
        )

        # 保存快照（应无变更）
        response = client.post(
            f'/api/workflows/{created_workflow.id}/snapshot',
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] is None  # 无变更时返回 None
        # 版本号不变
        db.session.refresh(created_workflow)
        assert created_workflow.current_version == 1

    def test_snapshot_rejected_for_draft(self, client, auth_headers, created_workflow):
        """测试草稿状态不允许保存版本快照"""
        response = client.post(
            f'/api/workflows/{created_workflow.id}/snapshot',
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_snapshot_rejected_for_active(self, client, auth_headers, created_workflow):
        """测试已发布状态不允许保存版本快照"""
        client.post(
            f'/api/workflows/{created_workflow.id}/publish',
            headers=auth_headers
        )
        response = client.post(
            f'/api/workflows/{created_workflow.id}/snapshot',
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_snapshot_then_publish_version_consistency(self, client, auth_headers, created_workflow):
        """测试暂停状态保存快照后再发布，版本号连续递增"""
        # 先发布（v1）
        client.post(
            f'/api/workflows/{created_workflow.id}/publish',
            headers=auth_headers
        )

        # 暂停
        client.post(
            f'/api/workflows/{created_workflow.id}/pause',
            headers=auth_headers
        )

        # 修改并保存快照（v2）
        client.put(
            f'/api/workflows/{created_workflow.id}/nodes',
            json={
                'nodes': [
                    {
                        'node_type': 'trigger',
                        'name': '记录创建',
                        'config': {},
                        'order': 0,
                        'next_nodes': []
                    }
                ]
            },
            headers=auth_headers
        )
        snapshot_response = client.post(
            f'/api/workflows/{created_workflow.id}/snapshot',
            headers=auth_headers
        )
        assert snapshot_response.get_json()['data']['version_number'] == 2

        # 再发布（v3）
        publish_response = client.post(
            f'/api/workflows/{created_workflow.id}/publish',
            headers=auth_headers
        )
        assert publish_response.status_code == 200
        publish_data = publish_response.get_json()
        assert publish_data['data']['workflow']['current_version'] == 3
        assert publish_data['data']['workflow']['status'] == 'active'


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
