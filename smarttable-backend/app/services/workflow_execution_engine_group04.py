"""
工作流执行引擎模块

订阅 WorkflowEventBus，负责根据事件匹配工作流、启动实例并按节点类型调度执行。
"""
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
from app.services.approval_service import ApprovalService
from app.services.email_queue_service import email_queue
from app.services.email_sender_service import EmailSenderService
from app.services.notification_service import NotificationService
from app.services.record_service import RecordService
from app.services.webhook_service import WebhookService
from app.services.workflow_event_bus import workflow_event_bus, WorkflowEvent
from app.services.workflow_service import WorkflowService


log = logging.getLogger(__name__)

# 旧 action + action_type 向细粒度类型的映射（仅用于向后兼容）
_ACTION_TYPE_UPGRADE = {
    'update_record': 'update_record',
    'create_record': 'create_record',
    'send_email': 'send_email',
    'trigger_webhook': 'trigger_webhook',
    'find_records': 'find_records',
}


def _resolve_node_type_value(node) -> str:
    """解析节点的 node_type 字符串值。

    对于新细粒度类型直接返回；对于旧 'action' 类型，
    按 config.action_type 升级为细粒度类型以便执行日志可读。
    """
    node_type = node.node_type
    if isinstance(node_type, WorkflowNodeType):
        node_type = node_type.value
    node_type = str(node_type)
    if node_type == 'action':
        action_type = (node.config or {}).get('action_type')
        if action_type and action_type in _ACTION_TYPE_UPGRADE:
            return _ACTION_TYPE_UPGRADE[action_type]
    return node_type


class _LoopBodyNodeWrapper:
    """将 dict 形式的循环体子节点包装为类似 WorkflowNode 的对象，以复用 _dispatch_node 分发逻辑。

    循环体子节点存储为 dict（在 loop 节点的 config.loop_body_nodes 中），不是 ORM 对象。
    此包装类暴露 execute_node / _dispatch_node 所需的属性（id / node_type / config / next_nodes 等）。

    使用前端传递的节点 ID（node_dict['id']），若无则生成临时标识符。
    node_id 字段已改为 String 类型，可存储任意字符串标识符。
    """

    def __init__(self, node_dict: Dict[str, Any]):
        self._dict = node_dict or {}
        # 使用前端传递的节点 ID，若无则生成临时标识符
        self.id = self._dict.get('id') or f"loop-body-{id(self)}"
        self.node_type = self._dict.get('node_type', 'action')
        self.config = self._dict.get('config', {}) or {}
        self.next_nodes = self._dict.get('next_nodes', []) or []
        self.order = self._dict.get('order', 0)
        self.name = self._dict.get('name', '')

    def __repr__(self) -> str:
        return f'<_LoopBodyNodeWrapper {self.name} ({self.node_type})>'

