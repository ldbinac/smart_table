"""
邮件日志服务模块
处理邮件发送日志的记录、查询和统计
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

from flask import current_app
from sqlalchemy import or_, func

from app.extensions import db
from app.models.email_log import EmailLog, EmailStatus

logger = logging.getLogger(__name__)


class EmailLogService:
    """
    邮件日志服务类
    提供邮件发送日志的 CRUD 操作和统计分析功能
    """

    # 默认分页大小
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    @staticmethod
    def log_email(
        recipient_email: str,
        recipient_name: Optional[str] = None,
        template_key: str = '',
        subject: str = ''
    ) -> Dict[str, Any]:
        """
        记录邮件发送

        Args:
            recipient_email: 收件人邮箱
            recipient_name: 收件人名称（可选）
            template_key: 使用的模板标识
            subject: 邮件主题

        Returns:
            包含操作结果的字典：
            - success: 是否成功
            - log_id: 日志 ID（成功时）
            - error: 错误信息（失败时）
        """
        try:
            email_log = EmailLog(
                recipient_email=recipient_email.lower().strip(),
                recipient_name=recipient_name,
                template_key=template_key,
                subject=subject,
                status=EmailStatus.PENDING,
                retry_count=0
            )

            db.session.add(email_log)
            db.session.commit()

            logger.debug(f'记录邮件发送日志：{email_log.id}')

            return {
                'success': True,
                'log_id': str(email_log.id)
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'记录邮件发送日志失败：{str(e)}')
            return {
                'success': False,
                'error': f'记录日志失败：{str(e)}'
            }

    @staticmethod
    def mark_as_sent(log_id: str) -> Dict[str, Any]:
        """
        标记为已发送

        Args:
            log_id: 日志 ID

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

            email_log.mark_as_sent()
            db.session.commit()

            logger.debug(f'标记邮件为已发送：{log_id}')

            return {
                'success': True,
                'message': '已标记为发送成功'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'标记邮件发送状态失败：{str(e)}')
            return {
                'success': False,
                'error': f'更新状态失败：{str(e)}'
            }

    @staticmethod
    def mark_as_failed(log_id: str, error: str) -> Dict[str, Any]:
        """
        标记为失败

        Args:
            log_id: 日志 ID
            error: 错误信息

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

            email_log.mark_as_failed(error)
            db.session.commit()

            logger.debug(f'标记邮件为发送失败：{log_id}')

            return {
                'success': True,
                'message': '已标记为发送失败'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'标记邮件失败状态失败：{str(e)}')
            return {
                'success': False,
                'error': f'更新状态失败：{str(e)}'
            }

    @staticmethod
    def mark_as_retrying(log_id: str) -> Dict[str, Any]:
        """
        标记为重试中

        Args:
            log_id: 日志 ID

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

            email_log.mark_as_retrying()
            db.session.commit()

            logger.debug(f'标记邮件为重试中：{log_id}')

            return {
                'success': True,
                'message': '已标记为重试中'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'标记邮件重试状态失败：{str(e)}')
            return {
                'success': False,
                'error': f'更新状态失败：{str(e)}'
            }

    @staticmethod
    def get_logs(
        filters: Optional[Dict[str, Any]] = None,
        pagination: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        查询日志

        Args:
            filters: 过滤条件，可包含：
                - status: 状态过滤（pending, sent, failed, retrying）
                - recipient_email: 收件人邮箱过滤
                - template_key: 模板标识过滤
                - start_date: 开始时间
                - end_date: 结束时间
                - search: 搜索关键词（搜索邮箱、主题）
            pagination: 分页参数，可包含：
                - page: 页码（从 1 开始，默认 1）
                - per_page: 每页数量（默认 20，最大 100）

        Returns:
            包含日志列表和分页信息的字典
        """
        filters = filters or {}
        pagination = pagination or {}

        try:
            query = EmailLog.query

            # 状态过滤
            if 'status' in filters and filters['status']:
                try:
                    status = EmailStatus(filters['status'])
                    query = query.filter(EmailLog.status == status)
                except ValueError:
                    logger.warning(f'无效的状态值：{filters["status"]}')

            # 收件人邮箱过滤
            if 'recipient_email' in filters and filters['recipient_email']:
                query = query.filter(
                    EmailLog.recipient_email.ilike(f'%{filters["recipient_email"]}%')
                )

            # 模板标识过滤
            if 'template_key' in filters and filters['template_key']:
                query = query.filter(EmailLog.template_key == filters['template_key'])

            # 时间范围过滤
            if 'start_date' in filters and filters['start_date']:
                if isinstance(filters['start_date'], str):
                    start_date = datetime.fromisoformat(filters['start_date'])
                else:
                    start_date = filters['start_date']
                query = query.filter(EmailLog.created_at >= start_date)

            if 'end_date' in filters and filters['end_date']:
                if isinstance(filters['end_date'], str):
                    end_date = datetime.fromisoformat(filters['end_date'])
                else:
                    end_date = filters['end_date']
                query = query.filter(EmailLog.created_at <= end_date)

            # 搜索关键词
            if 'search' in filters and filters['search']:
                search_pattern = f'%{filters["search"]}%'
                query = query.filter(
                    or_(
                        EmailLog.recipient_email.ilike(search_pattern),
                        EmailLog.subject.ilike(search_pattern)
                    )
                )

            # 分页
            page = pagination.get('page', 1)
            per_page = min(
                pagination.get('per_page', EmailLogService.DEFAULT_PAGE_SIZE),
                EmailLogService.MAX_PAGE_SIZE
            )

            result = query.order_by(EmailLog.created_at.desc()).paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )

            return {
                'success': True,
                'logs': [log.to_dict() for log in result.items],
                'pagination': {
                    'total': result.total,
                    'pages': result.pages,
                    'page': page,
                    'per_page': per_page
                }
            }

        except Exception as e:
            logger.error(f'查询邮件日志失败：{str(e)}')
            return {
                'success': False,
                'error': f'查询日志失败：{str(e)}'
            }

    @staticmethod
    def get_log(log_id: str) -> Dict[str, Any]:
        """
        获取单条日志详情

        Args:
            log_id: 日志 ID

        Returns:
            包含日志详情的字典
        """
        try:
            email_log = EmailLog.query.get(log_id)

            if not email_log:
                return {
                    'success': False,
                    'error': f'日志不存在：{log_id}'
                }

            return {
                'success': True,
                'log': email_log.to_dict()
            }

        except Exception as e:
            logger.error(f'获取邮件日志详情失败：{str(e)}')
            return {
                'success': False,
                'error': f'获取日志详情失败：{str(e)}'
            }

    @staticmethod
    def get_stats(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取发送统计

        Args:
            start_date: 开始时间（可选，默认 30 天前）
            end_date: 结束时间（可选，默认现在）

        Returns:
            包含统计信息的字典
        """
        try:
            if not end_date:
                end_date = datetime.now(timezone.utc)
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # 基础查询
            base_query = EmailLog.query.filter(
                EmailLog.created_at >= start_date,
                EmailLog.created_at <= end_date
            )

            # 总发送数
            total_count = base_query.count()

            # 各状态统计
            status_stats = {}
            for status in EmailStatus:
                count = base_query.filter(EmailLog.status == status).count()
                status_stats[status.value] = count

            # 成功率
            success_rate = 0
            if total_count > 0:
                success_rate = round((status_stats.get(EmailStatus.SENT.value, 0) / total_count) * 100, 2)

            # 平均重试次数
            avg_retries = db.session.query(func.avg(EmailLog.retry_count)).filter(
                EmailLog.created_at >= start_date,
                EmailLog.created_at <= end_date
            ).scalar() or 0

            # 按模板统计
            template_stats = db.session.query(
                EmailLog.template_key,
                func.count(EmailLog.id).label('count'),
                func.sum(func.case([(EmailLog.status == EmailStatus.SENT, 1)], else_=0)).label('sent_count')
            ).filter(
                EmailLog.created_at >= start_date,
                EmailLog.created_at <= end_date
            ).group_by(EmailLog.template_key).all()

            template_breakdown = []
            for template_key, count, sent_count in template_stats:
                template_breakdown.append({
                    'template_key': template_key,
                    'total': count,
                    'sent': sent_count or 0,
                    'failed': count - (sent_count or 0)
                })

            # 按日期统计（最近 7 天）
            daily_stats = []
            for i in range(7):
                day_end = end_date - timedelta(days=i)
                day_start = day_end - timedelta(days=1)

                day_total = EmailLog.query.filter(
                    EmailLog.created_at >= day_start,
                    EmailLog.created_at < day_end
                ).count()

                day_sent = EmailLog.query.filter(
                    EmailLog.created_at >= day_start,
                    EmailLog.created_at < day_end,
                    EmailLog.status == EmailStatus.SENT
                ).count()

                daily_stats.append({
                    'date': day_start.strftime('%Y-%m-%d'),
                    'total': day_total,
                    'sent': day_sent,
                    'failed': day_total - day_sent
                })

            daily_stats.reverse()  # 按日期升序排列

            return {
                'success': True,
                'stats': {
                    'period': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat()
                    },
                    'summary': {
                        'total': total_count,
                        'success_rate': success_rate,
                        'avg_retries': round(float(avg_retries), 2)
                    },
                    'by_status': status_stats,
                    'by_template': template_breakdown,
                    'daily': daily_stats
                }
            }

        except Exception as e:
            logger.error(f'获取邮件统计失败：{str(e)}')
            return {
                'success': False,
                'error': f'获取统计失败：{str(e)}'
            }

    @staticmethod
    def get_pending_logs(limit: int = 100) -> Dict[str, Any]:
        """
        获取待发送的邮件日志

        Args:
            limit: 返回数量限制

        Returns:
            包含待发送邮件列表的字典
        """
        try:
            logs = EmailLog.get_pending_emails(limit=limit)

            return {
                'success': True,
                'logs': [log.to_dict() for log in logs],
                'count': len(logs)
            }

        except Exception as e:
            logger.error(f'获取待发送邮件失败：{str(e)}')
            return {
                'success': False,
                'error': f'获取待发送邮件失败：{str(e)}'
            }

    @staticmethod
    def get_failed_logs(limit: int = 100, max_retries: int = 3) -> Dict[str, Any]:
        """
        获取可重试的失败邮件日志

        Args:
            limit: 返回数量限制
            max_retries: 最大重试次数

        Returns:
            包含可重试邮件列表的字典
        """
        try:
            logs = EmailLog.query.filter(
                EmailLog.status == EmailStatus.FAILED,
                EmailLog.retry_count < max_retries
            ).order_by(
                EmailLog.created_at.desc()
            ).limit(limit).all()

            return {
                'success': True,
                'logs': [log.to_dict() for log in logs],
                'count': len(logs)
            }

        except Exception as e:
            logger.error(f'获取失败邮件失败：{str(e)}')
            return {
                'success': False,
                'error': f'获取失败邮件失败：{str(e)}'
            }

    @staticmethod
    def delete_old_logs(days: int = 90) -> Dict[str, Any]:
        """
        删除旧的邮件日志

        Args:
            days: 保留天数，默认 90 天

        Returns:
            包含操作结果的字典
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            old_logs = EmailLog.query.filter(
                EmailLog.created_at < cutoff_date
            ).all()

            count = len(old_logs)

            for log in old_logs:
                db.session.delete(log)

            db.session.commit()

            logger.info(f'删除旧邮件日志：{count} 条')

            return {
                'success': True,
                'deleted_count': count,
                'message': f'已删除 {count} 条旧日志'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'删除旧邮件日志失败：{str(e)}')
            return {
                'success': False,
                'error': f'删除旧日志失败：{str(e)}'
            }
