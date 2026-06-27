"""
工作流路由模块
处理工作流的 CRUD、状态管理与手动触发
"""
from flask import Blueprint, request, g

from app.extensions import db
from app.models.workflow import (
    Workflow,
    WorkflowStatus,
    WorkflowTrigger,
    WorkflowTriggerType,
    WorkflowNodeType,
    WorkflowNode,
)
from app.models.workflow_instance import WorkflowInstance
from app.models.base import MemberRole
from app.services.workflow_service import WorkflowService
from app.services.permission_service import PermissionService
from app.services.record_service import RecordService
from app.services.table_service import TableService
from app.services.workflow_execution_engine import workflow_execution_engine
from app.services.workflow_event_bus import WorkflowEvent
from app.utils.decorators import jwt_required
from app.utils.response import (
    success_response,
    error_response,
    not_found_response,
    forbidden_response,
    bad_request_response,
    paginated_response,
)

workflows_bp = Blueprint('workflows', __name__)
# 禁用严格斜杠，允许带或不带斜杠的URL
workflows_bp.strict_slashes = False


def _to_str(value):
    """将 UUID 或字符串统一为字符串"""
    return str(value) if value is not None else None


def _get_workflow_or_404(workflow_id):
    """获取工作流，不存在时返回 404"""
    workflow = Workflow.query.filter_by(
        id=WorkflowService._to_uuid(workflow_id),
        is_deleted=False
    ).first()
    if not workflow:
        return None, not_found_response('工作流')
    return workflow, None


def _check_base_edit_permission(base_id, user_id):
    """检查 EDITOR 权限"""
    return PermissionService.check_permission(
        base_id=str(base_id),
        user_id=str(user_id),
        min_role=MemberRole.EDITOR
    )


def _check_base_view_permission(base_id, user_id):
    """检查 VIEWER 权限"""
    return PermissionService.check_permission(
        base_id=str(base_id),
        user_id=str(user_id),
        min_role=MemberRole.VIEWER
    )


# ==================== Base 下工作流操作 ====================

@workflows_bp.route('/bases/<uuid:base_id>/workflows', methods=['GET'])
@jwt_required
def get_base_workflows(base_id) -> tuple:
    """
    获取 Base 下工作流列表
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: 基础数据 ID
      - name: table_id
        in: query
        type: string
        description: 按表格 ID 筛选
      - name: status
        in: query
        type: string
        description: 按状态筛选（draft/active/paused/archived）
    responses:
      200:
        description: 工作流列表
      403:
        description: 无权限
    """
    user_id = g.current_user_id
    base_id_str = str(base_id)

    if not _check_base_view_permission(base_id_str, user_id):
        return forbidden_response('您没有权限访问此基础数据')

    table_id = request.args.get('table_id')
    status = request.args.get('status')

    workflows = WorkflowService.list_workflows(
        base_id=base_id_str,
        table_id=table_id,
        status=status,
        user_id=user_id
    )

    return success_response(
        data=[w.to_dict() for w in workflows],
        message='获取工作流列表成功'
    )


