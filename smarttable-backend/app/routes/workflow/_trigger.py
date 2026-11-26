# Auto-split from workflows.py

"""子蓝图模块"""

from app.routes.workflow import workflows_bp


def test_script_node(workflow_id) -> tuple:
    """
    测试执行脚本节点（不持久化、不产生工作流实例与执行日志）
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
            language:
              type: string
              enum: [python]
            script_source:
              type: string
            sample_input:
              description: 模拟上游节点输出
            timeout:
              type: integer
    responses:
      200:
        description: 执行结果（含 status/result/branch/error/duration_ms/stdout）
      400:
        description: 参数错误
      403:
        description: 无权限
      404:
        description: 工作流不存在
    """
    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_edit_permission(str(workflow.base_id), g.current_user_id):
        return forbidden_response('do_not_permission_modify_workflow')

    data = request.get_json() or {}
    language = data.get('language')
    script_source = data.get('script_source', '')
    sample_input = data.get('sample_input')
    timeout = data.get('timeout', 30)

    # 基本参数校验
    if language != 'python':
        return {'error': "language_python"}, 400
    if not script_source or not isinstance(script_source, str):
        return {'error': 'script_content_empty'}, 400
    try:
        timeout = int(timeout)
        if timeout < 1 or timeout > 300:
            raise ValueError()
    except (TypeError, ValueError):
        return {'error': 'timeout_positive_integer_between'}, 400

    from app.services.script_execution_service import ScriptExecutionService

    # 测试执行：仅提供最小上下文，不写实例与日志
    context = {
        'trigger': {},
        'record': {},
        'instance': {},
        'workflow': {},
        'loop': None,
        'node_outputs': {},
    }
    result = ScriptExecutionService.execute(
        language=language,
        script_source=script_source,
        input_data=sample_input,
        context=context,
        timeout=timeout,
    )
    # 即使脚本执行失败也返回 200：API 调用本身成功，失败信息在 body 的 status/error 字段
    return result, 200

