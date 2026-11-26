import html
import json
import logging
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

from app.i18n import translate
from app.extensions import db
from app.models.webhook import WebhookConfig
from app.models.record import Record
from app.models.table import Table
from app.models.workflow import Workflow, WorkflowNode, WorkflowNodeType
from app.models.workflow_instance import (
    WorkflowInstance,
    WorkflowExecutionLog,
    WorkflowInstanceStatus,
)
from app.services.email_queue_service import email_queue
from app.services.record_service import RecordService
from app.services.workflow_event_bus import workflow_event_bus, WorkflowEvent

log = logging.getLogger(__name__)

class WorkflowScriptAIWebhookMixin:
    """WorkflowScriptAIWebhookMixin — 8 个方法"""

    def _execute_script_node(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行自定义脚本节点"""
        from app.services.script_execution_service import ScriptExecutionService

        config = node.config or {}
        language = config.get('language', 'python')
        script_source = config.get('script_source', '')
        timeout = config.get('timeout', 30)
        result_variable = config.get('result_variable', 'script_result') or 'script_result'
        input_node_id = config.get('input_node_id')
        branches = config.get('branches', []) or []

        # 解析输入
        input_data = self._resolve_script_input(instance, node, input_node_id)

        # 构建上下文（复用渲染上下文）
        context = self._build_render_context(instance)

        # 调用沙箱执行
        exec_result = ScriptExecutionService.execute(
            language=language,
            script_source=script_source,
            input_data=input_data,
            context=context,
            timeout=timeout,
        )

        # 失败处理
        if exec_result.get('status') == 'error':
            error_msg = exec_result.get('error', '脚本执行失败')
            traceback_info = exec_result.get('traceback')
            if traceback_info:
                error_msg = f'{error_msg}\n--- traceback ---\n{traceback_info}'
            return {
                'status': 'error',
                'error_message': error_msg,
                'result': None,
                'next_nodes': node.next_nodes or [],
            }

        result_value = exec_result.get('result')
        branch_label = exec_result.get('branch')

        # 写入 instance.context（仅写结果变量；node_outputs 由 execute_node 统一写入）
        ctx = instance.context or {}
        ctx[result_variable] = result_value
        instance.context = ctx
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(instance, 'context')
        db.session.commit()

        # 分支路由
        next_nodes = self._resolve_script_branch(node, branches, branch_label)

        return {
            'result': {
                'result': result_value,
                'branch': branch_label,
                'duration_ms': exec_result.get('duration_ms', 0),
            },
            'next_nodes': next_nodes,
        }

    def _resolve_script_input(self, instance: WorkflowInstance, node: WorkflowNode, input_node_id) -> Any:
        """解析脚本节点的输入数据。

        注意：上下文中 node_outputs[id] 写入的是已展开的上游输出
        （见 execute_node 中仅写入 dispatch result 的 result 部分，无外层 'result' 包裹）。
        因此此处直接返回该输出，不再二次解包 .get('result')，
        否则当输出本身没有 'result' 键（如 find_records 的 {'count','records'}）时会取到 None。
        """
        ctx = instance.context or {}
        node_outputs = ctx.get('node_outputs') or {}

        # 找前驱节点（next_nodes 包含当前节点 id 的节点）
        all_nodes = WorkflowNode.query.filter_by(workflow_id=node.workflow_id).all()
        predecessors = []
        for n in all_nodes:
            if str(node.id) in [str(nid) for nid in (n.next_nodes or [])]:
                predecessors.append(n)

        if input_node_id:
            # 指定输入节点：返回其已展开的输出
            return node_outputs.get(str(input_node_id))
        elif len(predecessors) == 1:
            # 单一前驱：返回其已展开的输出
            return node_outputs.get(str(predecessors[0].id))
        elif len(predecessors) > 1:
            # 多前驱：返回 {node_id: output_result} 字典
            return {
                str(p.id): node_outputs.get(str(p.id))
                for p in predecessors
            }
        else:
            return None

    def _resolve_script_branch(self, node: WorkflowNode, branches: list, branch_label) -> list:
        """根据脚本返回的 branch label 解析 next_nodes"""
        if not branch_label:
            return node.next_nodes or []
        for b in branches:
            if isinstance(b, dict) and b.get('label') == branch_label:
                target = b.get('target_node_id')
                if target:
                    return [target]
        # label 未匹配，记录警告并回退默认顺序流
        log.warning(f'[WorkflowExecutionEngine] 脚本分支标签 {branch_label} 未匹配，使用默认顺序流')
        return node.next_nodes or []

    def _execute_ai_node(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行 AI 节点（02 文档 §3.4 D1-D6）。

        流程：渲染 prompt（trigger/record/loop/node_outputs 均可引用）→
        配额预扣（以工作流所有者计）→ LLM 调用（json_output 时按 json_mode 能力路由，
        缺失降级为结构化 prompt + 宽松解析）→ 审计（AICallLog feature=workflow）+ token 计量。

        失败/解析失败抛异常，由 execute_node 包装按 config.max_retries 重试、
        按 config.continue_on_error 决定是否中断实例；每次重试均为真实 LLM 调用，独立预扣配额。
        """
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

        # P1 修复：生产执行路径同样受 A5 功能开关约束（与试运行端点一致）；
        # 关闭时按 continue_on_error 语义抛错，由 execute_node 包装处理
        if not AIConfigService.is_feature_enabled('workflow_ai'):
            raise ValueError('AI workflow 功能未开启（AI_FEATURE_DISABLED）')

        config = node.config or {}
        prompt_template = (config.get('prompt_template') or '').strip()
        if not prompt_template:
            raise ValueError(translate('ai_node_prompt_required'))

        # 1. 渲染 prompt（整体命中返回原始值；否则 {{...}} 字符串替换）
        context = self._build_render_context(instance)
        prompt = self.render_template(prompt_template, context)
        system_prompt = self.render_template(config.get('system_prompt') or '', context)

        messages: List[dict] = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})

        workflow = Workflow.query.get(instance.workflow_id)
        quota_user = str(workflow.created_by) if workflow and workflow.created_by else None
        base_id = str(workflow.base_id) if workflow else None

        # 2. 配额预扣（H2；超限抛 QuotaExceededError，Redis 不可用 fail-closed）
        QuotaService.check_and_consume(quota_user, base_id=base_id, calls=1)

        # 3. LLM 调用（D1/P2 修复：config.model_usage 用途选择 + temperature 透传；
        #    json_mode 能力探测决定 response_format）
        usage = config.get('model_usage') or 'batch'
        if usage not in ('batch', 'assistant', 'vision'):
            usage = 'batch'
        json_output = bool(config.get('json_output'))
        manager = AIConfigService.get_manager()
        response_format: Optional[Dict[str, str]] = None
        if json_output and manager.resolve(usage, capability='json_mode') is not None:
            response_format = {'type': 'json_object'}
        elif json_output:
            # 降级路径（02 §4.1）：无 json_mode 模型，结构化 prompt 约束 + 宽松解析
            prompt = prompt + '\n\n请仅输出一个合法的 JSON 对象或数组，不要包含任何其他文字或代码块标记。'
            messages[-1]['content'] = prompt

        try:
            temperature = config.get('temperature')
            param_overrides = ({'temperature': float(temperature)}
                               if temperature is not None else None)
        except (TypeError, ValueError):
            param_overrides = None

        chat_kwargs: Dict[str, Any] = {}
        if response_format:
            chat_kwargs['response_format'] = response_format
        if param_overrides:
            chat_kwargs['param_overrides'] = param_overrides

        started = time.monotonic()
        result = None
        run_error: Optional[Exception] = None
        try:
            result = manager.chat(
                usage, messages,
                capability='json_mode' if response_format else None,
                **chat_kwargs)
            parsed = self._parse_json_output(result.content) if json_output else None
        except Exception as e:  # noqa: BLE001 —— 统一交由 execute_node 重试包装
            run_error = e

        duration_ms = int((time.monotonic() - started) * 1000)
        usage_dict = (getattr(result, 'usage', None) or {}) if result is not None else {}
        prompt_tokens = int(usage_dict.get('prompt_tokens') or 0)
        completion_tokens = int(usage_dict.get('completion_tokens') or 0)

        # 4. 审计（H3）+ token 计量（H2，best-effort；失败调用同样计量实际消耗）
        if prompt_tokens or completion_tokens:
            QuotaService.consume_tokens(
                quota_user, base_id=base_id,
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
        log_ai_call(
            feature=AI_FEATURE_WORKFLOW, user_id=quota_user, base_id=base_id,
            status='success' if run_error is None else 'error',
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            usage_estimated=bool(getattr(result, 'usage_estimated', False)),
            input_summary=prompt,
            output_summary=(getattr(result, 'content', '') or '')[:500] if result else '',
            duration_ms=duration_ms,
            error=None if run_error is None else {
                'kind': 'workflow_ai', 'message': str(run_error)},
        )
        if run_error is not None:
            raise run_error

        return {
            'status': 'success',
            'result': {
                # 主值：json_output 时为解析后的对象，否则为原始文本
                'result': parsed if json_output else result.content,
                'text': result.content,
                'json': parsed,
                'json_output': json_output,
                'duration_ms': duration_ms,
            },
            'next_nodes': node.next_nodes or [],
        }

    def _parse_json_output(content: str) -> Any:
        """宽松解析 AI 输出中的 JSON（剥除 markdown 围栏 / 前后缀文字后提取首个 JSON 值）"""
        if not isinstance(content, str) or not content.strip():
            raise ValueError('AI 输出为空，无法解析 JSON')
        text = content.strip()
        fence = re.match(r'^```(?:json)?\s*([\s\S]*?)\s*```$', text)
        if fence:
            text = fence.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # 容忍前后缀文字：定位首个 { / [ 起 raw_decode（允许其后带尾随文本）
        decoder = json.JSONDecoder()
        for open_ch in ('{', '['):
            start = text.find(open_ch)
            while start != -1:
                try:
                    obj, _end = decoder.raw_decode(text[start:])
                    return obj
                except json.JSONDecodeError:
                    start = text.find(open_ch, start + 1)
        raise ValueError('AI 输出不是合法 JSON')

    def _execute_condition_node(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行条件分支节点

        支持多条件组分支（if/else-if 语义）与默认分支（else 语义）。
        按 branches 数组顺序评估非默认分支，首个满足条件的分支的 target_node_id 作为后续节点；
        全部不满足时执行默认分支；无默认分支则终止该分支。
        """
        config = node.config or {}
        context = self._build_render_context(instance)
        normalized = self._normalize_condition_config(config)
        branches = normalized.get('branches', [])

        default_branch = None
        for branch in branches:
            if branch.get('is_default'):
                default_branch = branch
                continue
            conditions = branch.get('conditions', [])
            condition_config: Dict[str, Any] = {
                'conditions': conditions,
                'conjunction': branch.get('conjunction', 'and'),
            }
            if self.evaluate_condition(condition_config, context):
                target_node_id = branch.get('target_node_id')
                return {'result': True, 'next_nodes': [target_node_id] if target_node_id else []}

        if default_branch:
            target_node_id = default_branch.get('target_node_id')
            return {'result': True, 'next_nodes': [target_node_id] if target_node_id else []}

        return {'result': False, 'next_nodes': []}

    def _normalize_condition_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """将条件节点配置归一化为多分支结构。

        旧配置使用 {conditions, conjunction} 表示单一条件组，自动迁移为单分支。
        新配置使用 {branches: [{id, name, conditions, conjunction, target_node_id}]}。
        """
        config = config or {}
        branches = config.get('branches')
        if isinstance(branches, list) and branches:
            return {'branches': branches}

        old_conditions = config.get('conditions', [])
        old_conjunction = config.get('conjunction', 'and')
        return {
            'branches': [
                {
                    'id': f'branch_{uuid.uuid4().hex[:8]}',
                    'name': '满足条件',
                    'conditions': old_conditions,
                    'conjunction': old_conjunction,
                    'target_node_id': None,
                }
            ]
        }

    def _execute_webhook_node(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行 Webhook 节点"""
        config = node.config or {}
        # 兼容前端字段名 webhook_id 和历史字段名 webhook_config_id
        webhook_config_id = config.get('webhook_id') or config.get('webhook_config_id')

        if webhook_config_id:
            webhook_config = WebhookConfig.query.get(self._to_uuid(webhook_config_id))
            if not webhook_config:
                raise ValueError(
                    translate('webhook_config_not_found_node', webhook_config_id, node.id, instance.id)
                )
        else:
            # 内联模式：从节点配置构建临时 WebhookConfig（不持久化到数据库，
            # 避免循环体内重复执行时每次都创建新记录导致 webhook 列表膨胀）
            inline_webhook = config.get('inline_webhook')
            if not inline_webhook or not inline_webhook.get('url'):
                raise ValueError(
                    translate('webhook_config_id_missing', node.id, instance.id)
                )
            webhook_config = WebhookConfig(
                base_id=instance.workflow.base_id if instance.workflow else None,
                name=inline_webhook.get('name', '内联 Webhook'),
                url=inline_webhook['url'],
                method=inline_webhook.get('method', 'POST'),
                headers=inline_webhook.get('headers', {}),
                body_template=inline_webhook.get('body_template', ''),
                is_active=True
            )

        # 构建包含 record 的 event_data，确保 {{record}} 模板变量能获取到数据
        render_context = self._build_render_context(instance)
        event_data = dict(render_context.get('trigger', {}))
        event_data['record'] = render_context.get('record', {})
        event_data['workflow'] = render_context.get('workflow', {})
        event_data['instance'] = render_context.get('instance', {})
        # 传递循环上下文，确保 {{loop.current_data}} 等模板变量在循环体内可用
        loop_context = render_context.get('loop')
        if loop_context:
            event_data['loop'] = loop_context
        # 合并渲染上下文中的其他变量（如脚本结果 script_result、node_outputs 等），
        # 使下游 webhook 可通过 {{script_result.field}} 或 {{node_outputs.<id>.field}} 引用上游节点输出
        for ctx_key, ctx_value in render_context.items():
            if ctx_key not in event_data:
                event_data[ctx_key] = ctx_value
        return WebhookService.deliver(webhook_config, instance, event_data)