@workflows_bp.route('/bases/<uuid:base_id>/workflows', methods=['POST'])
@jwt_required
def create_base_workflow(base_id) -> tuple:
    """
    在 Base 下创建工作流（草稿状态）
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: 基础数据 ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
              description: 工作流名称
            description:
              type: string
              description: 工作流描述
            table_id:
              type: string
              description: 关联表格 ID
            trigger_config:
              type: object
              description: 触发器配置
            nodes_config:
              type: array
              description: 节点配置列表
              items:
                type: object
    responses:
      201:
        description: 创建的工作流详情
      400:
        description: 参数错误
      403:
        description: 无权限
    """
    user_id = g.current_user_id
    base_id_str = str(base_id)

    if not _check_base_edit_permission(base_id_str, user_id):
        return forbidden_response('您没有权限在此基础数据中创建工作流')

    data = request.get_json() or {}

    name = data.get('name', '').strip()
    if not name:
        return error_response('工作流名称不能为空', code=400)
    if len(name) > 200:
        return error_response('工作流名称不能超过200个字符', code=400)

    table_id = data.get('table_id')
    if table_id:
        table = TableService.get_table_by_id(str(table_id))
        if not table or str(table.base_id) != base_id_str:
            return error_response('关联表格不存在或不属于当前基础数据', code=400)

    trigger_config = data.get('trigger_config')
    nodes_config = data.get('nodes_config')

    # 简单校验节点配置
    if nodes_config is not None:
        if not isinstance(nodes_config, list):
            return error_response('nodes_config 必须是数组', code=400)
        for idx, node in enumerate(nodes_config):
            if not isinstance(node, dict):
                return error_response(f'第 {idx + 1} 个节点必须是对象', code=400)
            node_type = node.get('node_type')
            if node_type and node_type not in [t.value for t in WorkflowNodeType]:
                return error_response(f'第 {idx + 1} 个节点类型不合法', code=400)

    try:
        workflow = WorkflowService.create_workflow(
            base_id=base_id_str,
            table_id=table_id,
            name=name,
            description=data.get('description'),
            created_by=user_id,
            trigger_config=trigger_config,
            nodes_config=nodes_config
        )
    except Exception as e:
        return error_response(f'创建工作流失败: {str(e)}', code=400)

    return success_response(
        data=workflow.to_dict(),
        message='工作流创建成功',
        code=201
    )


# ==================== 单个工作流操作 ====================

@workflows_bp.route('/workflows/<uuid:workflow_id>', methods=['GET'])
@jwt_required
def get_workflow(workflow_id) -> tuple:
    """
    获取工作流详情（含版本、节点、触发器）
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: workflow_id
        in: path
        type: string
        required: true
        description: 工作流 ID
    responses:
      200:
        description: 工作流详情
      403:
        description: 无权限
      404:
        description: 工作流不存在
    """
    user_id = g.current_user_id

    result = WorkflowService.get_workflow(workflow_id)
    if result is None:
        return not_found_response('工作流')

    if not _check_base_view_permission(result['workflow']['base_id'], user_id):
        return forbidden_response('您没有权限访问此工作流')

    return success_response(
        data=result,
        message='获取工作流详情成功'
    )


@workflows_bp.route('/workflows/<uuid:workflow_id>/nodes', methods=['GET'])
@jwt_required
def get_workflow_nodes(workflow_id) -> tuple:
    """
    获取工作流节点列表
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: workflow_id
        in: path
        type: string
        required: true
        description: 工作流 ID
    responses:
      200:
        description: 节点列表
      403:
        description: 无权限
      404:
        description: 工作流不存在
    """
    user_id = g.current_user_id

    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_view_permission(str(workflow.base_id), user_id):
        return forbidden_response('您没有权限访问此工作流')

    nodes = WorkflowNode.query.filter_by(
        workflow_id=workflow.id
    ).order_by(WorkflowNode.order).all()

    return success_response(
        data=[node.to_dict() for node in nodes],
        message='获取节点列表成功'
    )


@workflows_bp.route('/workflows/<uuid:workflow_id>/trigger', methods=['GET'])
@jwt_required
def get_workflow_trigger(workflow_id) -> tuple:
    """
    获取工作流触发器配置
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: workflow_id
        in: path
        type: string
        required: true
        description: 工作流 ID
    responses:
      200:
        description: 触发器配置
      403:
        description: 无权限
      404:
        description: 工作流不存在
    """
    user_id = g.current_user_id

    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_view_permission(str(workflow.base_id), user_id):
        return forbidden_response('您没有权限访问此工作流')

    trigger = WorkflowTrigger.query.filter_by(
        workflow_id=workflow.id
    ).first()

    return success_response(
        data=trigger.to_dict() if trigger else None,
        message='获取触发器成功'
    )


