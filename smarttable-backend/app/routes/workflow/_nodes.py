# Auto-split from workflows.py

"""子蓝图模块"""

from app.routes.workflow import workflows_bp


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
        return forbidden_response('no_permission_access_workflow')

    nodes = WorkflowNode.query.filter_by(
        workflow_id=workflow.id
    ).order_by(WorkflowNode.order).all()

    return success_response(
        data=[node.to_dict() for node in nodes],
        message='fetched_node_list_successfully'
    )

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
        return forbidden_response('no_permission_access_workflow')

    trigger = WorkflowTrigger.query.filter_by(
        workflow_id=workflow.id
    ).first()

    return success_response(
        data=trigger.to_dict() if trigger else None,
        message='fetched_trigger_successfully'
    )

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
        return forbidden_response('do_not_permission_modify_workflow')

    if workflow.status not in (WorkflowStatus.DRAFT, WorkflowStatus.PAUSED):
        return bad_request_response('workflows_draft_paused_status_edit_nodes')

    data = request.get_json() or {}
    nodes = data.get('nodes', [])

    # 前端使用的细粒度类型（find_records/send_email/update_record/create_record/trigger_webhook）
    # 现在直接作为 WorkflowNodeType 枚举值存储，不再转换为 ACTION + config.action_type。
    # 保留对旧 'action' 类型的兼容：若前端传入 'action'，仍按 config.action_type 反查细粒度类型。
    _ACTION_TYPE_UPGRADE = {
        'update_record': 'update_record',
        'create_record': 'create_record',
        'send_email': 'send_email',
        'trigger_webhook': 'trigger_webhook',
        'find_records': 'find_records',
    }

    WorkflowNode.query.filter_by(workflow_id=workflow.id).delete()

    # 前端传入的节点 id 是字符串（如 node_xxx），而数据库使用 UUID，
    # 因此需要建立映射并在保存 next_nodes 时替换为后端生成的 UUID。
    frontend_to_backend_id: dict[str, Any] = {}
    created_nodes: list[WorkflowNode] = []

    if nodes:
        # 第一轮：创建节点并建立 id 映射
        for index, node_data in enumerate(nodes):
            node_type = node_data.get('node_type', 'action')
            node_config = dict(node_data.get('config', {}))

            # 将旧的 'action' + config.action_type 升级为细粒度 node_type
            if node_type == 'action':
                action_type = node_config.get('action_type')
                if action_type and action_type in _ACTION_TYPE_UPGRADE:
                    node_type = _ACTION_TYPE_UPGRADE[action_type]

            node = WorkflowNode(
                workflow_id=workflow.id,
                node_type=WorkflowNodeType(node_type),
                name=node_data.get('name', f'节点 {index + 1}'),
                config=node_config,
                order=node_data.get('order', index),
                next_nodes=[],
                ui_layout=node_data.get('ui_layout', {})
            )
            db.session.add(node)
            db.session.flush()
            created_nodes.append(node)
            frontend_id = node_data.get('id')
            if frontend_id:
                frontend_to_backend_id[str(frontend_id)] = node.id

        def _remap_ids(obj, id_map):
            """递归将对象中所有可映射的前端 id 替换为后端 UUID。

            处理范围：
            - next_nodes 列表中的节点 ID
            - 条件分支 branches[].target_node_id
            - 循环节点 config.data_source.node_id
            - 循环节点 config.loop_body_nodes 中每个子节点的 id、next_nodes 及嵌套 config
            """
            if not isinstance(obj, dict):
                return obj
            result = dict(obj)

            # next_nodes
            next_nodes = result.get('next_nodes')
            if isinstance(next_nodes, list):
                result['next_nodes'] = [
                    str(id_map[str(nid)]) for nid in next_nodes if str(nid) in id_map
                ]

            # 条件分支 target_node_id
            branches = result.get('branches')
            if isinstance(branches, list):
                updated_branches = []
                for branch in branches:
                    updated_branch = dict(branch)
                    target_id = updated_branch.get('target_node_id')
                    if target_id and str(target_id) in id_map:
                        updated_branch['target_node_id'] = str(id_map[str(target_id)])
                    updated_branches.append(updated_branch)
                result['branches'] = updated_branches

            # 循环节点 data_source.node_id
            data_source = result.get('data_source')
            if isinstance(data_source, dict):
                ds_node_id = data_source.get('node_id')
                if ds_node_id and str(ds_node_id) in id_map:
                    result['data_source'] = {
                        **data_source,
                        'node_id': str(id_map[str(ds_node_id)]),
                    }

            # 循环节点 loop_body_nodes（递归处理子节点）
            loop_body_nodes = result.get('loop_body_nodes')
            if isinstance(loop_body_nodes, list):
                result['loop_body_nodes'] = [
                    _remap_ids(body_node, id_map) for body_node in loop_body_nodes
                ]

            return result

        # 第二轮：根据映射把 next_nodes、条件分支、data_source、loop_body_nodes
        # 里的前端 id 替换为后端 UUID
        for node_data, node in zip(nodes, created_nodes):
            node_config = _remap_ids(node_data.get('config', {}), frontend_to_backend_id)
            next_nodes = node_data.get('next_nodes', [])
            node.next_nodes = [
                str(frontend_to_backend_id[str(nid)])
                for nid in next_nodes
                if str(nid) in frontend_to_backend_id
            ]
            node.config = node_config

    db.session.commit()

    updated_nodes = WorkflowNode.query.filter_by(
        workflow_id=workflow.id
    ).order_by(WorkflowNode.order).all()

    return success_response(
        data=[node.to_dict() for node in updated_nodes],
        message='node_updated'
    )

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
        return forbidden_response('do_not_permission_modify_workflow')

    if workflow.status not in (WorkflowStatus.DRAFT, WorkflowStatus.PAUSED):
        return bad_request_response('workflows_draft_paused_status_edit_triggers')

    data = request.get_json() or {}

    WorkflowTrigger.query.filter_by(workflow_id=workflow.id).delete()
    if data:
        trigger_type = data.get('trigger_type')
        trigger = WorkflowTrigger(
            workflow_id=workflow.id,
            trigger_type=WorkflowTriggerType(trigger_type) if trigger_type else WorkflowTriggerType.RECORD_CREATED,
            filter_config=WorkflowService._clean_filter_config(data.get('filter_config', {})),
            field_ids=data.get('field_ids', [])
        )
        db.session.add(trigger)

    db.session.commit()

    updated_trigger = WorkflowTrigger.query.filter_by(
        workflow_id=workflow.id
    ).first()

    return success_response(
        data=updated_trigger.to_dict() if updated_trigger else None,
        message='trigger_updated'
    )

