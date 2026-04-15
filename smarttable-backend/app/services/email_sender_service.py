"""
邮件发送服务模块
处理 SMTP 连接和邮件发送功能
"""
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Dict, Any, Tuple

from flask import current_app

from app.services.email_config_service import EmailConfigService
from app.services.email_template_service import EmailTemplateService
from app.services.email_log_service import EmailLogService

logger = logging.getLogger(__name__)


class EmailSenderService:
    """
    邮件发送服务类
    提供 SMTP 连接管理和邮件发送功能
    """

    def __init__(self):
        """
        初始化邮件发送服务

        初始化 SMTP 连接配置，但不立即建立连接
        """
        self._server: Optional[stplib.SMTP] = None
        self._config: Optional[Dict[str, Any]] = None
        self._sender_config: Optional[Dict[str, str]] = None
        self._is_connected = False

    def connect(self) -> bool:
        """
        连接 SMTP 服务器

        Returns:
            是否连接成功

        Raises:
            ConnectionError: 连接失败
        """
        if self._is_connected and self._server:
            try:
                # 测试连接是否仍然有效
                self._server.noop()
                return True
            except Exception:
                # 连接已断开，需要重新连接
                self._is_connected = False
                self._server = None

        # 获取配置
        self._config = EmailConfigService.get_smtp_config()
        self._sender_config = EmailConfigService.get_sender_config()

        # 验证配置
        if not self._config['host'] or not self._config['username']:
            raise ConnectionError('SMTP 配置不完整')

        try:
            context = ssl.create_default_context()

            if self._config['use_ssl']:
                self._server = smtplib.SMTP_SSL(
                    self._config['host'],
                    self._config['port'],
                    context=context,
                    timeout=self._config['timeout']
                )
            else:
                self._server = smtplib.SMTP(
                    self._config['host'],
                    self._config['port'],
                    timeout=self._config['timeout']
                )

            if not self._config['use_ssl'] and self._config['use_tls']:
                self._server.starttls(context=context)

            self._server.login(self._config['username'], self._config['password'])
            self._is_connected = True

            logger.info(f'SMTP 连接成功：{self._config["host"]}:{self._config["port"]}')
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f'SMTP 认证失败：{str(e)}')
            raise ConnectionError(f'SMTP 认证失败：请检查用户名和密码')
        except smtplib.SMTPConnectError as e:
            logger.error(f'无法连接到 SMTP 服务器：{str(e)}')
            raise ConnectionError(f'无法连接到 SMTP 服务器：{self._config["host"]}:{self._config["port"]}')
        except Exception as e:
            logger.error(f'SMTP 连接失败：{str(e)}')
            raise ConnectionError(f'SMTP 连接失败：{str(e)}')

    def close(self) -> None:
        """
        关闭 SMTP 连接
        """
        if self._server:
            try:
                self._server.quit()
                logger.info('SMTP 连接已关闭')
            except Exception as e:
                logger.warning(f'关闭 SMTP 连接时出错：{str(e)}')
            finally:
                self._server = None
                self._is_connected = False

    def __enter__(self):
        """
        上下文管理器入口
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器出口
        """
        self.close()
        return False

    def send_email(
        self,
        to_email: str,
        to_name: Optional[str] = None,
        subject: str = '',
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        log_email: bool = True,
        template_key: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        发送单封邮件

        Args:
            to_email: 收件人邮箱地址
            to_name: 收件人名称（可选）
            subject: 邮件主题
            html_content: HTML 格式邮件内容（可选）
            text_content: 纯文本格式邮件内容（可选）
            log_email: 是否记录邮件发送日志，默认 True
            template_key: 使用的模板标识（用于日志记录，可选）

        Returns:
            (是否发送成功, 错误信息) - 成功时错误信息为 None
        """
        if not html_content and not text_content:
            return False, '邮件内容不能为空'

        if not self._is_connected:
            try:
                self.connect()
            except ConnectionError as e:
                return False, str(e)

        # 记录邮件日志
        log_id = None
        if log_email:
            log_result = EmailLogService.log_email(
                recipient_email=to_email,
                recipient_name=to_name,
                template_key=template_key or 'custom',
                subject=subject
            )
            if log_result['success']:
                log_id = log_result['log_id']

        try:
            # 构建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f'{self._sender_config["name"]} <{self._sender_config["email"]}>'

            if to_name:
                msg['To'] = f'{to_name} <{to_email}>'
            else:
                msg['To'] = to_email

            # 添加纯文本内容
            if text_content:
                msg.attach(MIMEText(text_content, 'plain', 'utf-8'))

            # 添加 HTML 内容
            if html_content:
                msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # 发送邮件
            self._server.sendmail(
                self._sender_config['email'],
                [to_email],
                msg.as_string()
            )

            # 标记为已发送
            if log_id:
                EmailLogService.mark_as_sent(log_id)

            logger.info(f'邮件发送成功：{to_email}')
            return True, None

        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f'收件人地址被拒绝：{str(e)}'
            logger.error(error_msg)
            if log_id:
                EmailLogService.mark_as_failed(log_id, error_msg)
            return False, error_msg

        except smtplib.SMTPSenderRefused as e:
            error_msg = f'发件人地址被拒绝：{str(e)}'
            logger.error(error_msg)
            if log_id:
                EmailLogService.mark_as_failed(log_id, error_msg)
            return False, error_msg

        except smtplib.SMTPException as e:
            error_msg = f'SMTP 错误：{str(e)}'
            logger.error(error_msg)
            if log_id:
                EmailLogService.mark_as_failed(log_id, error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f'发送邮件失败：{str(e)}'
            logger.error(error_msg)
            if log_id:
                EmailLogService.mark_as_failed(log_id, error_msg)
            return False, error_msg

    def send_email_with_template(
        self,
        to_email: str,
        to_name: Optional[str] = None,
        template_key: str = '',
        template_data: Optional[Dict[str, Any]] = None,
        log_email: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        使用模板发送邮件

        Args:
            to_email: 收件人邮箱地址
            to_name: 收件人名称（可选）
            template_key: 模板标识
            template_data: 模板变量数据（可选）
            log_email: 是否记录邮件发送日志，默认 True

        Returns:
            (是否发送成功, 错误信息) - 成功时错误信息为 None
        """
        template_data = template_data or {}

        # 获取模板
        template_result = EmailTemplateService.get_template(template_key)
        if not template_result['success']:
            return False, f'获取模板失败：{template_result.get("error", "模板不存在")}'

        template = template_result['template']

        # 渲染模板
        try:
            subject = EmailTemplateService.render_template(
                template['subject'],
                template_data
            )
            html_content = EmailTemplateService.render_template(
                template['content_html'],
                template_data
            )
            text_content = None
            if template.get('content_text'):
                text_content = EmailTemplateService.render_template(
                    template['content_text'],
                    template_data
                )
        except Exception as e:
            return False, f'渲染模板失败：{str(e)}'

        # 发送邮件
        return self.send_email(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            log_email=log_email,
            template_key=template_key
        )

    @staticmethod
    def send_email_quick(
        to_email: str,
        to_name: Optional[str] = None,
        subject: str = '',
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        template_key: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        快速发送邮件（使用上下文管理器自动管理连接）

        Args:
            to_email: 收件人邮箱地址
            to_name: 收件人名称（可选）
            subject: 邮件主题
            html_content: HTML 格式邮件内容（可选）
            text_content: 纯文本格式邮件内容（可选）
            template_key: 模板标识（可选，与 template_data 一起使用）
            template_data: 模板变量数据（可选）

        Returns:
            (是否发送成功, 错误信息) - 成功时错误信息为 None
        """
        if not EmailConfigService.is_email_enabled():
            return False, '邮件服务未启用'

        try:
            with EmailSenderService() as sender:
                if template_key:
                    return sender.send_email_with_template(
                        to_email=to_email,
                        to_name=to_name,
                        template_key=template_key,
                        template_data=template_data or {}
                    )
                else:
                    return sender.send_email(
                        to_email=to_email,
                        to_name=to_name,
                        subject=subject,
                        html_content=html_content,
                        text_content=text_content
                    )
        except ConnectionError as e:
            return False, str(e)
        except Exception as e:
            logger.error(f'快速发送邮件失败：{str(e)}')
            return False, f'发送失败：{str(e)}'

    def is_connected(self) -> bool:
        """
        检查 SMTP 连接是否有效

        Returns:
            连接是否有效
        """
        if not self._is_connected or not self._server:
            return False

        try:
            self._server.noop()
            return True
        except Exception:
            self._is_connected = False
            return False