@workflows_bp.route('/workflows/<uuid:workflow_id>/nodes', methods=['PUT'])
@jwt_required
def update_workflow_nodes(workflow_id) -> tuple:
    """
    更新工作流节点列表（仅 draft 状态可编辑）
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: workflow_id
        in: path
        type: string
        required: true
        description: 工作流 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            nodes:
              type: array
              description: 节点配置列表
              items:
                type: object
    responses:
      200:
        description: 节点列表
      400:
        description: 参数错误或非 draft 状态
      403:
        description: 无权限
      404:
        description: 工作流不存在
    """
    user_id = g.current_user_id

    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_edit_permission(str(workflow.base_id), user_id):
        return forbidden_response('您没有权限修改此工作流')

    if workflow.status != WorkflowStatus.DRAFT:
        return bad_request_response('仅草稿状态可编辑节点')

    data = request.get_json() or {}
    nodes = data.get('nodes', [])

    # 前端使用的动作类型（update_record/create_record/send_email）非合法枚举值，
    # 需转换为 ACTION 节点 + config.action_type
    ACTION_TYPE_MAP = {
        'update_record': 'update_record',
        'create_record': 'create_record',
        'send_email': 'send_email',
        'trigger_webhook': 'trigger_webhook',
    }

    WorkflowNode.query.filter_by(workflow_id=workflow.id).delete()
    if nodes:
        for index, node_data in enumerate(nodes):
            node_type = node_data.get('node_type', 'action')
            node_config = dict(node_data.get('config', {}))

            # 转换前端动作类型为 ACTION 节点
            if node_type in ACTION_TYPE_MAP:
                node_config['action_type'] = ACTION_TYPE_MAP[node_type]
                node_type = 'action'

            node = WorkflowNode(
                workflow_id=workflow.id,
                node_type=WorkflowNodeType(node_type),
                name=node_data.get('name', f'节点 {index + 1}'),
                config=node_config,
                order=node_data.get('order', index),
                next_nodes=node_data.get('next_nodes', [])
            )
            db.session.add(node)

    db.session.commit()

    updated_nodes = WorkflowNode.query.filter_by(
        workflow_id=workflow.id
    ).order_by(WorkflowNode.order).all()

    return success_response(
        data=[node.to_dict() for node in updated_nodes],
        message='节点已更新'
    )


@workflows_bp.route('/workflows/<uuid:workflow_id>/trigger', methods=['PUT'])
@jwt_required
def update_workflow_trigger(workflow_id) -> tuple:
    """
    更新工作流触发器配置（仅 draft 状态可编辑）
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: workflow_id
        in: path
        type: string
        required: true
        description: 工作流 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            trigger_type:
              type: string
              description: 触发类型
            filter_config:
              type: object
              description: 过滤条件
            field_ids:
              type: array
              description: 监听字段 ID 列表
    responses:
      200:
        description: 触发器配置
      400:
        description: 参数错误或非 draft 状态
      403:
        description: 无权限
      404:
        description: 工作流不存在
    """
    user_id = g.current_user_id

    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_edit_permission(str(workflow.base_id), user_id):
        return forbidden_response('您没有权限修改此工作流')

    if workflow.status != WorkflowStatus.DRAFT:
        return bad_request_response('仅草稿状态可编辑触发器')

    data = request.get_json() or {}

    WorkflowTrigger.query.filter_by(workflow_id=workflow.id).delete()
    if data:
        trigger_type = data.get('trigger_type')
        trigger = WorkflowTrigger(
            workflow_id=workflow.id,
            trigger_type=WorkflowTriggerType(trigger_type) if trigger_type else WorkflowTriggerType.RECORD_CREATED,
            filter_config=data.get('filter_config', {}),
            field_ids=data.get('field_ids', [])
        )
        db.session.add(trigger)

    db.session.commit()

    updated_trigger = WorkflowTrigger.query.filter_by(
        workflow_id=workflow.id
    ).first()

    return success_response(
        data=updated_trigger.to_dict() if updated_trigger else None,
        message='触发器已更新'
    )


