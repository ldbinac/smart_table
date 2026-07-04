"""
审批路由模块

提供工作流审批任务的查询与操作接口。
"""
import traceback
import uuid
from typing import Optional

from flask import Blueprint, request, g, current_app

from app.models.base import Base, MemberRole
from app.models.operation_history import OperationHistory
from app.models.record import Record
from app.models.workflow import Workflow
from app.models.workflow_instance import (
    WorkflowInstance,
    WorkflowTask,
    WorkflowTaskStatus,
)
from app.services.approval_service import ApprovalService
from app.services.permission_service import PermissionService
from app.services.record_service import RecordService
from app.utils.decorators import jwt_required
from app.utils.response import success_response, error_response

approvals_bp = Blueprint('approvals', __name__)
# 禁用严格斜杠，允许带或不带斜杠的 URL
approvals_bp.strict_slashes = False


def _to_uuid(value: Optional[str]) -> Optional[uuid.UUID]:
    """将字符串转为 UUID 对象，转换失败返回 None"""
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def _check_base_viewer(base_id: str, user_id: str) -> bool:
    """检查用户在 Base 中至少拥有 VIEWER 权限"""
    return PermissionService.check_permission(
        str(base_id), str(user_id), MemberRole.VIEWER
    )


def _check_task_assignee(task: WorkflowTask, user_id: str) -> bool:
    """检查当前用户是否为任务处理人"""
    if not task.assignee_id:
        return False
    return str(task.assignee_id) == str(user_id)


def _get_task_or_404(task_id: str):
    """根据 ID 获取任务，不存在则返回 None"""
    task_uuid = _to_uuid(task_id)
    if not task_uuid:
        return None
    return WorkflowTask.query.get(task_uuid)


def _task_base_id(task: WorkflowTask) -> Optional[str]:
    """获取任务所属 Base 的 ID"""
    instance = task.instance
    if not instance:
        return None
    workflow = instance.workflow
    return str(workflow.base_id) if workflow and workflow.base_id else None


def _build_task_detail(task: WorkflowTask) -> dict:
    """构建任务详情，包含实例、触发记录与审批历史"""
    instance = task.instance
    record = None
    history = []

    if instance:
        record = instance.trigger_record
        history = OperationHistory.get_resource_history(
            resource_type='workflow',
            resource_id=str(instance.id),
            limit=100,
        )

    return {
        'task': task.to_dict(),
        'instance': instance.to_dict() if instance else None,
        'record': record.to_dict() if record else None,
        'history': [h.to_dict() for h in history],
    }


@approvals_bp.route('/bases/<base_id>/approvals', methods=['GET'])
@jwt_required
def get_my_approvals(base_id: str):
    """
    获取我的待审批/已审批列表
    ---
    tags:
      - Approvals
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: Base ID
      - name: status
        in: query
        type: string
        description: 状态筛选（pending/approved/rejected/transferred/expired）
    responses:
      200:
        description: 审批任务列表
      403:
        description: 无权限
      404:
        description: Base 不存在
    """
    base = Base.query.get(base_id)
    if not base:
        return error_response('Base 不存在', 404)

    if not _check_base_viewer(base_id, g.current_user_id):
        return error_response('无权访问该 Base', 403)

    status = request.args.get('status', '').strip()
    user_uuid = _to_uuid(g.current_user_id)
    base_uuid = _to_uuid(base_id)

    try:
        query = WorkflowTask.query.filter_by(assignee_id=user_uuid)
        query = (
            query.join(WorkflowInstance)
            .join(Workflow)
            .filter(Workflow.base_id == base_uuid)
        )

        if status:
            try:
                task_status = WorkflowTaskStatus(status)
                query = query.filter(WorkflowTask.status == task_status)
            except ValueError:
                return error_response(f'无效的状态值: {status}', 400)

        # 按实例开始时间倒序排列
        query = query.order_by(WorkflowInstance.started_at.desc())
        tasks = query.all()
        items = [t.to_dict() for t in tasks]

        return success_response(items, '获取审批列表成功')

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 获取审批列表失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response(
            '获取审批列表失败，请稍后重试',
            500,
            error='internal_server_error',
            request_id=request_id,
        )


@approvals_bp.route('/approvals/<task_id>', methods=['GET'])
@jwt_required
def get_approval_task(task_id: str):
    """
    获取审批任务详情
    ---
    tags:
      - Approvals
    security:
      - Bearer: []
    parameters:
      - name: task_id
        in: path
        type: string
        required: true
        description: 审批任务 ID
    responses:
      200:
        description: 审批任务详情
      403:
        description: 无权限
      404:
        description: 任务不存在
    """
    task = _get_task_or_404(task_id)
    if not task:
        return error_response('审批任务不存在', 404)

    task_base_id = _task_base_id(task)
    if not task_base_id:
        return error_response('任务数据异常', 500)

    if not _check_task_assignee(task, g.current_user_id) and \
            not _check_base_viewer(task_base_id, g.current_user_id):
        return error_response('无权查看该审批任务', 403)

    try:
        detail = _build_task_detail(task)
        return success_response(detail, '获取审批任务详情成功')

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 获取审批任务详情失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response(
            '获取审批任务详情失败，请稍后重试',
            500,
            error='internal_server_error',
            request_id=request_id,
        )


