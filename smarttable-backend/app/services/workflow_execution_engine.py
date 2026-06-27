"""
工作流执行引擎模块

订阅 WorkflowEventBus，负责根据事件匹配工作流、启动实例并按节点类型调度执行。
"""
import logging
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import current_app

from app.extensions import db
from app.models.webhook import WebhookConfig
from app.models.workflow import Workflow, WorkflowNode, WorkflowNodeType
from app.models.workflow_instance import (
    WorkflowInstance,
    WorkflowExecutionLog,
    WorkflowInstanceStatus,
)
from app.services.approval_service import ApprovalService
from app.services.email_queue_service import email_queue
from app.services.record_service import RecordService
from app.services.webhook_service import WebhookService
from app.services.workflow_event_bus import workflow_event_bus, WorkflowEvent
from app.services.workflow_service import WorkflowService


log = logging.getLogger(__name__)


class WorkflowExecutionEngine:
    """工作流执行引擎"""

    SYSTEM_USER_ID = '00000000-0000-0000-0000-000000000000'
    MAX_TRIGGER_DEPTH = 3
    RECORD_LOCK_TIMEOUT = 30

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
        if event.event_type not in ('record_created', 'record_updated', 'field_changed'):
            return

        record_id = event.record_id
        if record_id and not self._acquire_record_lock(record_id):
            log.warning(f'[WorkflowExecutionEngine] 未获取到记录锁，跳过: {record_id}')
            return

        try:
            with self._app_context():
                record = RecordService.get_record_by_id(record_id) if record_id else None
                workflows = WorkflowService.match_triggers(
                    event.table_id,
                    event.event_type,
                    record,
                    changes=event.changes
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

        for next_node_id in next_nodes:
            next_node = WorkflowNode.query.get(self._to_uuid(next_node_id))
            if next_node:
                self._execute_chain(instance, next_node)

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
        execution_log = WorkflowExecutionLog(
            instance_id=instance.id,
            node_id=node.id,
            node_type=node.node_type.value if isinstance(node.node_type, WorkflowNodeType) else str(node.node_type),
            status='running',
            input_context=instance.context or {}
        )
        db.session.add(execution_log)
        db.session.flush()

        max_retries = node.config.get('max_retries', 0) if node.config else 0
        attempt = 0
        last_error = None

        while attempt <= max_retries:
            try:
                result = self._dispatch_node(instance, node)
                execution_log.status = 'success'
                execution_log.output_result = result if isinstance(result, dict) else {'result': result}
                execution_log.completed_at = datetime.now(timezone.utc)
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

        if node_type == WorkflowNodeType.APPROVAL.value:
            return ApprovalService.create_tasks(instance, node)

        if node_type == WorkflowNodeType.CONDITION.value:
            return self._execute_condition_node(instance, node)

        if node_type == WorkflowNodeType.WEBHOOK.value:
            return self._execute_webhook_node(instance, node)

        # 兼容前端直接使用动作类型作为 node_type 的情况
        action_type = node_type
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

        if node_type == WorkflowNodeType.ACTION.value:
            raise ValueError(f'未知动作类型: {action_type}')

        raise ValueError(f'未知节点类型: {node_type}')

    def _execute_update_record(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行更新记录动作"""
        config = node.config or {}
        record_id = config.get('record_id') or instance.trigger_record_id
        if not record_id:
            raise ValueError('缺少目标记录 ID')

        record = RecordService.get_record_by_id(str(record_id))
        if not record:
            raise ValueError(f'记录不存在: {record_id}')

        values = config.get('values', {})
        context = self._build_render_context(instance)
        rendered_values = {
            k: self.render_template(v, context)
            for k, v in values.items()
        }

        RecordService.update_record(record, rendered_values, updated_by=self.SYSTEM_USER_ID)
        return {'record_id': str(record.id)}

    def _execute_create_record(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行创建记录动作"""
        config = node.config or {}
        table_id = config.get('table_id')
        if not table_id:
            raise ValueError('缺少目标表格 ID')

        values = config.get('values', {})
        context = self._build_render_context(instance)
        rendered_values = {
            k: self.render_template(v, context)
            for k, v in values.items()
        }

        record = RecordService.create_record(
            str(table_id),
            rendered_values,
            created_by=self.SYSTEM_USER_ID
        )
        return {'record_id': str(record.id)}

    def _execute_send_email(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行发送邮件动作"""
        config = node.config or {}
        context = self._build_render_context(instance)

        to_email = self.render_template(config.get('to_email'), context)
        to_name = self.render_template(config.get('to_name', ''), context)
        template_key = config.get('template_key')
        if not template_key:
            raise ValueError('缺少邮件模板 key')

        template_data = {
            k: self.render_template(v, context)
            for k, v in config.get('template_data', {}).items()
        }

        task_id = email_queue.enqueue_quick(
            to_email=str(to_email),
            to_name=str(to_name),
            template_key=template_key,
            template_data=template_data
        )
        return {'task_id': task_id}

    def _execute_condition_node(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行条件分支节点"""
        config = node.config or {}
        condition = config.get('condition', {})
        context = self._build_render_context(instance)
        result = self.evaluate_condition(condition, context)

        if result:
            next_nodes = config.get('true_next_nodes', node.next_nodes)
        else:
            next_nodes = config.get('false_next_nodes', [])

        return {'result': result, 'next_nodes': next_nodes}

    def _execute_webhook_node(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行 Webhook 节点"""
        config = node.config or {}
        # 兼容前端字段名 webhook_id 和历史字段名 webhook_config_id
        webhook_config_id = config.get('webhook_id') or config.get('webhook_config_id')

        if webhook_config_id:
            webhook_config = WebhookConfig.query.get(self._to_uuid(webhook_config_id))
            if not webhook_config:
                raise ValueError(
                    f'Webhook 配置不存在: {webhook_config_id}（节点: {node.id}, 工作流实例: {instance.id}）'
                )
        else:
            # 内联模式：从节点配置创建临时 WebhookConfig
            inline_webhook = config.get('inline_webhook')
            if not inline_webhook or not inline_webhook.get('url'):
                raise ValueError(
                    f'缺少 Webhook 配置 ID 或内联配置（节点: {node.id}, 工作流实例: {instance.id}）'
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
            db.session.add(webhook_config)
            db.session.commit()

        # 构建包含 record 的 event_data，确保 {{record}} 模板变量能获取到数据
        render_context = self._build_render_context(instance)
        event_data = dict(render_context.get('trigger', {}))
        event_data['record'] = render_context.get('record', {})
        event_data['workflow'] = render_context.get('workflow', {})
        event_data['instance'] = render_context.get('instance', {})
        return WebhookService.deliver(webhook_config, instance, event_data)

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

        return {
            'trigger': trigger_event_with_record,
            'record': record_values,
            'instance': instance.to_dict(),
            'workflow': workflow.to_dict() if workflow else {}
        }

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
        """评估条件表达式（支持 eq / contains / gt / lt / regex 及 AND/OR 组合）"""
        if not isinstance(condition, dict):
            return False

        operator = condition.get('operator')
        if operator in ('and', 'or'):
            sub_conditions = condition.get('conditions', [])
            if operator == 'and':
                return all(WorkflowExecutionEngine.evaluate_condition(c, context) for c in sub_conditions)
            return any(WorkflowExecutionEngine.evaluate_condition(c, context) for c in sub_conditions)

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


# 全局执行引擎实例，导入时即订阅事件总线
workflow_execution_engine = WorkflowExecutionEngine()


def init_workflow_execution_engine(app: Any) -> WorkflowExecutionEngine:
    """使用指定 Flask 应用初始化执行引擎"""
    global workflow_execution_engine
    workflow_event_bus.unsubscribe(workflow_execution_engine._event_handler)
    workflow_execution_engine = WorkflowExecutionEngine(app)
    return workflow_execution_engine
