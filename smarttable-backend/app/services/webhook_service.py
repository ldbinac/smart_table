"""
Webhook 投递服务模块

负责：
- 渲染请求体模板
- 计算 HMAC-SHA256 签名
- 发送 HTTP 请求并记录 WebhookDeliveryLog
- 指数退避重试与失败扫描
"""
import hashlib
import hmac
import json
import logging
import re
import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

import requests
from flask import current_app
from requests.exceptions import RequestException

from app.extensions import db
from app.models.webhook import (
    WebhookConfig,
    WebhookDeliveryLog,
    WebhookDeliveryStatus,
    WebhookMethod,
)


log = logging.getLogger(__name__)


class WebhookService:
    """Webhook 投递服务"""

    # 最大重试次数（不含首次投递）
    MAX_RETRIES = 5

    # 指数退避重试间隔（秒）：30s、2m、10m、1h、6h
    RETRY_DELAYS = [30, 120, 600, 3600, 21600]

    # HTTP 请求超时（秒）
    REQUEST_TIMEOUT = 30

    # 响应体日志长度限制（字节）
    RESPONSE_BODY_LIMIT = 4096

    # 自定义请求头
    SIGNATURE_HEADER = 'X-SmartTable-Signature'
    EVENT_HEADER = 'X-SmartTable-Event'

    # 重试调度线程
    _retry_thread: Optional[threading.Thread] = None
    _shutdown_event = threading.Event()
    _app: Optional[Any] = None
    _scheduler_lock = threading.Lock()

    @staticmethod
    def deliver(
        webhook_config: WebhookConfig,
        instance: Any = None,
        event_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        投递 Webhook

        Args:
            webhook_config: WebhookConfig 实例
            instance: WorkflowInstance 实例（可选）
            event_data: 事件数据（可选）

        Returns:
            投递结果字典
        """
        event_data = event_data or {}

        delivery_log = WebhookDeliveryLog(
            webhook_config_id=webhook_config.id,
            instance_id=instance.id if instance else None,
            status=WebhookDeliveryStatus.PENDING,
            retry_count=0,
        )
        db.session.add(delivery_log)
        db.session.commit()

        return WebhookService._execute_delivery(webhook_config, instance, event_data, delivery_log)

    @staticmethod
    def _execute_delivery(
        webhook_config: WebhookConfig,
        instance: Any,
        event_data: Dict[str, Any],
        delivery_log: WebhookDeliveryLog
    ) -> Dict[str, Any]:
        """
        执行单次 Webhook 投递并更新日志

        Args:
            webhook_config: WebhookConfig 实例
            instance: WorkflowInstance 实例（可选）
            event_data: 事件数据
            delivery_log: 投递日志记录

        Returns:
            投递结果字典
        """
        try:
            payload = WebhookService._build_payload(webhook_config, instance, event_data)
            headers = WebhookService._build_headers(webhook_config, event_data, payload)

            delivery_log.payload = payload
            delivery_log.status = WebhookDeliveryStatus.PENDING
            db.session.commit()

            method = WebhookService._normalize_method(webhook_config.method)
            url = webhook_config.url

            if method == 'GET':
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=WebhookService.REQUEST_TIMEOUT
                )
            else:
                response = requests.request(
                    method,
                    url,
                    data=payload.encode('utf-8'),
                    headers=headers,
                    timeout=WebhookService.REQUEST_TIMEOUT
                )

            response_body = response.text[:WebhookService.RESPONSE_BODY_LIMIT]
            now = datetime.now(timezone.utc)

            if 200 <= response.status_code < 300:
                delivery_log.status = WebhookDeliveryStatus.SUCCESS
                delivery_log.response_status = response.status_code
                delivery_log.response_body = response_body
                delivery_log.delivered_at = now
                delivery_log.next_retry_at = None
                delivery_log.error_message = None
                db.session.commit()

                log.info(f'[WebhookService] Webhook 投递成功: {delivery_log.id} -> {url}')
                return {
                    'success': True,
                    'status': 'success',
                    'delivery_log_id': str(delivery_log.id),
                    'response_status': response.status_code,
                    'response_body': response_body,
                }

            delivery_log.status = WebhookDeliveryStatus.FAILED
            delivery_log.response_status = response.status_code
            delivery_log.response_body = response_body
            delivery_log.error_message = f'HTTP {response.status_code}'
            db.session.commit()

            log.warning(
                f'[WebhookService] Webhook 投递失败: {delivery_log.id} -> {url}, '
                f'status={response.status_code}'
            )
            WebhookService._schedule_retry(webhook_config, instance, event_data, delivery_log)

            return {
                'success': False,
                'status': 'failed',
                'delivery_log_id': str(delivery_log.id),
                'response_status': response.status_code,
                'response_body': response_body,
                'error_message': delivery_log.error_message,
            }

        except RequestException as e:
            error_message = f'请求异常: {str(e)}'
            WebhookService._record_delivery_failure(delivery_log, error_message)
            WebhookService._schedule_retry(webhook_config, instance, event_data, delivery_log)
            log.warning(f'[WebhookService] Webhook 请求异常: {delivery_log.id} - {error_message}')
            return {
                'success': False,
                'status': 'failed',
                'delivery_log_id': str(delivery_log.id),
                'error_message': error_message,
            }

        except Exception as e:
            error_message = f'投递异常: {str(e)}'
            WebhookService._record_delivery_failure(delivery_log, error_message)
            WebhookService._schedule_retry(webhook_config, instance, event_data, delivery_log)
            log.exception(f'[WebhookService] Webhook 投递异常: {delivery_log.id}')
            return {
                'success': False,
                'status': 'failed',
                'delivery_log_id': str(delivery_log.id),
                'error_message': error_message,
            }

    @staticmethod
    def _build_payload(
        webhook_config: WebhookConfig,
        instance: Any,
        event_data: Dict[str, Any]
    ) -> str:
        """
        构建 Webhook 请求体

        优先使用 body_template，支持 {{event}}、{{record}}、{{workflow}}、{{instance}} 变量。
        模板为空时使用默认 JSON payload。
        """
        context = WebhookService._build_render_context(instance, event_data)

        body_template = webhook_config.body_template
        if body_template:
            return WebhookService._render_template(body_template, context)

        default_payload = {
            'event': event_data,
            'record': context.get('record', {}),
            'workflow': context.get('workflow', {}),
            'instance': context.get('instance', {}),
        }
        return json.dumps(default_payload, ensure_ascii=False, default=str)

    @staticmethod
    def _build_headers(
        webhook_config: WebhookConfig,
        event_data: Dict[str, Any],
        payload: str
    ) -> Dict[str, str]:
        """构建请求头，合并自定义头并添加签名与事件头"""
        headers: Dict[str, str] = {}
        config_headers = webhook_config.headers or {}
        headers.update({str(k): str(v) for k, v in config_headers.items()})

        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'

        event_type = event_data.get('event_type', 'unknown') if isinstance(event_data, dict) else 'unknown'
        headers[WebhookService.EVENT_HEADER] = str(event_type)

        secret = webhook_config.secret
        if secret:
            signature = WebhookService._compute_signature(secret, payload)
            headers[WebhookService.SIGNATURE_HEADER] = f'sha256={signature}'

        return headers

    @staticmethod
    def _compute_signature(secret: str, payload: str) -> str:
        """使用 HMAC-SHA256 计算签名，返回 hex 字符串"""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def _build_render_context(instance: Any, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建模板渲染上下文"""
        event_data = event_data or {}

        if instance is not None:
            from app.models.workflow import Workflow
            instance_dict = instance.to_dict() if hasattr(instance, 'to_dict') else {}
            workflow = Workflow.query.get(instance.workflow_id) if hasattr(instance, 'workflow_id') else None
            workflow_dict = workflow.to_dict() if workflow and hasattr(workflow, 'to_dict') else {}
        else:
            instance_dict = event_data.get('instance', {}) if isinstance(event_data, dict) else {}
            workflow_dict = event_data.get('workflow', {}) if isinstance(event_data, dict) else {}

        record = event_data.get('record', {}) if isinstance(event_data, dict) else {}

        return {
            'event': event_data,
            'record': record,
            'workflow': workflow_dict,
            'instance': instance_dict,
        }

    @staticmethod
    def _render_template(template: str, context: Dict[str, Any]) -> str:
        """将模板字符串中的 {{...}} 替换为 context 中的值"""
        pattern = re.compile(r'\{\{\s*(.*?)\s*\}\}')

        def replacer(match: re.Match) -> str:
            resolved = WebhookService._resolve_path(match.group(1).strip(), context)
            return str(resolved) if resolved is not None else ''

        return pattern.sub(replacer, template)

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
    def _normalize_method(method: Any) -> str:
        """统一请求方法为大写字符串"""
        if isinstance(method, WebhookMethod):
            return method.value
        return str(method).upper() if method else 'POST'

    @staticmethod
    def _record_delivery_failure(delivery_log: WebhookDeliveryLog, error_message: str) -> None:
        """记录投递失败"""
        delivery_log.status = WebhookDeliveryStatus.FAILED
        delivery_log.error_message = error_message
        db.session.commit()

    @staticmethod
    def _schedule_retry(
        webhook_config: WebhookConfig,
        instance: Any,
        event_data: Dict[str, Any],
        delivery_log: WebhookDeliveryLog
    ) -> None:
        """调度重试：更新日志并启动延迟定时器"""
        if delivery_log.retry_count >= WebhookService.MAX_RETRIES:
            log.info(f'[WebhookService] 达到最大重试次数，不再重试: {delivery_log.id}')
            return

        delay = WebhookService.RETRY_DELAYS[delivery_log.retry_count]
        next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)

        delivery_log.retry_count += 1
        delivery_log.next_retry_at = next_retry_at
        db.session.commit()

        log.info(
            f'[WebhookService] 安排 Webhook 重试: {delivery_log.id}, '
            f'第 {delivery_log.retry_count}/{WebhookService.MAX_RETRIES} 次, '
            f'延迟 {delay}s, 计划时间 {next_retry_at.isoformat()}'
        )

        try:
            app = current_app._get_current_object()
        except RuntimeError:
            app = WebhookService._app

        if app is None:
            log.warning(f'[WebhookService] 无法获取 Flask 应用，跳过定时重试: {delivery_log.id}')
            return

        def _retry_callback():
            try:
                with app.app_context():
                    WebhookService._execute_delivery(webhook_config, instance, event_data, delivery_log)
            except Exception as e:
                log.exception(f'[WebhookService] 定时重试执行失败: {delivery_log.id} - {e}')

        timer = threading.Timer(delay, _retry_callback)
        timer.daemon = True
        timer.name = f'webhook-retry-{delivery_log.id}'
        timer.start()

    @staticmethod
    def retry_pending() -> Dict[str, Any]:
        """
        扫描并重试失败的 Webhook 投递

        Returns:
            处理结果字典
        """
        results = {
            'processed': 0,
            'succeeded': 0,
            'failed': 0,
            'skipped': 0,
        }

        try:
            now = datetime.now(timezone.utc)
            pending_logs = WebhookDeliveryLog.query.filter(
                WebhookDeliveryLog.status == WebhookDeliveryStatus.FAILED,
                WebhookDeliveryLog.retry_count < WebhookService.MAX_RETRIES,
                WebhookDeliveryLog.next_retry_at <= now
            ).order_by(
                WebhookDeliveryLog.next_retry_at.asc()
            ).limit(100).all()

            for delivery_log in pending_logs:
                results['processed'] += 1

                webhook_config = delivery_log.webhook_config
                if not webhook_config:
                    results['failed'] += 1
                    continue

                try:
                    event_data = _parse_event_data(delivery_log.payload)
                    instance = delivery_log.instance
                    result = WebhookService._execute_delivery(
                        webhook_config, instance, event_data, delivery_log
                    )
                    if result.get('success'):
                        results['succeeded'] += 1
                    else:
                        results['failed'] += 1
                except Exception as e:
                    log.exception(f'[WebhookService] 重试扫描中处理失败: {delivery_log.id}')
                    results['failed'] += 1

            return {
                'success': True,
                'results': results,
                'message': (
                    f'扫描完成: 处理 {results["processed"]}, 成功 {results["succeeded"]}, '
                    f'失败 {results["failed"]}, 跳过 {results["skipped"]}'
                )
            }

        except Exception as e:
            log.exception(f'[WebhookService] 重试扫描失败: {e}')
            return {
                'success': False,
                'error': str(e),
                'results': results
            }

    @staticmethod
    def test_webhook(webhook_config: WebhookConfig) -> Dict[str, Any]:
        """
        测试 Webhook 投递

        Args:
            webhook_config: WebhookConfig 实例

        Returns:
            最后一次投递结果
        """
        sample_event_data = {
            'event_type': 'webhook.test',
            'record': {
                'id': str(uuid.uuid4()),
                'name': 'Sample Record',
                'status': 'active',
            },
            'workflow': {
                'id': str(uuid.uuid4()),
                'name': 'Sample Workflow',
            },
            'instance': {
                'id': str(uuid.uuid4()),
                'status': 'running',
            },
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

        return WebhookService.deliver(webhook_config, instance=None, event_data=sample_event_data)

    @classmethod
    def start_retry_scheduler(cls, app: Any) -> None:
        """启动后台重试扫描线程"""
        with cls._scheduler_lock:
            if cls._retry_thread is not None and cls._retry_thread.is_alive():
                log.info('[WebhookService] 重试调度线程已在运行')
                return

            cls._app = app
            cls._shutdown_event.clear()
            cls._retry_thread = threading.Thread(
                target=cls._retry_loop,
                args=(app,),
                daemon=True,
                name='webhook-retry-scheduler'
            )
            cls._retry_thread.start()
            log.info('[WebhookService] 重试调度线程已启动')

    @classmethod
    def stop_retry_scheduler(cls) -> None:
        """停止后台重试扫描线程"""
        cls._shutdown_event.set()
        with cls._scheduler_lock:
            thread = cls._retry_thread
            if thread is not None and thread.is_alive():
                thread.join(timeout=5)
                cls._retry_thread = None
        log.info('[WebhookService] 重试调度线程已停止')

    @classmethod
    def _retry_loop(cls, app: Any) -> None:
        """后台重试循环，每分钟扫描一次"""
        while not cls._shutdown_event.is_set():
            try:
                with app.app_context():
                    cls.retry_pending()
            except Exception as e:
                log.exception(f'[WebhookService] 后台重试扫描失败: {e}')
            cls._shutdown_event.wait(60)


def _parse_event_data(payload: Optional[str]) -> Dict[str, Any]:
    """从 payload 中解析 event 数据，用于重试"""
    if not payload:
        return {}
    try:
        data = json.loads(payload)
        return data.get('event', data)
    except (json.JSONDecodeError, TypeError):
        return {}
