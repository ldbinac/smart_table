# Auto-split from workflows.py

"""子蓝图模块"""

from app.routes.workflow import workflows_bp


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
        return forbidden_response('no_permission_access_base')

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
        message='fetched_workflow_list_successfully'
    )

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
            - table_id
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
        return forbidden_response('do_not_permission_create_workflow_base')

    data = request.get_json() or {}

    name = data.get('name', '').strip()
    if not name:
        return error_response('workflow_name_empty', code=400)
    if len(name) > 200:
        return error_response('workflow_name_exceed_characters', code=400)

    table_id = data.get('table_id')
    if not table_id:
        return error_response('select_linked_data_table', code=400)

    table = TableService.get_table_by_id(str(table_id))
    if not table or str(table.base_id) != base_id_str:
        return error_response('linked_table_does_not_exist_does_not_belong_current_base', code=400)

    trigger_config = data.get('trigger_config')
    nodes_config = data.get('nodes_config')

    # 简单校验节点配置
    if nodes_config is not None:
        if not isinstance(nodes_config, list):
            return error_response('nodes_config_array', code=400)
        for idx, node in enumerate(nodes_config):
            if not isinstance(node, dict):
                return error_response(translate('node_must_be_object', idx + 1), code=400)
            node_type = node.get('node_type')
            if node_type and node_type not in [t.value for t in WorkflowNodeType]:
                return error_response(translate('node_type_invalid', idx + 1), code=400)

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
        return error_response(translate('workflow_creation_failed', str(e)), code=400)

    return success_response(
        data=workflow.to_dict(),
        message='workflow_created_successfully',
        code=201
    )

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
        return not_found_response('workflow')

    if not _check_base_view_permission(result['workflow']['base_id'], user_id):
        return forbidden_response('no_permission_access_workflow')

    return success_response(
        data=result,
        message='fetched_workflow_details_successfully'
    )

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
        return forbidden_response('do_not_permission_delete_workflow')

    success = WorkflowService.delete_workflow(workflow_id, user_id=user_id)
    if not success:
        return error_response('failed_delete_workflow', code=500)

    return success_response(message='workflow_deleted_successfully')

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
        return forbidden_response('do_not_permission_publish_workflow')

    try:
        published = WorkflowService.publish_workflow(workflow_id, created_by=user_id)
    except ValueError as e:
        return bad_request_response(str(e))

    if published is None:
        return error_response('failed_publish_workflow', code=400)

    result = WorkflowService.get_workflow(published.id)
    return success_response(
        data=result,
        message='workflow_published_successfully'
    )

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
        return forbidden_response('do_not_permission_clone_workflow')

    cloned = WorkflowService.clone_workflow(workflow_id, user_id=user_id)
    if cloned is None:
        return error_response('failed_clone_workflow', code=400)

    return success_response(
        data=cloned.to_dict(),
        message='workflow_cloned_successfully',
        code=201
    )

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
        return forbidden_response('no_permission_access_workflow')

    versions = WorkflowService.list_workflow_versions(workflow_id)
    return success_response(
        data=[v.to_dict() for v in versions],
        message='fetched_version_list_successfully'
    )

def save_workflow_snapshot(workflow_id) -> tuple:
    """
    为暂停状态的工作流保存版本快照
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
    responses:
      200:
        description: 版本快照保存成功（或无变更跳过）
      400:
        description: 工作流不存在或非暂停状态
    """
    user_id = g.current_user_id

    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_edit_permission(str(workflow.base_id), user_id):
        return forbidden_response('do_not_permission_modify_workflow')

    try:
        version = WorkflowService.save_version_snapshot(workflow_id, created_by=user_id)
    except ValueError as e:
        return bad_request_response(str(e))

    if version is None:
        return success_response(
            data=None,
            message='no_content_changes_skipping_version_snapshot_creation'
        )

    return success_response(
        data=version.to_dict(),
        message=translate('version_snapshot_saved', version.version_number)
    )

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
        return forbidden_response('do_not_permission_pause_workflow')

    paused = WorkflowService.pause_workflow(workflow_id, user_id=user_id)
    if paused is None:
        return error_response('failed_pause_workflow', code=400)

    result = WorkflowService.get_workflow(paused.id)
    return success_response(
        data=result,
        message='workflow_paused'
    )

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
        return forbidden_response('do_not_permission_resume_workflow')

    resumed = WorkflowService.resume_workflow(workflow_id, user_id=user_id)
    if resumed is None:
        return error_response('failed_resume_workflow', code=400)

    result = WorkflowService.get_workflow(resumed.id)
    return success_response(
        data=result,
        message='workflow_resumed'
    )