@approvals_bp.route('/approvals/<task_id>/approve', methods=['POST'])
@jwt_required
def approve_task(task_id: str):
    """
    同意审批
    ---
    tags:
      - Approvals
    security:
      - Bearer: []
    parameters:
      - name: task_id
        in: path
        type: string
        required: true
        description: 审批任务 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            comment:
              type: string
              description: 审批意见（可选）
    responses:
      200:
        description: 审批成功
      403:
        description: 无权处理
      404:
        description: 任务不存在
    """
    task = _get_task_or_404(task_id)
    if not task:
        return error_response('审批任务不存在', 404)

    if not _check_task_assignee(task, g.current_user_id):
        return error_response('无权处理该审批任务', 403)

    data = request.get_json(silent=True) or {}
    comment = data.get('comment')

    try:
        result = ApprovalService.approve(
            task_id=task_id,
            user_id=g.current_user_id,
            comment=comment,
        )
        if not result.get('success'):
            return error_response(
                result.get('error', '审批失败'),
                400,
            )
        return success_response(result, '审批已通过')

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 审批同意失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response(
            '审批同意失败，请稍后重试',
            500,
            error='internal_server_error',
            request_id=request_id,
        )


@approvals_bp.route('/approvals/<task_id>/reject', methods=['POST'])
@jwt_required
def reject_task(task_id: str):
    """
    驳回审批
    ---
    tags:
      - Approvals
    security:
      - Bearer: []
    parameters:
      - name: task_id
        in: path
        type: string
        required: true
        description: 审批任务 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            comment:
              type: string
              description: 驳回意见（可选）
    responses:
      200:
        description: 驳回成功
      403:
        description: 无权处理
      404:
        description: 任务不存在
    """
    task = _get_task_or_404(task_id)
    if not task:
        return error_response('审批任务不存在', 404)

    if not _check_task_assignee(task, g.current_user_id):
        return error_response('无权处理该审批任务', 403)

    data = request.get_json(silent=True) or {}
    comment = data.get('comment')

    try:
        result = ApprovalService.reject(
            task_id=task_id,
            user_id=g.current_user_id,
            comment=comment,
        )
        if not result.get('success'):
            return error_response(
                result.get('error', '驳回失败'),
                400,
            )
        return success_response(result, '审批已驳回')

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 审批驳回失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response(
            '审批驳回失败，请稍后重试',
            500,
            error='internal_server_error',
            request_id=request_id,
        )


@approvals_bp.route('/approvals/<task_id>/transfer', methods=['POST'])
@jwt_required
def transfer_task(task_id: str):
    """
    转办审批
    ---
    tags:
      - Approvals
    security:
      - Bearer: []
    parameters:
      - name: task_id
        in: path
        type: string
        required: true
        description: 审批任务 ID
      - name: body
        in: body
        schema:
          type: object
          required:
            - new_assignee_id
          properties:
            new_assignee_id:
              type: string
              description: 新审批人 ID
            comment:
              type: string
              description: 转交说明（可选）
    responses:
      200:
        description: 转办成功
      400:
        description: 参数错误
      403:
        description: 无权处理
      404:
        description: 任务不存在
    """
    task = _get_task_or_404(task_id)
    if not task:
        return error_response('审批任务不存在', 404)

    if not _check_task_assignee(task, g.current_user_id):
        return error_response('无权处理该审批任务', 403)

    data = request.get_json(silent=True) or {}
    new_assignee_id = data.get('new_assignee_id')
    comment = data.get('comment')

    if not new_assignee_id:
        return error_response('缺少 new_assignee_id 参数', 400)

    try:
        result = ApprovalService.transfer(
            task_id=task_id,
            user_id=g.current_user_id,
            new_assignee_id=new_assignee_id,
            comment=comment,
        )
        if not result.get('success'):
            return error_response(
                result.get('error', '转办失败'),
                400,
            )
        return success_response(result, '审批已转办')

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 审批转办失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response(
            '审批转办失败，请稍后重试',
            500,
            error='internal_server_error',
            request_id=request_id,
        )


@approvals_bp.route('/records/<record_id>/approval-history', methods=['GET'])
@jwt_required
def get_record_approval_history(record_id: str):
    """
    获取某条记录的审批历史
    ---
    tags:
      - Approvals
    security:
      - Bearer: []
    parameters:
      - name: record_id
        in: path
        type: string
        required: true
        description: 记录 ID
    responses:
      200:
        description: 审批历史
      403:
        description: 无权限
      404:
        description: 记录不存在
    """
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)

    table = record.table
    if table and not _check_base_viewer(str(table.base_id), g.current_user_id):
        return error_response('无权访问该记录', 403)

    try:
        record_uuid = _to_uuid(record_id)
        instances = WorkflowInstance.query.filter_by(
            trigger_record_id=record_uuid
        ).order_by(WorkflowInstance.started_at.desc()).all()

        result = []
        for instance in instances:
            tasks = instance.tasks.all()
            history = OperationHistory.get_resource_history(
                resource_type='workflow',
                resource_id=str(instance.id),
                limit=100,
            )
            result.append({
                'instance': instance.to_dict(),
                'tasks': [t.to_dict() for t in tasks],
                'history': [h.to_dict() for h in history],
            })

        return success_response(result, '获取审批历史成功')

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 获取记录审批历史失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response(
            '获取记录审批历史失败，请稍后重试',
            500,
            error='internal_server_error',
            request_id=request_id,
        )
