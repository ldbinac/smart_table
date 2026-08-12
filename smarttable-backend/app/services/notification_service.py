"""
站内信服务模块
处理站内信通知的发送、查询、已读管理和统计分析
"""
import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from sqlalchemy import func

from app.extensions import db
from app.models.notification import Notification, NotificationStatus
from app.models.user import User
from app.services.email_sender_service import EmailSenderService
from app.services.email_template_service import EmailTemplateService
from app.services.email_config_service import EmailConfigService

logger = logging.getLogger(__name__)


class NotificationService:
    """
    站内信服务类
    提供站内信通知的发送、查询、已读管理和统计分析功能
    """

    @staticmethod
    def send_notification(
        recipient_email: Optional[str] = None,
        recipient_user_id: Optional[uuid.UUID] = None,
        template_key: Optional[str] = None,
        template_data: Optional[Dict] = None,
        source: str = 'system',
        title: Optional[str] = None,
        content: Optional[str] = None,
        content_text: Optional[str] = None,
        send_email: bool = True
    ) -> Dict[str, Any]:
        """
        发送站内信通知（并可同时发送邮件）

        严格保证站内信先于邮件写入：先持久化站内信并标记为已发送，
        再尝试发送邮件；邮件失败不影响站内信状态。

        Args:
            recipient_email: 收件人邮箱（可选）
            recipient_user_id: 收件人用户 ID（可选，优先使用）
            template_key: 模板标识（可选）
            template_data: 模板变量（可选）
            source: 通知来源，默认 'system'
            title: 标题（覆盖模板主题，可选）
            content: HTML 内容（覆盖模板内容，可选）
            content_text: 纯文本内容（可选）
            send_email: 是否同时发送邮件，默认 True

        Returns:
            包含操作结果的字典：
            - success: 是否成功（站内信写入成功即视为成功；外部邮箱取决于邮件结果）
            - notification_id: 站内信 ID（成功时）
            - email_sent: 邮件是否发送成功
            - email_error: 邮件错误信息（失败时）
            - error: 错误信息（失败时）
        """
        template_data = template_data or {}

        try:
            # 1. 解析收件人用户
            user = None
            user_id = recipient_user_id
            if user_id is None and recipient_email:
                user = User.query.filter_by(email=recipient_email).first()
                if user:
                    user_id = user.id
            elif user_id is not None:
                user = User.query.get(user_id)

            to_name = user.name if user else None
            # 收件邮箱：优先使用参数提供的，否则使用用户的邮箱
            to_email = recipient_email or (user.email if user else None)

            # 2. 解析标题与内容
            if template_key:
                template_result = EmailTemplateService.get_template(template_key)
                if not template_result['success']:
                    return {
                        'success': False,
                        'notification_id': None,
                        'email_sent': False,
                        'email_error': None,
                        'error': template_result.get('error', '获取模板失败')
                    }

                template = template_result['template']
                try:
                    rendered_subject = EmailTemplateService.render_template(
                        template['subject'], template_data
                    )
                    rendered_html = EmailTemplateService.render_template(
                        template['content_html'], template_data
                    )
                    rendered_text = ''
                    if template.get('content_text'):
                        rendered_text = EmailTemplateService.render_template(
                            template['content_text'], template_data
                        )
                except ValueError:
                    logger.error('渲染站内信模板失败')
                    return {
                        'success': False,
                        'notification_id': None,
                        'email_sent': False,
                        'email_error': None,
                        'error': '渲染模板失败，请检查模板格式'
                    }

                final_title = title or rendered_subject
                final_content = content or rendered_html
                final_content_text = content_text or rendered_text
            else:
                final_title = title
                final_content = content
                final_content_text = content_text
                # 无模板时标题与内容必须由参数提供
                if not final_title or not final_content:
                    return {
                        'success': False,
                        'notification_id': None,
                        'email_sent': False,
                        'email_error': None,
                        'error': '标题和内容不能为空'
                    }

            # 3. 先写站内信（仅当 user_id 不为 None）
            notification_id = None
            if user_id is not None:
                try:
                    notification = Notification(
                        recipient_user_id=user_id,
                        recipient_email=to_email,
                        title=final_title,
                        content=final_content,
                        content_text=final_content_text,
                        template_key=template_key,
                        source=source,
                        status=NotificationStatus.PENDING,
                        extra_metadata=template_data or {}
                    )
                    db.session.add(notification)
                    db.session.commit()

                    # 标记为已发送
                    notification.mark_as_sent()
                    db.session.commit()

                    notification_id = str(notification.id)
                    logger.info(f'站内信写入成功：{notification_id}')
                except Exception as e:
                    db.session.rollback()
                    logger.error(f'写入站内信失败：{str(e)}')
                    return {
                        'success': False,
                        'notification_id': None,
                        'email_sent': False,
                        'email_error': None,
                        'error': f'写入站内信失败：{str(e)}'
                    }

            # 4. 再发邮件（仅当 send_email 且 recipient_email 提供）
            email_sent = False
            email_error = None
            if send_email and to_email:
                if not EmailConfigService.is_email_enabled():
                    # 邮件服务未启用，跳过不发邮件但不报错
                    logger.info('邮件服务未启用，跳过发送邮件')
                else:
                    try:
                        success, error = EmailSenderService.send_email_quick(
                            to_email=to_email,
                            to_name=to_name,
                            subject=final_title,
                            html_content=final_content,
                            text_content=final_content_text,
                            template_key=template_key,
                            template_data=template_data
                        )
                        if success:
                            email_sent = True
                        else:
                            email_error = error
                            logger.warning(f'发送站内信邮件失败：{error}')
                    except Exception as e:
                        email_error = str(e)
                        logger.warning(f'发送站内信邮件异常：{str(e)}')

            # 5. 返回结果
            # 只要站内信写入成功，success=True（即使邮件失败）
            # 外部邮箱（user_id=None）则 success 取决于邮件发送结果
            if user_id is not None:
                success = True
            else:
                success = email_sent

            return {
                'success': success,
                'notification_id': notification_id,
                'email_sent': email_sent,
                'email_error': email_error
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'发送站内信通知失败：{str(e)}')
            return {
                'success': False,
                'notification_id': None,
                'email_sent': False,
                'email_error': None,
                'error': '发送站内信失败，请稍后重试'
            }

    @staticmethod
    def get_notifications(
        user_id,
        page: int = 1,
        per_page: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分页获取指定用户的站内信列表

        Args:
            user_id: 用户 ID
            page: 页码（从 1 开始）
            per_page: 每页数量
            filters: 过滤条件，支持 is_read(bool) / status(字符串) / source

        Returns:
            包含站内信列表和分页信息的字典
        """
        try:
            query_filters: Dict[str, Any] = {}
            if filters:
                if 'is_read' in filters:
                    query_filters['is_read'] = filters['is_read']
                if 'status' in filters and filters['status']:
                    try:
                        query_filters['status'] = NotificationStatus(filters['status'])
                    except ValueError:
                        logger.warning(f'无效的状态值：{filters["status"]}')
                if 'source' in filters and filters['source']:
                    query_filters['source'] = filters['source']

            result = Notification.get_user_notifications(
                user_id,
                page=page,
                per_page=per_page,
                filters=query_filters
            )

            return {
                'success': True,
                'notifications': result['items'],
                'pagination': {
                    'total': result['total'],
                    'pages': result['pages'],
                    'current_page': result['current_page'],
                    'per_page': result['per_page']
                }
            }

        except Exception as e:
            logger.error(f'获取站内信列表失败：{str(e)}')
            return {
                'success': False,
                'error': '获取站内信列表失败，请稍后重试'
            }

    @staticmethod
    def get_unread_count(user_id) -> Dict[str, Any]:
        """
        获取指定用户的未读站内信数量

        Args:
            user_id: 用户 ID

        Returns:
            包含未读数量的字典
        """
        try:
            count = Notification.get_unread_count(user_id)
            return {
                'success': True,
                'count': count
            }
        except Exception as e:
            logger.error(f'获取未读站内信数量失败：{str(e)}')
            return {
                'success': False,
                'error': '获取未读数量失败，请稍后重试'
            }

    @staticmethod
    def get_notification(notification_id, user_id=None) -> Dict[str, Any]:
        """
        获取单条站内信详情

        Args:
            notification_id: 站内信 ID
            user_id: 用户 ID（可选，提供时校验归属）

        Returns:
            包含站内信详情的字典
        """
        try:
            notification = Notification.query.get(notification_id)

            if not notification:
                return {
                    'success': False,
                    'error': f'站内信不存在：{notification_id}'
                }

            if user_id is not None and str(notification.recipient_user_id) != str(user_id):
                return {
                    'success': False,
                    'error': '无权访问该站内信'
                }

            return {
                'success': True,
                'notification': notification.to_dict()
            }

        except Exception as e:
            logger.error(f'获取站内信详情失败：{str(e)}')
            return {
                'success': False,
                'error': '获取站内信详情失败，请稍后重试'
            }

    @staticmethod
    def mark_as_read(notification_id, user_id) -> Dict[str, Any]:
        """
        标记单条站内信为已读

        Args:
            notification_id: 站内信 ID
            user_id: 用户 ID（校验归属）

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

            if str(notification.recipient_user_id) != str(user_id):
                return {
                    'success': False,
                    'error': '无权操作该站内信'
                }

            notification.mark_as_read()
            db.session.commit()

            return {
                'success': True,
                'message': '已标记为已读'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'标记站内信已读失败：{str(e)}')
            return {
                'success': False,
                'error': '更新状态失败，请稍后重试'
            }

    @staticmethod
    def mark_all_as_read(user_id) -> Dict[str, Any]:
        """
        标记指定用户的所有未读站内信为已读

        Args:
            user_id: 用户 ID

        Returns:
            包含操作结果的字典，updated_count 为更新条数
        """
        try:
            now = datetime.now(timezone.utc)
            count = Notification.query.filter_by(
                recipient_user_id=user_id,
                is_read=False
            ).update(
                {'is_read': True, 'read_at': now},
                synchronize_session=False
            )
            db.session.commit()

            logger.info(f'批量标记站内信已读：用户 {user_id}，{count} 条')

            return {
                'success': True,
                'updated_count': count
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'批量标记站内信已读失败：{str(e)}')
            return {
                'success': False,
                'error': '更新状态失败，请稍后重试'
            }

    @staticmethod
    def delete_notification(notification_id, user_id) -> Dict[str, Any]:
        """
        删除单条站内信

        Args:
            notification_id: 站内信 ID
            user_id: 用户 ID（校验归属）

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

            if str(notification.recipient_user_id) != str(user_id):
                return {
                    'success': False,
                    'error': '无权删除该站内信'
                }

            db.session.delete(notification)
            db.session.commit()

            logger.info(f'删除站内信：{notification_id}')

            return {
                'success': True,
                'message': '站内信已删除'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'删除站内信失败：{str(e)}')
            return {
                'success': False,
                'error': '删除站内信失败，请稍后重试'
            }

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """
        获取站内信管理端统计信息

        Returns:
            包含统计信息的字典：总量、各状态数量、已读/未读数、按 source 分组、按 template_key 分组
        """
        try:
            # 总量
            total_count = Notification.query.count()

            # 各状态统计
            status_stats: Dict[str, int] = {}
            for status in NotificationStatus:
                count = Notification.query.filter(
                    Notification.status == status
                ).count()
                status_stats[status.value] = count

            # 已读 / 未读
            read_count = Notification.query.filter(
                Notification.is_read == True  # noqa: E712
            ).count()
            unread_count = Notification.query.filter(
                Notification.is_read == False  # noqa: E712
            ).count()

            # 按 source 分组
            source_stats = db.session.query(
                Notification.source,
                func.count(Notification.id).label('count')
            ).group_by(Notification.source).all()
            source_breakdown = [
                {'source': s, 'count': c} for s, c in source_stats
            ]

            # 按 template_key 分组（排除 NULL）
            template_stats = db.session.query(
                Notification.template_key,
                func.count(Notification.id).label('count')
            ).filter(
                Notification.template_key.isnot(None)
            ).group_by(Notification.template_key).all()
            template_breakdown = [
                {'template_key': t, 'count': c} for t, c in template_stats
            ]

            return {
                'success': True,
                'stats': {
                    'total': total_count,
                    'by_status': status_stats,
                    'read': read_count,
                    'unread': unread_count,
                    'by_source': source_breakdown,
                    'by_template': template_breakdown
                }
            }

        except Exception as e:
            logger.error(f'获取站内信统计失败：{str(e)}')
            return {
                'success': False,
                'error': '获取统计失败，请稍后重试'
            }
