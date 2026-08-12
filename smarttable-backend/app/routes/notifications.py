"""
站内信通知服务 API 路由模块
处理站内信通知的查询、已读管理、统计分析与管理端日志查询等功能
"""
import traceback
from datetime import datetime

from flask import Blueprint, request, g, current_app

from app.utils.decorators import jwt_required, admin_required
from app.utils.response import (
    success_response,
    error_response,
    paginated_response,
    not_found_response
)
from app.services.notification_service import NotificationService
from app.services.notification_retry_service import NotificationRetryService
from app.models.notification import Notification, NotificationStatus

notifications_bp = Blueprint('notifications', __name__)
notifications_bp.strict_slashes = False


# ==================== 用户端路由 ====================

@notifications_bp.route('/notifications', methods=['GET'])
@jwt_required
def get_notifications() -> tuple:
    """
    获取当前用户的站内信列表
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    description: 分页获取当前登录用户的站内信列表，支持按已读状态、来源、状态过滤
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
      - name: is_read
        in: query
        type: string
        enum: ['true', 'false']
        description: 是否已读过滤
      - name: source
        in: query
        type: string
        description: 通知来源过滤（system/auth/admin/workflow/approval 等）
      - name: status
        in: query
        type: string
        enum: ['pending', 'sent', 'failed', 'retrying']
        description: 状态过滤
    responses:
      200:
        description: 返回分页站内信列表
      401:
        description: 未授权访问
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        is_read = request.args.get('is_read', None)
        source = request.args.get('source', None)
        status = request.args.get('status', None)

        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20

        filters = {}
        if is_read is not None:
            filters['is_read'] = is_read.lower() == 'true'
        if source:
            filters['source'] = source
        if status:
            filters['status'] = status

        result = NotificationService.get_notifications(
            g.current_user_id,
            page,
            per_page,
            filters
        )

        if not result.get('success'):
            return error_response(
                result.get('error', '获取站内信列表失败'),
                code=500
            )

        pagination = result.get('pagination', {})

        return paginated_response(
            items=result.get('notifications', []),
            total=pagination.get('total', 0),
            page=pagination.get('current_page', page),
            per_page=pagination.get('per_page', per_page),
            message='获取站内信列表成功'
        )

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 获取站内信列表失败：{str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪：{traceback.format_exc()}')
        return error_response('获取站内信列表失败，请稍后重试', code=500, error='internal_server_error', request_id=request_id)


@notifications_bp.route('/notifications/unread-count', methods=['GET'])
@jwt_required
def get_unread_count() -> tuple:
    """
    获取当前用户的未读站内信数量
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    description: 获取当前登录用户的未读站内信数量
    responses:
      200:
        description: 返回未读数量
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 200
            message:
              type: string
              example: "获取未读数量成功"
            data:
              type: object
              properties:
                count:
                  type: integer
                  description: 未读数量
                  example: 5
      401:
        description: 未授权访问
    """
    try:
        result = NotificationService.get_unread_count(g.current_user_id)

        if not result.get('success'):
            return error_response(
                result.get('error', '获取未读数量失败'),
                code=500
            )

        return success_response(
            data={'count': result.get('count', 0)},
            message='获取未读数量成功'
        )

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 获取未读站内信数量失败：{str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪：{traceback.format_exc()}')
        return error_response('获取未读数量失败，请稍后重试', code=500, error='internal_server_error', request_id=request_id)


@notifications_bp.route('/notifications/<notification_id>', methods=['GET'])
@jwt_required
def get_notification(notification_id: str) -> tuple:
    """
    获取单条站内信详情
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    description: 获取当前用户指定站内信的详情（仅可访问自己的站内信）
    parameters:
      - name: notification_id
        in: path
        type: string
        required: true
        description: 站内信 ID
    responses:
      200:
        description: 返回站内信详情
      401:
        description: 未授权访问
      403:
        description: 无权访问该站内信
      404:
        description: 站内信不存在
    """
    try:
        result = NotificationService.get_notification(notification_id, g.current_user_id)

        if not result.get('success'):
            error_msg = result.get('error', '')
            if '不存在' in error_msg:
                return not_found_response('站内信')
            if '无权' in error_msg:
                return error_response(error_msg, code=403, error='forbidden')
            return error_response(error_msg or '获取站内信详情失败', code=400)

        return success_response(
            data=result.get('notification'),
            message='获取站内信详情成功'
        )

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 获取站内信详情失败：{str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪：{traceback.format_exc()}')
        return error_response('获取站内信详情失败，请稍后重试', code=500, error='internal_server_error', request_id=request_id)


@notifications_bp.route('/notifications/<notification_id>/read', methods=['POST'])
@jwt_required
def mark_notification_as_read(notification_id: str) -> tuple:
    """
    标记单条站内信为已读
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    description: 标记当前用户指定的站内信为已读（仅可操作自己的站内信）
    parameters:
      - name: notification_id
        in: path
        type: string
        required: true
        description: 站内信 ID
    responses:
      200:
        description: 标记成功
      401:
        description: 未授权访问
      403:
        description: 无权操作该站内信
      404:
        description: 站内信不存在
    """
    try:
        result = NotificationService.mark_as_read(notification_id, g.current_user_id)

        if not result.get('success'):
            error_msg = result.get('error', '')
            if '不存在' in error_msg:
                return not_found_response('站内信')
            if '无权' in error_msg:
                return error_response(error_msg, code=403, error='forbidden')
            return error_response(error_msg or '标记已读失败', code=400)

        return success_response(message=result.get('message', '已标记为已读'))

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 标记站内信已读失败：{str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪：{traceback.format_exc()}')
        return error_response('标记站内信已读失败，请稍后重试', code=500, error='internal_server_error', request_id=request_id)


@notifications_bp.route('/notifications/read-all', methods=['POST'])
@jwt_required
def mark_all_notifications_as_read() -> tuple:
    """
    标记当前用户的所有未读站内信为已读
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    description: 批量标记当前登录用户的所有未读站内信为已读
    responses:
      200:
        description: 标记成功，返回更新条数
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 200
            message:
              type: string
              example: "已全部标记为已读"
            data:
              type: object
              properties:
                updated_count:
                  type: integer
                  description: 更新条数
                  example: 10
      401:
        description: 未授权访问
    """
    try:
        result = NotificationService.mark_all_as_read(g.current_user_id)

        if not result.get('success'):
            return error_response(
                result.get('error', '标记已读失败'),
                code=500
            )

        return success_response(
            data={'updated_count': result.get('updated_count', 0)},
            message='已全部标记为已读'
        )

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 批量标记站内信已读失败：{str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪：{traceback.format_exc()}')
        return error_response('批量标记站内信已读失败，请稍后重试', code=500, error='internal_server_error', request_id=request_id)


@notifications_bp.route('/notifications/<notification_id>', methods=['DELETE'])
@jwt_required
def delete_notification(notification_id: str) -> tuple:
    """
    删除单条站内信
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    description: 删除当前用户指定的站内信（仅可删除自己的站内信）
    parameters:
      - name: notification_id
        in: path
        type: string
        required: true
        description: 站内信 ID
    responses:
      200:
        description: 删除成功
      401:
        description: 未授权访问
      403:
        description: 无权删除该站内信
      404:
        description: 站内信不存在
    """
    try:
        result = NotificationService.delete_notification(notification_id, g.current_user_id)

        if not result.get('success'):
            error_msg = result.get('error', '')
            if '不存在' in error_msg:
                return not_found_response('站内信')
            if '无权' in error_msg:
                return error_response(error_msg, code=403, error='forbidden')
            return error_response(error_msg or '删除站内信失败', code=400)

        return success_response(message=result.get('message', '站内信已删除'))

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 删除站内信失败：{str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪：{traceback.format_exc()}')
        return error_response('删除站内信失败，请稍后重试', code=500, error='internal_server_error', request_id=request_id)


# ==================== 管理端路由 ====================

@notifications_bp.route('/admin/notifications/logs', methods=['GET'])
@jwt_required
@admin_required
def get_notification_logs() -> tuple:
    """
    获取站内信发送日志
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    description: 获取全站站内信发送日志（需要管理员权限）
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
      - name: source
        in: query
        type: string
        description: 通知来源过滤
      - name: recipient_user_id
        in: query
        type: string
        description: 收件人用户 ID 过滤
      - name: is_read
        in: query
        type: string
        enum: ['true', 'false']
        description: 是否已读过滤
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
        description: 返回分页站内信日志列表
      400:
        description: 时间格式错误或无效的参数值
      401:
        description: 未授权访问
      403:
        description: 权限不足
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status', None)
        source = request.args.get('source', None)
        recipient_user_id = request.args.get('recipient_user_id', None)
        is_read = request.args.get('is_read', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)

        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20

        query = Notification.query

        if status:
            try:
                notification_status = NotificationStatus(status.lower())
                query = query.filter_by(status=notification_status)
            except ValueError:
                return error_response('无效的状态值', code=400)

        if source:
            query = query.filter_by(source=source)

        if recipient_user_id:
            from uuid import UUID
            try:
                recipient_uuid = UUID(recipient_user_id)
            except (ValueError, AttributeError):
                return error_response('无效的收件人用户 ID', code=400)
            query = query.filter_by(recipient_user_id=recipient_uuid)

        if is_read is not None:
            query = query.filter_by(is_read=(is_read.lower() == 'true'))

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(Notification.created_at >= start_dt)
            except ValueError:
                return error_response('开始时间格式错误', code=400)

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(Notification.created_at <= end_dt)
            except ValueError:
                return error_response('结束时间格式错误', code=400)

        total = query.count()
        logs = query.order_by(Notification.created_at.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()

        return paginated_response(
            items=[log.to_dict() for log in logs],
            total=total,
            page=page,
            per_page=per_page,
            message='获取站内信日志成功'
        )

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 获取站内信日志失败：{str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪：{traceback.format_exc()}')
        return error_response('获取站内信日志失败，请稍后重试', code=500, error='internal_server_error', request_id=request_id)


@notifications_bp.route('/admin/notifications/stats', methods=['GET'])
@jwt_required
@admin_required
def get_notification_stats() -> tuple:
    """
    获取站内信发送统计
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    description: 获取全站站内信发送统计数据（需要管理员权限）
    responses:
      200:
        description: 返回站内信发送统计数据
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 200
            message:
              type: string
              example: "获取站内信统计成功"
            data:
              type: object
              properties:
                total:
                  type: integer
                  description: 总数量
                  example: 1000
                by_status:
                  type: object
                  description: 按状态统计
                read:
                  type: integer
                  description: 已读数量
                  example: 600
                unread:
                  type: integer
                  description: 未读数量
                  example: 400
                by_source:
                  type: array
                  description: 按来源统计
                by_template:
                  type: array
                  description: 按模板统计
      401:
        description: 未授权访问
      403:
        description: 权限不足
    """
    try:
        result = NotificationService.get_stats()

        if not result.get('success'):
            return error_response(
                result.get('error', '获取站内信统计失败'),
                code=500
            )

        return success_response(
            data=result.get('stats'),
            message='获取站内信统计成功'
        )

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 获取站内信统计失败：{str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪：{traceback.format_exc()}')
        return error_response('获取站内信统计失败，请稍后重试', code=500, error='internal_server_error', request_id=request_id)


@notifications_bp.route('/admin/notifications/<notification_id>/retry', methods=['POST'])
@jwt_required
@admin_required
def retry_notification(notification_id: str) -> tuple:
    """
    重试发送失败的站内信
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    description: 手动重试发送指定失败的站内信（需要管理员权限）
    parameters:
      - name: notification_id
        in: path
        type: string
        required: true
        description: 站内信 ID
    responses:
      200:
        description: 重试成功
      400:
        description: 站内信状态不允许重试或已达到最大重试次数
      401:
        description: 未授权访问
      403:
        description: 权限不足
      404:
        description: 站内信不存在
    """
    try:
        result = NotificationRetryService.retry_failed_notification(notification_id)

        if not result.get('success'):
            error_msg = result.get('error', '')
            if '不存在' in error_msg:
                return not_found_response('站内信')
            return error_response(error_msg or '重试失败', code=400)

        return success_response(message=result.get('message', '站内信重试处理成功'))

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 重试站内信失败：{str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪：{traceback.format_exc()}')
        return error_response('重试站内信失败，请稍后重试', code=500, error='internal_server_error', request_id=request_id)
