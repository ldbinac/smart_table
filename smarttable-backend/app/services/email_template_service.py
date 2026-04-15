"""
邮件模板服务模块
处理邮件模板的获取、渲染和管理
"""
import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from flask import current_app
from sqlalchemy import or_

from app.extensions import db
from app.models.email_template import EmailTemplate

logger = logging.getLogger(__name__)


class EmailTemplateService:
    """
    邮件模板服务类
    提供邮件模板的 CRUD 操作和模板渲染功能
    """

    # 默认邮件模板
    DEFAULT_TEMPLATES = {
        'user_registration': {
            'name': '用户注册欢迎邮件',
            'subject': '欢迎加入 SmartTable',
            'content_html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>欢迎加入 SmartTable</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #6366F1; color: white; padding: 20px; text-align: center; }
        .content { background: #f9f9f9; padding: 20px; margin: 20px 0; }
        .footer { text-align: center; color: #666; font-size: 12px; }
        .button { display: inline-block; background: #6366F1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>欢迎加入 SmartTable</h1>
        </div>
        <div class="content">
            <p>您好 {{user_name}}，</p>
            <p>感谢您注册 SmartTable 账户！我们很高兴您加入我们。</p>
            <p>您的账户信息：</p>
            <ul>
                <li>邮箱：{{user_email}}</li>
                <li>注册时间：{{registration_time}}</li>
            </ul>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{{login_url}}" class="button">立即登录</a>
            </p>
        </div>
        <div class="footer">
            <p>此邮件由系统自动发送，请勿回复。</p>
            <p>&copy; {{year}} SmartTable. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
            ''',
            'content_text': '''
您好 {{user_name}}，

感谢您注册 SmartTable 账户！我们很高兴您加入我们。

您的账户信息：
- 邮箱：{{user_email}}
- 注册时间：{{registration_time}}

请点击以下链接登录：
{{login_url}}

此邮件由系统自动发送，请勿回复。
&copy; {{year}} SmartTable. All rights reserved.
            ''',
            'description': '用户注册成功后发送的欢迎邮件'
        },
        'password_reset': {
            'name': '密码重置邮件',
            'subject': '重置您的 SmartTable 密码',
            'content_html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>重置密码</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #6366F1; color: white; padding: 20px; text-align: center; }
        .content { background: #f9f9f9; padding: 20px; margin: 20px 0; }
        .footer { text-align: center; color: #666; font-size: 12px; }
        .button { display: inline-block; background: #6366F1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; margin: 10px 0; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>重置密码</h1>
        </div>
        <div class="content">
            <p>您好 {{user_name}}，</p>
            <p>我们收到了重置您 SmartTable 账户密码的请求。</p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{{reset_url}}" class="button">重置密码</a>
            </p>
            <div class="warning">
                <p><strong>注意：</strong>此链接将在 {{expiry_hours}} 小时后过期。</p>
            </div>
            <p>如果您没有请求重置密码，请忽略此邮件。</p>
        </div>
        <div class="footer">
            <p>此邮件由系统自动发送，请勿回复。</p>
            <p>&copy; {{year}} SmartTable. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
            ''',
            'content_text': '''
您好 {{user_name}}，

我们收到了重置您 SmartTable 账户密码的请求。

请点击以下链接重置密码：
{{reset_url}}

注意：此链接将在 {{expiry_hours}} 小时后过期。

如果您没有请求重置密码，请忽略此邮件。

此邮件由系统自动发送，请勿回复。
&copy; {{year}} SmartTable. All rights reserved.
            ''',
            'description': '用户请求重置密码时发送的邮件'
        },
        'invitation': {
            'name': '成员邀请邮件',
            'subject': '您被邀请加入 SmartTable 工作区',
            'content_html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>工作区邀请</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #6366F1; color: white; padding: 20px; text-align: center; }
        .content { background: #f9f9f9; padding: 20px; margin: 20px 0; }
        .footer { text-align: center; color: #666; font-size: 12px; }
        .button { display: inline-block; background: #6366F1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>工作区邀请</h1>
        </div>
        <div class="content">
            <p>您好，</p>
            <p><strong>{{inviter_name}}</strong> 邀请您加入 SmartTable 工作区 <strong>{{base_name}}</strong>。</p>
            <p>您的角色：<strong>{{role}}</strong></p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{{invitation_url}}" class="button">接受邀请</a>
            </p>
            <p>如果您还没有 SmartTable 账户，请先注册。</p>
        </div>
        <div class="footer">
            <p>此邮件由系统自动发送，请勿回复。</p>
            <p>&copy; {{year}} SmartTable. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
            ''',
            'content_text': '''
您好，

{{inviter_name}} 邀请您加入 SmartTable 工作区 {{base_name}}。

您的角色：{{role}}

请点击以下链接接受邀请：
{{invitation_url}}

如果您还没有 SmartTable 账户，请先注册。

此邮件由系统自动发送，请勿回复。
&copy; {{year}} SmartTable. All rights reserved.
            ''',
            'description': '邀请用户加入工作区时发送的邮件'
        },
        'notification': {
            'name': '系统通知邮件',
            'subject': '{{notification_title}}',
            'content_html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{notification_title}}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #6366F1; color: white; padding: 20px; text-align: center; }
        .content { background: #f9f9f9; padding: 20px; margin: 20px 0; }
        .footer { text-align: center; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{notification_title}}</h1>
        </div>
        <div class="content">
            <p>您好 {{user_name}}，</p>
            <p>{{notification_content}}</p>
        </div>
        <div class="footer">
            <p>此邮件由系统自动发送，请勿回复。</p>
            <p>&copy; {{year}} SmartTable. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
            ''',
            'content_text': '''
您好 {{user_name}}，

{{notification_content}}

此邮件由系统自动发送，请勿回复。
&copy; {{year}} SmartTable. All rights reserved.
            ''',
            'description': '通用系统通知邮件模板'
        }
    }

    @staticmethod
    def get_template(template_key: str) -> Dict[str, Any]:
        """
        获取模板

        Args:
            template_key: 模板标识

        Returns:
            包含模板信息的字典：
            - success: 是否成功
            - template: 模板字典（成功时）
            - error: 错误信息（失败时）
        """
        try:
            template = EmailTemplate.query.filter_by(template_key=template_key).first()

            if not template:
                # 尝试从默认模板创建
                if template_key in EmailTemplateService.DEFAULT_TEMPLATES:
                    default_data = EmailTemplateService.DEFAULT_TEMPLATES[template_key]
                    template = EmailTemplate(
                        template_key=template_key,
                        name=default_data['name'],
                        subject=default_data['subject'],
                        content_html=default_data['content_html'],
                        content_text=default_data.get('content_text'),
                        description=default_data.get('description'),
                        is_default=True
                    )
                    db.session.add(template)
                    db.session.commit()
                    logger.info(f'创建默认模板：{template_key}')
                else:
                    return {
                        'success': False,
                        'error': f'模板不存在：{template_key}'
                    }

            return {
                'success': True,
                'template': template.to_dict()
            }

        except Exception as e:
            logger.error(f'获取模板失败：{str(e)}')
            return {
                'success': False,
                'error': f'获取模板失败：{str(e)}'
            }

    @staticmethod
    def render_template(template: str, data: Dict[str, Any]) -> str:
        """
        渲染模板（替换变量如 {{user_name}}）

        Args:
            template: 模板字符串
            data: 模板变量数据

        Returns:
            渲染后的字符串

        Raises:
            ValueError: 模板渲染失败
        """
        if not template:
            return ''

        try:
            # 添加默认变量
            render_data = {
                'year': datetime.now().year,
                'app_name': 'SmartTable',
                **data
            }

            # 使用正则表达式替换 {{variable}} 格式的变量
            def replace_var(match):
                var_name = match.group(1).strip()
                value = render_data.get(var_name, '')
                return str(value) if value is not None else ''

            rendered = re.sub(r'\{\{(\w+)\}\}', replace_var, template)

            return rendered

        except Exception as e:
            logger.error(f'渲染模板失败：{str(e)}')
            raise ValueError(f'渲染模板失败：{str(e)}')

    @staticmethod
    def get_all_templates() -> Dict[str, Any]:
        """
        获取所有模板

        Returns:
            包含所有模板的字典：
            - success: 是否成功
            - templates: 模板列表
            - error: 错误信息（失败时）
        """
        try:
            templates = EmailTemplate.query.all()

            # 确保所有默认模板都存在
            for template_key, default_data in EmailTemplateService.DEFAULT_TEMPLATES.items():
                exists = any(t.template_key == template_key for t in templates)
                if not exists:
                    template = EmailTemplate(
                        template_key=template_key,
                        name=default_data['name'],
                        subject=default_data['subject'],
                        content_html=default_data['content_html'],
                        content_text=default_data.get('content_text'),
                        description=default_data.get('description'),
                        is_default=True
                    )
                    db.session.add(template)
                    templates.append(template)

            db.session.commit()

            return {
                'success': True,
                'templates': [t.to_dict() for t in templates]
            }

        except Exception as e:
            logger.error(f'获取所有模板失败：{str(e)}')
            return {
                'success': False,
                'error': f'获取模板失败：{str(e)}'
            }

    @staticmethod
    def update_template(template_key: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新模板

        Args:
            template_key: 模板标识
            data: 更新数据，可包含：
                - name: 模板名称
                - subject: 邮件主题
                - content_html: HTML 内容
                - content_text: 纯文本内容
                - description: 描述

        Returns:
            包含操作结果的字典：
            - success: 是否成功
            - template: 更新后的模板（成功时）
            - error: 错误信息（失败时）
        """
        try:
            template = EmailTemplate.query.filter_by(template_key=template_key).first()

            if not template:
                # 如果模板不存在，创建新模板
                if template_key in EmailTemplateService.DEFAULT_TEMPLATES:
                    # 基于默认模板创建
                    default_data = EmailTemplateService.DEFAULT_TEMPLATES[template_key]
                    template = EmailTemplate(
                        template_key=template_key,
                        name=data.get('name', default_data['name']),
                        subject=data.get('subject', default_data['subject']),
                        content_html=data.get('content_html', default_data['content_html']),
                        content_text=data.get('content_text', default_data.get('content_text')),
                        description=data.get('description', default_data.get('description')),
                        is_default=False
                    )
                else:
                    # 创建全新模板
                    template = EmailTemplate(
                        template_key=template_key,
                        name=data.get('name', '未命名模板'),
                        subject=data.get('subject', ''),
                        content_html=data.get('content_html', ''),
                        content_text=data.get('content_text'),
                        description=data.get('description'),
                        is_default=False
                    )
                db.session.add(template)
            else:
                # 更新现有模板
                allowed_fields = ['name', 'subject', 'content_html', 'content_text', 'description']
                for field in allowed_fields:
                    if field in data:
                        setattr(template, field, data[field])

                # 标记为非默认模板（因为已被修改）
                if template.is_default:
                    template.is_default = False

                template.updated_at = datetime.now(timezone.utc)

            db.session.commit()

            logger.info(f'更新模板成功：{template_key}')

            return {
                'success': True,
                'template': template.to_dict()
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'更新模板失败：{str(e)}')
            return {
                'success': False,
                'error': f'更新模板失败：{str(e)}'
            }

    @staticmethod
    def reset_template(template_key: str) -> Dict[str, Any]:
        """
        重置为默认模板

        Args:
            template_key: 模板标识

        Returns:
            包含操作结果的字典：
            - success: 是否成功
            - template: 重置后的模板（成功时）
            - error: 错误信息（失败时）
        """
        if template_key not in EmailTemplateService.DEFAULT_TEMPLATES:
            return {
                'success': False,
                'error': f'不存在默认模板：{template_key}'
            }

        try:
            default_data = EmailTemplateService.DEFAULT_TEMPLATES[template_key]

            template = EmailTemplate.query.filter_by(template_key=template_key).first()

            if template:
                # 重置为默认值
                template.name = default_data['name']
                template.subject = default_data['subject']
                template.content_html = default_data['content_html']
                template.content_text = default_data.get('content_text')
                template.description = default_data.get('description')
                template.is_default = True
                template.updated_at = datetime.now(timezone.utc)
            else:
                # 创建默认模板
                template = EmailTemplate(
                    template_key=template_key,
                    name=default_data['name'],
                    subject=default_data['subject'],
                    content_html=default_data['content_html'],
                    content_text=default_data.get('content_text'),
                    description=default_data.get('description'),
                    is_default=True
                )
                db.session.add(template)

            db.session.commit()

            logger.info(f'重置模板成功：{template_key}')

            return {
                'success': True,
                'template': template.to_dict()
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'重置模板失败：{str(e)}')
            return {
                'success': False,
                'error': f'重置模板失败：{str(e)}'
            }

    @staticmethod
    def delete_template(template_key: str) -> Dict[str, Any]:
        """
        删除模板

        Args:
            template_key: 模板标识

        Returns:
            包含操作结果的字典
        """
        try:
            template = EmailTemplate.query.filter_by(template_key=template_key).first()

            if not template:
                return {
                    'success': False,
                    'error': f'模板不存在：{template_key}'
                }

            # 不允许删除系统默认模板
            if template.is_default and template_key in EmailTemplateService.DEFAULT_TEMPLATES:
                return {
                    'success': False,
                    'error': '不能删除系统默认模板，请使用重置功能'
                }

            db.session.delete(template)
            db.session.commit()

            logger.info(f'删除模板成功：{template_key}')

            return {
                'success': True,
                'message': '模板删除成功'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f'删除模板失败：{str(e)}')
            return {
                'success': False,
                'error': f'删除模板失败：{str(e)}'
            }

    @staticmethod
    def search_templates(query: str) -> Dict[str, Any]:
        """
        搜索模板

        Args:
            query: 搜索关键词

        Returns:
            包含搜索结果的字典
        """
        try:
            search_pattern = f'%{query}%'
            templates = EmailTemplate.query.filter(
                or_(
                    EmailTemplate.template_key.ilike(search_pattern),
                    EmailTemplate.name.ilike(search_pattern),
                    EmailTemplate.description.ilike(search_pattern)
                )
            ).all()

            return {
                'success': True,
                'templates': [t.to_dict() for t in templates]
            }

        except Exception as e:
            logger.error(f'搜索模板失败：{str(e)}')
            return {
                'success': False,
                'error': f'搜索模板失败：{str(e)}'
            }
