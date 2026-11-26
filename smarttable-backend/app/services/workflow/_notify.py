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

class WorkflowNotifyMixin:
    """WorkflowNotifyMixin — 7 个方法"""

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

    def _resolve_notify_base_id(instance: WorkflowInstance) -> Optional[Any]:
        """解析站内信节点所属空间 ID（用于按空间批量下发）"""
        workflow = Workflow.query.get(instance.workflow_id)
        return workflow.base_id if workflow else None