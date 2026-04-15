"""
邮件队列服务模块
提供异步邮件发送功能，使用线程池处理邮件队列
"""
import logging
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from flask import current_app

from app.services.email_sender_service import EmailSenderService
from app.services.email_log_service import EmailLogService
from app.services.email_config_service import EmailConfigService
from app.models.email_log import EmailStatus

logger = logging.getLogger(__name__)


class EmailPriority(Enum):
    """邮件优先级"""
    HIGH = 1      # 高优先级：密码重置、账号安全相关
    NORMAL = 2    # 普通优先级：注册验证、通知
    LOW = 3       # 低优先级：营销邮件、批量通知


@dataclass
class EmailTask:
    """邮件任务数据类"""
    task_id: str
    to_email: str
    to_name: str
    subject: str
    html_content: str
    text_content: str
    template_key: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    priority: EmailPriority = EmailPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    callback: Optional[Callable] = None

    def __post_init__(self):
        if isinstance(self.priority, int):
            self.priority = EmailPriority(self.priority)


class EmailQueueService:
    """
    邮件队列服务类
    提供异步邮件发送功能，支持优先级队列和批量处理
    """

    _instance = None
    _lock = threading.Lock()

    # 线程池配置
    MAX_WORKERS = 5           # 最大工作线程数
    QUEUE_SIZE = 1000         # 队列最大容量
    BATCH_SIZE = 10           # 批量处理大小
    BATCH_INTERVAL = 5        # 批量处理间隔（秒）

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化邮件队列服务"""
        if self._initialized:
            return

        self._initialized = True
        self._task_queue = queue.PriorityQueue(maxsize=self.QUEUE_SIZE)
        self._executor = ThreadPoolExecutor(max_workers=self.MAX_WORKERS)
        self._is_running = False
        self._worker_thread = None
        self._batch_thread = None
        self._lock = threading.Lock()
        self._stats = {
            'queued': 0,
            'sent': 0,
            'failed': 0,
            'retried': 0
        }

    def start(self):
        """启动邮件队列服务"""
        with self._lock:
            if self._is_running:
                logger.warning('邮件队列服务已经在运行')
                return

            self._is_running = True
            self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self._worker_thread.start()

            self._batch_thread = threading.Thread(target=self._process_batch, daemon=True)
            self._batch_thread.start()

            logger.info('邮件队列服务已启动')

    def stop(self):
        """停止邮件队列服务"""
        with self._lock:
            if not self._is_running:
                return

            self._is_running = False
            self._executor.shutdown(wait=True)

            logger.info('邮件队列服务已停止')

    def enqueue(self, task: EmailTask) -> bool:
        """
        将邮件任务加入队列

        Args:
            task: 邮件任务

        Returns:
            是否成功加入队列
        """
        try:
            # 优先级队列使用 (priority, task) 格式
            self._task_queue.put((task.priority.value, task), block=False)
            with self._lock:
                self._stats['queued'] += 1
            logger.debug(f'邮件任务已加入队列: {task.task_id}')
            return True
        except queue.Full:
            logger.error('邮件队列已满，无法加入新任务')
            return False

    def enqueue_quick(self, to_email: str, to_name: str, template_key: str,
                      template_data: Dict[str, Any], priority: EmailPriority = EmailPriority.NORMAL,
                      callback: Optional[Callable] = None) -> str:
        """
        快速创建并加入邮件任务

        Args:
            to_email: 收件人邮箱
            to_name: 收件人名称
            template_key: 模板标识
            template_data: 模板数据
            priority: 优先级
            callback: 回调函数

        Returns:
            任务ID
        """
        import uuid
        task_id = str(uuid.uuid4())

        task = EmailTask(
            task_id=task_id,
            to_email=to_email,
            to_name=to_name,
            subject='',  # 将从模板获取
            html_content='',  # 将从模板获取
            text_content='',  # 将从模板获取
            template_key=template_key,
            template_data=template_data,
            priority=priority,
            callback=callback
        )

        if self.enqueue(task):
            return task_id
        else:
            raise Exception('无法将邮件任务加入队列')

    def _process_queue(self):
        """处理队列中的邮件任务"""
        while self._is_running:
            try:
                # 从队列获取任务（阻塞等待，超时1秒）
                priority, task = self._task_queue.get(timeout=1)
                self._executor.submit(self._send_email_task, task)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f'处理邮件队列时出错: {str(e)}')

    def _process_batch(self):
        """批量处理邮件"""
        while self._is_running:
            time.sleep(self.BATCH_INTERVAL)

            batch_tasks = []
            try:
                # 收集一批任务
                for _ in range(self.BATCH_SIZE):
                    if not self._task_queue.empty():
                        priority, task = self._task_queue.get_nowait()
                        batch_tasks.append(task)
                    else:
                        break

                if batch_tasks:
                    self._process_batch_tasks(batch_tasks)

            except Exception as e:
                logger.error(f'批量处理邮件时出错: {str(e)}')

    def _process_batch_tasks(self, tasks: List[EmailTask]):
        """
        批量处理邮件任务

        Args:
            tasks: 邮件任务列表
        """
        logger.info(f'批量处理 {len(tasks)} 个邮件任务')

        futures = []
        for task in tasks:
            future = self._executor.submit(self._send_email_task, task)
            futures.append(future)

        # 等待所有任务完成
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f'批量处理中的邮件任务失败: {str(e)}')

    def _send_email_task(self, task: EmailTask):
        """
        发送单个邮件任务

        Args:
            task: 邮件任务
        """
        try:
            # 检查邮件服务是否启用
            if not EmailConfigService.is_email_enabled():
                logger.warning('邮件服务未启用，跳过发送')
                self._handle_failure(task, '邮件服务未启用')
                return

            # 如果使用模板，获取模板内容
            if task.template_key:
                from app.services.email_template_service import EmailTemplateService

                template_result = EmailTemplateService.get_template(task.template_key)
                if not template_result['success']:
                    self._handle_failure(task, f'模板不存在: {task.template_key}')
                    return

                template = template_result['template']
                task.subject = EmailTemplateService.render_template(
                    template['subject'], task.template_data or {}
                )
                task.html_content = EmailTemplateService.render_template(
                    template['content_html'], task.template_data or {}
                )
                task.text_content = EmailTemplateService.render_template(
                    template['content_text'] or '', task.template_data or {}
                )

            # 创建邮件日志
            log = EmailLogService.create_log(
                recipient_email=task.to_email,
                recipient_name=task.to_name,
                template_key=task.template_key,
                subject=task.subject,
                status=EmailStatus.PENDING
            )

            # 发送邮件
            success, error = EmailSenderService.send_email(
                to_email=task.to_email,
                to_name=task.to_name,
                subject=task.subject,
                html_content=task.html_content,
                text_content=task.text_content
            )

            if success:
                EmailLogService.update_log_status(
                    log_id=log.id,
                    status=EmailStatus.SENT,
                    sent_at=datetime.now(timezone.utc)
                )
                with self._lock:
                    self._stats['sent'] += 1
                logger.info(f'邮件发送成功: {task.task_id} -> {task.to_email}')

                # 调用回调函数
                if task.callback:
                    try:
                        task.callback(True, None)
                    except Exception as e:
                        logger.error(f'回调函数执行失败: {str(e)}')
            else:
                raise Exception(error)

        except Exception as e:
            logger.error(f'邮件发送失败: {task.task_id} - {str(e)}')
            self._handle_failure(task, str(e))

    def _handle_failure(self, task: EmailTask, error_message: str):
        """
        处理发送失败

        Args:
            task: 邮件任务
            error_message: 错误信息
        """
        # 检查是否需要重试
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.priority = EmailPriority.HIGH  # 提升优先级

            # 延迟重试（指数退避）
            delay = 2 ** task.retry_count
            time.sleep(delay)

            if self.enqueue(task):
                with self._lock:
                    self._stats['retried'] += 1
                logger.info(f'邮件任务重新加入队列: {task.task_id}, 第 {task.retry_count} 次重试')
            else:
                logger.error(f'邮件任务重试失败，队列已满: {task.task_id}')
        else:
            with self._lock:
                self._stats['failed'] += 1
            logger.error(f'邮件任务最终失败: {task.task_id} - {error_message}')

            # 调用回调函数
            if task.callback:
                try:
                    task.callback(False, error_message)
                except Exception as e:
                    logger.error(f'回调函数执行失败: {str(e)}')

    def get_stats(self) -> Dict[str, Any]:
        """
        获取队列统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            return {
                'queued': self._stats['queued'],
                'sent': self._stats['sent'],
                'failed': self._stats['failed'],
                'retried': self._stats['retried'],
                'pending': self._task_queue.qsize(),
                'is_running': self._is_running
            }

    def clear_stats(self):
        """清除统计信息"""
        with self._lock:
            self._stats = {
                'queued': 0,
                'sent': 0,
                'failed': 0,
                'retried': 0
            }


# 全局邮件队列服务实例
email_queue = EmailQueueService()


def init_email_queue(app):
    """
    初始化邮件队列服务

    Args:
        app: Flask 应用实例
    """
    if EmailConfigService.is_email_enabled():
        email_queue.start()
        logger.info('邮件队列服务已随应用启动')
    else:
        logger.info('邮件服务未启用，跳过启动邮件队列服务')


def shutdown_email_queue():
    """关闭邮件队列服务"""
    email_queue.stop()
