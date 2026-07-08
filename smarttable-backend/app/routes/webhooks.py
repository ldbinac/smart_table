"""
Webhook 路由模块
处理 Webhook 配置的 CRUD 操作、测试发送和投递日志查询
"""
import secrets
from urllib.parse import urlparse

from flask import Blueprint, request, g

from app.models.base import MemberRole
from app.models.webhook import WebhookConfig, WebhookDeliveryLog, WebhookMethod
from app.services.permission_service import PermissionService
from app.services.webhook_service import WebhookService
from app.utils.decorators import jwt_required
from app.utils.response import (
    success_response, error_response, not_found_response,
    forbidden_response, paginated_response
)

webhooks_bp = Blueprint('webhooks', __name__)
# 禁用严格斜杠，允许带或不带斜杠的 URL
webhooks_bp.strict_slashes = False


def _get_webhook_or_404(webhook_id):
    """获取 Webhook 配置，不存在时返回 None"""
    return WebhookConfig.query.get(webhook_id)


def _check_base_permission(base_id, min_role=MemberRole.VIEWER):
    """检查当前用户对 Base 的权限"""
    return PermissionService.check_permission(
        str(base_id), str(g.current_user_id), min_role
    )


def _normalize_method(method):
    """将请求方法字符串转换为 WebhookMethod 枚举"""
    if isinstance(method, WebhookMethod):
        return method
    method_str = str(method).upper() if method else 'POST'
    try:
        return WebhookMethod(method_str)
    except ValueError:
        return None


