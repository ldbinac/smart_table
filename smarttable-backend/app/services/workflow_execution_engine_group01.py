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

class WorkflowExecutionEngineGroup01Mixin:
    """Mixin auto-split"""
    
    """工作流执行引擎"""
    
    SYSTEM_USER_ID = '00000000-0000-0000-0000-000000000000'
    
    MAX_TRIGGER_DEPTH = 3
    
    RECORD_LOCK_TIMEOUT = 30
    
    MAX_NOTIFY_RECIPIENTS = 200
    
    NOTIFY_RECIPIENT_SOURCES = ('fixed', 'field', 'trigger_user', 'record_creator', 'base_members')
    
    
    def __init__(self, app: Any = None):
        """
        初始化执行引擎并订阅事件总线
    
        Args:
            app: Flask 应用实例（可选，若未提供则尝试使用 current_app）
        """
        self.app = app
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix='workflow-exec-')
        self._event_handler = self._on_workflow_event
        workflow_event_bus.subscribe(self._event_handler)
        log.info('[WorkflowExecutionEngine] 已订阅 workflow_event_bus')
    
    def _app_context(self):
        """获取可用的 Flask 应用上下文"""
        if self.app is not None:
            return self.app.app_context()
        try:
            return current_app.app_context()
        except RuntimeError:
            return nullcontext()
    
    @staticmethod
    def _to_uuid(value: Any) -> Optional[uuid.UUID]:
        """将字符串或 UUID 对象转换为 UUID 对象"""
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))
    
    def _acquire_record_lock(self, record_id: str, timeout: int = RECORD_LOCK_TIMEOUT) -> bool:
        """获取同一记录的触发分布式锁"""
        from app.extensions import redis_client
        if redis_client is None:
            return True
        key = f'workflow:lock:record:{record_id}'
        acquired = redis_client.set(key, '1', nx=True, ex=timeout)
        return bool(acquired)
    
    def _release_record_lock(self, record_id: str) -> None:
        """释放记录触发锁"""
        from app.extensions import redis_client
        if redis_client is not None:
            redis_client.delete(f'workflow:lock:record:{record_id}')
    
    def _on_workflow_event(self, event: WorkflowEvent) -> None:
        """事件总线处理器：匹配工作流并异步启动实例"""
        if event.actor_id == self.SYSTEM_USER_ID:
            return
        if event.metadata and event.metadata.get('workflow_source'):
            return
        if event.event_type not in ('record_created', 'record_updated', 'field_changed', 'specified_time', 'record_time_reached'):
            return
    
        record_id = event.record_id
        is_recordless = event.event_type == 'specified_time' or record_id is None
    
        if not is_recordless and record_id and not self._acquire_record_lock(record_id):
            log.warning(f'[WorkflowExecutionEngine] 未获取到记录锁，跳过: {record_id}')
            return
    
        try:
            with self._app_context():
                record = RecordService.get_record_by_id(record_id) if record_id else None
                workflow_id = (event.metadata or {}).get('workflow_id')
                workflows = WorkflowService.match_triggers(
                    event.table_id,
                    event.event_type,
                    record,
                    changes=event.changes,
                    workflow_id=workflow_id
                )
                for workflow in workflows:
                    instance = self.start_instance(workflow, event)
                    if instance:
                        self.executor.submit(self._run_instance, str(instance.id))
        except Exception as e:
            log.exception(f'[WorkflowExecutionEngine] 事件处理失败: {e}')
        finally:
            if record_id:
                self._release_record_lock(record_id)
    
    def start_instance(
        self,
        workflow: Workflow,
        trigger_event: WorkflowEvent
    ) -> Optional[WorkflowInstance]:
        """
        启动工作流实例
    
        Args:
            workflow: 匹配到的工作流
            trigger_event: 触发事件
    
        Returns:
            创建的实例，超过触发链深度时返回 None
        """
        chain = (trigger_event.metadata or {}).get('trigger_chain', [])
        depth = len(chain)
        if depth >= self.MAX_TRIGGER_DEPTH:
            log.warning(
                f'[WorkflowExecutionEngine] 触发链深度 {depth} 超过上限，终止实例: {workflow.id}'
            )
            return None
    
        context = {
            'trigger_event': trigger_event.to_dict(),
            'trigger_chain': chain + [str(workflow.id)],
            'depth': depth + 1,
            'visited_node_ids': []
        }
    
        instance = WorkflowInstance(
            workflow_id=workflow.id,
            version_number=max(workflow.current_version or 0, 1),
            trigger_type=trigger_event.event_type,
            trigger_record_id=self._to_uuid(trigger_event.record_id),
            status=WorkflowInstanceStatus.RUNNING,
            context=context
        )
    
        db.session.add(instance)
        db.session.commit()
    
        log.info(f'[WorkflowExecutionEngine] 实例已启动: {instance.id} (workflow={workflow.id})')
        return instance
    
    def _run_instance(self, instance_id) -> None:
        """在线程池中运行实例
    
        通过 instance_id 重新查询实例对象，避免跨线程会话导致的 detached 对象问题。
        """
        with self._app_context():
            try:
                instance_uuid = self._to_uuid(instance_id) if isinstance(instance_id, str) else instance_id
                instance = WorkflowInstance.query.get(instance_uuid)
                if not instance:
                    log.error(f'[WorkflowExecutionEngine] 实例不存在: {instance_id}')
                    return
    
                trigger_node = WorkflowNode.query.filter_by(
                    workflow_id=instance.workflow_id,
                    node_type=WorkflowNodeType.TRIGGER
                ).order_by(WorkflowNode.order).first()
    
                if not trigger_node:
                    # 前端设计器不创建 TRIGGER 类型节点，回退到首节点作为入口
                    trigger_node = WorkflowNode.query.filter_by(
                        workflow_id=instance.workflow_id
                    ).order_by(WorkflowNode.order).first()
    
                if not trigger_node:
                    self._record_missing_trigger_node(instance)
                    self._complete_instance(instance, WorkflowInstanceStatus.ERROR, '未找到触发节点')
                    return
    
                self._execute_chain(instance, trigger_node)
    
                if instance.status == WorkflowInstanceStatus.RUNNING:
                    self._complete_instance(instance, WorkflowInstanceStatus.COMPLETED)
            except Exception as e:
                log.exception(f'[WorkflowExecutionEngine] 实例执行失败: {instance_id}')
                instance_uuid = self._to_uuid(instance_id) if isinstance(instance_id, str) else instance_id
                instance = WorkflowInstance.query.get(instance_uuid)
                if instance:
                    self._complete_instance(instance, WorkflowInstanceStatus.ERROR, str(e))
    
    def _record_missing_trigger_node(self, instance: WorkflowInstance) -> None:
        """触发节点缺失时记录 error 执行日志，便于前端展示"""
        execution_log = WorkflowExecutionLog(
            instance_id=instance.id,
            node_id=None,
            node_name=None,
            node_type='trigger',
            status='error',
            input_context=instance.context or {},
            output_result={},
            error_message='未找到触发节点',
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc)
        )
        db.session.add(execution_log)
        db.session.commit()
    
    def _execute_chain(self, instance: WorkflowInstance, node: WorkflowNode) -> None:
        """递归执行节点链，支持循环检测"""
        context = instance.context or {}
        visited = set(context.get('visited_node_ids', []))
        if str(node.id) in visited:
            log.warning(f'[WorkflowExecutionEngine] 检测到节点循环，跳过: {node.id}')
            return
    
        visited.add(str(node.id))
        context['visited_node_ids'] = list(visited)
        instance.context = context
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(instance, 'context')
        db.session.commit()
    
        result = self.execute_node(instance, node)
    
        if (
            isinstance(result, dict)
            and result.get('status') == 'error'
            and not (node.config or {}).get('continue_on_error')
        ):
            raise Exception(result.get('error_message', '节点执行失败'))
    
        next_nodes = result.get('next_nodes') if isinstance(result, dict) else None
        if next_nodes is None:
            next_nodes = node.next_nodes or []
    
        if not next_nodes:
            log.info(
                f'[WorkflowExecutionEngine] 节点 {node.id} ({node.node_type}) '
                f'next_nodes 为空，执行链结束'
            )
    
        for next_node_id in next_nodes:
            next_node = WorkflowNode.query.get(self._to_uuid(next_node_id))
            if next_node:
                self._execute_chain(instance, next_node)
            else:
                log.warning(
                    f'[WorkflowExecutionEngine] next_node_id={next_node_id} '
                    f'在数据库中未找到对应节点，跳过'
                )
    
    def execute_node(
        self,
        instance: WorkflowInstance,
        node: WorkflowNode
    ) -> Dict[str, Any]:
        """
        节点执行分发器
    
        Args:
            instance: 工作流实例
            node: 当前节点
    
        Returns:
            节点执行结果字典
        """
        # 构建 input_context：复制 instance.context，并在循环体内追加 iteration_index
        # 以便执行日志关联当前迭代轮次（循环体外 loop_context 为 None，不影响主链节点）
        input_context = dict(instance.context or {})
        loop_context = input_context.get('loop_context')
        if loop_context:
            input_context['iteration_index'] = loop_context.get('index')
    
        execution_log = WorkflowExecutionLog(
            instance_id=instance.id,
            node_id=str(node.id) if node.id else None,
            node_name=node.name if hasattr(node, 'name') else None,
            node_type=_resolve_node_type_value(node),
            status='running',
            input_context=input_context
        )
        db.session.add(execution_log)
        db.session.flush()
    
        max_retries = node.config.get('max_retries', 0) if node.config else 0
        attempt = 0
        last_error = None
    
        while attempt <= max_retries:
            try:
                result = self._dispatch_node(instance, node)
    
                # 检测节点返回的错误状态（脚本节点等返回 dict 含 status=error 而非 raise）
                if isinstance(result, dict) and result.get('status') == 'error':
                    execution_log.status = 'error'
                    execution_log.error_message = result.get('error_message', '节点执行失败')
                    execution_log.output_result = result
                    execution_log.completed_at = datetime.now(timezone.utc)
                    db.session.commit()
                    # 错误也写入 node_outputs 以便下游引用（含 error 信息）
                    try:
                        ctx = instance.context or {}
                        node_outputs = ctx.get('node_outputs') or {}
                        node_outputs[str(node.id) if node.id else None] = result.get('result') or {'error': result.get('error_message')}
                        ctx['node_outputs'] = node_outputs
                        instance.context = ctx
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(instance, 'context')
                        db.session.commit()
                    except Exception as node_out_err:
                        log.warning(f'[WorkflowExecutionEngine] 写入 node_outputs 失败: {node_out_err}')
                    if node.config and node.config.get('continue_on_error'):
                        return result
                    raise RuntimeError(result.get('error_message', '节点执行失败'))
    
                execution_log.status = 'success'
                execution_log.output_result = result if isinstance(result, dict) else {'result': result}
                execution_log.completed_at = datetime.now(timezone.utc)
    
                # 追加写入 node_outputs（统一节点输出流转接口，纯新增向后兼容）
                # 仅写入 dispatch_result 的 result 部分（output_result），使 {{node_outputs.<id>.result.field}} 模板路径可正确解析
                # 注意：execution_log.output_result 仍写入完整 dispatch result（含 next_nodes 等调度信息，用于审计）
                try:
                    ctx = instance.context or {}
                    node_outputs = ctx.get('node_outputs') or {}
                    output_result = result.get('result', result) if isinstance(result, dict) and 'result' in result else (result if isinstance(result, dict) else {'result': result})
                    node_outputs[str(node.id) if node.id else None] = output_result
                    ctx['node_outputs'] = node_outputs
                    instance.context = ctx
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(instance, 'context')
                except Exception as node_out_err:
                    log.warning(f'[WorkflowExecutionEngine] 写入 node_outputs 失败: {node_out_err}')
    
                db.session.commit()
                return result if isinstance(result, dict) else {'result': result}
            except Exception as e:
                last_error = e
                attempt += 1
                log.warning(
                    f'[WorkflowExecutionEngine] 节点执行失败（{attempt}/{max_retries + 1}）: {node.id} - {e}'
                )
    
        execution_log.status = 'error'
        execution_log.error_message = str(last_error)
        execution_log.completed_at = datetime.now(timezone.utc)
        db.session.commit()
    
        if node.config and node.config.get('continue_on_error'):
            return {'status': 'error', 'error_message': str(last_error), 'continued': True}
    
        raise last_error
    
    def _dispatch_node(self, instance: WorkflowInstance, node: WorkflowNode) -> Any:
        """根据节点类型分发到对应执行器"""
        node_type = node.node_type
        if isinstance(node_type, WorkflowNodeType):
            node_type = node_type.value
    
        if node_type == WorkflowNodeType.TRIGGER.value:
            return {'status': 'success'}
    
        if node_type == WorkflowNodeType.FIND_RECORDS.value:
            return self._execute_find_records(instance, node)
    
        if node_type == WorkflowNodeType.UPDATE_RECORD.value:
            return self._execute_update_record(instance, node)
    
        if node_type == WorkflowNodeType.CREATE_RECORD.value:
            return self._execute_create_record(instance, node)
    
        if node_type == WorkflowNodeType.SEND_EMAIL.value:
            return self._execute_send_email(instance, node)
    
        if node_type == WorkflowNodeType.NOTIFY.value:
            return self._execute_notify(instance, node)
    
        if node_type == WorkflowNodeType.TRIGGER_WEBHOOK.value:
            return self._execute_webhook_node(instance, node)
    
        if node_type == WorkflowNodeType.APPROVAL.value:
            return ApprovalService.create_tasks(instance, node)
    
        if node_type == WorkflowNodeType.CONDITION.value:
            return self._execute_condition_node(instance, node)
    
        if node_type == WorkflowNodeType.WEBHOOK.value:
            return self._execute_webhook_node(instance, node)
    
        if node_type == WorkflowNodeType.LOOP.value:
            return self._execute_loop_node(instance, node)
    
        if node_type == WorkflowNodeType.SCRIPT.value:
            return self._execute_script_node(instance, node)
    
        if node_type == WorkflowNodeType.AI.value:
            return self._execute_ai_node(instance, node)
    
        # 兼容旧数据：node_type='action' + config.action_type
        if node_type == WorkflowNodeType.ACTION.value:
            action_type = (node.config or {}).get('action_type')
            if action_type == 'update_record':
                return self._execute_update_record(instance, node)
            if action_type == 'create_record':
                return self._execute_create_record(instance, node)
            if action_type == 'send_email':
                return self._execute_send_email(instance, node)
            if action_type == 'trigger_webhook':
                return self._execute_webhook_node(instance, node)
            if action_type == 'find_records':
                return self._execute_find_records(instance, node)
            raise ValueError(translate('unknown_action_type', action_type))
    
        raise ValueError(translate('unknown_node_type', node_type))
    
