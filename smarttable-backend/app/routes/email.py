"""
邮件服务 API 路由模块
处理邮件模板管理和邮件发送日志查询等功能
"""
from datetime import datetime

from flask import Blueprint, request
from marshmallow import ValidationError
from sqlalchemy import func, case

from app.extensions import db
from app.models.email_template import EmailTemplate
from app.models.email_log import EmailLog, EmailStatus
from app.utils.decorators import jwt_required, admin_required
from app.utils.response import (
    success_response,
    error_response,
    paginated_response,
    not_found_response,
    validation_error_response
)

email_bp = Blueprint('email', __name__)
email_bp.strict_slashes = False


@email_bp.route('/templates', methods=['GET'])
@jwt_required
@admin_required
def get_email_templates() -> tuple:
    """
    获取邮件模板列表

    查询参数:
        page: 页码，从 1 开始，默认 1
        per_page: 每页数量，默认 20
        is_default: 是否只显示默认模板（true/false）

    响应:
        200: 返回分页邮件模板列表
        401: 未授权访问
        403: 权限不足

    示例:
        GET /api/admin/email/templates?page=1&per_page=20&is_default=true
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        is_default = request.args.get('is_default', None)

        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20

        query = EmailTemplate.query

        if is_default is not None:
            is_default_bool = is_default.lower() == 'true'
            query = query.filter_by(is_default=is_default_bool)

        total = query.count()
        templates = query.order_by(EmailTemplate.template_key.asc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()

        return paginated_response(
            items=[t.to_dict() for t in templates],
            total=total,
            page=page,
            per_page=per_page,
            message='获取邮件模板列表成功'
        )

    except Exception as e:
        return error_response(f'获取邮件模板列表失败：{str(e)}', code=500)


@email_bp.route('/templates/<template_key>', methods=['GET'])
@jwt_required
@admin_required
def get_email_template(template_key: str) -> tuple:
    """
    获取单个邮件模板详情

    路径参数:
        template_key: 模板标识（如 'user_registration', 'password_reset'）

    响应:
        200: 返回邮件模板详情
        401: 未授权访问
        403: 权限不足
        404: 模板不存在
    """
    template = EmailTemplate.query.filter_by(template_key=template_key).first()

    if not template:
        return not_found_response('邮件模板')

    return success_response(
        data=template.to_dict(),
        message='获取邮件模板详情成功'
    )


@email_bp.route('/templates/<template_key>', methods=['PUT'])
@jwt_required
@admin_required
def update_email_template(template_key: str) -> tuple:
    """
    更新邮件模板

    路径参数:
        template_key: 模板标识

    请求体:
        {
            "name": "模板名称" (可选),
            "subject": "邮件主题" (可选),
            "content_html": "HTML内容" (可选),
            "content_text": "纯文本内容" (可选),
            "description": "模板描述" (可选)
        }

    响应:
        200: 更新成功，返回更新后的模板
        400: 请求数据验证失败
        401: 未授权访问
        403: 权限不足
        404: 模板不存在
    """
    template = EmailTemplate.query.filter_by(template_key=template_key).first()

    if not template:
        return not_found_response('邮件模板')

    data = request.get_json()

    if not data:
        return error_response('请求体不能为空', code=400)

    try:
        allowed_fields = ['name', 'subject', 'content_html', 'content_text', 'description']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        if not update_data:
            return error_response('没有提供有效的更新字段', code=400)

        for field, value in update_data.items():
            setattr(template, field, value)

        db.session.commit()

        return success_response(
            data=template.to_dict(),
            message='邮件模板更新成功'
        )

    except Exception as e:
        db.session.rollback()
        return error_response(f'更新邮件模板失败：{str(e)}', code=500)


@email_bp.route('/templates/<template_key>/reset', methods=['POST'])
@jwt_required
@admin_required
def reset_email_template(template_key: str) -> tuple:
    """
    重置邮件模板为默认模板

    路径参数:
        template_key: 模板标识

    响应:
        200: 重置成功
        400: 该模板不支持重置
        401: 未授权访问
        403: 权限不足
        404: 模板不存在
    """
    template = EmailTemplate.query.filter_by(template_key=template_key).first()

    if not template:
        return not_found_response('邮件模板')

    if not template.is_default:
        return error_response('只有系统默认模板支持重置操作', code=400)

    try:
        default_templates = _get_default_templates()

        if template_key not in default_templates:
            return error_response('未找到该模板的默认内容', code=400)

        default_data = default_templates[template_key]
        template.name = default_data['name']
        template.subject = default_data['subject']
        template.content_html = default_data['content_html']
        template.content_text = default_data.get('content_text')
        template.description = default_data.get('description')

        db.session.commit()

        return success_response(
            data=template.to_dict(),
            message='邮件模板已重置为默认内容'
        )

    except Exception as e:
        db.session.rollback()
        return error_response(f'重置邮件模板失败：{str(e)}', code=500)


@email_bp.route('/logs', methods=['GET'])
@jwt_required
@admin_required
def get_email_logs() -> tuple:
    """
    获取邮件发送日志

    查询参数:
        page: 页码，从 1 开始，默认 1
        per_page: 每页数量，默认 20
        status: 状态过滤（pending, sent, failed, retrying）
        template_key: 模板标识过滤
        recipient_email: 收件人邮箱过滤
        start_date: 开始时间（ISO 8601 格式）
        end_date: 结束时间（ISO 8601 格式）

    响应:
        200: 返回分页邮件发送日志列表
        400: 时间格式错误
        401: 未授权访问
        403: 权限不足
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status', None)
        template_key = request.args.get('template_key', None)
        recipient_email = request.args.get('recipient_email', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)

        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20

        query = EmailLog.query

        if status:
            try:
                email_status = EmailStatus(status.lower())
                query = query.filter_by(status=email_status)
            except ValueError:
                return error_response('无效的状态值', code=400)

        if template_key:
            query = query.filter_by(template_key=template_key)

        if recipient_email:
            query = query.filter(EmailLog.recipient_email.ilike(f'%{recipient_email}%'))

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(EmailLog.created_at >= start_dt)
            except ValueError:
                return error_response('开始时间格式错误', code=400)

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(EmailLog.created_at <= end_dt)
            except ValueError:
                return error_response('结束时间格式错误', code=400)

        total = query.count()
        logs = query.order_by(EmailLog.created_at.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()

        return paginated_response(
            items=[log.to_dict() for log in logs],
            total=total,
            page=page,
            per_page=per_page,
            message='获取邮件发送日志成功'
        )

    except Exception as e:
        return error_response(f'获取邮件发送日志失败：{str(e)}', code=500)


@email_bp.route('/stats', methods=['GET'])
@jwt_required
@admin_required
def get_email_stats() -> tuple:
    """
    获取邮件发送统计

    响应:
        200: 返回邮件发送统计数据
        401: 未授权访问
        403: 权限不足

    返回示例:
        {
            "total": 1000,
            "sent": 950,
            "failed": 40,
            "pending": 5,
            "retrying": 5,
            "success_rate": 95.0,
            "by_template": {
                "user_registration": {"total": 100, "sent": 98, "failed": 2},
                "password_reset": {"total": 50, "sent": 50, "failed": 0}
            },
            "by_status": {
                "pending": 5,
                "sent": 950,
                "failed": 40,
                "retrying": 5
            }
        }
    """
    try:
        total = EmailLog.query.count()
        sent = EmailLog.query.filter_by(status=EmailStatus.SENT).count()
        failed = EmailLog.query.filter_by(status=EmailStatus.FAILED).count()
        pending = EmailLog.query.filter_by(status=EmailStatus.PENDING).count()
        retrying = EmailLog.query.filter_by(status=EmailStatus.RETRYING).count()

        success_rate = (sent / total * 100) if total > 0 else 0.0

        template_stats = db.session.query(
            EmailLog.template_key,
            func.count(EmailLog.id).label('total'),
            func.sum(case((EmailLog.status == EmailStatus.SENT, 1), else_=0)).label('sent'),
            func.sum(case((EmailLog.status == EmailStatus.FAILED, 1), else_=0)).label('failed'),
            func.sum(case((EmailLog.status == EmailStatus.PENDING, 1), else_=0)).label('pending'),
            func.sum(case((EmailLog.status == EmailStatus.RETRYING, 1), else_=0)).label('retrying')
        ).group_by(EmailLog.template_key).all()

        by_template = {}
        for stat in template_stats:
            by_template[stat.template_key] = {
                'total': stat.total,
                'sent': stat.sent or 0,
                'failed': stat.failed or 0,
                'pending': stat.pending or 0,
                'retrying': stat.retrying or 0
            }

        stats = {
            'total': total,
            'sent': sent,
            'failed': failed,
            'pending': pending,
            'retrying': retrying,
            'success_rate': round(success_rate, 2),
            'by_template': by_template,
            'by_status': {
                'pending': pending,
                'sent': sent,
                'failed': failed,
                'retrying': retrying
            }
        }

        return success_response(
            data=stats,
            message='获取邮件发送统计成功'
        )

    except Exception as e:
        return error_response(f'获取邮件发送统计失败：{str(e)}', code=500)


def _get_default_templates() -> dict:
    """
    获取系统默认邮件模板内容

    Returns:
        包含默认模板内容的字典
    """
    return {
        'user_registration': {
            'name': '用户注册欢迎邮件',
            'subject': '欢迎注册 SmartTable',
            'content_html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>欢迎注册</title>
</head>
<body>
    <h2>欢迎加入 SmartTable！</h2>
    <p>您好 {{ user_name }}，</p>
    <p>感谢您注册 SmartTable 账号。您的账号已成功创建，现在可以开始使用我们的服务了。</p>
    <p>如果您有任何问题，请随时联系我们的支持团队。</p>
    <p>祝您使用愉快！</p>
    <p>SmartTable 团队</p>
</body>
</html>
            ''',
            'content_text': '''
欢迎加入 SmartTable！

您好 {{ user_name }}，

感谢您注册 SmartTable 账号。您的账号已成功创建，现在可以开始使用我们的服务了。

如果您有任何问题，请随时联系我们的支持团队。

祝您使用愉快！

SmartTable 团队
            ''',
            'description': '用户注册成功后发送的欢迎邮件'
        },
        'password_reset': {
            'name': '密码重置邮件',
            'subject': 'SmartTable 密码重置请求',
            'content_html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>密码重置</title>
</head>
<body>
    <h2>密码重置请求</h2>
    <p>您好，</p>
    <p>我们收到了您的密码重置请求。请点击以下链接重置您的密码：</p>
    <p><a href="{{ reset_link }}">重置密码</a></p>
    <p>此链接将在 {{ expires_in }} 小时后过期。</p>
    <p>如果您没有请求重置密码，请忽略此邮件。</p>
    <p>SmartTable 团队</p>
</body>
</html>
            ''',
            'content_text': '''
密码重置请求

您好，

我们收到了您的密码重置请求。请访问以下链接重置您的密码：

{{ reset_link }}

此链接将在 {{ expires_in }} 小时后过期。

如果您没有请求重置密码，请忽略此邮件。

SmartTable 团队
            ''',
            'description': '用户请求密码重置时发送的邮件'
        },
        'email_verification': {
            'name': '邮箱验证邮件',
            'subject': '请验证您的邮箱地址',
            'content_html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>邮箱验证</title>
</head>
<body>
    <h2>验证您的邮箱地址</h2>
    <p>您好 {{ user_name }}，</p>
    <p>感谢您注册 SmartTable。请点击以下链接验证您的邮箱地址：</p>
    <p><a href="{{ verification_link }}">验证邮箱</a></p>
    <p>此链接将在 {{ expires_in }} 小时后过期。</p>
    <p>如果您没有注册 SmartTable，请忽略此邮件。</p>
    <p>SmartTable 团队</p>
</body>
</html>
            ''',
            'content_text': '''
验证您的邮箱地址

您好 {{ user_name }}，

感谢您注册 SmartTable。请访问以下链接验证您的邮箱地址：

{{ verification_link }}

此链接将在 {{ expires_in }} 小时后过期。

如果您没有注册 SmartTable，请忽略此邮件。

SmartTable 团队
            ''',
            'description': '用户注册后发送的邮箱验证邮件'
        }
    }
