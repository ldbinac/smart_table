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

class WorkflowExecutionEngineGroup03Mixin:
    """Mixin auto-split"""
    
    """工作流执行引擎"""
    
    SYSTEM_USER_ID = '00000000-0000-0000-0000-000000000000'
    
    MAX_TRIGGER_DEPTH = 3
    
    RECORD_LOCK_TIMEOUT = 30
    
    MAX_NOTIFY_RECIPIENTS = 200
    
    NOTIFY_RECIPIENT_SOURCES = ('fixed', 'field', 'trigger_user', 'record_creator', 'base_members')
    
    
    def _resolve_notify_recipients(
        self,
        instance: WorkflowInstance,
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[str]:
        """解析站内信节点的接收人用户 ID 列表
    
        支持多来源叠加：fixed / field / trigger_user / record_creator / base_members。
        解析结果归一化后去重（保序），并一次性校验用户存在性，避免外键写入失败。
    
        Returns:
            去重后的合法用户 ID 字符串列表
        """
        from app.models.user import User
        from app.models.base import BaseMember
    
        sources = config.get('recipient_sources')
        if isinstance(sources, str):
            sources = [sources]
        if not sources:
            # 兼容单来源结构
            legacy_type = config.get('recipient_type')
            sources = [legacy_type] if legacy_type else []
    
        record = context.get('record') or {}
        candidates: List[str] = []
    
        for source in sources:
            if source == 'fixed':
                for raw in config.get('recipient_user_ids') or []:
                    if isinstance(raw, dict):
                        raw = raw.get('id') or raw.get('user_id')
                    if raw:
                        candidates.append(str(raw))
    
            elif source == 'field':
                field_ids = config.get('recipient_field_ids') or []
                if isinstance(field_ids, str):
                    field_ids = [field_ids]
                for field_id in field_ids:
                    if isinstance(record, dict):
                        candidates.extend(
                            self._extract_user_ids_from_field_value(record.get(field_id))
                        )
    
            elif source == 'trigger_user':
                actor_id = (context.get('trigger') or {}).get('actor_id')
                if actor_id and str(actor_id) != self.SYSTEM_USER_ID:
                    candidates.append(str(actor_id))
    
            elif source == 'record_creator':
                creator = record.get('created_by') if isinstance(record, dict) else None
                if not creator and instance.trigger_record_id:
                    db_record = RecordService.get_record_by_id(str(instance.trigger_record_id))
                    creator = db_record.created_by if db_record else None
                candidates.extend(self._extract_user_ids_from_field_value(creator))
    
            elif source == 'base_members':
                base_id = self._resolve_notify_base_id(instance)
                if base_id:
                    members = BaseMember.query.filter_by(base_id=base_id).all()
                    candidates.extend(str(m.user_id) for m in members if m.user_id)
    
        # 归一化 + 去重（保序）
        normalized: List[str] = []
        seen: set = set()
        for raw in candidates:
            try:
                uid = str(uuid.UUID(str(raw)))
            except (ValueError, TypeError, AttributeError):
                log.warning(f'[WorkflowExecutionEngine] 站内信节点解析到非法用户 ID，已忽略: {raw}')
                continue
            if uid in seen:
                continue
            seen.add(uid)
            normalized.append(uid)
    
        if not normalized:
            return []
    
        # 一次性校验用户存在性，避免外键写入失败
        existing = User.query.filter(User.id.in_(normalized)).all()
        existing_ids = {str(user.id) for user in existing}
        missing_count = len(normalized) - len(existing_ids)
        if missing_count > 0:
            log.warning(
                f'[WorkflowExecutionEngine] 站内信节点忽略 {missing_count} 个不存在的用户 ID'
            )
        return [uid for uid in normalized if uid in existing_ids]
    
    def _execute_notify(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行站内信通知节点
    
        按配置的接收人来源解析用户，仅写入站内信（send_email=False），不走邮件通道。
        解析不到接收人时跳过该节点并记录告警，不中断流程。
        """
        config = node.config or {}
        context = self._build_render_context(instance)
    
        recipient_ids = self._resolve_notify_recipients(instance, config, context)
        if not recipient_ids:
            log.warning(
                f'[WorkflowExecutionEngine] 站内信节点 {node.id} 未解析到接收人，跳过发送，'
                f'配置来源: {config.get("recipient_sources")}'
            )
            return {
                'status': 'skipped',
                'reason': 'no_recipients',
                'recipient_count': 0,
                'notification_ids': [],
            }
    
        truncated = False
        if len(recipient_ids) > self.MAX_NOTIFY_RECIPIENTS:
            truncated = True
            log.warning(
                f'[WorkflowExecutionEngine] 站内信节点 {node.id} 接收人 {len(recipient_ids)} 人，'
                f'超出上限 {self.MAX_NOTIFY_RECIPIENTS}，已截断'
            )
            recipient_ids = recipient_ids[:self.MAX_NOTIFY_RECIPIENTS]
    
        title = str(self.render_template(config.get('subject', ''), context) or '')
        body_text = str(self.render_template(config.get('body', ''), context) or '')
    
        if not title.strip():
            raise ValueError(translate('notify_title_required'))
    
        # Notification.title 为 String(500)，超出会导致写入失败
        if len(title) > 500:
            title = title[:500]
    
        # 正文按纯文本转义后写入，避免消息中心以 HTML 渲染时产生 XSS
        escaped_body = html.escape(body_text).replace('\r\n', '\n').replace('\n', '<br>')
    
        notification_ids: List[str] = []
        for user_id in recipient_ids:
            result = NotificationService.send_notification(
                recipient_user_id=self._to_uuid(user_id),
                title=title,
                content=escaped_body,
                content_text=body_text,
                source='workflow',
                send_email=False,
            )
            if not result.get('success'):
                raise ValueError(translate('notification_send_failed', result.get('error')))
            if result.get('notification_id'):
                notification_ids.append(result['notification_id'])
    
        log.info(
            f'[WorkflowExecutionEngine] 站内信节点 {node.id} 已发送，'
            f'接收人 {len(recipient_ids)} 人'
        )
        return {
            'status': 'sent',
            'recipient_count': len(recipient_ids),
            'notification_ids': notification_ids,
            'truncated': truncated,
        }
    
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
            node_id = data_source_config.get('node_id')
            if not field_id:
                log.warning(
                    f'[WorkflowExecutionEngine] find_records_column 数据源缺少 field_id，'
                    f'node_id={node_id}，返回空数组'
                )
                return []
            result_variable = self._resolve_find_records_variable(instance, node_id)
            result = context.get(result_variable, {})
            records = result.get('records', []) if isinstance(result, dict) else []
            if not isinstance(records, list):
                records = []
    
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
    
            if not flattened:
                log.warning(
                    f'[WorkflowExecutionEngine] find_records_column 提取为空: '
                    f'field_id={field_id}, node_id={node_id}, '
                    f'records 数量={len(records)}, '
                    f'提示: 如果需要遍历全部记录，请将 data_source.type 改为 find_records_all'
                )
    
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
    