@workflows_bp.route('/workflows/<uuid:workflow_id>', methods=['PUT'])
@jwt_required
def update_workflow(workflow_id) -> tuple:
    """
    更新工作流（仅 draft 状态可编辑）
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: workflow_id
        in: path
        type: string
        required: true
        description: 工作流 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            name:
              type: string
              description: 工作流名称
            description:
              type: string
              description: 工作流描述
            trigger_config:
              type: object
              description: 触发器配置
            nodes_config:
              type: array
              description: 节点配置列表
              items:
                type: object
    responses:
      200:
        description: 更新后的工作流详情
      400:
        description: 参数错误或非 draft 状态
      403:
        description: 无权限
      404:
        description: 工作流不存在
    """
    user_id = g.current_user_id

    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_edit_permission(str(workflow.base_id), user_id):
        return forbidden_response('您没有权限修改此工作流')

    data = request.get_json() or {}

    kwargs = {}

    if 'name' in data:
        name = str(data['name']).strip()
        if not name:
            return error_response('工作流名称不能为空', code=400)
        if len(name) > 200:
            return error_response('工作流名称不能超过200个字符', code=400)
        kwargs['name'] = name

    if 'description' in data:
        kwargs['description'] = data['description']

    if 'table_id' in data:
        table_id = data['table_id']
        if table_id:
            kwargs['table_id'] = table_id
        else:
            return error_response('关联数据表不能为空', code=400)

    if 'trigger_config' in data:
        kwargs['trigger_config'] = data['trigger_config']

    if 'nodes_config' in data:
        nodes_config = data['nodes_config']
        if not isinstance(nodes_config, list):
            return error_response('nodes_config 必须是数组', code=400)
        for idx, node in enumerate(nodes_config):
            if not isinstance(node, dict):
                return error_response(f'第 {idx + 1} 个节点必须是对象', code=400)
            node_type = node.get('node_type')
            if node_type and node_type not in [t.value for t in WorkflowNodeType]:
                return error_response(f'第 {idx + 1} 个节点类型不合法', code=400)
        kwargs['nodes_config'] = nodes_config

    # 结构变更（节点/触发器）仅草稿状态可编辑
    has_structure_changes = 'trigger_config' in kwargs or 'nodes_config' in kwargs
    if has_structure_changes and workflow.status != WorkflowStatus.DRAFT:
        return error_response('仅 draft 状态的工作流可编辑节点和触发器', code=400)

    updated = WorkflowService.update_workflow(
        workflow_id=workflow_id,
        user_id=user_id,
        **kwargs
    )

    if updated is None:
        return error_response('更新失败', code=400)

    return success_response(
        data=updated.to_dict(),
        message='工作流更新成功'
    )


@workflows_bp.route('/workflows/<uuid:workflow_id>', methods=['DELETE'])
@jwt_required
def delete_workflow(workflow_id) -> tuple:
    """
    删除工作流（软删除）
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: workflow_id
        in: path
        type: string
        required: true
        description: 工作流 ID
    responses:
      200:
        description: 删除成功
      403:
        description: 无权限
      404:
        description: 工作流不存在
    """
    user_id = g.current_user_id

    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_edit_permission(str(workflow.base_id), user_id):
        return forbidden_response('您没有权限删除此工作流')

    success = WorkflowService.delete_workflow(workflow_id, user_id=user_id)
    if not success:
        return error_response('删除工作流失败', code=500)

    return success_response(message='工作流删除成功')


# ==================== 工作流状态管理 ====================

@workflows_bp.route('/workflows/<uuid:workflow_id>/publish', methods=['POST'])
@jwt_required
def publish_workflow(workflow_id) -> tuple:
    """
    发布工作流
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: workflow_id
        in: path
        type: string
        required: true
        description: 工作流 ID
    responses:
      200:
        description: 发布成功
      403:
        description: 无权限
      404:
        description: 工作流不存在
    """
    user_id = g.current_user_id

    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_edit_permission(str(workflow.base_id), user_id):
        return forbidden_response('您没有权限发布此工作流')

    published = WorkflowService.publish_workflow(workflow_id, created_by=user_id)
    if published is None:
        return error_response('发布工作流失败', code=400)

    result = WorkflowService.get_workflow(published.id)
    return success_response(
        data=result,
        message='工作流发布成功'
    )


@workflows_bp.route('/workflows/<uuid:workflow_id>/pause', methods=['POST'])
@jwt_required
def pause_workflow(workflow_id) -> tuple:
    """
    暂停工作流
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: workflow_id
        in: path
        type: string
        required: true
        description: 工作流 ID
    responses:
      200:
        description: 暂停成功
      403:
        description: 无权限
      404:
        description: 工作流不存在
    """
    user_id = g.current_user_id

    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_edit_permission(str(workflow.base_id), user_id):
        return forbidden_response('您没有权限暂停此工作流')

    paused = WorkflowService.pause_workflow(workflow_id, user_id=user_id)
    if paused is None:
        return error_response('暂停工作流失败', code=400)

    result = WorkflowService.get_workflow(paused.id)
    return success_response(
        data=result,
        message='工作流已暂停'
    )


