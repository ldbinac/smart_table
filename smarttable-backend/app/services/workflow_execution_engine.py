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

    id 设为 None 以避免 WorkflowExecutionLog.node_id 的外键约束冲突——
    循环体子节点的 ID 不在 workflow_nodes 表中，强制写入会触发 ForeignKey 约束失败。
    """

    def __init__(self, node_dict: Dict[str, Any]):
        self._dict = node_dict or {}
        self.id = None
        self.node_type = self._dict.get('node_type', 'action')
        self.config = self._dict.get('config', {}) or {}
        self.next_nodes = self._dict.get('next_nodes', []) or []
        self.order = self._dict.get('order', 0)
        self.name = self._dict.get('name', '')

    def __repr__(self) -> str:
        return f'<_LoopBodyNodeWrapper {self.name} ({self.node_type})>'


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
            node_id=node.id,
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

        if node_type == WorkflowNodeType.FIND_RECORDS.value:
            return self._execute_find_records(instance, node)

        if node_type == WorkflowNodeType.UPDATE_RECORD.value:
            return self._execute_update_record(instance, node)

        if node_type == WorkflowNodeType.CREATE_RECORD.value:
            return self._execute_create_record(instance, node)

        if node_type == WorkflowNodeType.SEND_EMAIL.value:
            return self._execute_send_email(instance, node)

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

        # 前端存储为 updates 数组，需转为字段ID→值的字典
        updates = config.get('updates', [])
        context = self._build_render_context(instance)
        rendered_values = {}
        for mapping in updates:
            field_id = mapping.get('field_id')
            if not field_id:
                continue
            value_template = mapping.get('value_template', '')
            rendered_values[field_id] = self.render_template(value_template, context)

        RecordService.update_record(record, rendered_values, updated_by=self.SYSTEM_USER_ID)
        return {'record_id': str(record.id)}

    def _execute_create_record(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行创建记录动作"""
        config = node.config or {}
        table_id = config.get('target_table_id')
        if not table_id:
            raise ValueError('缺少目标表格 ID')

        # 前端存储为 field_mappings 数组，需转为字段ID→值的字典
        field_mappings = config.get('field_mappings', [])
        context = self._build_render_context(instance)
        rendered_values = {}
        for mapping in field_mappings:
            target_field_id = mapping.get('target_field_id')
            if not target_field_id:
                continue
            value_template = mapping.get('value_template', '')
            rendered_values[target_field_id] = self.render_template(value_template, context)

        record = RecordService.create_record(
            str(table_id),
            rendered_values,
            created_by=self.SYSTEM_USER_ID
        )
        return {'record_id': str(record.id)}

    def _execute_find_records(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行查找记录动作"""
        config = node.config or {}

        target_table_id = config.get('target_table_id')
        if not target_table_id:
            raise ValueError('缺少目标表格 ID')

        table = Table.query.get(self._to_uuid(target_table_id))
        if not table:
            raise ValueError(f'目标表格不存在: {target_table_id}')

        conditions = config.get('conditions', [])
        conjunction = config.get('conjunction', 'and')
        sort_field_id = config.get('sort_field_id')
        sort_direction = config.get('sort_direction', 'asc')

        limit = config.get('limit', 100)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 100
        limit = max(1, min(limit, 1000))

        result_variable = config.get('result_variable', 'records') or 'records'
        empty_result_action = config.get('empty_result_action', 'continue')

        records = Record.query.filter_by(
            table_id=self._to_uuid(target_table_id),
            is_deleted=False
        ).all()

        matching_records = []
        condition_config = {'conditions': conditions, 'conjunction': conjunction}
        for record in records:
            context = {field_id: record.values.get(field_id) for field_id in (record.values or {})}
            if self.evaluate_condition(condition_config, context):
                matching_records.append(record)

        if sort_field_id:
            reverse = sort_direction == 'desc'
            matching_records.sort(
                key=lambda r: (r.values or {}).get(sort_field_id),
                reverse=reverse
            )

        matching_records = matching_records[:limit]

        result = {
            'count': len(matching_records),
            'records': [r.to_dict() if hasattr(r, 'to_dict') else r.values for r in matching_records]
        }

        context = instance.context or {}
        context[result_variable] = result
        instance.context = context
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(instance, 'context')
        db.session.commit()

        if not matching_records and empty_result_action == 'stop':
            return {'result': result, 'next_nodes': []}

        return {'result': result, 'next_nodes': node.next_nodes or []}

    def _resolve_email_recipients(self, config: Dict[str, Any], context: Dict[str, Any]) -> str:
        """根据收件人配置解析邮箱地址列表

        Args:
            config: 节点配置字典
            context: 模板渲染上下文（来自 _build_render_context）

        Returns:
            逗号分隔的邮箱地址字符串
        """
        recipient_type = config.get('recipient_type', 'fixed')
        recipient_value = config.get('recipient_value', [])
        emails: list = []

        if recipient_type == 'field':
            # 从记录字段值中提取邮箱
            record = context.get('record', {})
            field_ids = recipient_value if isinstance(recipient_value, list) else [recipient_value]
            for field_id in field_ids:
                field_value = record.get(field_id) if isinstance(record, dict) else None
                if field_value is None:
                    continue
                emails.extend(self._extract_emails_from_field_value(field_value))
        else:
            # fixed 模式：直接使用配置值
            if isinstance(recipient_value, str):
                emails.append(recipient_value)
            elif isinstance(recipient_value, list):
                for item in recipient_value:
                    if isinstance(item, str):
                        emails.append(item)
                    elif isinstance(item, dict) and item.get('email'):
                        emails.append(item['email'])

        return ','.join(filter(None, emails))

    @staticmethod
    def _extract_emails_from_field_value(value: Any) -> list:
        """从字段值中提取邮箱地址列表

        支持以下格式：
        - 单个邮箱字符串
        - 逗号分隔的邮箱字符串
        - 邮箱字符串列表
        - 包含 email 键的对象列表（成员/协作者字段）
        - 成员用户ID（UUID格式），自动查询用户表获取邮箱
        """
        from app.models.user import User
        from uuid import UUID

        emails: list = []
        if value is None:
            return emails
        if isinstance(value, str):
            # 检查是否是UUID格式的成员ID
            try:
                uuid_value = UUID(value)
                user = User.query.get(uuid_value)
                if user and user.email:
                    emails.append(user.email)
                    return emails
            except (ValueError, TypeError):
                pass  # 不是UUID，继续作为邮箱处理

            # 逗号分隔字符串
            for part in value.split(','):
                part = part.strip()
                if part:
                    emails.append(part)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    # 检查是否是UUID格式的成员ID
                    try:
                        uuid_value = UUID(item)
                        user = User.query.get(uuid_value)
                        if user and user.email:
                            emails.append(user.email)
                            continue
                    except (ValueError, TypeError):
                        pass  # 不是UUID，继续作为邮箱处理
                    emails.append(item)
                elif isinstance(item, dict) and item.get('email'):
                    emails.append(item['email'])
        return emails

    def _execute_send_email(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行发送邮件动作"""
        from app.services.email_config_service import EmailConfigService
        if not EmailConfigService.is_email_enabled():
            raise ValueError('邮件服务未启用或配置不完整')

        config = node.config or {}
        context = self._build_render_context(instance)
        content_mode = config.get('content_mode', 'custom')

        to_email = self._resolve_email_recipients(config, context)

        if content_mode == 'custom':
            subject = self.render_template(config.get('subject', ''), context)
            body = self.render_template(config.get('body', ''), context)

            success, error = EmailSenderService.send_email_quick(
                to_email=to_email,
                subject=str(subject),
                html_content=str(body),
            )
            if not success:
                raise ValueError(f'邮件发送失败: {error}')
            return {'status': 'sent', 'to_email': to_email}

        # template 模式
        template_key = config.get('template_key')
        if not template_key:
            raise ValueError('缺少邮件模板 key')

        to_name = self.render_template(config.get('to_name', ''), context)
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

    @staticmethod
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

    def _resolve_loop_data_source(
        self,
        instance: WorkflowInstance,
        data_source_config: Dict[str, Any]
    ) -> List[Any]:
        """解析循环节点数据源，返回待迭代的数组。

        支持四种数据源类型：
        - find_records_all: 取 find_records 节点输出的 records 数组
        - find_records_column: 从 records 数组中提取指定字段值并扁平化（人员/群组/附件字段自动去重）
        - trigger_field: 取触发记录中指定字段值（列表直接返回，否则包装为单元素列表）
        - webhook_array: 从 webhook 节点输出的 json.array 中读取数组

        非 dict 配置、未知类型或数据为空时返回空列表。
        """
        if not isinstance(data_source_config, dict):
            return []

        source_type = data_source_config.get('type')
        context = instance.context or {}

        if source_type == 'find_records_all':
            result_variable = self._resolve_find_records_variable(instance, data_source_config.get('node_id'))
            result = context.get(result_variable, {})
            if isinstance(result, dict):
                records = result.get('records', [])
                return records if isinstance(records, list) else []
            return []

        if source_type == 'find_records_column':
            field_id = data_source_config.get('field_id')
            if not field_id:
                return []
            result_variable = self._resolve_find_records_variable(instance, data_source_config.get('node_id'))
            result = context.get(result_variable, {})
            records = result.get('records', []) if isinstance(result, dict) else []
            if not isinstance(records, list):
                return []

            flattened: List[Any] = []
            seen_ids: set = set()
            for record in records:
                if not isinstance(record, dict):
                    continue
                value = record.get(field_id)
                if value is None:
                    continue
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and 'id' in item:
                            item_id = item.get('id')
                            if item_id and item_id not in seen_ids:
                                seen_ids.add(item_id)
                                flattened.append(item)
                        elif item is not None:
                            flattened.append(item)
                else:
                    flattened.append(value)
            return flattened

        if source_type == 'trigger_field':
            trigger_field_id = data_source_config.get('trigger_field_id') or data_source_config.get('field_id')
            trigger_event = context.get('trigger_event', {}) or {}
            record = trigger_event.get('record', {}) or {}
            value = record.get(trigger_field_id) if trigger_field_id else None
            if isinstance(value, list):
                return value
            if value is None:
                return []
            return [value]

        if source_type == 'webhook_array':
            node_id = data_source_config.get('node_id')
            if not node_id:
                return []
            webhook_result = context.get(f'{node_id}_result', {})
            if not isinstance(webhook_result, dict):
                return []
            json_data = webhook_result.get('json', {}) or {}
            array = json_data.get('array')
            return array if isinstance(array, list) else []

        return []

    def _resolve_find_records_variable(self, instance: WorkflowInstance, node_id: Any) -> str:
        """根据 node_id 查找 find_records 节点配置以确定 result_variable，未配置则默认 'records'"""
        if not node_id:
            return 'records'
        try:
            node = WorkflowNode.query.get(self._to_uuid(node_id))
        except (ValueError, TypeError):
            return 'records'
        if node and node.config:
            return node.config.get('result_variable', 'records') or 'records'
        return 'records'

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

        data_array = self._resolve_loop_data_source(instance, data_source_config)

        if not data_array:
            if empty_result_action == 'error':
                raise ValueError('循环数据源为空')
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
            node_id=node.id,
            node_type='loop',
            status='running',
            input_context={
                'data_source': data_source_config,
                'array_length': len(data_array),
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
            'workflow': workflow.to_dict() if workflow else {},
            'loop': context.get('loop_context')
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


# 全局执行引擎实例，导入时即订阅事件总线
workflow_execution_engine = WorkflowExecutionEngine()


def init_workflow_execution_engine(app: Any) -> WorkflowExecutionEngine:
    """使用指定 Flask 应用初始化执行引擎"""
    global workflow_execution_engine
    workflow_event_bus.unsubscribe(workflow_execution_engine._event_handler)
    workflow_execution_engine = WorkflowExecutionEngine(app)
    return workflow_execution_engine
