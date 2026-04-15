"""
邮件重试服务模块
处理邮件发送失败后的重试逻辑和待发送邮件的处理
"""
import logging
import smtplib
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

from flask import current_app

from app.extensions import db
from app.models.email_log import EmailLog, EmailStatus
from app.services.email_config_service import EmailConfigService
from app.services.email_sender_service import EmailSenderService
from app.services.email_template_service import EmailTemplateService
from app.services.email_log_service import EmailLogService

logger = logging.getLogger(__name__)


class EmailRetryService:
    """
    邮件重试服务类
    提供邮件重试调度、失败处理和批量处理功能
    """

    # 最大重试次数
    MAX_RETRY_COUNT = 3

    # 重试延迟配置（秒）- 指数退避
    RETRY_DELAYS = [60, 300, 1800]  # 1分钟, 5分钟, 30分钟

    # 可重试的错误类型
    RETRYABLE_ERRORS = [
        'ConnectionError',
        'SMTPConnectError',
        'SMTPServerDisconnected',
        'SMTPDataError',
        'Temporary failure',
        'Service unavailable',
        'Network is unreachable',
        'Connection timed out',
        'Temporary authentication failure'
    ]

    # 不可重试的错误类型
    NON_RETRYABLE_ERRORS = [
        'SMTPRecipientsRefused',
        'SMTPSenderRefused',
        'SMTPAuthenticationError',
        'Invalid email address',
        'Domain not found',
        'Mailbox does not exist'
    ]

    @staticmethod
    def schedule_retry(log_id: str, retry_count: int) -> Dict[str, Any]:
        """
        安排重试

        Args:
            log_id: 邮件日志 ID
            retry_count: 当前重试次数

        Returns:
            包含操作结果的字典：
            - success: 是否成功
            - scheduled_at: 计划重试时间（成功时）
            - should_retry: 是否应该重试
            - error: 错误信息（失败时）
        """
        try:
            email_log = EmailLog.query.get(log_id)

            if not email_log:
                return {
                    'success': False,
                    'error': f'日志不存在：{log_id}'
                }

            # 检查是否达到最大重试次数
            if retry_count >= EmailRetryService.MAX_RETRY_COUNT:
                return {
                    'success': False,
                    'should_retry': False,
                    'error': f'已达到最大重试次数：{EmailRetryService.MAX_RETRY_COUNT}'
                }

            # 计算下次重试时间
            delay = EmailRetryService.RETRY_DELAYS[min(retry_count, len(EmailRetryService.RETRY_DELAYS) - 1)]
            scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=delay)

            # 更新日志状态
            email_log.mark_as_retrying()
            db.session.commit()

            logger.info(f'安排邮件重试：{log_id}，第 {retry_count + 1} 次重试，计划时间：{scheduled_at}')

            return {
                'success': True,
                'should_retry': True,
                'scheduled_at': scheduled_at.isoformat(),
                'delay_seconds': delay,
                'retry_count': retry_count + 1
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'安排邮件重试失败：{str(e)}')
            return {
                'success': False,
                'error': f'安排重试失败：{str(e)}'
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
        for non_retryable in EmailRetryService.NON_RETRYABLE_ERRORS:
            if non_retryable.lower() in error_lower:
                return False

        # 检查是否为可重试的错误
        for retryable in EmailRetryService.RETRYABLE_ERRORS:
            if retryable.lower() in error_lower:
                return True

        # 默认重试（保守策略）
        return True

    @staticmethod
    def process_pending_emails(
        batch_size: int = 50,
        process_failed: bool = True
    ) -> Dict[str, Any]:
        """
        处理待发送邮件

        Args:
            batch_size: 批量处理大小
            process_failed: 是否处理失败的邮件（重试）

        Returns:
            包含处理结果的字典
        """
        if not EmailConfigService.is_email_enabled():
            return {
                'success': False,
                'error': '邮件服务未启用'
            }

        results = {
            'processed': 0,
            'sent': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }

        try:
            # 获取待发送的邮件
            pending_logs = EmailLog.query.filter(
                EmailLog.status == EmailStatus.PENDING
            ).order_by(
                EmailLog.created_at.asc()
            ).limit(batch_size).all()

            # 如果需要处理失败的邮件，获取可重试的失败邮件
            if process_failed:
                failed_logs = EmailLog.query.filter(
                    EmailLog.status == EmailStatus.FAILED,
                    EmailLog.retry_count < EmailRetryService.MAX_RETRY_COUNT
                ).order_by(
                    EmailLog.created_at.asc()
                ).limit(batch_size).all()

                # 合并列表，去重
                seen_ids = {str(log.id) for log in pending_logs}
                for log in failed_logs:
                    if str(log.id) not in seen_ids:
                        pending_logs.append(log)

            if not pending_logs:
                return {
                    'success': True,
                    'results': results,
                    'message': '没有待处理的邮件'
                }

            # 使用上下文管理器处理邮件
            with EmailSenderService() as sender:
                for email_log in pending_logs:
                    results['processed'] += 1

                    try:
                        # 检查是否应该跳过（重试时间未到）
                        if email_log.status == EmailStatus.FAILED:
                            retry_delay = EmailRetryService.RETRY_DELAYS[min(
                                email_log.retry_count,
                                len(EmailRetryService.RETRY_DELAYS) - 1
                            )]
                            min_retry_time = email_log.created_at + timedelta(seconds=retry_delay)
                            if datetime.now(timezone.utc) < min_retry_time:
                                results['skipped'] += 1
                                continue

                        # 标记为重试中
                        if email_log.status == EmailStatus.FAILED:
                            EmailLogService.mark_as_retrying(str(email_log.id))

                        # 获取模板
                        template_result = EmailTemplateService.get_template(email_log.template_key)
                        if not template_result['success']:
                            # 如果没有模板，使用自定义发送
                            success, error = sender.send_email(
                                to_email=email_log.recipient_email,
                                to_name=email_log.recipient_name,
                                subject=email_log.subject,
                                log_email=False
                            )
                        else:
                            # 使用模板发送
                            template = template_result['template']
                            success, error = sender.send_email(
                                to_email=email_log.recipient_email,
                                to_name=email_log.recipient_name,
                                subject=template['subject'],
                                html_content=template['content_html'],
                                text_content=template.get('content_text'),
                                log_email=False,
                                template_key=email_log.template_key
                            )

                        if success:
                            EmailLogService.mark_as_sent(str(email_log.id))
                            results['sent'] += 1
                            logger.info(f'邮件发送成功：{email_log.id}')
                        else:
                            # 检查是否应该重试
                            if EmailRetryService.should_retry(error or ''):
                                retry_result = EmailRetryService.schedule_retry(
                                    str(email_log.id),
                                    email_log.retry_count
                                )
                                if retry_result['should_retry']:
                                    results['skipped'] += 1
                                    logger.warning(f'邮件发送失败，已安排重试：{email_log.id}')
                                else:
                                    EmailLogService.mark_as_failed(str(email_log.id), error or '未知错误')
                                    results['failed'] += 1
                            else:
                                EmailLogService.mark_as_failed(str(email_log.id), error or '未知错误')
                                results['failed'] += 1
                                results['errors'].append({
                                    'log_id': str(email_log.id),
                                    'error': error,
                                    'reason': '不可重试的错误'
                                })

                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f'处理邮件失败：{email_log.id}，错误：{error_msg}')

                        # 检查是否应该重试
                        if EmailRetryService.should_retry(error_msg):
                            retry_result = EmailRetryService.schedule_retry(
                                str(email_log.id),
                                email_log.retry_count
                            )
                            if retry_result['should_retry']:
                                results['skipped'] += 1
                            else:
                                EmailLogService.mark_as_failed(str(email_log.id), error_msg)
                                results['failed'] += 1
                        else:
                            EmailLogService.mark_as_failed(str(email_log.id), error_msg)
                            results['failed'] += 1

                        results['errors'].append({
                            'log_id': str(email_log.id),
                            'error': error_msg
                        })

                    # 短暂延迟，避免发送过快
                    time.sleep(0.1)

            return {
                'success': True,
                'results': results,
                'message': f'处理完成：成功 {results["sent"]}，失败 {results["failed"]}，跳过 {results["skipped"]}'
            }

        except Exception as e:
            logger.error(f'处理待发送邮件失败：{str(e)}')
            return {
                'success': False,
                'error': f'处理失败：{str(e)}',
                'results': results
            }

    @staticmethod
    def retry_failed_email(log_id: str) -> Dict[str, Any]:
        """
        重试单封失败的邮件

        Args:
            log_id: 邮件日志 ID

        Returns:
            包含操作结果的字典
        """
        try:
            email_log = EmailLog.query.get(log_id)

            if not email_log:
                return {
                    'success': False,
                    'error': f'日志不存在：{log_id}'
                }

            if email_log.status not in [EmailStatus.FAILED, EmailStatus.RETRYING]:
                return {
                    'success': False,
                    'error': f'邮件状态不允许重试：{email_log.status.value}'
                }

            if email_log.retry_count >= EmailRetryService.MAX_RETRY_COUNT:
                return {
                    'success': False,
                    'error': f'已达到最大重试次数'
                }

            # 使用上下文管理器发送邮件
            with EmailSenderService() as sender:
                # 获取模板
                template_result = EmailTemplateService.get_template(email_log.template_key)

                if template_result['success']:
                    template = template_result['template']
                    success, error = sender.send_email(
                        to_email=email_log.recipient_email,
                        to_name=email_log.recipient_name,
                        subject=template['subject'],
                        html_content=template['content_html'],
                        text_content=template.get('content_text'),
                        log_email=False,
                        template_key=email_log.template_key
                    )
                else:
                    # 没有模板，尝试直接发送
                    success, error = sender.send_email(
                        to_email=email_log.recipient_email,
                        to_name=email_log.recipient_name,
                        subject=email_log.subject,
                        log_email=False
                    )

                if success:
                    EmailLogService.mark_as_sent(log_id)
                    return {
                        'success': True,
                        'message': '邮件重试发送成功'
                    }
                else:
                    EmailLogService.mark_as_failed(log_id, error or '未知错误')
                    return {
                        'success': False,
                        'error': error or '发送失败'
                    }

        except Exception as e:
            logger.error(f'重试邮件失败：{str(e)}')
            EmailLogService.mark_as_failed(log_id, str(e))
            return {
                'success': False,
                'error': f'重试失败：{str(e)}'
            }

    @staticmethod
    def get_retry_stats() -> Dict[str, Any]:
        """
        获取重试统计信息

        Returns:
            包含重试统计的字典
        """
        try:
            # 待发送数量
            pending_count = EmailLog.query.filter(
                EmailLog.status == EmailStatus.PENDING
            ).count()

            # 重试中数量
            retrying_count = EmailLog.query.filter(
                EmailLog.status == EmailStatus.RETRYING
            ).count()

            # 可重试的失败数量
            retryable_failed_count = EmailLog.query.filter(
                EmailLog.status == EmailStatus.FAILED,
                EmailLog.retry_count < EmailRetryService.MAX_RETRY_COUNT
            ).count()

            # 不可重试的失败数量
            non_retryable_failed_count = EmailLog.query.filter(
                EmailLog.status == EmailStatus.FAILED,
                EmailLog.retry_count >= EmailRetryService.MAX_RETRY_COUNT
            ).count()

            # 按重试次数统计
            retry_distribution = []
            for i in range(EmailRetryService.MAX_RETRY_COUNT + 1):
                count = EmailLog.query.filter(
                    EmailLog.retry_count == i,
                    EmailLog.status.in_([EmailStatus.FAILED, EmailStatus.RETRYING])
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
                    'max_retries': EmailRetryService.MAX_RETRY_COUNT,
                    'retry_delays': EmailRetryService.RETRY_DELAYS
                }
            }

        except Exception as e:
            logger.error(f'获取重试统计失败：{str(e)}')
            return {
                'success': False,
                'error': f'获取统计失败：{str(e)}'
            }

    @staticmethod
    def cancel_retry(log_id: str) -> Dict[str, Any]:
        """
        取消邮件重试

        Args:
            log_id: 邮件日志 ID

        Returns:
            包含操作结果的字典
        """
        try:
            email_log = EmailLog.query.get(log_id)

            if not email_log:
                return {
                    'success': False,
                    'error': f'日志不存在：{log_id}'
                }

            if email_log.status not in [EmailStatus.PENDING, EmailStatus.RETRYING]:
                return {
                    'success': False,
                    'error': f'邮件状态不允许取消：{email_log.status.value}'
                }

            # 标记为失败并设置重试次数为最大值
            email_log.mark_as_failed('用户取消重试')
            email_log.retry_count = EmailRetryService.MAX_RETRY_COUNT
            db.session.commit()

            logger.info(f'取消邮件重试：{log_id}')

            return {
                'success': True,
                'message': '已取消重试'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'取消邮件重试失败：{str(e)}')
            return {
                'success': False,
                'error': f'取消失败：{str(e)}'
            }