@workflows_bp.route('/workflows/<uuid:workflow_id>/resume', methods=['POST'])
@jwt_required
def resume_workflow(workflow_id) -> tuple:
    """
    恢复工作流
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: workflow_id
        in: path
        type: string
        required: true
        description: 工作流 ID
    responses:
      200:
        description: 恢复成功
      403:
        description: 无权限
      404:
        description: 工作流不存在
    """
    user_id = g.current_user_id

    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_edit_permission(str(workflow.base_id), user_id):
        return forbidden_response('您没有权限恢复此工作流')

    resumed = WorkflowService.resume_workflow(workflow_id, user_id=user_id)
    if resumed is None:
        return error_response('恢复工作流失败', code=400)

    result = WorkflowService.get_workflow(resumed.id)
    return success_response(
        data=result,
        message='工作流已恢复'
    )


@workflows_bp.route('/workflows/<uuid:workflow_id>/clone', methods=['POST'])
@jwt_required
def clone_workflow(workflow_id) -> tuple:
    """
    基于现有工作流创建副本（草稿状态）
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: workflow_id
        in: path
        type: string
        required: true
        description: 工作流 ID
    responses:
      201:
        description: 克隆成功
      403:
        description: 无权限
      404:
        description: 工作流不存在
    """
    user_id = g.current_user_id

    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_edit_permission(str(workflow.base_id), user_id):
        return forbidden_response('您没有权限克隆此工作流')

    cloned = WorkflowService.clone_workflow(workflow_id, user_id=user_id)
    if cloned is None:
        return error_response('克隆工作流失败', code=400)

    return success_response(
        data=cloned.to_dict(),
        message='工作流克隆成功',
        code=201
    )


@workflows_bp.route('/workflows/<uuid:workflow_id>/versions', methods=['GET'])
@jwt_required
def get_workflow_versions(workflow_id) -> tuple:
    """
    获取工作流历史版本列表
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: workflow_id
        in: path
        type: string
        required: true
        description: 工作流 ID
    responses:
      200:
        description: 版本列表
      403:
        description: 无权限
      404:
        description: 工作流不存在
    """
    user_id = g.current_user_id

    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_view_permission(str(workflow.base_id), user_id):
        return forbidden_response('您没有权限访问此工作流')

    versions = WorkflowService.list_workflow_versions(workflow_id)
    return success_response(
        data=[v.to_dict() for v in versions],
        message='获取版本列表成功'
    )


# ==================== 工作流实例 ====================

@workflows_bp.route('/workflows/<uuid:workflow_id>/instances', methods=['GET'])
@jwt_required
def get_workflow_instances(workflow_id) -> tuple:
    """
    获取工作流执行实例列表
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: workflow_id
        in: path
        type: string
        required: true
        description: 工作流 ID
      - name: page
        in: query
        type: integer
        default: 1
        description: 页码
      - name: per_page
        in: query
        type: integer
        default: 20
        description: 每页数量
    responses:
      200:
        description: 实例列表（分页）
      403:
        description: 无权限
      404:
        description: 工作流不存在
    """
    user_id = g.current_user_id

    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_view_permission(str(workflow.base_id), user_id):
        return forbidden_response('您没有权限访问此工作流')

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 20
    if per_page > 500:
        per_page = 500

    query = WorkflowInstance.query.filter_by(
        workflow_id=workflow.id
    ).order_by(WorkflowInstance.started_at.desc())

    total = query.count()
    instances = query.offset((page - 1) * per_page).limit(per_page).all()

    items = [i.to_dict() for i in instances]

    return paginated_response(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        message='获取实例列表成功'
    )