def test_ai_node(workflow_id) -> tuple:
    """
    试运行 AI 节点（P2-8，D7；不持久化、不产生工作流实例与执行日志，
    真实 LLM 调用照常配额计量 + 审计）
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
            prompt_template:
              type: string
              description: prompt 模板（支持 {{record.xxx}} 等占位符）
            system_prompt:
              type: string
            json_output:
              type: boolean
              description: 是否要求 JSON 输出（json_mode 路由与宽松解析同生产节点）
            sample_context:
              type: object
              description: 模拟渲染上下文（trigger/record/node_outputs/loop 等）
    responses:
      200:
        description: 执行结果（status/result 含 text/json/rendered_prompt/duration_ms）
      400:
        description: 参数错误
      403/429/502/503:
        description: 功能未开/配额超限/生成失败/无可用模型
    """
    import time as _time

    workflow, error = _get_workflow_or_404(workflow_id)
    if error:
        return error

    if not _check_base_edit_permission(str(workflow.base_id), g.current_user_id):
        return forbidden_response('do_not_permission_modify_workflow')

    data = request.get_json() or {}
    prompt_template = (data.get('prompt_template') or '').strip()
    system_prompt = data.get('system_prompt') or ''
    json_output = bool(data.get('json_output'))
    sample_context = data.get('sample_context')
    if not isinstance(sample_context, dict):
        sample_context = {}

    if not prompt_template:
        return {'error': 'ai_node_prompt_required'}, 400

    try:
        from app.services.ai.ai_config_service import AIConfigService
    except ImportError:
        AIConfigService = None
    try:
        from app.services.ai.audit_logger import AI_FEATURE_WORKFLOW, log_ai_call
    except ImportError:
        AI_FEATURE_WORKFLOW = None
        log_ai_call = None
    try:
        from app.services.ai.quota_service import QuotaService
    except ImportError:
        QuotaService = None

    # 功能开关 + 模型可用性（对齐 insight/doc 的治理前置检查）
    if not AIConfigService.is_feature_enabled('workflow_ai'):
        return {'error': 'AI_FEATURE_DISABLED',
                'message': '工作流 AI 功能未开启'}, 403
    manager = AIConfigService.get_manager()
    if manager.resolve('batch') is None:
        return {'error': 'AI_NO_MODEL',
                'message': '没有可用的 AI 模型，请联系管理员配置'}, 503

    user_id = str(g.current_user_id)
    base_id = str(workflow.base_id)
    try:
        quota_info = QuotaService.check_and_consume(user_id, base_id=base_id,
                                                    calls=1)
    except Exception as e:  # noqa: BLE001 —— 配额超限/Redis 不可用
        code = getattr(e, 'error_code', 'AI_QUOTA_EXCEEDED')
        return {'error': code, 'message': str(e)}, 429
    quota_remaining = (quota_info or {}).get('quota_remaining')

    # 渲染：最小上下文 + 前端样例覆盖（变量名与生产渲染上下文一致）
    context = {
        'trigger': {},
        'record': {},
        'instance': {},
        'workflow': {},
        'loop': None,
        'node_outputs': {},
    }
    for key in ('trigger', 'record', 'node_outputs', 'loop',
                'instance', 'workflow'):
        if sample_context.get(key) is not None:
            context[key] = sample_context[key]

    prompt = workflow_execution_engine.render_template(prompt_template, context)
    rendered_system = (workflow_execution_engine.render_template(
        system_prompt, context) if system_prompt else '')

    messages = []
    if rendered_system:
        messages.append({'role': 'system', 'content': rendered_system})
    messages.append({'role': 'user', 'content': prompt})

    # json_output 路由与降级：与生产 _execute_ai_node 保持一致
    response_format = None
    if json_output and manager.resolve('batch', capability='json_mode') is not None:
        response_format = {'type': 'json_object'}
    elif json_output:
        prompt = prompt + '\n\n请仅输出一个合法的 JSON 对象或数组，不要包含任何其他文字或代码块标记。'
        messages[-1]['content'] = prompt

    started = _time.monotonic()
    result = None
    run_error = None
    parsed = None
    try:
        result = manager.chat(
            'batch', messages,
            capability='json_mode' if response_format else None,
            **({'response_format': response_format} if response_format else {}))
        if json_output:
            parsed = workflow_execution_engine._parse_json_output(result.content)
    except Exception as e:  # noqa: BLE001 —— 统一包装为 502
        run_error = e

    duration_ms = int((_time.monotonic() - started) * 1000)
    usage_dict = (getattr(result, 'usage', None) or {}) if result is not None else {}
    prompt_tokens = int(usage_dict.get('prompt_tokens') or 0)
    completion_tokens = int(usage_dict.get('completion_tokens') or 0)
    try:
        if prompt_tokens or completion_tokens:
            QuotaService.consume_tokens(
                user_id, base_id=base_id,
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    except Exception:  # noqa: BLE001 —— token 计量 best-effort
        logger.warning('AI token 计量失败（AI 节点试运行）', exc_info=True)
    log_ai_call(
        feature=AI_FEATURE_WORKFLOW, user_id=user_id, base_id=base_id,
        status='success' if run_error is None else 'error',
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
        usage_estimated=bool(getattr(result, 'usage_estimated', False)),
        input_summary=prompt,
        output_summary=(getattr(result, 'content', '') or '')[:500] if result else '',
        duration_ms=duration_ms,
        error=None if run_error is None else {
            'kind': 'workflow_ai_test', 'message': str(run_error)},
    )
    if run_error is not None:
        return {'error': 'AI_GENERATE_FAILED',
                'message': f'AI 生成失败：{str(run_error)[:200]}'}, 502

    return {
        'status': 'success',
        'result': {
            'result': parsed if json_output else result.content,
            'text': result.content,
            'json': parsed,
            'json_output': json_output,
            'duration_ms': duration_ms,
            'rendered_prompt': prompt,
            'rendered_system_prompt': rendered_system,
        },
        'quota_remaining': quota_remaining,
    }, 200

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
        return error_response('table_does_not_exist', code=404)

    base_id = str(table.base_id)

    if not _check_base_edit_permission(base_id, user_id):
        return forbidden_response('do_not_permission_trigger_workflow_record')

    record = RecordService.get_record_by_id(str(record_id))
    if not record:
        return error_response('record_does_not_exist', code=404)

    if str(record.table_id) != str(table_id):
        return error_response('record_does_not_belong_table', code=400)

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
            message='fetched_manually_triggerable_workflow_list_successfully'
        )

    # 触发指定工作流
    target_workflow = None
    for trigger in manual_triggers:
        if str(trigger.workflow_id) == str(workflow_id):
            target_workflow = trigger.workflow
            break

    if not target_workflow:
        return error_response('specified_workflow_does_not_exist_manually_triggered', code=404)

    event = WorkflowEvent(
        event_type=WorkflowTriggerType.MANUAL.value,
        table_id=str(table_id),
        record_id=str(record_id),
        actor_id=str(user_id),
        metadata={'workflow_source': 'manual_api'}
    )

    instance = workflow_execution_engine.start_instance(target_workflow, event)
    if not instance:
        return error_response('failed_trigger_workflow_try_again_later', code=500)

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
        message='workflow_triggered_successfully'
    )
