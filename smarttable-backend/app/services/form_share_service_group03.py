"""
表单分享服务模块
处理表单分享的创建、管理和数据提交
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

from flask import current_app

from app.extensions import db, cache
from app.models.form_share import FormShare
from app.models.form_submission import FormSubmission
from app.models.table import Table
from app.models.field import Field, FieldType
from app.models.base import Base, MemberRole
from app.services.record_service import RecordService
from app.services.table_service import TableService
from app.services.field_service import FieldService
from app.services.link_service import LinkService
from app.services.permission_service import PermissionService
from app.utils.captcha import CaptchaService
from app.i18n import translate


class FormShareError(Exception):
    """表单分享错误"""
    pass

class FormShareServiceGroup03Mixin:
    """Mixin auto-split"""
    
    """表单分享服务类"""
    
    SUBMIT_RATE_LIMIT = 100  # 每个分享链接每 15 分钟最多的提交次数（用于防刷，而非限制正常多用户填写）
    
    RATE_LIMIT_WINDOW = 900  # 15 分钟（秒）
    
    
    @staticmethod
    def update_form_share(
        share_id: str,
        user_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新表单分享配置
    
        Args:
            share_id: 表单分享 ID
            user_id: 操作用户 ID
            data: 更新数据
    
        Returns:
            包含操作结果的字典
        """
        try:
            form_share = FormShareService.get_form_share_by_id(share_id)
            if not form_share:
                return {'success': False, 'error': 'form_share_does_not_exist', 'status': 404}
    
            # 验证权限（只有创建者可以更新）
            if str(form_share.created_by) != str(user_id):
                # 或者检查用户是否有表格的管理权限
                table = TableService.get_table_by_id(form_share.table_id)
                if table and not PermissionService.check_permission(
                    str(table.base_id), user_id, MemberRole.ADMIN
                ):
                    return {'success': False, 'error': 'no_permission_update_form_share', 'status': 403}
    
            # 更新字段
            if 'is_active' in data:
                form_share.is_active = bool(data['is_active'])
    
            if 'allow_anonymous' in data:
                form_share.allow_anonymous = bool(data['allow_anonymous'])
    
            if 'require_captcha' in data:
                form_share.require_captcha = bool(data['require_captcha'])
    
            if 'expires_at' in data:
                expires_at = data['expires_at']
                if expires_at is not None:
                    try:
                        expires_at = int(expires_at)
                        if expires_at < int(datetime.now(timezone.utc).timestamp()):
                            return {'success': False, 'error': 'expiry_time_past'}
                        form_share.expires_at = expires_at
                    except (ValueError, TypeError):
                        return {'success': False, 'error': 'expiry_time_valid_unix_timestamp'}
                else:
                    form_share.expires_at = None
    
            if 'max_submissions' in data:
                max_submissions = data['max_submissions']
                if max_submissions is not None:
                    form_share.max_submissions = int(max_submissions)
                else:
                    form_share.max_submissions = None
    
            if 'allowed_fields' in data:
                allowed_fields = data['allowed_fields']
                if allowed_fields:
                    # 验证字段是否存在
                    table_fields = FieldService.get_all_fields(form_share.table_id)
                    table_field_ids = {str(f.id) for f in table_fields}
                    invalid_fields = [f for f in allowed_fields if f not in table_field_ids]
                    if invalid_fields:
                        return {'success': False, 'error': translate('form_share_invalid_fields', invalid_fields)}
                    form_share.set_allowed_fields_list(allowed_fields)
                else:
                    form_share.allowed_fields = None
    
            if 'field_settings' in data:
                field_settings = data['field_settings']
                if field_settings:
                    # 验证配置中的字段是否存在
                    table_fields = FieldService.get_all_fields(form_share.table_id)
                    table_field_ids = {str(f.id) for f in table_fields}
                    invalid_fields = [
                        fid for fid in (field_settings or {})
                        if str(fid) not in table_field_ids
                    ]
                    if invalid_fields:
                        return {'success': False, 'error': translate('form_share_invalid_fields', invalid_fields)}
                    form_share.set_field_settings(field_settings)
                else:
                    form_share.field_settings = None
    
            if 'title' in data:
                form_share.title = data['title']
    
            if 'description' in data:
                form_share.description = data['description']
    
            if 'submit_button_text' in data:
                form_share.submit_button_text = data['submit_button_text']
    
            if 'success_message' in data:
                form_share.success_message = data['success_message']
    
            if 'theme' in data:
                form_share.theme = data['theme']
    
            if 'columns' in data:
                form_share.columns = FormShareService._normalize_columns(data['columns'])
    
            form_share.updated_at = datetime.now(timezone.utc)
            db.session.commit()
    
            current_app.logger.info(
                f'[FormShareService] 更新表单分享: id={share_id}, by={user_id}'
            )
    
            return {'success': True, 'form_share': form_share}
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[FormShareService] 更新表单分享失败: {str(e)}')
            return {'success': False, 'error': translate('form_share_update_failed', str(e)), 'status': 500}
    
    @staticmethod
    def delete_form_share(share_id: str, user_id: str) -> Dict[str, Any]:
        """
        删除表单分享
    
        Args:
            share_id: 表单分享 ID
            user_id: 操作用户 ID
    
        Returns:
            包含操作结果的字典
        """
        try:
            form_share = FormShareService.get_form_share_by_id(share_id)
            if not form_share:
                return {'success': False, 'error': 'form_share_does_not_exist', 'status': 404}
    
            # 验证权限（只有创建者或管理员可以删除）
            if str(form_share.created_by) != str(user_id):
                table = TableService.get_table_by_id(form_share.table_id)
                if table and not PermissionService.check_permission(
                    str(table.base_id), user_id, MemberRole.ADMIN
                ):
                    return {'success': False, 'error': 'no_permission_delete_form_share', 'status': 403}
    
            db.session.delete(form_share)
            db.session.commit()
    
            current_app.logger.info(
                f'[FormShareService] 删除表单分享: id={share_id}, by={user_id}'
            )
    
            return {'success': True}
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[FormShareService] 删除表单分享失败: {str(e)}')
            return {'success': False, 'error': translate('form_share_delete_failed', str(e)), 'status': 500}
    
    @staticmethod
    def get_submissions(
        share_id: str,
        user_id: str,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        获取表单提交记录
    
        Args:
            share_id: 表单分享 ID
            user_id: 操作用户 ID
            page: 页码
            per_page: 每页数量
    
        Returns:
            包含提交记录的字典
        """
        try:
            form_share = FormShareService.get_form_share_by_id(share_id)
            if not form_share:
                return {'success': False, 'error': 'form_share_does_not_exist', 'status': 404}
    
            # 验证权限
            if str(form_share.created_by) != str(user_id):
                table = TableService.get_table_by_id(form_share.table_id)
                if table and not PermissionService.check_permission(
                    str(table.base_id), user_id, MemberRole.VIEWER
                ):
                    return {'success': False, 'error': 'no_permission_view_submission_records_form', 'status': 403}
    
            # 查询提交记录
            query = FormSubmission.query.filter_by(form_share_id=share_id)
            total = query.count()
    
            submissions = query.order_by(
                FormSubmission.submitted_at.desc()
            ).offset((page - 1) * per_page).limit(per_page).all()
    
            return {
                'success': True,
                'data': {
                    'items': [s.to_dict() for s in submissions],
                    'total': total,
                    'page': page,
                    'per_page': per_page
                }
            }
    
        except Exception as e:
            current_app.logger.error(f'[FormShareService] 获取提交记录失败: {str(e)}')
            return {'success': False, 'error': 'failed_fetch_submission_records', 'status': 500}
    
    @staticmethod
    def _trigger_approval_flow(
        table_id: str,
        record_id: str,
        form_data: Dict[str, Any],
        form_share: FormShare
    ) -> Optional[str]:
        """
        触发审批流（如果该数据表有已发布的审批流）
    
        Args:
            table_id: 数据表 ID
            record_id: 已创建的记录 ID
            form_data: 表单数据
            form_share: 表单分享对象
    
        Returns:
            审批流实例 ID，如果没有触发则返回 None
    
        Note:
            此方法在表单提交成功后调用，触发失败不影响表单提交结果
        """
        # 延迟导入避免循环依赖
        try:
            from app.models.approval_flow import ApprovalFlow, ApprovalFlowStatus
        except ImportError:
            ApprovalFlow = None
            ApprovalFlowStatus = None
        try:
            from app.services.approval_flow_execution_engine import ApprovalFlowExecutionEngine
        except ImportError:
            ApprovalFlowExecutionEngine = None
    
        try:
            # 查询该数据表关联的、状态为 ACTIVE 的审批流
            active_flow = ApprovalFlow.query.filter_by(
                table_id=table_id,
                status=ApprovalFlowStatus.ACTIVE,
                is_deleted=False
            ).first()
    
            if not active_flow:
                # 没有关联的审批流，直接返回
                current_app.logger.debug(
                    f'[FormShareService] 数据表 {table_id} 没有已发布的审批流'
                )
                return None
    
            # 使用表单分享的创建者作为发起人（如果是匿名提交）
            # 如果需要真实用户，前端应在 submitter_info 中传递
            initiator_id = form_share.created_by
    
            # 启动审批流实例
            instance = ApprovalFlowExecutionEngine.start_instance(
                flow_id=str(active_flow.id),
                record_id=record_id,
                initiator_id=str(initiator_id),
                form_data=form_data
            )
    
            return str(instance.id)
    
        except Exception as e:
            # 记录详细错误信息
            current_app.logger.error(
                f'[FormShareService] 触发审批流异常: {str(e)}, '
                f'table={table_id}, record={record_id}'
            )
            # 不重新抛出异常，让表单提交仍然成功
            return None
    
