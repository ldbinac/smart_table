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

class WorkflowExecutionEngineGroup05Mixin:
    """Mixin auto-split"""
    
    """工作流执行引擎"""
    
    SYSTEM_USER_ID = '00000000-0000-0000-0000-000000000000'
    
    MAX_TRIGGER_DEPTH = 3
    
    RECORD_LOCK_TIMEOUT = 30
    
    MAX_NOTIFY_RECIPIENTS = 200
    
    NOTIFY_RECIPIENT_SOURCES = ('fixed', 'field', 'trigger_user', 'record_creator', 'base_members')
    
    
    def _build_render_context(self, instance: WorkflowInstance) -> Dict[str, Any]:
        """构建模板渲染上下文"""
        context = instance.context or {}
        trigger_event = context.get('trigger_event', {})
    
        # 优先使用上下文中已携带的记录数据，否则根据 trigger_record_id 查询数据库
        record_values = context.get('record')
        if record_values is None:
            record_id = instance.trigger_record_id
            record = RecordService.get_record_by_id(str(record_id)) if record_id else None
            record_values = record.values if record else {}
    
        trigger_event_with_record = dict(trigger_event)
        trigger_event_with_record['record'] = record_values
    
        workflow = Workflow.query.get(instance.workflow_id)
    
        render_ctx = {
            'trigger': trigger_event_with_record,
            'record': record_values,
            'instance': instance.to_dict(),
            'workflow': workflow.to_dict() if workflow else {},
            'loop': context.get('loop_context'),
            'node_outputs': context.get('node_outputs') or {},
        }
        # 暴露脚本结果变量（如 script_result）到顶层，使 {{<result_variable>.field}} 可直接引用
        # 保留键不再上抛，避免覆盖既有顶层结构
        RESERVED_CONTEXT_KEYS = {'trigger_event', 'record', 'loop_context', 'node_outputs'}
        for key, value in context.items():
            if key not in RESERVED_CONTEXT_KEYS and key not in render_ctx:
                render_ctx[key] = value
        return render_ctx
    
    @staticmethod
    def render_template(value: Any, context: Dict[str, Any]) -> Any:
        """将模板字符串中的 {{...}} 替换为 context 中的值"""
        if not isinstance(value, str):
            return value
    
        pattern = re.compile(r'\{\{\s*(.*?)\s*\}\}')
        full_match = pattern.fullmatch(value)
        if full_match:
            return WorkflowExecutionEngine._resolve_path(full_match.group(1).strip(), context)
    
        def replacer(match: re.Match) -> str:
            resolved = WorkflowExecutionEngine._resolve_path(match.group(1).strip(), context)
            return str(resolved) if resolved is not None else ''
    
        return pattern.sub(replacer, value)
    
    @staticmethod
    def _resolve_path(path: str, context: Dict[str, Any]) -> Any:
        """按点号路径从上下文中解析值"""
        parts = path.split('.')
        current = context
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, (list, tuple)) and part.isdigit():
                idx = int(part)
                current = current[idx] if 0 <= idx < len(current) else None
            else:
                return None
            if current is None:
                return None
        return current
    
    @staticmethod
    def evaluate_condition(condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """评估条件表达式（操作符直接使用前端 FilterOperator 字符串）
    
        支持前端 19 个操作符 + AND/OR 组合（group 通过 conditions 数组判断，
        conjunction 缺失时默认 'and'，与 _evaluate_filter_condition 保持一致）。
        """
        if not isinstance(condition, dict):
            return False
    
        # group 结构通过 conditions 数组判断（conjunction 默认 'and'）
        sub_conditions = condition.get('conditions')
        if isinstance(sub_conditions, list):
            conjunction = condition.get('conjunction', 'and')
            if conjunction == 'or':
                return any(WorkflowExecutionEngine.evaluate_condition(c, context) for c in sub_conditions)
            return all(WorkflowExecutionEngine.evaluate_condition(c, context) for c in sub_conditions)
    
        # 叶子条件：直接读取 operator 字段（前端驼峰命名，无需转换）
        operator = condition.get('operator')
        field_id = condition.get('field_id')
        expected = condition.get('value')
        actual = context.get(field_id)
        if actual is None and isinstance(context, dict) and 'record' in context:
            actual = context['record'].get(field_id)
    
        return WorkflowService._eval_operator(actual, operator, expected)
    
    def _complete_instance(
        self,
        instance: WorkflowInstance,
        status: WorkflowInstanceStatus,
        error_message: Optional[str] = None
    ) -> None:
        """完成实例并记录状态"""
        instance.status = status
        instance.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        log.info(
            f'[WorkflowExecutionEngine] 实例结束: {instance.id} -> {status.value}'
            f'{f", error={error_message}" if error_message else ""}'
        )
    