class WorkflowExecutionEngineGroup04Mixin:
    """Mixin auto-split"""
    
    """工作流执行引擎"""
    
    SYSTEM_USER_ID = '00000000-0000-0000-0000-000000000000'
    
    MAX_TRIGGER_DEPTH = 3
    
    RECORD_LOCK_TIMEOUT = 30
    
    MAX_NOTIFY_RECIPIENTS = 200
    
    NOTIFY_RECIPIENT_SOURCES = ('fixed', 'field', 'trigger_user', 'record_creator', 'base_members')
    
    
    def _execute_loop_node(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行循环节点：解析数据源 → 依次迭代循环体 → 返回主链 next_nodes。
    
        循环结束后返回 {next_nodes: node.next_nodes} 以继续主链。
        """
        config = node.config or {}
        data_source_config = config.get('data_source', {}) or {}
        max_iterations = config.get('max_iterations', 100)
        error_handling = config.get('error_handling', 'skip')
        empty_result_action = config.get('empty_result_action', 'skip')
        loop_body_nodes = config.get('loop_body_nodes', []) or []
    
        log.info(
            f'[WorkflowExecutionEngine] 循环节点 {node.id}: '
            f'data_source={data_source_config}, '
            f'loop_body_nodes 数量={len(loop_body_nodes)}, '
            f'loop_body_nodes 类型={[type(n).__name__ for n in loop_body_nodes]}'
        )
    
        data_array = self._resolve_loop_data_source(instance, data_source_config)
    
        log.info(
            f'[WorkflowExecutionEngine] 循环节点 {node.id}: '
            f'data_array 长度={len(data_array)}, '
            f'instance.context keys={list((instance.context or {}).keys())}'
        )
    
        if not data_array:
            # 记录诊断执行日志，便于前端排查循环未执行的原因
            diagnostic_log = WorkflowExecutionLog(
                instance_id=instance.id,
                node_id=str(node.id) if node.id else None,
                node_name=node.name if hasattr(node, 'name') else None,
                node_type='loop',
                status='success' if empty_result_action != 'error' else 'error',
                input_context={
                    'data_source': data_source_config,
                    'array_length': 0,
                    'loop_body_nodes_count': len(loop_body_nodes),
                    'context_keys': list((instance.context or {}).keys()),
                },
                output_result={
                    'total_iterations': 0,
                    'success_count': 0,
                    'failure_count': 0,
                    'early_terminated': False,
                    'skipped_reason': 'data_array_empty',
                },
                completed_at=datetime.now(timezone.utc)
            )
            db.session.add(diagnostic_log)
            db.session.commit()
    
            if empty_result_action == 'error':
                raise ValueError('loop_data_source_empty')
            # skip 模式：跳过循环，继续主链
            return {'next_nodes': node.next_nodes or []}
    
        try:
            max_iterations_int = int(max_iterations)
        except (TypeError, ValueError):
            max_iterations_int = 100
        max_iterations_int = max(1, min(max_iterations_int, 1000))
    
        total = min(len(data_array), max_iterations_int)
    
        execution_log = WorkflowExecutionLog(
            instance_id=instance.id,
            node_id=str(node.id) if node.id else None,
            node_name=node.name if hasattr(node, 'name') else None,
            node_type='loop',
            status='running',
            input_context={
                'data_source': data_source_config,
                'array_length': len(data_array),
                'loop_body_nodes_count': len(loop_body_nodes),
                'max_iterations': max_iterations_int,
                'total': total
            }
        )
        db.session.add(execution_log)
        db.session.flush()
    
        success_count = 0
        failure_count = 0
        early_terminated = False
        error_message: Optional[str] = None
    
        try:
            for index in range(total):
                current_data = data_array[index]
                try:
                    self._execute_loop_body(
                        instance, loop_body_nodes, current_data, index, total
                    )
                    success_count += 1
                except Exception as e:
                    failure_count += 1
                    if error_handling == 'terminate':
                        early_terminated = True
                        error_message = str(e)
                        raise
                    # skip 模式：异常已通过 _execute_loop_body_chain 传播中断当前迭代剩余节点，
                    # 此处记录日志后继续下一次迭代
                    log.warning(
                        f'[WorkflowExecutionEngine] 循环体第 {index + 1}/{total} 轮执行失败'
                        f'（error_handling=skip，跳过当次剩余节点）: {e}'
                    )
        finally:
            execution_log.status = 'error' if early_terminated else 'success'
            execution_log.error_message = error_message
            execution_log.output_result = {
                'total_iterations': success_count + failure_count,
                'success_count': success_count,
                'failure_count': failure_count,
                'early_terminated': early_terminated
            }
            execution_log.completed_at = datetime.now(timezone.utc)
            db.session.commit()
    
        return {'next_nodes': node.next_nodes or []}
    
    def _execute_loop_body(
        self,
        instance: WorkflowInstance,
        loop_body_nodes: List[Dict[str, Any]],
        current_data: Any,
        index: int,
        total: int
    ) -> None:
        """执行单次循环体：写入 loop_context → 执行子节点链 → 恢复外层 loop_context。
    
        异常向上抛出（由 _execute_loop_node 根据 error_handling 决定处理方式）。
        finally 中保证外层 loop_context 被恢复，以支持嵌套循环。
        """
        from sqlalchemy.orm.attributes import flag_modified
    
        context = instance.context or {}
        outer_loop_context = context.get('loop_context')
    
        context['loop_context'] = {
            'current_data': current_data,
            'index': index,
            'round': index + 1,
            'total': total
        }
        instance.context = context
        flag_modified(instance, 'context')
        db.session.commit()
    
        try:
            if not loop_body_nodes:
                return
    
            valid_nodes = [n for n in loop_body_nodes if isinstance(n, dict)]
            if not valid_nodes:
                return
    
            nodes_by_id: Dict[str, Dict[str, Any]] = {}
            all_next_ids: set = set()
            for n in valid_nodes:
                node_id = n.get('id')
                if node_id is not None:
                    nodes_by_id[node_id] = n
                all_next_ids.update(n.get('next_nodes', []) or [])
    
            # 入口节点：order 最小且不在其他节点 next_nodes 中的节点
            sorted_nodes = sorted(valid_nodes, key=lambda n: n.get('order', 0))
            entry_node: Optional[Dict[str, Any]] = None
            for n in sorted_nodes:
                if n.get('id') not in all_next_ids:
                    entry_node = n
                    break
            if entry_node is None:
                entry_node = sorted_nodes[0]
    
            self._execute_loop_body_chain(instance, entry_node, nodes_by_id)
        finally:
            # 恢复外层 loop_context（嵌套支持）；若无外层则清除
            context = instance.context or {}
            if outer_loop_context is not None:
                context['loop_context'] = outer_loop_context
            else:
                context.pop('loop_context', None)
            instance.context = context
            flag_modified(instance, 'context')
            db.session.commit()
    
    def _execute_loop_body_chain(
        self,
        instance: WorkflowInstance,
        node_dict: Dict[str, Any],
        nodes_by_id: Dict[str, Dict[str, Any]]
    ) -> None:
        """递归执行循环体子节点链（不使用 visited_node_ids，每次迭代独立）。
    
        子节点通过 _LoopBodyNodeWrapper 包装后调用 execute_node 复用现有节点执行器。
        异常向上抛出，由 _execute_loop_node 根据 error_handling 决定是否终止循环。
        """
        wrapper = _LoopBodyNodeWrapper(node_dict)
        result = self.execute_node(instance, wrapper)
    
        # 兼容 continue_on_error 的错误返回（理论上 execute_node 会 raise，保险起见）
        if (
            isinstance(result, dict)
            and result.get('status') == 'error'
            and not (node_dict.get('config') or {}).get('continue_on_error')
        ):
            raise Exception(result.get('error_message', '节点执行失败'))
    
        next_ids = node_dict.get('next_nodes', []) or []
        for next_id in next_ids:
            next_node = nodes_by_id.get(next_id)
            if next_node:
                self._execute_loop_body_chain(instance, next_node, nodes_by_id)
            else:
                log.warning(
                    f'[WorkflowExecutionEngine] 循环体子节点 next_node 未找到: {next_id}'
                )
    
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
    
    @staticmethod
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
    
