"""
审批服务模块

实现工作流审批节点的完整生命周期：
- 根据节点配置解析审批人并创建 WorkflowTask
- 支持或签（any）、会签（all）、串行（serial）三种审批模式
- 审批同意、驳回、转交
- 超时扫描与自动处理
- 审计日志与邮件/实时通知
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from flask import current_app

from app.extensions import db, socketio
from app.models.base import BaseMember, MemberRole
from app.models.operation_history import OperationHistory
from app.models.user import User
from app.models.workflow import WorkflowNode
from app.models.workflow_instance import (
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowTask,
    WorkflowTaskStatus,
)
from app.services.email_queue_service import EmailPriority, email_queue
from app.services.record_service import RecordService


log = logging.getLogger(__name__)


class ApprovalService:
    """审批服务"""

    DEFAULT_TIMEOUT_HOURS = 72
    SYSTEM_USER_ID = '00000000-0000-0000-0000-000000000000'

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    @staticmethod
    def _to_uuid(value: Any) -> Optional[uuid.UUID]:
        """将字符串或 UUID 对象转换为 UUID 对象"""
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _now() -> datetime:
        """获取当前 UTC 时间（与 SQLite 存储保持一致，使用 naive datetime）"""
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _user_email(user_id: Any) -> Optional[str]:
        """根据用户 ID 查询邮箱"""
        user = User.query.get(ApprovalService._to_uuid(user_id))
        return user.email if user else None

    @staticmethod
    def _user_name(user_id: Any) -> str:
        """根据用户 ID 查询用户名"""
        user = User.query.get(ApprovalService._to_uuid(user_id))
        return user.name if user else '用户'

    @staticmethod
    def _instance_base_id(instance: WorkflowInstance) -> Optional[str]:
        """获取实例所属 base_id"""
        workflow = instance.workflow
        return str(workflow.base_id) if workflow else None

    @staticmethod
    def _get_record(instance: WorkflowInstance) -> Optional[Any]:
        """获取触发记录"""
        record_id = instance.trigger_record_id
        if not record_id:
            return None
        return RecordService.get_record_by_id(str(record_id))

    @staticmethod
    def _extract_user_id(value: Any) -> Optional[uuid.UUID]:
        """从字段值中提取用户 ID"""
        if value is None:
            return None
        if isinstance(value, dict):
            value = value.get('id') or value.get('user_id')
        return ApprovalService._to_uuid(value)

    @staticmethod
    def _resolve_approvers(instance: WorkflowInstance, node: WorkflowNode) -> List[uuid.UUID]:
        """
        根据节点配置解析审批人列表

        支持来源：fixed_users / field_member / field_members / record_creator /
                 record_updater / base_role
        """
        config = node.config or {}
        approvers_config = config.get('approvers', {})
        source = approvers_config.get('source')
        record = ApprovalService._get_record(instance)
        result: List[uuid.UUID] = []

        if source == 'fixed_users':
            for uid in approvers_config.get('user_ids', []):
                user_uuid = ApprovalService._to_uuid(uid)
                if user_uuid:
                    result.append(user_uuid)

        elif source == 'field_member':
            field_id = approvers_config.get('field_id')
            if record and field_id:
                user_uuid = ApprovalService._extract_user_id(record.values.get(field_id))
                if user_uuid:
                    result.append(user_uuid)

        elif source == 'field_members':
            field_id = approvers_config.get('field_id')
            if record and field_id:
                value = record.values.get(field_id)
                if isinstance(value, list):
                    for item in value:
                        user_uuid = ApprovalService._extract_user_id(item)
                        if user_uuid:
                            result.append(user_uuid)

        elif source == 'record_creator':
            if record and record.created_by:
                result.append(record.created_by)

        elif source == 'record_updater':
            if record and record.updated_by:
                result.append(record.updated_by)

        elif source == 'base_role':
            role_value = approvers_config.get('role')
            workflow = instance.workflow
            base_id = workflow.base_id if workflow else None
            if base_id and role_value:
                try:
                    role = MemberRole(role_value)
                except ValueError:
                    log.warning(f'[ApprovalService] 未知角色: {role_value}')
                    role = None
                if role:
                    members = BaseMember.query.filter_by(
                        base_id=base_id,
                        role=role
                    ).all()
                    result.extend([m.user_id for m in members if m.user_id])

        # 去重并保持顺序
        seen = set()
        unique: List[uuid.UUID] = []
        for uid in result:
            if uid not in seen:
                seen.add(uid)
                unique.append(uid)
        return unique

    @staticmethod
    def _log_history(
        user_id: Any,
        instance: WorkflowInstance,
        operation_type: str,
        detail: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录操作审计日志"""
        try:
            base_id = ApprovalService._instance_base_id(instance)
            OperationHistory.log(
                user_id=user_id,
                resource_type='workflow',
                resource_id=str(instance.id),
                operation_type=operation_type,
                base_id=ApprovalService._to_uuid(base_id),
                detail=detail
            )
            db.session.commit()
        except Exception as e:
            log.warning(f'[ApprovalService] 记录审计日志失败: {e}')
            db.session.rollback()

    @staticmethod
    def _emit_if_enabled(event_name: str, base_id: Optional[str], data: Dict[str, Any]) -> None:
        """如果 SocketIO 可用则推送实时通知"""
        if not base_id:
            return
        try:
            if not current_app.config.get('REALTIME_ENABLED', False):
                return
            socketio.emit(event_name, data, room=f'base:{base_id}')
        except Exception as e:
            log.warning(f'[ApprovalService] socketio 推送失败: {e}')

    @staticmethod
    def _send_notification(
        to_user_id: Any,
        title: str,
        content: str,
        priority: EmailPriority = EmailPriority.NORMAL
    ) -> None:
        """通过邮件队列发送通知邮件"""
        email = ApprovalService._user_email(to_user_id)
        if not email:
            return
        try:
            email_queue.enqueue_quick(
                to_email=email,
                to_name=ApprovalService._user_name(to_user_id),
                template_key='notification',
                template_data={
                    'notification_title': title,
                    'notification_content': content,
                    'user_name': ApprovalService._user_name(to_user_id)
                },
                priority=priority
            )
        except Exception as e:
            log.warning(f'[ApprovalService] 发送邮件通知失败: {e}')

    @staticmethod
    def _notify_task_created(instance: WorkflowInstance, task: WorkflowTask, node: WorkflowNode) -> None:
        """通知审批人新任务"""
        base_id = ApprovalService._instance_base_id(instance)
        workflow_name = instance.workflow.name if instance.workflow else '工作流'
        title = '您有一条待审批任务'
        content = (
            f'工作流「{workflow_name}」中的审批节点「{node.name}」需要您处理，'
            f'任务 ID：{task.id}。'
        )
        ApprovalService._send_notification(task.assignee_id, title, content, EmailPriority.HIGH)
        ApprovalService._emit_if_enabled(
            'workflow:task_created',
            base_id,
            {
                'task_id': str(task.id),
                'instance_id': str(instance.id),
                'node_id': str(task.node_id) if task.node_id else None,
                'assignee_id': str(task.assignee_id) if task.assignee_id else None,
                'node_name': node.name,
                'workflow_name': workflow_name
            }
        )

    @staticmethod
    def _notify_action(
        instance: WorkflowInstance,
        task: WorkflowTask,
        node: WorkflowNode,
        action: str,
        comment: Optional[str] = None,
        actor_user_id: Optional[Any] = None
    ) -> None:
        """通知发起人和相关审批人任务状态变化"""
        base_id = ApprovalService._instance_base_id(instance)
        workflow_name = instance.workflow.name if instance.workflow else '工作流'
        actor_name = ApprovalService._user_name(actor_user_id if actor_user_id is not None else task.assignee_id)
        action_text = {'approved': '已通过', 'rejected': '已驳回', 'transferred': '已转交'}.get(action, action)
        title = f'审批任务{action_text}'
        content = (
            f'工作流「{workflow_name}」节点「{node.name}」的审批任务{action_text}。'
            f'处理人：{actor_name}。'
        )
        if comment:
            content += f'意见：{comment}。'

        # 通知发起人
        initiator_id = ApprovalService._get_initiator_id(instance)
        if initiator_id and initiator_id != task.assignee_id:
            ApprovalService._send_notification(initiator_id, title, content)

        # 通知当前审批人（转交场景下为新审批人）
        if action == 'transferred' and task.assignee_id:
            ApprovalService._send_notification(
                task.assignee_id,
                '审批任务已转交给您',
                f'工作流「{workflow_name}」节点「{node.name}」的审批任务已转交给您处理。'
            )

        ApprovalService._emit_if_enabled(
            f'workflow:task_{action}',
            base_id,
            {
                'task_id': str(task.id),
                'instance_id': str(instance.id),
                'node_id': str(task.node_id) if task.node_id else None,
                'assignee_id': str(task.assignee_id) if task.assignee_id else None,
                'action': action,
                'comment': comment,
                'node_name': node.name,
                'workflow_name': workflow_name
            }
        )

    @staticmethod
    def _get_initiator_id(instance: WorkflowInstance) -> Optional[uuid.UUID]:
        """获取工作流发起人 ID"""
        context = instance.context or {}
        trigger_event = context.get('trigger_event', {})
        actor_id = trigger_event.get('actor_id')
        if actor_id:
            return ApprovalService._to_uuid(actor_id)
        record = ApprovalService._get_record(instance)
        if record and record.created_by:
            return record.created_by
        return None

    @staticmethod
    def _continue_instance(instance: WorkflowInstance, node: WorkflowNode) -> None:
        """审批通过后继续执行后续节点"""
        from app.services.workflow_execution_engine import workflow_execution_engine

        next_nodes = node.next_nodes or []
        if not next_nodes:
            # 无后续节点，标记实例完成
            if instance.status == WorkflowInstanceStatus.RUNNING:
                instance.status = WorkflowInstanceStatus.COMPLETED
                instance.completed_at = ApprovalService._now()
                db.session.commit()
            return

        for next_node_id in next_nodes:
            next_node = WorkflowNode.query.get(ApprovalService._to_uuid(next_node_id))
            if not next_node:
                log.warning(f'[ApprovalService] 后续节点不存在: {next_node_id}')
                continue
            try:
                workflow_execution_engine._execute_chain(instance, next_node)
            except Exception as e:
                log.exception(f'[ApprovalService] 继续执行后续节点失败: {next_node_id} - {e}')

    @staticmethod
    def _create_single_task(
        instance: WorkflowInstance,
        node: WorkflowNode,
        assignee_id: uuid.UUID,
        transferred_from_id: Optional[uuid.UUID] = None
    ) -> WorkflowTask:
        """创建单个审批任务"""
        task = WorkflowTask(
            instance_id=instance.id,
            node_id=node.id,
            assignee_id=assignee_id,
            status=WorkflowTaskStatus.PENDING,
            transferred_from_id=transferred_from_id
        )
        db.session.add(task)
        db.session.flush()
        return task

    @staticmethod
    def _mark_instance_rejected(instance: WorkflowInstance, reason: Optional[str] = None) -> None:
        """将实例标记为已驳回"""
        if instance.status == WorkflowInstanceStatus.RUNNING:
            instance.status = WorkflowInstanceStatus.REJECTED
            instance.completed_at = ApprovalService._now()
            db.session.commit()
            log.info(f'[ApprovalService] 实例已驳回: {instance.id}, reason={reason}')

    @staticmethod
    def _trigger_on_rejected(instance: WorkflowInstance, node: WorkflowNode, task: WorkflowTask, comment: Optional[str]) -> None:
        """触发节点配置的 on_rejected 动作"""
        config = node.config or {}
        on_rejected = config.get('on_rejected', {})
        if not on_rejected:
            return

        workflow_name = instance.workflow.name if instance.workflow else '工作流'
        actor_name = ApprovalService._user_name(task.assignee_id)
        title = '审批已被驳回'
        content = (
            f'您发起的工作流「{workflow_name}」节点「{node.name}」已被 {actor_name} 驳回。'
        )
        if comment:
            content += f'驳回意见：{comment}。'

        if on_rejected.get('notify_initiator'):
            initiator_id = ApprovalService._get_initiator_id(instance)
            if initiator_id:
                ApprovalService._send_notification(initiator_id, title, content, EmailPriority.HIGH)

        # 其他动作仅记录日志，不实现具体逻辑以保持简洁
        extra_keys = set(on_rejected.keys()) - {'notify_initiator'}
        if extra_keys:
            log.info(f'[ApprovalService] on_rejected 其他动作未实现: {extra_keys}')

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------
    @staticmethod
    def create_tasks(instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """
        为审批节点创建审批任务

        Args:
            instance: WorkflowInstance 实例
            node: WorkflowNode 节点

        Returns:
            操作结果字典
        """
        config = node.config or {}
        approvers_config = config.get('approvers', {})
        mode = config.get('mode', 'any')

        approvers = ApprovalService._resolve_approvers(instance, node)
        if not approvers:
            log.warning(f'[ApprovalService] 节点 {node.id} 未解析到审批人')
            return {'success': False, 'error': '未解析到审批人', 'tasks': []}

        # 若执行引擎尚未写入执行日志（如直接调用 API 测试），补充一条
        # 以便超时扫描能够定位任务开始时间
        from app.models.workflow_instance import WorkflowExecutionLog
        existing_log = WorkflowExecutionLog.query.filter_by(
            instance_id=instance.id,
            node_id=node.id
        ).first()
        if not existing_log:
            db.session.add(WorkflowExecutionLog(
                instance_id=instance.id,
                node_id=node.id,
                node_type=node.node_type.value if hasattr(node.node_type, 'value') else str(node.node_type),
                status='success',
                input_context=instance.context or {},
                output_result={},
                started_at=ApprovalService._now()
            ))

        created_tasks: List[WorkflowTask] = []

        try:
            if mode == 'serial':
                # 串行：仅创建第一个任务，其余审批人保存到上下文
                context = instance.context or {}
                approval_ctx = context.setdefault('approval_serial', {})
                approval_ctx[str(node.id)] = {
                    'approvers': [str(uid) for uid in approvers],
                    'current_index': 0
                }
                instance.context = context
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(instance, 'context')

                first_task = ApprovalService._create_single_task(instance, node, approvers[0])
                created_tasks.append(first_task)
            else:
                # 或签 / 会签：为每个审批人创建任务
                for assignee_id in approvers:
                    task = ApprovalService._create_single_task(instance, node, assignee_id)
                    created_tasks.append(task)

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            log.exception(f'[ApprovalService] 创建审批任务失败: {e}')
            return {'success': False, 'error': f'创建审批任务失败: {e}', 'tasks': []}

        # 发送通知
        for task in created_tasks:
            try:
                ApprovalService._notify_task_created(instance, task, node)
            except Exception as e:
                log.warning(f'[ApprovalService] 任务创建通知失败: {e}')

        log.info(
            f'[ApprovalService] 节点 {node.id} 创建 {len(created_tasks)} 个审批任务，'
            f'模式={mode}'
        )
        return {
            'success': True,
            'tasks': [t.to_dict() for t in created_tasks],
            'mode': mode,
            'next_nodes': []  # 通知执行引擎暂停，等待审批动作
        }

    @staticmethod
    def approve(task_id: str, user_id: str, comment: str = None) -> Dict[str, Any]:
        """
        同意审批任务

        Args:
            task_id: 任务 ID
            user_id: 当前用户 ID
            comment: 审批意见

        Returns:
            操作结果字典
        """
        task_uuid = ApprovalService._to_uuid(task_id)
        user_uuid = ApprovalService._to_uuid(user_id)

        task = WorkflowTask.query.get(task_uuid)
        if not task:
            return {'success': False, 'error': '任务不存在'}
        if task.assignee_id != user_uuid:
            return {'success': False, 'error': '无权处理该任务'}

        # 使用数据库状态做并发控制：只有 pending 状态才能更新
        now = ApprovalService._now()
        updated = db.session.query(WorkflowTask).filter_by(
            id=task_uuid,
            status=WorkflowTaskStatus.PENDING
        ).update({
            'status': WorkflowTaskStatus.APPROVED,
            'comment': comment,
            'acted_at': now
        })
        db.session.commit()

        if updated == 0:
            return {'success': False, 'error': '任务已被处理或不存在'}

        db.session.refresh(task)
        instance = task.instance
        node = task.node
        config = node.config or {} if node else {}
        mode = config.get('mode', 'any')

        # 审计与通知
        ApprovalService._log_history(
            user_uuid,
            instance,
            'approve',
            {'task_id': str(task.id), 'node_id': str(node.id) if node else None, 'comment': comment, 'mode': mode}
        )
        ApprovalService._notify_action(instance, task, node, 'approved', comment)

        # 根据审批模式决定后续动作
        try:
            if mode == 'any':
                ApprovalService._continue_instance(instance, node)
            elif mode == 'all':
                pending_count = WorkflowTask.query.filter_by(
                    instance_id=instance.id,
                    node_id=node.id,
                    status=WorkflowTaskStatus.PENDING
                ).count()
                if pending_count == 0:
                    ApprovalService._continue_instance(instance, node)
            elif mode == 'serial':
                context = instance.context or {}
                approval_serial = context.setdefault('approval_serial', {})
                serial_ctx = approval_serial.setdefault(str(node.id), {})
                approvers = serial_ctx.get('approvers', [])
                current_index = serial_ctx.get('current_index', 0)
                next_index = current_index + 1

                if next_index < len(approvers):
                    # 创建下一审批任务
                    next_assignee = ApprovalService._to_uuid(approvers[next_index])
                    if next_assignee:
                        next_task = ApprovalService._create_single_task(
                            instance, node, next_assignee
                        )
                        serial_ctx['current_index'] = next_index
                        instance.context = context
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(instance, 'context')
                        db.session.commit()
                        ApprovalService._notify_task_created(instance, next_task, node)
                else:
                    ApprovalService._continue_instance(instance, node)
            else:
                log.warning(f'[ApprovalService] 未知审批模式: {mode}')
        except Exception as e:
            db.session.rollback()
            log.exception(f'[ApprovalService] approve 后续处理失败: {e}')
            return {'success': True, 'warning': '审批已记录，但后续处理失败', 'task': task.to_dict()}

        return {'success': True, 'task': task.to_dict()}

    @staticmethod
    def reject(task_id: str, user_id: str, comment: str = None) -> Dict[str, Any]:
        """
        驳回审批任务

        Args:
            task_id: 任务 ID
            user_id: 当前用户 ID
            comment: 驳回意见

        Returns:
            操作结果字典
        """
        task_uuid = ApprovalService._to_uuid(task_id)
        user_uuid = ApprovalService._to_uuid(user_id)

        task = WorkflowTask.query.get(task_uuid)
        if not task:
            return {'success': False, 'error': '任务不存在'}
        if task.assignee_id != user_uuid:
            return {'success': False, 'error': '无权处理该任务'}

        now = ApprovalService._now()
        updated = db.session.query(WorkflowTask).filter_by(
            id=task_uuid,
            status=WorkflowTaskStatus.PENDING
        ).update({
            'status': WorkflowTaskStatus.REJECTED,
            'comment': comment,
            'acted_at': now
        })
        db.session.commit()

        if updated == 0:
            return {'success': False, 'error': '任务已被处理或不存在'}

        db.session.refresh(task)
        instance = task.instance
        node = task.node

        ApprovalService._mark_instance_rejected(instance, comment)

        ApprovalService._log_history(
            user_uuid,
            instance,
            'reject',
            {'task_id': str(task.id), 'node_id': str(node.id) if node else None, 'comment': comment}
        )
        ApprovalService._notify_action(instance, task, node, 'rejected', comment)
        ApprovalService._trigger_on_rejected(instance, node, task, comment)

        return {'success': True, 'task': task.to_dict()}

    @staticmethod
    def transfer(
        task_id: str,
        user_id: str,
        new_assignee_id: str,
        comment: str = None
    ) -> Dict[str, Any]:
        """
        转交审批任务

        Args:
            task_id: 原任务 ID
            user_id: 当前用户 ID
            new_assignee_id: 新审批人 ID
            comment: 转交说明

        Returns:
            操作结果字典
        """
        task_uuid = ApprovalService._to_uuid(task_id)
        user_uuid = ApprovalService._to_uuid(user_id)
        new_assignee_uuid = ApprovalService._to_uuid(new_assignee_id)

        if not new_assignee_uuid:
            return {'success': False, 'error': '新审批人 ID 无效'}

        task = WorkflowTask.query.get(task_uuid)
        if not task:
            return {'success': False, 'error': '任务不存在'}
        if task.assignee_id != user_uuid:
            return {'success': False, 'error': '无权处理该任务'}

        now = ApprovalService._now()
        updated = db.session.query(WorkflowTask).filter_by(
            id=task_uuid,
            status=WorkflowTaskStatus.PENDING
        ).update({
            'status': WorkflowTaskStatus.TRANSFERRED,
            'comment': comment,
            'acted_at': now
        })
        db.session.commit()

        if updated == 0:
            return {'success': False, 'error': '任务已被处理或不存在'}

        db.session.refresh(task)
        instance = task.instance
        node = task.node

        # 创建新任务
        try:
            new_task = ApprovalService._create_single_task(
                instance, node, new_assignee_uuid, transferred_from_id=task.id
            )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            log.exception(f'[ApprovalService] 创建转交任务失败: {e}')
            return {'success': False, 'error': f'创建转交任务失败: {e}'}

        ApprovalService._log_history(
            user_uuid,
            instance,
            'transfer',
            {
                'task_id': str(task.id),
                'new_task_id': str(new_task.id),
                'new_assignee_id': str(new_assignee_uuid),
                'comment': comment
            }
        )
        ApprovalService._notify_action(
            instance, new_task, node, 'transferred', comment, actor_user_id=user_uuid
        )

        return {
            'success': True,
            'task': task.to_dict(),
            'new_task': new_task.to_dict()
        }

    @staticmethod
    def check_timeout() -> None:
        """扫描超时审批任务并按配置执行动作"""
        from app.models.workflow_instance import WorkflowExecutionLog

        now = ApprovalService._now()
        pending_tasks = WorkflowTask.query.filter_by(
            status=WorkflowTaskStatus.PENDING
        ).all()

        for task in pending_tasks:
            try:
                node = task.node
                if not node:
                    continue
                config = node.config or {}
                timeout_hours = config.get('timeout_hours', ApprovalService.DEFAULT_TIMEOUT_HOURS)
                if timeout_hours <= 0:
                    continue

                # 通过节点执行日志获取任务开始时间
                log_entry = WorkflowExecutionLog.query.filter_by(
                    instance_id=task.instance_id,
                    node_id=task.node_id
                ).order_by(WorkflowExecutionLog.started_at.asc()).first()

                if not log_entry or not log_entry.started_at:
                    continue

                deadline = log_entry.started_at + timedelta(hours=timeout_hours)
                if now < deadline:
                    continue

                action = config.get('timeout_action', 'notify')
                ApprovalService._handle_timeout(task, action, now)
            except Exception as e:
                db.session.rollback()
                log.exception(f'[ApprovalService] 处理超时任务失败 {task.id}: {e}')

    @staticmethod
    def _handle_timeout(task: WorkflowTask, action: str, now: datetime) -> None:
        """处理单个超时任务"""
        instance = task.instance
        node = task.node
        base_id = ApprovalService._instance_base_id(instance)
        workflow_name = instance.workflow.name if instance.workflow else '工作流'

        if action == 'auto_approve':
            db.session.query(WorkflowTask).filter_by(
                id=task.id,
                status=WorkflowTaskStatus.PENDING
            ).update({
                'status': WorkflowTaskStatus.APPROVED,
                'comment': '系统自动审批：超时通过',
                'acted_at': now
            })
            db.session.commit()
            db.session.refresh(task)
            ApprovalService._log_history(
                ApprovalService.SYSTEM_USER_ID,
                instance,
                'auto_approve',
                {'task_id': str(task.id), 'reason': 'timeout'}
            )
            ApprovalService._notify_action(instance, task, node, 'approved', '系统自动审批：超时通过')
            # 触发与人工 approve 相同的后续逻辑
            ApprovalService._process_post_approval(instance, node)
        elif action == 'auto_reject':
            db.session.query(WorkflowTask).filter_by(
                id=task.id,
                status=WorkflowTaskStatus.PENDING
            ).update({
                'status': WorkflowTaskStatus.REJECTED,
                'comment': '系统自动驳回：超时',
                'acted_at': now
            })
            db.session.commit()
            db.session.refresh(task)
            ApprovalService._mark_instance_rejected(instance, 'timeout')
            ApprovalService._log_history(
                ApprovalService.SYSTEM_USER_ID,
                instance,
                'auto_reject',
                {'task_id': str(task.id), 'reason': 'timeout'}
            )
            ApprovalService._notify_action(instance, task, node, 'rejected', '系统自动驳回：超时')
        else:
            # notify / 默认：仅发送提醒
            title = '审批任务即将超时'
            content = (
                f'工作流「{workflow_name}」节点「{node.name}」的审批任务已超时，'
                f'请尽快处理。'
            )
            ApprovalService._send_notification(
                task.assignee_id, title, content, EmailPriority.HIGH
            )
            ApprovalService._emit_if_enabled(
                'workflow:task_timeout',
                base_id,
                {
                    'task_id': str(task.id),
                    'instance_id': str(instance.id),
                    'node_id': str(node.id) if node else None
                }
            )

    @staticmethod
    def _process_post_approval(instance: WorkflowInstance, node: WorkflowNode) -> None:
        """审批通过后的公共处理逻辑"""
        config = node.config or {}
        mode = config.get('mode', 'any')

        if mode == 'any':
            ApprovalService._continue_instance(instance, node)
        elif mode == 'all':
            pending_count = WorkflowTask.query.filter_by(
                instance_id=instance.id,
                node_id=node.id,
                status=WorkflowTaskStatus.PENDING
            ).count()
            if pending_count == 0:
                ApprovalService._continue_instance(instance, node)
        elif mode == 'serial':
            context = instance.context or {}
            approval_serial = context.setdefault('approval_serial', {})
            serial_ctx = approval_serial.setdefault(str(node.id), {})
            approvers = serial_ctx.get('approvers', [])
            current_index = serial_ctx.get('current_index', 0)
            next_index = current_index + 1

            if next_index < len(approvers):
                next_assignee = ApprovalService._to_uuid(approvers[next_index])
                if next_assignee:
                    next_task = ApprovalService._create_single_task(
                        instance, node, next_assignee
                    )
                    serial_ctx['current_index'] = next_index
                    instance.context = context
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(instance, 'context')
                    db.session.commit()
                    ApprovalService._notify_task_created(instance, next_task, node)
            else:
                ApprovalService._continue_instance(instance, node)
