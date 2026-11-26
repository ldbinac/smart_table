# Auto-split skeleton

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

from .workflow_execution_engine_group01 import WorkflowExecutionEngineGroup01Mixin
from .workflow_execution_engine_group02 import WorkflowExecutionEngineGroup02Mixin
from .workflow_execution_engine_group03 import WorkflowExecutionEngineGroup03Mixin
from .workflow_execution_engine_group04 import WorkflowExecutionEngineGroup04Mixin
from .workflow_execution_engine_group05 import WorkflowExecutionEngineGroup05Mixin

class WorkflowExecutionEngine(WorkflowExecutionEngineGroup01Mixin, WorkflowExecutionEngineGroup02Mixin, WorkflowExecutionEngineGroup03Mixin, WorkflowExecutionEngineGroup04Mixin, WorkflowExecutionEngineGroup05Mixin):
    """WorkflowExecutionEngine — 主类，方法在 mixin 中"""
    
    """工作流执行引擎"""
    
    SYSTEM_USER_ID = '00000000-0000-0000-0000-000000000000'
    
    MAX_TRIGGER_DEPTH = 3
    
    RECORD_LOCK_TIMEOUT = 30
    
    MAX_NOTIFY_RECIPIENTS = 200
    
    NOTIFY_RECIPIENT_SOURCES = ('fixed', 'field', 'trigger_user', 'record_creator', 'base_members')
    


workflow_execution_engine = WorkflowExecutionEngine()

def init_workflow_execution_engine(app: Any) -> WorkflowExecutionEngine:
    """使用指定 Flask 应用初始化执行引擎"""
    global workflow_execution_engine
    workflow_event_bus.unsubscribe(workflow_execution_engine._event_handler)
    workflow_execution_engine = WorkflowExecutionEngine(app)
    return workflow_execution_engine

# === 反向注入：把主类注入到所有 group mixin 模块 ===
from app.services._inject import inject_main_class
inject_main_class(WorkflowExecutionEngine, 'workflow_execution_engine_group01', 'workflow_execution_engine_group02', 'workflow_execution_engine_group03', 'workflow_execution_engine_group04', 'workflow_execution_engine_group05')