@workflows_bp.route('/workflows/<uuid:workflow_id>/instances/<uuid:instance_id>', methods=['GET'])
@jwt_required
def get_workflow_instance(workflow_id, instance_id) -> tuple:
    """
    获取工作流实例详情（含执行日志轨迹）
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: workflow_id
        in: path
        type: string
        required: true
        description: 工作流 ID
      - name: instance_id
        in: path
        type: string
        required: true
        description: 实例 ID
    responses:
      200:
        description: 实例详情（含执行日志）
      403:
        description: 无权限
      404:
        description: 工作流或实例不存在
    """
    user_id = g.current_user_id

    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_view_permission(str(workflow.base_id), user_id):
        return forbidden_response('您没有权限访问此工作流')

    instance = WorkflowInstance.query.filter_by(
        id=WorkflowService._to_uuid(instance_id),
        workflow_id=workflow.id
    ).first()

    if not instance:
        return not_found_response('实例')

    execution_logs = instance.execution_logs.all()

    return success_response(
        data={
            'instance': instance.to_dict(),
            'execution_logs': [log.to_dict() for log in execution_logs]
        },
        message='获取实例详情成功'
    )


# ==================== 手动触发 ====================

@workflows_bp.route('/tables/<table_id>/records/<record_id>/trigger', methods=['POST'])
@jwt_required
def trigger_record_workflow(table_id, record_id) -> tuple:
    """
    手动触发工作流
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    parameters:
      - name: table_id
        in: path
        type: string
        required: true
        description: 表格 ID
      - name: record_id
        in: path
        type: string
        required: true
        description: 记录 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            workflow_id:
              type: string
              description: 要触发的工作流 ID（不提供则返回可手动触发的工作流列表）
    responses:
      200:
        description: 可手动触发的工作流列表或触发结果
      400:
        description: 参数错误
      403:
        description: 无权限
      404:
        description: 记录或工作流不存在
    """
    user_id = g.current_user_id

    table = TableService.get_table_by_id(str(table_id))
    if not table:
        return error_response('表格不存在', code=404)

    base_id = str(table.base_id)

    if not _check_base_edit_permission(base_id, user_id):
        return forbidden_response('您没有权限触发此记录的工作流')

    record = RecordService.get_record_by_id(str(record_id))
    if not record:
        return error_response('记录不存在', code=404)

    if str(record.table_id) != str(table_id):
        return error_response('记录不属于该表格', code=400)

    # 查询可手动触发的工作流：active 状态且触发器类型为 manual
    manual_triggers = WorkflowTrigger.query.join(Workflow).filter(
        Workflow.table_id == WorkflowService._to_uuid(table_id),
        Workflow.status == WorkflowStatus.ACTIVE,
        Workflow.is_deleted == False,
        WorkflowTrigger.trigger_type == WorkflowTriggerType.MANUAL
    ).all()

    available_workflows = [
        {
            'workflow_id': str(t.workflow_id),
            'workflow': t.workflow.to_dict()
        }
        for t in manual_triggers
    ]

    data = request.get_json() or {}
    workflow_id = data.get('workflow_id')

    # 未提供 workflow_id，返回可触发列表
    if not workflow_id:
        return success_response(
            data={
                'available_workflows': available_workflows
            },
            message='获取可手动触发的工作流列表成功'
        )

    # 触发指定工作流
    target_workflow = None
    for trigger in manual_triggers:
        if str(trigger.workflow_id) == str(workflow_id):
            target_workflow = trigger.workflow
            break

    if not target_workflow:
        return error_response('指定的工作流不存在或不可手动触发', code=404)

    event = WorkflowEvent(
        event_type=WorkflowTriggerType.MANUAL.value,
        table_id=str(table_id),
        record_id=str(record_id),
        actor_id=str(user_id),
        metadata={'workflow_source': 'manual_api'}
    )

    instance = workflow_execution_engine.start_instance(target_workflow, event)
    if not instance:
        return error_response('触发工作流失败，请稍后重试', code=500)

    workflow_execution_engine.executor.submit(
        workflow_execution_engine._run_instance,
        str(instance.id)
    )

    return success_response(
        data={
            'instance_id': str(instance.id),
            'workflow_id': str(target_workflow.id),
            'version_number': instance.version_number
        },
        message='工作流触发成功'
    )