def update_workflow(workflow_id) -> tuple:
    """
    更新工作流（名称/描述任意状态可编辑，数据表/节点/触发器仅 draft 可编辑）
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
            table_id:
              type: string
              description: 关联数据表 ID（仅 draft 可变更）
            trigger_config:
              type: object
              description: 触发器配置（仅 draft 可编辑）
            nodes_config:
              type: array
              description: 节点配置列表（仅 draft 可编辑）
              items:
                type: object
    responses:
      200:
        description: 更新后的工作流详情
      400:
        description: 参数错误或尝试在非 draft 状态变更数据表/节点/触发器
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
        return forbidden_response('do_not_permission_modify_workflow')

    data = request.get_json() or {}

    kwargs = {}

    if 'name' in data:
        name = str(data['name']).strip()
        if not name:
            return error_response('workflow_name_empty', code=400)
        if len(name) > 200:
            return error_response('workflow_name_exceed_characters', code=400)
        kwargs['name'] = name

    if 'description' in data:
        kwargs['description'] = data['description']

    if 'table_id' in data:
        table_id = data['table_id']
        if table_id:
            kwargs['table_id'] = table_id
        else:
            return error_response('linked_data_table_empty', code=400)

    if 'trigger_config' in data:
        kwargs['trigger_config'] = data['trigger_config']

    if 'nodes_config' in data:
        nodes_config = data['nodes_config']
        if not isinstance(nodes_config, list):
            return error_response('nodes_config_array', code=400)
        for idx, node in enumerate(nodes_config):
            if not isinstance(node, dict):
                return error_response(translate('node_must_be_object', idx + 1), code=400)
            node_type = node.get('node_type')
            if node_type and node_type not in [t.value for t in WorkflowNodeType]:
                return error_response(translate('node_type_invalid', idx + 1), code=400)
        kwargs['nodes_config'] = nodes_config

    # 关联数据表仅草稿状态可变更
    if 'table_id' in kwargs and workflow.status != WorkflowStatus.DRAFT:
        return error_response('workflows_draft_status_change_linked_data_table', code=400)

    # 结构变更（节点/触发器）仅草稿状态可编辑
    has_structure_changes = 'trigger_config' in kwargs or 'nodes_config' in kwargs
    if has_structure_changes and workflow.status != WorkflowStatus.DRAFT:
        return error_response('workflows_draft_status_edit_nodes_triggers', code=400)

    updated = WorkflowService.update_workflow(
        workflow_id=workflow_id,
        user_id=user_id,
        **kwargs
    )

    if updated is None:
        return error_response('update_failed', code=400)

    result = WorkflowService.get_workflow(updated.id)
    return success_response(
        data=result['workflow'],
        message='workflow_updated_successfully'
    )

def _get_workflow_or_404(workflow_id):
    """获取工作流，不存在时返回 404"""
    workflow = Workflow.query.filter_by(
        id=WorkflowService._to_uuid(workflow_id),
        is_deleted=False
    ).first()
    if not workflow:
        return None, not_found_response('workflow')
    return workflow, None

def _check_base_edit_permission(base_id, user_id):
    """检查 ADMIN 权限（工作流管理需要管理员及以上角色）"""
    return PermissionService.check_permission(
        base_id=str(base_id),
        user_id=str(user_id),
        min_role=MemberRole.ADMIN
    )

def _check_base_view_permission(base_id, user_id):
    """检查 VIEWER 权限"""
    return PermissionService.check_permission(
        base_id=str(base_id),
        user_id=str(user_id),
        min_role=MemberRole.VIEWER
    )

def _to_str(value):
    """将 UUID 或字符串统一为字符串"""
    return str(value) if value is not None else None
