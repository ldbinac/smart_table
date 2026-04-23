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
    ---
    tags:
      - Email
    security:
      - Bearer: []
    description: 获取邮件模板列表（需要管理员权限）
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: 页码，从 1 开始
      - name: per_page
        in: query
        type: integer
        default: 20
        description: 每页数量
      - name: is_default
        in: query
        type: boolean
        description: 是否只显示默认模板
    responses:
      200:
        description: 返回分页邮件模板列表
      401:
        description: 未授权访问
      403:
        description: 权限不足
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
    ---
    tags:
      - Email
    security:
      - Bearer: []
    description: 获取单个邮件模板详情（需要管理员权限）
    parameters:
      - name: template_key
        in: path
        type: string
        required: true
        description: 模板标识（如 'user_registration', 'password_reset'）
    responses:
      200:
        description: 返回邮件模板详情
      401:
        description: 未授权访问
      403:
        description: 权限不足
      404:
        description: 模板不存在
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
    ---
    tags:
      - Email
    security:
      - Bearer: []
    description: 更新邮件模板（需要管理员权限）
    parameters:
      - name: template_key
        in: path
        type: string
        required: true
        description: 模板标识
      - name: body
        in: body
        schema:
          type: object
          properties:
            name:
              type: string
              description: 模板名称
            subject:
              type: string
              description: 邮件主题
            content_html:
              type: string
              description: HTML内容
            content_text:
              type: string
              description: 纯文本内容
            description:
              type: string
              description: 模板描述
    responses:
      200:
        description: 更新成功，返回更新后的模板
      400:
        description: 请求数据验证失败
      401:
        description: 未授权访问
      403:
        description: 权限不足
      404:
        description: 模板不存在
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
    ---
    tags:
      - Email
    security:
      - Bearer: []
    description: 重置邮件模板为默认模板（需要管理员权限）
    parameters:
      - name: template_key
        in: path
        type: string
        required: true
        description: 模板标识
    responses:
      200:
        description: 重置成功
      400:
        description: 该模板不支持重置
      401:
        description: 未授权访问
      403:
        description: 权限不足
      404:
        description: 模板不存在
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
    ---
    tags:
      - Email
    security:
      - Bearer: []
    description: 获取邮件发送日志（需要管理员权限）
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: 页码，从 1 开始
      - name: per_page
        in: query
        type: integer
        default: 20
        description: 每页数量
      - name: status
        in: query
        type: string
        enum: ['pending', 'sent', 'failed', 'retrying']
        description: 状态过滤
      - name: template_key
        in: query
        type: string
        description: 模板标识过滤
      - name: recipient_email
        in: query
        type: string
        description: 收件人邮箱过滤
      - name: start_date
        in: query
        type: string
        description: 开始时间（ISO 8601 格式）
      - name: end_date
        in: query
        type: string
        description: 结束时间（ISO 8601 格式）
    responses:
      200:
        description: 返回分页邮件发送日志列表
      400:
        description: 时间格式错误
      401:
        description: 未授权访问
      403:
        description: 权限不足
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
    ---
    tags:
      - Email
    security:
      - Bearer: []
    description: 获取邮件发送统计数据（需要管理员权限）
    responses:
      200:
        description: 返回邮件发送统计数据
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 200
            message:
              type: string
              example: "获取邮件发送统计成功"
            data:
              type: object
              properties:
                total:
                  type: integer
                  description: 总发送数量
                  example: 1000
                sent:
                  type: integer
                  description: 成功发送数量
                  example: 950
                failed:
                  type: integer
                  description: 失败数量
                  example: 40
                pending:
                  type: integer
                  description: 待发送数量
                  example: 5
                retrying:
                  type: integer
                  description: 重试中数量
                  example: 5
                success_rate:
                  type: number
                  description: 成功率
                  example: 95.0
                by_template:
                  type: object
                  description: 按模板统计
                by_status:
                  type: object
                  description: 按状态统计
      401:
        description: 未授权访问
      403:
        description: 权限不足
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


@email_bp.route('/queue/stats', methods=['GET'])
@jwt_required
@admin_required
def get_email_queue_stats() -> tuple:
    """
    获取邮件队列统计信息
    ---
    tags:
      - Email
    security:
      - Bearer: []
    description: 获取邮件队列统计信息（需要管理员权限）
    responses:
      200:
        description: 返回邮件队列统计
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 200
            message:
              type: string
              example: "获取邮件队列统计成功"
            data:
              type: object
              properties:
                queued:
                  type: integer
                  description: 队列中数量
                  example: 100
                sent:
                  type: integer
                  description: 已发送数量
                  example: 95
                failed:
                  type: integer
                  description: 失败数量
                  example: 3
                retried:
                  type: integer
                  description: 重试数量
                  example: 2
                pending:
                  type: integer
                  description: 待处理数量
                  example: 5
                is_running:
                  type: boolean
                  description: 队列是否运行中
                  example: true
      401:
        description: 未授权访问
      403:
        description: 权限不足
    """
    try:
        from app.services.email_queue_service import email_queue

        stats = email_queue.get_stats()

        return success_response(
            data=stats,
            message='获取邮件队列统计成功'
        )

    except Exception as e:
        return error_response(f'获取邮件队列统计失败：{str(e)}', code=500)


@email_bp.route('/queue/clear', methods=['POST'])
@jwt_required
@admin_required
def clear_email_queue_stats() -> tuple:
    """
    清除邮件队列统计信息
    ---
    tags:
      - Email
    security:
      - Bearer: []
    description: 清除邮件队列统计信息（需要管理员权限）
    responses:
      200:
        description: 清除成功
      401:
        description: 未授权访问
      403:
        description: 权限不足
    """
    try:
        from app.services.email_queue_service import email_queue

        email_queue.clear_stats()

        return success_response(message='邮件队列统计已清除')

    except Exception as e:
        return error_response(f'清除邮件队列统计失败：{str(e)}', code=500)


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
