# Auto-split from workflows.py

"""子蓝图模块"""

from app.routes.workflow import workflows_bp


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
        return forbidden_response('no_permission_access_workflow')

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
        message='fetched_instance_list_successfully'
    )

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
        return forbidden_response('no_permission_access_workflow')

    instance = WorkflowInstance.query.filter_by(
        id=WorkflowService._to_uuid(instance_id),
        workflow_id=workflow.id
    ).first()

    if not instance:
        return not_found_response('instance')

    execution_logs = instance.execution_logs.all()

    return success_response(
        data={
            'instance': instance.to_dict(),
            'execution_logs': [log.to_dict() for log in execution_logs]
        },
        message='fetched_instance_details_successfully'
    )

def get_instance_webhook_deliveries(workflow_id, instance_id) -> tuple:
    """
    获取工作流实例的 Webhook 投递日志
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
        description: Webhook 投递日志列表
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
        return forbidden_response('no_permission_access_workflow')

    instance = WorkflowInstance.query.filter_by(
        id=WorkflowService._to_uuid(instance_id),
        workflow_id=workflow.id
    ).first()

    if not instance:
        return not_found_response('instance')

    # 查询该实例的所有 Webhook 投递日志（包括内联 webhook）
    delivery_logs = WebhookDeliveryLog.query.filter_by(
        instance_id=instance.id
    ).order_by(WebhookDeliveryLog.created_at.desc()).all()

    return success_response(
        data=[log.to_dict() for log in delivery_logs],
        message='fetched_webhook_delivery_logs_successfully'
    )

def get_record_time_scanner_stats() -> tuple:
    """
    获取"到达记录中的时间"扫描器的运行统计
    ---
    tags:
      - Workflows
    security:
      - Bearer: []
    responses:
      200:
        description: 扫描器统计信息
        schema:
          properties:
            last_scan_at:
              type: string
              description: 最近一次扫描时间（本地时区 ISO 格式）
            last_scan_utc:
              type: string
              description: 最近一次扫描时间（UTC ISO 格式）
            scanned_workflows:
              type: integer
              description: 最近一次扫描的工作流数量
            triggered_instances:
              type: integer
              description: 最近一次扫描触发的实例数量
            errors:
              type: integer
              description: 最近一次扫描的错误数
            last_error:
              type: string
              description: 最近一次错误信息
    """
    from app.services.workflow_record_time_scanner import get_scan_stats, SCAN_INTERVAL_SECONDS
    from app.services.workflow_scheduler_service import scheduler
    from datetime import datetime, timezone

    stats = get_scan_stats()
    # 附加调度器状态
    stats['scheduler_running'] = bool(scheduler and scheduler.running)
    stats['scan_interval_seconds'] = SCAN_INTERVAL_SECONDS
    stats['server_time_utc'] = datetime.now(timezone.utc).isoformat()
    stats['server_time_local'] = datetime.now().astimezone().isoformat()

    return success_response(data=stats)