@webhooks_bp.route('/bases/<uuid:base_id>/webhooks', methods=['GET'])
@jwt_required
def get_webhooks(base_id):
    """
    获取 Base 下的 Webhook 配置列表
    ---
    tags:
      - Webhooks
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: 基础数据 ID
    responses:
      200:
        description: Webhook 配置列表
    """
    if not _check_base_permission(base_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限访问此基础数据')

    webhooks = WebhookConfig.query.filter_by(base_id=base_id).order_by(
        WebhookConfig.created_at.desc()
    ).all()

    return success_response(
        data=[webhook.to_dict() for webhook in webhooks],
        message='获取 Webhook 列表成功'
    )


@webhooks_bp.route('/bases/<uuid:base_id>/webhooks', methods=['POST'])
@jwt_required
def create_webhook(base_id):
    """
    在 Base 下创建 Webhook 配置
    ---
    tags:
      - Webhooks
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: 基础数据 ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
            - url
          properties:
            name:
              type: string
              description: Webhook 名称
            url:
              type: string
              description: 请求地址
            method:
              type: string
              enum: ['GET', 'POST', 'PUT']
              default: 'POST'
              description: 请求方法
            headers:
              type: object
              description: 自定义请求头
            body_template:
              type: string
              description: 请求体模板
            secret:
              type: string
              description: 签名密钥（不填则自动生成）
            retry_policy:
              type: object
              description: 重试策略
    responses:
      201:
        description: 创建的 Webhook 配置详情
    """
    if not _check_base_permission(base_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限在此基础数据中创建 Webhook')

    data = request.get_json() or {}

    # 验证必填字段
    name = (data.get('name') or '').strip()
    if not name:
        return error_response('Webhook 名称不能为空', code=400)
    if len(name) > 200:
        return error_response('Webhook 名称不能超过200个字符', code=400)

    url = (data.get('url') or '').strip()
    if not url:
        return error_response('Webhook URL 不能为空', code=400)
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return error_response('Webhook URL 格式不正确', code=400)

    method = _normalize_method(data.get('method', 'POST'))
    if method is None:
        return error_response('请求方法必须是 GET、POST 或 PUT', code=400)

    headers = data.get('headers', {})
    if not isinstance(headers, dict):
        return error_response('headers 必须是对象', code=400)

    retry_policy = data.get('retry_policy', {})
    if not isinstance(retry_policy, dict):
        return error_response('retry_policy 必须是对象', code=400)

    secret = data.get('secret')
    if secret is None or secret == '':
        secret = secrets.token_hex(32)

    webhook = WebhookConfig(
        base_id=base_id,
        name=name,
        url=url,
        method=method,
        headers=headers,
        body_template=data.get('body_template'),
        secret=secret,
        retry_policy=retry_policy,
        is_active=data.get('is_active', True),
        created_by=g.current_user_id
    )

    from app.extensions import db
    db.session.add(webhook)
    db.session.commit()

    return success_response(
        data=webhook.to_dict(),
        message='Webhook 创建成功',
        code=201
    )


@webhooks_bp.route('/webhooks/<uuid:webhook_id>', methods=['GET'])
@jwt_required
def get_webhook(webhook_id):
    """
    获取 Webhook 配置详情
    ---
    tags:
      - Webhooks
    security:
      - Bearer: []
    parameters:
      - name: webhook_id
        in: path
        type: string
        required: true
        description: Webhook 配置 ID
    responses:
      200:
        description: Webhook 配置详情
      404:
        description: Webhook 配置不存在
    """
    webhook = _get_webhook_or_404(webhook_id)
    if not webhook:
        return not_found_response('Webhook 配置')

    if not _check_base_permission(webhook.base_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限访问此 Webhook')

    return success_response(
        data=webhook.to_dict(),
        message='获取 Webhook 详情成功'
    )


@webhooks_bp.route('/webhooks/<uuid:webhook_id>', methods=['PUT'])
@jwt_required
def update_webhook(webhook_id):
    """
    更新 Webhook 配置
    ---
    tags:
      - Webhooks
    security:
      - Bearer: []
    parameters:
      - name: webhook_id
        in: path
        type: string
        required: true
        description: Webhook 配置 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            name:
              type: string
              description: Webhook 名称
            url:
              type: string
              description: 请求地址
            method:
              type: string
              enum: ['GET', 'POST', 'PUT']
              description: 请求方法
            headers:
              type: object
              description: 自定义请求头
            body_template:
              type: string
              description: 请求体模板
            secret:
              type: string
              description: 签名密钥
            retry_policy:
              type: object
              description: 重试策略
            is_active:
              type: boolean
              description: 是否启用
    responses:
      200:
        description: 更新后的 Webhook 配置详情
    """
    webhook = _get_webhook_or_404(webhook_id)
    if not webhook:
        return not_found_response('Webhook 配置')

    if not _check_base_permission(webhook.base_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限修改此 Webhook')

    data = request.get_json() or {}

    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name:
            return error_response('Webhook 名称不能为空', code=400)
        if len(name) > 200:
            return error_response('Webhook 名称不能超过200个字符', code=400)
        webhook.name = name

    if 'url' in data:
        url = (data['url'] or '').strip()
        if not url:
            return error_response('Webhook URL 不能为空', code=400)
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return error_response('Webhook URL 格式不正确', code=400)
        webhook.url = url

    if 'method' in data:
        method = _normalize_method(data['method'])
        if method is None:
            return error_response('请求方法必须是 GET、POST 或 PUT', code=400)
        webhook.method = method

    if 'headers' in data:
        headers = data['headers']
        if not isinstance(headers, dict):
            return error_response('headers 必须是对象', code=400)
        webhook.headers = headers

    if 'body_template' in data:
        webhook.body_template = data['body_template']

    if 'secret' in data:
        secret = data['secret']
        if secret is None or secret == '':
            secret = secrets.token_hex(32)
        webhook.secret = secret

    if 'retry_policy' in data:
        retry_policy = data['retry_policy']
        if not isinstance(retry_policy, dict):
            return error_response('retry_policy 必须是对象', code=400)
        webhook.retry_policy = retry_policy

    if 'is_active' in data:
        webhook.is_active = bool(data['is_active'])

    from app.extensions import db
    db.session.commit()

    return success_response(
        data=webhook.to_dict(),
        message='Webhook 更新成功'
    )


@webhooks_bp.route('/webhooks/<uuid:webhook_id>', methods=['DELETE'])
@jwt_required
def delete_webhook(webhook_id):
    """
    删除 Webhook 配置
    ---
    tags:
      - Webhooks
    security:
      - Bearer: []
    parameters:
      - name: webhook_id
        in: path
        type: string
        required: true
        description: Webhook 配置 ID
    responses:
      200:
        description: 删除成功
    """
    webhook = _get_webhook_or_404(webhook_id)
    if not webhook:
        return not_found_response('Webhook 配置')

    if not _check_base_permission(webhook.base_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限删除此 Webhook')

    from app.extensions import db
    db.session.delete(webhook)
    db.session.commit()

    return success_response(message='Webhook 删除成功')


@webhooks_bp.route('/webhooks/<uuid:webhook_id>/test', methods=['POST'])
@jwt_required
def test_webhook(webhook_id):
    """
    测试发送 Webhook
    ---
    tags:
      - Webhooks
    security:
      - Bearer: []
    parameters:
      - name: webhook_id
        in: path
        type: string
        required: true
        description: Webhook 配置 ID
    responses:
      200:
        description: 测试结果
    """
    webhook = _get_webhook_or_404(webhook_id)
    if not webhook:
        return not_found_response('Webhook 配置')

    if not _check_base_permission(webhook.base_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限测试此 Webhook')

    result = WebhookService.test_webhook(webhook)

    if result.get('success'):
        return success_response(
            data=result,
            message='Webhook 测试发送成功'
        )

    return error_response(
        message=result.get('error_message', 'Webhook 测试发送失败'),
        code=400,
        error='webhook_test_failed',
        details=[{
            'field': 'delivery',
            'message': result.get('error_message', '未知错误')
        }]
    )


@webhooks_bp.route('/webhooks/<uuid:webhook_id>/deliveries', methods=['GET'])
@jwt_required
def get_webhook_deliveries(webhook_id):
    """
    获取 Webhook 投递日志
    ---
    tags:
      - Webhooks
    security:
      - Bearer: []
    parameters:
      - name: webhook_id
        in: path
        type: string
        required: true
        description: Webhook 配置 ID
      - name: page
        in: query
        type: integer
        default: 1
        description: 页码
      - name: per_page
        in: query
        type: integer
        default: 20
        description: 每页数量
    responses:
      200:
        description: 投递日志列表
    """
    webhook = _get_webhook_or_404(webhook_id)
    if not webhook:
        return not_found_response('Webhook 配置')

    if not _check_base_permission(webhook.base_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限查看此 Webhook 的投递日志')

    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
    except ValueError:
        return error_response('分页参数必须是整数', code=400)

    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 1
    if per_page > 100:
        per_page = 100

    query = WebhookDeliveryLog.query.filter_by(webhook_config_id=webhook_id).order_by(
        WebhookDeliveryLog.created_at.desc()
    )
    total = query.count()
    logs = query.offset((page - 1) * per_page).limit(per_page).all()

    return paginated_response(
        items=[log.to_dict() for log in logs],
        total=total,
        page=page,
        per_page=per_page,
        message='获取投递日志成功'
    )


@webhooks_bp.route('/webhooks/deliveries/<uuid:delivery_id>/redeliver', methods=['POST'])
@jwt_required
def redeliver_webhook(delivery_id):
    """
    重新投递 Webhook
    ---
    tags:
      - Webhooks
    security:
      - Bearer: []
    parameters:
      - name: delivery_id
        in: path
        type: string
        required: true
        description: 投递记录 ID
    responses:
      200:
        description: 重新投递成功
      403:
        description: 无权限
      404:
        description: 投递记录或 Webhook 配置不存在
    """
    delivery_log = WebhookDeliveryLog.query.get(delivery_id)
    if not delivery_log:
        return not_found_response('投递记录')

    webhook_config = WebhookConfig.query.get(delivery_log.webhook_config_id)
    if not webhook_config:
        return not_found_response('Webhook 配置')

    if not _check_base_permission(webhook_config.base_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限重新投递此 Webhook')

    try:
        result = WebhookService.redeliver(delivery_log)
        return success_response(data=result, message='重新投递成功')
    except Exception as e:
        return error_response(f'重新投递失败: {e}', code=500)
