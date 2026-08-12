"""
站内信重试服务模块
处理站内信发送失败后的重试逻辑和待发送站内信的批量处理
"""
import logging
import time
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.models.notification import Notification, NotificationStatus
from app.services.email_sender_service import EmailSenderService
from app.services.email_config_service import EmailConfigService

logger = logging.getLogger(__name__)


class NotificationRetryService:
    """
    站内信重试服务类
    提供站内信重试调度、失败处理和批量处理功能
    """

    # 最大重试次数
    MAX_RETRY_COUNT = 3

    # 重试延迟配置（秒）- 指数退避
    RETRY_DELAYS = [60, 300, 1800]  # 1分钟, 5分钟, 30分钟

    # 可重试的错误类型
    RETRYABLE_ERRORS = [
        'ConnectionError',
        'OperationalError',
        'Temporary failure',
        'Service unavailable',
        'Network is unreachable',
        'Connection timed out',
        'Database is locked',
        '数据库连接失败',
        '数据库临时错误',
        '临时错误'
    ]

    # 不可重试的错误类型
    NON_RETRYABLE_ERRORS = [
        'IntegrityError',
        'DataError',
        'ProgrammingError',
        'Invalid email address',
        '参数错误',
        '数据格式错误'
    ]

    @staticmethod
    def schedule_retry(notification_id: str, retry_count: int) -> Dict[str, Any]:
        """
        安排重试

        Args:
            notification_id: 站内信 ID
            retry_count: 当前重试次数

        Returns:
            包含操作结果的字典：
            - success: 是否成功
            - should_retry: 是否应该重试
            - scheduled_at: 计划重试时间（成功时）
            - delay_seconds: 延迟秒数
            - retry_count: 更新后的重试次数
            - error: 错误信息（失败时）
        """
        try:
            notification = Notification.query.get(notification_id)

            if not notification:
                return {
                    'success': False,
                    'error': f'站内信不存在：{notification_id}'
                }

            # 检查是否达到最大重试次数
            if retry_count >= NotificationRetryService.MAX_RETRY_COUNT:
                return {
                    'success': False,
                    'should_retry': False,
                    'error': f'已达到最大重试次数：{NotificationRetryService.MAX_RETRY_COUNT}'
                }

            # 计算下次重试时间
            delay = NotificationRetryService.RETRY_DELAYS[
                min(retry_count, len(NotificationRetryService.RETRY_DELAYS) - 1)
            ]
            scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=delay)

            # 更新站内信状态为重试中（mark_as_retrying 会自增 retry_count）
            notification.mark_as_retrying()
            db.session.commit()

            logger.info(
                f'安排站内信重试：{notification_id}，'
                f'第 {retry_count + 1} 次重试，计划时间：{scheduled_at}'
            )

            return {
                'success': True,
                'should_retry': True,
                'scheduled_at': scheduled_at.isoformat(),
                'delay_seconds': delay,
                'retry_count': retry_count + 1
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'安排站内信重试失败：{str(e)}')
            return {
                'success': False,
                'error': '安排重试失败，请稍后重试'
            }

    @staticmethod
    def should_retry(error: str) -> bool:
        """
        判断是否应重试

        Args:
            error: 错误信息

        Returns:
            是否应该重试
        """
        error_lower = error.lower()

        # 检查是否为不可重试的错误
        for non_retryable in NotificationRetryService.NON_RETRYABLE_ERRORS:
            if non_retryable.lower() in error_lower:
                return False

        # 检查是否为可重试的错误
        for retryable in NotificationRetryService.RETRYABLE_ERRORS:
            if retryable.lower() in error_lower:
                return True

        # 默认重试（保守策略）
        return True

    @staticmethod
    def process_pending_notifications(
        batch_size: int = 50,
        process_failed: bool = True
    ) -> Dict[str, Any]:
        """
        处理待发送站内信

        Args:
            batch_size: 批量处理大小
            process_failed: 是否处理失败的站内信（重试）

        Returns:
            包含处理结果的字典
        """
        results = {
            'processed': 0,
            'sent': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }

        try:
            # 获取待发送的站内信
            pending_notifications = Notification.query.filter(
                Notification.status == NotificationStatus.PENDING
            ).order_by(
                Notification.created_at.asc()
            ).limit(batch_size).all()

            # 如果需要处理失败的站内信，获取可重试的失败站内信
            if process_failed:
                failed_notifications = Notification.query.filter(
                    Notification.status == NotificationStatus.FAILED,
                    Notification.retry_count < NotificationRetryService.MAX_RETRY_COUNT
                ).order_by(
                    Notification.created_at.asc()
                ).limit(batch_size).all()

                # 合并列表，去重
                seen_ids = {str(n.id) for n in pending_notifications}
                for n in failed_notifications:
                    if str(n.id) not in seen_ids:
                        pending_notifications.append(n)

            if not pending_notifications:
                return {
                    'success': True,
                    'results': results,
                    'message': '没有待处理的站内信'
                }

            email_enabled = EmailConfigService.is_email_enabled()

            for notification in pending_notifications:
                results['processed'] += 1

                try:
                    # 检查是否应该跳过（重试时间未到）
                    if notification.status == NotificationStatus.FAILED:
                        retry_delay = NotificationRetryService.RETRY_DELAYS[
                            min(
                                notification.retry_count,
                                len(NotificationRetryService.RETRY_DELAYS) - 1
                            )
                        ]
                        min_retry_time = notification.created_at + timedelta(seconds=retry_delay)
                        if datetime.now(timezone.utc) < min_retry_time:
                            results['skipped'] += 1
                            continue

                        # 标记为重试中
                        notification.mark_as_retrying()
                        db.session.commit()

                    # 标记站内信为已发送
                    notification.mark_as_sent()
                    db.session.commit()

                    # 视情况重试邮件
                    if notification.recipient_email and email_enabled:
                        try:
                            success, error = EmailSenderService.send_email_quick(
                                to_email=notification.recipient_email,
                                to_name=None,
                                subject=notification.title,
                                html_content=notification.content,
                                text_content=notification.content_text,
                                template_key=notification.template_key,
                                template_data=notification.extra_metadata or {}
                            )
                            if not success:
                                logger.warning(
                                    f'站内信邮件发送失败：{notification.id}，{error}'
                                )
                        except Exception as e:
                            logger.warning(
                                f'站内信邮件发送异常：{notification.id}，{str(e)}'
                            )

                    results['sent'] += 1
                    logger.info(f'站内信处理成功：{notification.id}')

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f'处理站内信失败：{notification.id}，错误：{error_msg}')

                    # 检查是否应该重试
                    if NotificationRetryService.should_retry(error_msg):
                        retry_result = NotificationRetryService.schedule_retry(
                            str(notification.id),
                            notification.retry_count
                        )
                        if retry_result.get('should_retry'):
                            results['skipped'] += 1
                            logger.warning(f'站内信处理失败，已安排重试：{notification.id}')
                        else:
                            try:
                                notification = Notification.query.get(str(notification.id))
                                notification.mark_as_failed(error_msg)
                                db.session.commit()
                            except Exception:
                                db.session.rollback()
                            results['failed'] += 1
                    else:
                        try:
                            notification = Notification.query.get(str(notification.id))
                            notification.mark_as_failed(error_msg)
                            db.session.commit()
                        except Exception:
                            db.session.rollback()
                        results['failed'] += 1
                        results['errors'].append({
                            'notification_id': str(notification.id),
                            'error': error_msg,
                            'reason': '不可重试的错误'
                        })

                # 短暂延迟，避免处理过快
                time.sleep(0.1)

            return {
                'success': True,
                'results': results,
                'message': f'处理完成：成功 {results["sent"]}，失败 {results["failed"]}，跳过 {results["skipped"]}'
            }

        except Exception as e:
            logger.error(f'处理待发送站内信失败：{str(e)}')
            return {
                'success': False,
                'error': '处理失败，请稍后重试',
                'results': results
            }

    @staticmethod
    def retry_failed_notification(notification_id: str) -> Dict[str, Any]:
        """
        重试单条失败的站内信

        Args:
            notification_id: 站内信 ID

        Returns:
            包含操作结果的字典
        """
        try:
            notification = Notification.query.get(notification_id)

            if not notification:
                return {
                    'success': False,
                    'error': f'站内信不存在：{notification_id}'
                }

            if notification.status not in [NotificationStatus.FAILED, NotificationStatus.RETRYING]:
                return {
                    'success': False,
                    'error': f'站内信状态不允许重试：{notification.status.value}'
                }

            if notification.retry_count >= NotificationRetryService.MAX_RETRY_COUNT:
                return {
                    'success': False,
                    'error': '已达到最大重试次数'
                }

            # 重新标记为已发送
            notification.mark_as_sent()
            db.session.commit()

            # 视情况重试邮件
            if notification.recipient_email and EmailConfigService.is_email_enabled():
                try:
                    success, error = EmailSenderService.send_email_quick(
                        to_email=notification.recipient_email,
                        to_name=None,
                        subject=notification.title,
                        html_content=notification.content,
                        text_content=notification.content_text,
                        template_key=notification.template_key,
                        template_data=notification.extra_metadata or {}
                    )
                    if not success:
                        logger.warning(f'站内信重试邮件发送失败：{notification_id}，{error}')
                except Exception as e:
                    logger.warning(f'站内信重试邮件发送异常：{notification_id}，{str(e)}')

            logger.info(f'站内信重试处理成功：{notification_id}')

            return {
                'success': True,
                'message': '站内信重试处理成功'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'重试站内信失败：{str(e)}')

            # 标记为失败
            try:
                notification = Notification.query.get(notification_id)
                if notification:
                    notification.mark_as_failed('重试处理失败')
                    db.session.commit()
            except Exception:
                db.session.rollback()

            return {
                'success': False,
                'error': '重试失败，请稍后重试'
            }

    @staticmethod
    def get_retry_stats() -> Dict[str, Any]:
        """
        获取站内信重试统计信息

        Returns:
            包含重试统计的字典
        """
        try:
            # 待发送数量
            pending_count = Notification.query.filter(
                Notification.status == NotificationStatus.PENDING
            ).count()

            # 重试中数量
            retrying_count = Notification.query.filter(
                Notification.status == NotificationStatus.RETRYING
            ).count()

            # 可重试的失败数量
            retryable_failed_count = Notification.query.filter(
                Notification.status == NotificationStatus.FAILED,
                Notification.retry_count < NotificationRetryService.MAX_RETRY_COUNT
            ).count()

            # 不可重试的失败数量
            non_retryable_failed_count = Notification.query.filter(
                Notification.status == NotificationStatus.FAILED,
                Notification.retry_count >= NotificationRetryService.MAX_RETRY_COUNT
            ).count()

            # 按重试次数统计
            retry_distribution = []
            for i in range(NotificationRetryService.MAX_RETRY_COUNT + 1):
                count = Notification.query.filter(
                    Notification.retry_count == i,
                    Notification.status.in_([
                        NotificationStatus.FAILED,
                        NotificationStatus.RETRYING
                    ])
                ).count()
                retry_distribution.append({
                    'retry_count': i,
                    'count': count
                })

            return {
                'success': True,
                'stats': {
                    'pending': pending_count,
                    'retrying': retrying_count,
                    'retryable_failed': retryable_failed_count,
                    'non_retryable_failed': non_retryable_failed_count,
                    'total_to_process': pending_count + retrying_count + retryable_failed_count,
                    'retry_distribution': retry_distribution,
                    'max_retries': NotificationRetryService.MAX_RETRY_COUNT,
                    'retry_delays': NotificationRetryService.RETRY_DELAYS
                }
            }

        except Exception as e:
            logger.error(f'获取站内信重试统计失败：{str(e)}')
            return {
                'success': False,
                'error': '获取统计失败，请稍后重试'
            }

    @staticmethod
    def cancel_retry(notification_id: str) -> Dict[str, Any]:
        """
        取消站内信重试

        Args:
            notification_id: 站内信 ID

        Returns:
            包含操作结果的字典
        """
        try:
            notification = Notification.query.get(notification_id)

            if not notification:
                return {
                    'success': False,
                    'error': f'站内信不存在：{notification_id}'
                }

            if notification.status not in [NotificationStatus.PENDING, NotificationStatus.RETRYING]:
                return {
                    'success': False,
                    'error': f'站内信状态不允许取消：{notification.status.value}'
                }

            # 标记为失败并设置重试次数为最大值
            notification.mark_as_failed('用户取消重试')
            notification.retry_count = NotificationRetryService.MAX_RETRY_COUNT
            db.session.commit()

            logger.info(f'取消站内信重试：{notification_id}')

            return {
                'success': True,
                'message': '已取消重试'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'取消站内信重试失败：{str(e)}')
            return {
                'success': False,
                'error': '取消失败，请稍后重试'
            }
