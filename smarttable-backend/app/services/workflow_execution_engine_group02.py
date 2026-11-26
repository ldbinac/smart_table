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

class WorkflowExecutionEngineGroup02Mixin:
    """Mixin auto-split"""
    
    """工作流执行引擎"""
    
    SYSTEM_USER_ID = '00000000-0000-0000-0000-000000000000'
    
    MAX_TRIGGER_DEPTH = 3
    
    RECORD_LOCK_TIMEOUT = 30
    
    MAX_NOTIFY_RECIPIENTS = 200
    
    NOTIFY_RECIPIENT_SOURCES = ('fixed', 'field', 'trigger_user', 'record_creator', 'base_members')
    
    
    def _execute_update_record(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行更新记录动作。
    
        在更新主记录自身表内容的同时，支持通过 ``related_updates`` 配置同步更新
        其他关联表的内容。所有更新（主记录 + 全部关联表记录）在同一个数据库事务中
        完成：只要任一环节失败，整体回滚并记录执行日志，保证多表数据一致性。
        """
        config = node.config or {}
        record_id = config.get('record_id') or instance.trigger_record_id
        if not record_id:
            raise ValueError('missing_target_record_id')
    
        main_record = RecordService.get_record_by_id(str(record_id))
        if not main_record:
            raise ValueError(translate('record_not_found', record_id))
    
        context = self._build_render_context(instance)
    
        # 1) 主记录（自身表）字段更新
        updates = config.get('updates', []) or []
        main_values: Dict[str, Any] = {}
        for mapping in updates:
            field_id = mapping.get('field_id')
            if not field_id:
                continue
            main_values[field_id] = self.render_template(mapping.get('value_template', ''), context)
    
        # 2) 解析关联表同步更新任务
        related_updates = config.get('related_updates', []) or []
        resolved: List[Tuple[Record, Dict[str, Any]]] = []
        for idx, task in enumerate(related_updates):
            if not isinstance(task, dict):
                continue
            target_table_id = task.get('target_table_id')
            if not target_table_id:
                raise ValueError(translate('related_update_missing_target_table', idx + 1))
    
            table = Table.query.get(self._to_uuid(target_table_id))
            if not table:
                raise ValueError(translate('target_table_not_found', target_table_id))
    
            candidate_ids = self._resolve_related_record_ids(main_record, task, context)
            field_mappings = task.get('field_mappings', []) or []
            if not field_mappings:
                continue
    
            query = Record.query.filter_by(
                table_id=self._to_uuid(target_table_id), is_deleted=False
            )
            if candidate_ids is not None:
                query = query.filter(Record.id.in_(candidate_ids))
            candidate_records = query.all()
    
            # 同步触发方式：condition 模式下，仅当关联表中存在满足「同步触发条件」的记录时才执行本次同步。
            # 注意：条件字段取自关联表，需逐条在关联记录上下文（rec_context）中求值的「存在性」判断。
            trigger = task.get('trigger', 'always')
            if trigger == 'condition':
                trigger_condition = self._render_condition_values(
                    task.get('trigger_condition', []) or [], context
                )
                trigger_conjunction = task.get('trigger_condition_conjunction', 'and')
                trigger_matched = False
                for rec in candidate_records:
                    rec_context = self._build_related_context(context, main_record, rec)
                    if self.evaluate_condition(
                        {'conditions': trigger_condition, 'conjunction': trigger_conjunction}, rec_context
                    ):
                        trigger_matched = True
                        break
                if not trigger_matched:
                    continue
    
            conditions = self._render_condition_values(task.get('conditions', []) or [], context)
            conditions_conjunction = task.get('conditions_conjunction', 'and')
            for rec in candidate_records:
                rec_context = self._build_related_context(context, main_record, rec)
                if conditions and not self.evaluate_condition(
                    {'conditions': conditions, 'conjunction': conditions_conjunction}, rec_context
                ):
                    continue
                values: Dict[str, Any] = {}
                for m in field_mappings:
                    tf = m.get('target_field_id')
                    if not tf:
                        continue
                    values[tf] = self.render_template(m.get('value_template', ''), rec_context)
                if values:
                    resolved.append((rec, values))
    
        # 3) 单事务执行：任一环节失败则整体回滚，保证多表一致性
        try:
            if main_values:
                RecordService.update_record(
                    main_record, main_values, updated_by=self.SYSTEM_USER_ID, commit=False
                )
            related_updated = 0
            for rec, values in resolved:
                RecordService.update_record(
                    rec, values, updated_by=self.SYSTEM_USER_ID, commit=False
                )
                related_updated += 1
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            log.error(
                f'[WorkflowExecutionEngine] 更新记录节点多表更新失败，已整体回滚: '
                f'instance={instance.id}, node={node.id}, error={e}'
            )
            raise
    
        return {
            'record_id': str(main_record.id),
            'main_updated': bool(main_values),
            'related_updated': related_updated,
        }
    
    def _resolve_related_record_ids(
        self, main_record: Record, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Optional[List[str]]:
        """根据关联字段解析出需要同步更新的目标记录 ID 列表。
    
        返回 ``None`` 表示不限定（将对目标表全表按条件过滤）；
        返回空列表表示没有关联到任何记录（即本次关联更新无目标）。
        """
        link_field_id = task.get('link_field_id')
        if not link_field_id:
            return None
        raw = (main_record.values or {}).get(link_field_id)
        if raw is None:
            return []
        if isinstance(raw, str):
            return [raw]
        if isinstance(raw, list):
            ids: List[str] = []
            for item in raw:
                if isinstance(item, str):
                    ids.append(item)
                elif isinstance(item, dict) and item.get('id'):
                    ids.append(str(item['id']))
            return ids
        return []
    
    def _build_related_context(
        self, context: Dict[str, Any], main_record: Record, rec: Record
    ) -> Dict[str, Any]:
        """构建关联记录更新时的模板渲染上下文。
    
        主记录仍通过 ``record`` 访问；关联记录字段除了以 ``target_record`` 显式暴露外，
        其字段值（以字段 ID 为键）也提升到顶层，便于在条件与映射中直接引用。
        """
        rec_values = dict(rec.values or {})
        related_ctx = dict(context)
        related_ctx['target_record'] = rec_values
        for k, v in rec_values.items():
            related_ctx.setdefault(k, v)
        return related_ctx
    
    def _render_condition_values(
        self, conditions: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """递归渲染条件中的模板值（如 ``{{record.field_id}}``），便于在条件中引用主记录。"""
        rendered: List[Dict[str, Any]] = []
        for c in conditions:
            if not isinstance(c, dict):
                continue
            rc = dict(c)
            if isinstance(rc.get('value'), str):
                rc['value'] = self.render_template(rc['value'], context)
            if isinstance(rc.get('conditions'), list):
                rc['conditions'] = self._render_condition_values(rc['conditions'], context)
            rendered.append(rc)
        return rendered
    
    def _execute_create_record(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行创建记录动作"""
        config = node.config or {}
        table_id = config.get('target_table_id')
        if not table_id:
            raise ValueError('missing_target_table_id')
    
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
            raise ValueError('missing_target_table_id')
    
        table = Table.query.get(self._to_uuid(target_table_id))
        if not table:
            raise ValueError(translate('target_table_not_found', target_table_id))
    
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
        """执行发送通知动作（站内信先于邮件，邮件不可用时站内信仍独立工作）"""
        config = node.config or {}
        context = self._build_render_context(instance)
        content_mode = config.get('content_mode', 'custom')
    
        to_email = self._resolve_email_recipients(config, context)
        # to_email 可能是逗号分隔的多个邮箱，拆分后逐个发送
        emails = [e.strip() for e in to_email.split(',') if e.strip()]
    
        if content_mode == 'custom':
            subject = self.render_template(config.get('subject', ''), context)
            body = self.render_template(config.get('body', ''), context)
    
            last_result = None
            for email in emails:
                result = NotificationService.send_notification(
                    recipient_email=email,
                    title=str(subject),
                    content=str(body),
                    source='workflow'
                )
                last_result = result
                if not result['success']:
                    raise ValueError(translate('notification_send_failed', result.get('error')))
            return {
                'status': 'sent',
                'to_email': to_email,
                'notification_id': last_result.get('notification_id') if last_result else None
            }
    
        # template 模式
        template_key = config.get('template_key')
        if not template_key:
            raise ValueError('missing_email_template_key')
    
        to_name = self.render_template(config.get('to_name', ''), context)
        template_data = {
            k: self.render_template(v, context)
            for k, v in config.get('template_data', {}).items()
        }
    
        last_result = None
        for email in emails:
            result = NotificationService.send_notification(
                recipient_email=str(email),
                recipient_user_id=None,
                template_key=template_key,
                template_data=template_data,
                source='workflow'
            )
            last_result = result
        return {
            'status': 'sent',
            'to_email': to_email,
            'notification_id': last_result.get('notification_id') if last_result else None
        }
    
    @staticmethod
    def _extract_user_ids_from_field_value(value: Any) -> List[str]:
        """从成员/协作者字段值中提取用户 ID 列表
    
        支持以下格式：
        - UUID 字符串（成员字段直接存用户 ID）
        - 逗号分隔的 UUID / 邮箱字符串
        - 邮箱字符串（反查用户表）
        - 包含 id / user_id / email 键的对象或其列表
        """
        from app.models.user import User
    
        if value is None:
            return []
    
        if isinstance(value, dict):
            items: List[Any] = [value]
        elif isinstance(value, list):
            items = list(value)
        elif isinstance(value, str):
            items = [part.strip() for part in value.split(',') if part.strip()]
        else:
            items = [value]
    
        user_ids: List[str] = []
        for item in items:
            raw_id = None
            email = None
            if isinstance(item, dict):
                raw_id = item.get('id') or item.get('user_id') or item.get('userId')
                email = item.get('email')
            elif isinstance(item, str):
                if '@' in item:
                    email = item
                else:
                    raw_id = item
            elif item is not None:
                # UUID 对象等非字符串标量（如 Record.created_by 在 PostgreSQL 下返回 UUID）
                raw_id = item
    
            if raw_id:
                try:
                    user_ids.append(str(uuid.UUID(str(raw_id))))
                    continue
                except (ValueError, TypeError, AttributeError):
                    pass
    
            if email:
                user = User.query.filter_by(email=email).first()
                if user:
                    user_ids.append(str(user.id))
        return user_ids
    
    @staticmethod
    def _resolve_notify_base_id(instance: WorkflowInstance) -> Optional[Any]:
        """解析站内信节点所属空间 ID（用于按空间批量下发）"""
        workflow = Workflow.query.get(instance.workflow_id)
        return workflow.base_id if workflow else None
    
