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

class FormShareServiceGroup02Mixin:
    """Mixin auto-split"""
    
    """表单分享服务类"""
    
    SUBMIT_RATE_LIMIT = 100  # 每个分享链接每 15 分钟最多的提交次数（用于防刷，而非限制正常多用户填写）
    
    RATE_LIMIT_WINDOW = 900  # 15 分钟（秒）
    
    
    @staticmethod
    def submit_form_data(
        token: str,
        data: Dict[str, Any],
        client_info: Dict[str, str],
        submitter_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        提交表单数据
    
        Args:
            token: 分享令牌
            data: 提交的数据
                - values: 字段值字典
                - submitter_info: 提交者信息（邮箱、姓名等）
                - captcha: 验证码（如果需要）
            client_info: 客户端信息
                - ip: IP 地址
                - user_agent: User-Agent
            submitter_user_id: 提交者用户 ID（登录用户填写时为该用户 ID，匿名提交为 None）
    
        Returns:
            包含操作结果的字典
        """
        # 验证表单分享
        valid, form_share, error = FormShareService.validate_form_share(token)
    
        if not valid:
            status = 403 if error in ('form_share_been_invalidated', 'form_share_expired', 'submission_limit_reached') else 404
            return {'success': False, 'error': error, 'status': status}
    
        # 检查速率限制（按分享令牌维度）
        if not FormShareService._check_rate_limit(token):
            return {'success': False, 'error': 'submissions_too_frequent_try_again_later', 'status': 429}
    
        # 获取提交者 IP（用于记录，不参与限流判断）
        client_ip = client_info.get('ip', 'unknown')
    
        # 验证验证码（如果需要）
        if form_share.require_captcha:
            captcha = data.get('captcha')
            if not captcha:
                return {'success': False, 'error': 'enter_captcha', 'status': 400}
    
            # 验证验证码
            is_valid, error_msg = CaptchaService.verify_captcha(token, captcha)
            if not is_valid:
                return {'success': False, 'error': error_msg, 'status': 400}
    
        try:
            # 获取提交的值
            values = data.get('values', {})
    
            # 字段级配置：只读字段忽略填写者输入，强制使用默认值
            # 默认值优先级：分享表单配置 > 字段自身默认配置
            field_settings_map = form_share.get_field_settings()
            allowed_field_ids = form_share.get_allowed_fields_list()
            if field_settings_map:
                all_fields = FieldService.get_all_fields(form_share.table_id)
                for field_id in list(values.keys()):
                    setting = field_settings_map.get(str(field_id), {}) or {}
                    if setting.get('readOnly'):
                        # 只读字段：丢弃填写者提交的值
                        del values[field_id]
                for field in all_fields:
                    fid = str(field.id)
                    if allowed_field_ids and fid not in allowed_field_ids:
                        continue
                    setting = field_settings_map.get(fid, {}) or {}
                    if setting.get('readOnly'):
                        share_default = setting.get('defaultValue')
                        if share_default is not None:
                            values[fid] = share_default
                        else:
                            fcfg = (field.config or {}).get('defaultValue')
                            if fcfg is None:
                                fcfg = (field.config or {}).get('default')
                            if fcfg is not None:
                                values[fid] = fcfg
    
            # 验证数据
            validation_result = FormShareService._validate_form_data(
                form_share, values, field_settings_map
            )
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': 'data_validation_failed',
                    'details': validation_result['errors'],
                    'status': 400
                }
    
            # 过滤只允许提交的字段
            if allowed_field_ids:
                values = {k: v for k, v in values.items() if k in allowed_field_ids}
    
            # 成员字段「添加记录用户」默认值：登录用户填写时自动填充为当前用户
            if submitter_user_id:
                all_fields = FieldService.get_all_fields(form_share.table_id)
                for field in all_fields:
                    if getattr(field, 'type', None) != FieldType.COLLABORATOR.value:
                        continue
                    fcfg = field.config or {}
                    fopts = field.options or {}
                    is_current_user = (
                        fcfg.get('defaultValue') == 'current_user'
                        or fcfg.get('default') == 'current_user'
                        or fopts.get('memberDefaultType') == 'current_user'
                        or fopts.get('defaultType') == 'current_user'
                    )
                    if not is_current_user:
                        continue
                    fid = str(field.id)
                    cur = values.get(fid)
                    # 未填写、空值或仍是标记字符串时，填充当前用户 ID
                    if cur is None or cur == '' or cur == 'current_user' or (isinstance(cur, list) and len(cur) == 0):
                        values[fid] = [submitter_user_id]
    
            # 创建记录
            record = RecordService.create_record(
                table_id=form_share.table_id,
                values=values,
                created_by=submitter_user_id  # 登录提交记录填表人，匿名提交为 None
            )
    
            # 创建提交记录
            submission = FormSubmission(
                form_share_id=form_share.id,
                record_id=str(record.id),
                submitter_ip=client_ip,
                submitter_user_agent=client_info.get('user_agent'),
            )
    
            # 设置提交者信息
            submitter_info = data.get('submitter_info', {})
            if submitter_info:
                submission.set_submitter_info_dict(submitter_info)
    
            db.session.add(submission)
    
            # 增加提交次数
            form_share.increment_submissions()
    
            # 先提交表单数据，确保记录、提交记录、提交次数都持久化
            db.session.commit()
    
            # ===== 触发审批流（如果该数据表有已发布的审批流） =====
            # 注意：审批流触发在表单数据提交后进行，确保即使审批流启动失败，
            # 表单提交结果也已保存。用户可以稍后手动触发审批或查看已提交的记录。
            approval_flow_instance_id = None
            try:
                approval_flow_instance_id = FormShareService._trigger_approval_flow(
                    table_id=form_share.table_id,
                    record_id=str(record.id),
                    form_data=values,
                    form_share=form_share
                )
                if approval_flow_instance_id:
                    current_app.logger.info(
                        f'[FormShareService] 审批流实例已创建: instance={approval_flow_instance_id}, '
                        f'record={record.id}, table={form_share.table_id}'
                    )
            except Exception as e:
                # 审批流触发失败不影响表单提交结果（记录已创建并提交）
                # 只记录错误日志，让用户可以查看记录并手动触发审批
                current_app.logger.error(
                    f'[FormShareService] 触发审批流失败: {str(e)}, '
                    f'record={record.id}, table={form_share.table_id}'
                )
    
            # 记录日志
            current_app.logger.info(
                f'[FormShareService] 表单提交成功: form_share={form_share.id}, '
                f'record={record.id}, ip={client_ip}'
            )
    
            # 创建关联字段（LINK）的关联数据（含双向关联）
            # 与表格视图新增记录流程一致：主记录与提交记录提交成功后，再为每个 LINK 字段建立关联。
            # 匿名分享表单无法走需鉴权的 /records/<id>/links/<field_id> 接口，
            # 因此在此直接通过 LinkService 建立关联（best-effort，失败不影响主提交结果）。
            try:
                link_fields = [
                    f for f in FieldService.get_all_fields(form_share.table_id)
                    if f.type in (FieldType.LINK_TO_RECORD.value, 'link')
                ]
                for link_field in link_fields:
                    raw = values.get(str(link_field.id))
                    if raw is None or raw == '':
                        continue
                    ids = raw if isinstance(raw, list) else [str(raw)]
                    ids = [str(i) for i in ids if i]
                    if not ids:
                        continue
    
                    field_config = link_field.config or {}
                    target_table_id = field_config.get('linkedTableId')
                    if not target_table_id:
                        continue
    
                    # 获取或自动创建关联关系
                    link_relation = LinkService.get_link_relation_by_field(
                        str(link_field.id), str(target_table_id)
                    )
                    if not link_relation:
                        link_relation, _ = LinkService.create_link_relation({
                            'source_table_id': str(link_field.table_id),
                            'target_table_id': str(target_table_id),
                            'source_field_id': str(link_field.id),
                            'target_field_id': None,
                            'relationship_type': field_config.get('relationshipType', 'one_to_many'),
                            'bidirectional': field_config.get('bidirectional', False),
                        })
                        if not link_relation:
                            continue
    
                    # 一对一约束：超过一个目标记录则跳过
                    if link_relation.relationship_type == 'one_to_one' and len(ids) > 1:
                        continue
    
                    LinkService.update_link_values(
                        link_relation_id=link_relation.id,
                        source_record_id=str(record.id),
                        target_record_ids=ids,
                    )
            except Exception as link_err:
                current_app.logger.error(
                    f'[FormShareService] 关联字段创建失败（已忽略）: {str(link_err)}'
                )
    
            response_data = {
                'record_id': str(record.id),
                'submitted_at': datetime.now(timezone.utc).isoformat()
            }
    
            # 如果审批流实例创建成功，返回实例 ID
            if approval_flow_instance_id:
                response_data['approval_flow_instance_id'] = str(approval_flow_instance_id)
    
            return {
                'success': True,
                'data': response_data,
                'message': form_share.success_message
            }
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[FormShareService] 表单提交失败: {str(e)}')
            return {'success': False, 'error': 'submission_failed_try_again_later', 'status': 500}
    
    @staticmethod
    def _validate_form_data(
        form_share: FormShare,
        values: Dict[str, Any],
        field_settings_map: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        验证表单数据
    
        Returns:
            {'valid': bool, 'errors': Dict[str, str]}
        """
        errors = {}
    
        field_settings_map = field_settings_map or {}
    
        # 获取允许提交的字段
        allowed_field_ids = form_share.get_allowed_fields_list()
    
        # 获取表格字段定义
        fields = FieldService.get_all_fields(form_share.table_id)
        field_map = {str(f.id): f for f in fields}
    
        # 如果指定了允许字段，只验证这些字段
        if allowed_field_ids:
            valid_fields = {k: v for k, v in values.items() if k in allowed_field_ids}
        else:
            valid_fields = values
    
        # 验证每个字段
        for field_id, value in valid_fields.items():
            field = field_map.get(field_id)
            if not field:
                errors[field_id] = 'field_does_not_exist'
                continue
    
            # 只读字段由创建者固定（默认值），填写者不可编辑，跳过必填校验
            is_readonly = bool((field_settings_map.get(field_id, {}) or {}).get('readOnly', False))
            if is_readonly:
                continue
    
            # 验证必填字段
            is_required = field.is_required if hasattr(field, 'is_required') else False
            if is_required and (value is None or value == ''):
                errors[field_id] = f'{field.name} 不能为空'
                continue
    
            # 验证字段类型
            if value is not None and value != '':
                type_error = FormShareService._validate_field_type(field, value)
                if type_error:
                    errors[field_id] = type_error
    
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def _validate_field_type(field: Field, value: Any) -> Optional[str]:
        """
        验证字段类型
    
        Returns:
            错误信息，如果验证通过返回 None
        """
        field_type = field.type
    
        try:
            if field_type == FieldType.SINGLE_LINE_TEXT.value:
                # 单行文本：正则、长度、自定义规则校验
                config = field.config or {}
                field_options = field.options or {}
                # 校验规则优先从 config 取，回退到 options
                regex = config.get('regex') or field_options.get('regex')
                regex_message = config.get('regexMessage') or field_options.get('regexMessage')
                str_value = str(value)
    
                if regex:
                    try:
                        if not re.match(regex, str_value):
                            return regex_message or f'{field.name} 格式不正确'
                    except re.error:
                        # 非法正则，跳过正则校验
                        pass
    
                min_length = config.get('minLength')
                if min_length is not None and len(str_value) < int(min_length):
                    return f'{field.name} 至少需要 {min_length} 个字符'
    
                max_length = config.get('maxLength')
                if max_length is not None and len(str_value) > int(max_length):
                    return f'{field.name} 不能超过 {max_length} 个字符'
    
                validation = config.get('validation') or field_options.get('validation')
                if isinstance(validation, dict) and validation.get('pattern'):
                    try:
                        if not re.match(validation['pattern'], str_value):
                            return validation.get('message') or f'{field.name} 格式不正确'
                    except re.error:
                        pass
    
            elif field_type in (
                FieldType.LONG_TEXT.value,
                FieldType.RICH_TEXT.value,
            ):
                # 多行文本/富文本：长度校验
                config = field.config or {}
                field_options = field.options or {}
                str_value = str(value)
    
                min_length = config.get('minLength')
                if min_length is not None and len(str_value) < int(min_length):
                    return f'{field.name} 至少需要 {min_length} 个字符'
    
                max_length = config.get('maxLength')
                if max_length is not None and len(str_value) > int(max_length):
                    return f'{field.name} 不能超过 {max_length} 个字符'
    
            elif field_type == FieldType.MULTI_SELECT.value:
                # 多选：选项数量长度校验
                config = field.config or {}
                field_options = field.options or {}
    
                min_length = config.get('minLength')
                if min_length is not None and isinstance(value, list) and len(value) < int(min_length):
                    return f'{field.name} 至少需要选择 {min_length} 项'
    
                max_length = config.get('maxLength')
                if max_length is not None and isinstance(value, list) and len(value) > int(max_length):
                    return f'{field.name} 最多只能选择 {max_length} 项'
    
                if not isinstance(value, list):
                    return f'{field.name} 必须是选项列表'
    
                options = (
                    config.get('options', [])
                    or field_options.get('options', [])
                    or field_options.get('choices', [])
                )
                option_values = [opt.get('value') or opt.get('id') for opt in options]
                for v in value:
                    if v not in option_values:
                        return f'{field.name} 包含无效选项'
    
            elif field_type == FieldType.NUMBER.value:
                # 数字类型验证
                if not isinstance(value, (int, float)):
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        return f'{field.name} 必须是数字'
    
                # 检查范围限制
                config = field.config or {}
                min_val = config.get('min')
                max_val = config.get('max')
                num_val = float(value)
    
                if min_val is not None and num_val < float(min_val):
                    return f'{field.name} 不能小于 {min_val}'
                if max_val is not None and num_val > float(max_val):
                    return f'{field.name} 不能大于 {max_val}'
    
            elif field_type == FieldType.DATE.value:
                # 日期类型验证
                from datetime import datetime as dt
                try:
                    dt.strptime(str(value), '%Y-%m-%d')
                except ValueError:
                    return f'{field.name} 必须是有效的日期格式（YYYY-MM-DD）'
    
            elif field_type == FieldType.DATE_TIME.value:
                # 日期时间类型验证
                from datetime import datetime as dt
                try:
                    dt.fromisoformat(str(value).replace('Z', '+00:00'))
                except ValueError:
                    return f'{field.name} 必须是有效的日期时间格式'
    
            elif field_type == FieldType.SINGLE_SELECT.value:
                # 单选类型验证
                config = field.config or {}
                field_options = field.options or {}
    
                # 合并 config.options 和 field.options
                options = config.get('options', []) or field_options.get('options', []) or field_options.get('choices', [])
                option_values = [opt.get('value') or opt.get('id') for opt in options]
    
                if value not in option_values:
                    return f'{field.name} 必须是有效的选项'
    
            elif field_type == FieldType.EMAIL.value:
                # 邮箱类型验证
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, str(value)):
                    return f'{field.name} 必须是有效的邮箱地址'
    
            elif field_type == FieldType.URL.value:
                # URL 类型验证
                url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
                if not re.match(url_pattern, str(value)):
                    return f'{field.name} 必须是有效的 URL 地址'
    
            elif field_type == FieldType.PHONE.value:
                # 手机号验证（简化版）
                phone_pattern = r'^1[3-9]\d{9}$'
                if not re.match(phone_pattern, str(value)):
                    return f'{field.name} 必须是有效的手机号码'
    
        except Exception as e:
            return f'{field.name} 验证失败: {str(e)}'
    
        return None
    
    @staticmethod
    def _check_rate_limit(token: str) -> bool:
        """
        检查速率限制（按分享令牌维度，避免同一局域网/出口 IP 的多个正常用户被全局限流误伤）
    
        Returns:
            True 表示允许提交，False 表示超过限制
        """
        cache_key = f'form_share_submit:{token}'
    
        # 获取当前提交次数
        submit_count = cache.get(cache_key) or 0
    
        if submit_count >= FormShareService.SUBMIT_RATE_LIMIT:
            return False
    
        # 增加提交次数
        cache.set(cache_key, submit_count + 1, timeout=FormShareService.RATE_LIMIT_WINDOW)
    
        return True
    
