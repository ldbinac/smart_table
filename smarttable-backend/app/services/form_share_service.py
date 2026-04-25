"""
表单分享服务模块
处理表单分享的创建、管理和数据提交
"""
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
from app.services.permission_service import PermissionService
from app.utils.captcha import CaptchaService


class FormShareError(Exception):
    """表单分享错误"""
    pass


class FormShareService:
    """表单分享服务类"""
    
    # 速率限制配置
    SUBMIT_RATE_LIMIT = 10  # 每 IP 每 15 分钟最多提交次数
    RATE_LIMIT_WINDOW = 900  # 15 分钟（秒）
    
    @staticmethod
    def create_form_share(
        table_id: str,
        user_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        创建表单分享
        
        Args:
            table_id: 表格 ID
            user_id: 创建者用户 ID
            config: 配置参数
                - allow_anonymous: 是否允许匿名提交
                - require_captcha: 是否需要验证码
                - expires_at: 过期时间（Unix 时间戳）
                - max_submissions: 最大提交次数
                - allowed_fields: 允许提交的字段列表
                - title: 表单标题
                - description: 表单描述
                - submit_button_text: 提交按钮文字
                - success_message: 成功提示信息
                - theme: 主题样式
        
        Returns:
            包含操作结果的字典
        """
        try:
            # 验证表格是否存在
            table = TableService.get_table_by_id(table_id)
            if not table:
                return {'success': False, 'error': '表格不存在', 'status': 404}
            
            # 验证用户权限（需要 EDITOR 或更高权限）
            if not PermissionService.check_permission(
                str(table.base_id), user_id, MemberRole.EDITOR
            ):
                return {'success': False, 'error': '无权创建表单分享', 'status': 403}
            
            # 验证过期时间
            expires_at = config.get('expires_at')
            if expires_at is not None:
                try:
                    expires_at = int(expires_at)
                    if expires_at < int(datetime.now(timezone.utc).timestamp()):
                        return {'success': False, 'error': '过期时间不能是过去的时间'}
                except (ValueError, TypeError):
                    return {'success': False, 'error': '过期时间必须是有效的 Unix 时间戳'}
            
            # 验证允许字段列表
            allowed_fields = config.get('allowed_fields', [])
            if allowed_fields:
                # 获取表格所有字段
                table_fields = FieldService.get_all_fields(table_id)
                table_field_ids = {str(f.id) for f in table_fields}
                
                # 检查所有指定字段是否存在于表格中
                invalid_fields = [f for f in allowed_fields if f not in table_field_ids]
                if invalid_fields:
                    return {'success': False, 'error': f'以下字段不存在: {invalid_fields}'}
            
            # 创建表单分享
            form_share = FormShare(
                table_id=str(table_id),
                created_by=str(user_id),
                is_active=config.get('is_active', True),
                allow_anonymous=config.get('allow_anonymous', True),
                require_captcha=config.get('require_captcha', False),
                expires_at=expires_at,
                max_submissions=config.get('max_submissions'),
                title=config.get('title'),
                description=config.get('description'),
                submit_button_text=config.get('submit_button_text', '提交'),
                success_message=config.get('success_message', '提交成功，感谢您的参与！'),
                theme=config.get('theme', 'default')
            )
            
            # 设置允许字段
            if allowed_fields:
                form_share.set_allowed_fields_list(allowed_fields)
            
            db.session.add(form_share)
            db.session.commit()
            
            current_app.logger.info(
                f'[FormShareService] 创建表单分享: id={form_share.id}, '
                f'table={table_id}, created_by={user_id}'
            )
            
            return {
                'success': True,
                'form_share': form_share,
                'share_url': f'/form/{form_share.share_token}'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[FormShareService] 创建表单分享失败: {str(e)}')
            return {'success': False, 'error': f'创建失败: {str(e)}', 'status': 500}
    
    @staticmethod
    def get_form_share_by_token(token: str) -> Optional[FormShare]:
        """通过分享令牌获取表单分享"""
        return FormShare.query.filter_by(share_token=token).first()
    
    @staticmethod
    def get_form_share_by_id(share_id: str) -> Optional[FormShare]:
        """通过 ID 获取表单分享"""
        return FormShare.query.get(share_id)
    
    @staticmethod
    def get_form_shares_by_table(table_id: str) -> List[FormShare]:
        """获取表格的所有表单分享"""
        return FormShare.query.filter_by(
            table_id=str(table_id)
        ).order_by(FormShare.created_at.desc()).all()
    
    @staticmethod
    def validate_form_share(token: str) -> Tuple[bool, Optional[FormShare], Optional[str]]:
        """
        验证表单分享有效性
        
        Returns:
            (是否有效, 表单分享对象, 错误信息)
        """
        form_share = FormShareService.get_form_share_by_token(token)
        
        if not form_share:
            return False, None, '表单分享不存在'
        
        if not form_share.is_active:
            return False, None, '该表单分享已失效'
        
        if form_share.is_expired():
            return False, None, '该表单分享已过期'
        
        if form_share.is_reached_limit():
            return False, None, '提交次数已达上限'
        
        return True, form_share, None
    
    @staticmethod
    def get_form_schema(token: str) -> Dict[str, Any]:
        """
        获取表单结构（字段定义）
        
        Returns:
            包含表单结构的字典
        """
        valid, form_share, error = FormShareService.validate_form_share(token)
        
        if not valid:
            return {'success': False, 'error': error, 'status': 403 if '失效' in error or '过期' in error or '上限' in error else 404}
        
        try:
            # 获取表格信息
            table = TableService.get_table_by_id(form_share.table_id)
            if not table:
                return {'success': False, 'error': '表格不存在', 'status': 404}
            
            # 获取字段列表
            all_fields = FieldService.get_all_fields(form_share.table_id)
            
            # 过滤允许提交的字段
            allowed_field_ids = form_share.get_allowed_fields_list()
            if allowed_field_ids:
                fields = [f for f in all_fields if str(f.id) in allowed_field_ids]
            else:
                fields = all_fields
            
            # 构建字段定义
            fields_schema = []
            for field in fields:
                # 合并 config 和 options，确保选项数据正确传递
                config = field.config or {}
                options = field.options or {}
                
                # 对于单选/多选字段，选项可能存储在 options 中
                merged_config = {**config}
                if options:
                    # 如果 options 中有 choices，合并到 config
                    if 'choices' in options:
                        merged_config['choices'] = options['choices']
                    # 如果 options 中有 options，合并到 config
                    if 'options' in options:
                        merged_config['options'] = options['options']
                    # 合并最大长度配置
                    if 'maxLength' in options:
                        merged_config['maxLength'] = options['maxLength']
                
                field_schema = {
                    'id': str(field.id),
                    'name': field.name,
                    'type': field.type,
                    'required': field.is_required if hasattr(field, 'is_required') else False,
                    'config': merged_config,
                    'description': field.description if hasattr(field, 'description') else None
                }
                fields_schema.append(field_schema)
            
            return {
                'success': True,
                'data': {
                    'table_id': str(table.id),
                    'table_name': table.name,
                    'form_title': form_share.title or table.name,
                    'form_description': form_share.description,
                    'submit_button_text': form_share.submit_button_text,
                    'success_message': form_share.success_message,
                    'theme': form_share.theme,
                    'require_captcha': form_share.require_captcha,
                    'fields': fields_schema
                }
            }
            
        except Exception as e:
            current_app.logger.error(f'[FormShareService] 获取表单结构失败: {str(e)}')
            return {'success': False, 'error': '获取表单结构失败', 'status': 500}
    
    @staticmethod
    def submit_form_data(
        token: str,
        data: Dict[str, Any],
        client_info: Dict[str, str]
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
        
        Returns:
            包含操作结果的字典
        """
        # 验证表单分享
        valid, form_share, error = FormShareService.validate_form_share(token)
        
        if not valid:
            status = 403 if '失效' in error or '过期' in error or '上限' in error else 404
            return {'success': False, 'error': error, 'status': status}
        
        # 检查速率限制
        client_ip = client_info.get('ip', 'unknown')
        if not FormShareService._check_rate_limit(client_ip):
            return {'success': False, 'error': '提交过于频繁，请稍后再试', 'status': 429}
        
        # 验证验证码（如果需要）
        if form_share.require_captcha:
            captcha = data.get('captcha')
            if not captcha:
                return {'success': False, 'error': '请输入验证码', 'status': 400}
            
            # 验证验证码
            is_valid, error_msg = CaptchaService.verify_captcha(token, captcha)
            if not is_valid:
                return {'success': False, 'error': error_msg, 'status': 400}
        
        try:
            # 获取提交的值
            values = data.get('values', {})
            
            # 验证数据
            validation_result = FormShareService._validate_form_data(
                form_share, values
            )
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': '数据验证失败',
                    'details': validation_result['errors'],
                    'status': 400
                }
            
            # 过滤只允许提交的字段
            allowed_field_ids = form_share.get_allowed_fields_list()
            if allowed_field_ids:
                values = {k: v for k, v in values.items() if k in allowed_field_ids}
            
            # 创建记录
            record = RecordService.create_record(
                table_id=form_share.table_id,
                values=values,
                created_by=None  # 匿名提交
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
            
            db.session.commit()
            
            # 记录日志
            current_app.logger.info(
                f'[FormShareService] 表单提交成功: form_share={form_share.id}, '
                f'record={record.id}, ip={client_ip}'
            )
            
            return {
                'success': True,
                'data': {
                    'record_id': str(record.id),
                    'submitted_at': datetime.now(timezone.utc).isoformat()
                },
                'message': form_share.success_message
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[FormShareService] 表单提交失败: {str(e)}')
            return {'success': False, 'error': '提交失败，请稍后重试', 'status': 500}
    
    @staticmethod
    def _validate_form_data(
        form_share: FormShare,
        values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证表单数据
        
        Returns:
            {'valid': bool, 'errors': Dict[str, str]}
        """
        errors = {}
        
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
                errors[field_id] = '字段不存在'
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
            if field_type == FieldType.NUMBER.value:
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
            
            elif field_type == FieldType.MULTI_SELECT.value:
                # 多选类型验证
                if not isinstance(value, list):
                    return f'{field.name} 必须是选项列表'
                
                config = field.config or {}
                field_options = field.options or {}
                
                # 合并 config.options 和 field.options
                options = config.get('options', []) or field_options.get('options', []) or field_options.get('choices', [])
                option_values = [opt.get('value') or opt.get('id') for opt in options]
                
                for v in value:
                    if v not in option_values:
                        return f'{field.name} 包含无效选项'
            
            elif field_type == FieldType.EMAIL.value:
                # 邮箱类型验证
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, str(value)):
                    return f'{field.name} 必须是有效的邮箱地址'
            
            elif field_type == FieldType.URL.value:
                # URL 类型验证
                import re
                url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
                if not re.match(url_pattern, str(value)):
                    return f'{field.name} 必须是有效的 URL 地址'
            
            elif field_type == FieldType.PHONE.value:
                # 手机号验证（简化版）
                import re
                phone_pattern = r'^1[3-9]\d{9}$'
                if not re.match(phone_pattern, str(value)):
                    return f'{field.name} 必须是有效的手机号码'
            
        except Exception as e:
            return f'{field.name} 验证失败: {str(e)}'
        
        return None
    
    @staticmethod
    def _check_rate_limit(client_ip: str) -> bool:
        """
        检查速率限制
        
        Returns:
            True 表示允许提交，False 表示超过限制
        """
        cache_key = f'form_share_submit:{client_ip}'
        
        # 获取当前提交次数
        submit_count = cache.get(cache_key) or 0
        
        if submit_count >= FormShareService.SUBMIT_RATE_LIMIT:
            return False
        
        # 增加提交次数
        cache.set(cache_key, submit_count + 1, timeout=FormShareService.RATE_LIMIT_WINDOW)
        
        return True
    
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
                return {'success': False, 'error': '表单分享不存在', 'status': 404}
            
            # 验证权限（只有创建者可以更新）
            if str(form_share.created_by) != str(user_id):
                # 或者检查用户是否有表格的管理权限
                table = TableService.get_table_by_id(form_share.table_id)
                if table and not PermissionService.check_permission(
                    str(table.base_id), user_id, MemberRole.ADMIN
                ):
                    return {'success': False, 'error': '无权更新此表单分享', 'status': 403}
            
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
                            return {'success': False, 'error': '过期时间不能是过去的时间'}
                        form_share.expires_at = expires_at
                    except (ValueError, TypeError):
                        return {'success': False, 'error': '过期时间必须是有效的 Unix 时间戳'}
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
                        return {'success': False, 'error': f'以下字段不存在: {invalid_fields}'}
                    form_share.set_allowed_fields_list(allowed_fields)
                else:
                    form_share.allowed_fields = None
            
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
            
            form_share.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            current_app.logger.info(
                f'[FormShareService] 更新表单分享: id={share_id}, by={user_id}'
            )
            
            return {'success': True, 'form_share': form_share}
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[FormShareService] 更新表单分享失败: {str(e)}')
            return {'success': False, 'error': f'更新失败: {str(e)}', 'status': 500}
    
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
                return {'success': False, 'error': '表单分享不存在', 'status': 404}
            
            # 验证权限（只有创建者或管理员可以删除）
            if str(form_share.created_by) != str(user_id):
                table = TableService.get_table_by_id(form_share.table_id)
                if table and not PermissionService.check_permission(
                    str(table.base_id), user_id, MemberRole.ADMIN
                ):
                    return {'success': False, 'error': '无权删除此表单分享', 'status': 403}
            
            db.session.delete(form_share)
            db.session.commit()
            
            current_app.logger.info(
                f'[FormShareService] 删除表单分享: id={share_id}, by={user_id}'
            )
            
            return {'success': True}
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[FormShareService] 删除表单分享失败: {str(e)}')
            return {'success': False, 'error': f'删除失败: {str(e)}', 'status': 500}
    
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
                return {'success': False, 'error': '表单分享不存在', 'status': 404}
            
            # 验证权限
            if str(form_share.created_by) != str(user_id):
                table = TableService.get_table_by_id(form_share.table_id)
                if table and not PermissionService.check_permission(
                    str(table.base_id), user_id, MemberRole.VIEWER
                ):
                    return {'success': False, 'error': '无权查看此表单的提交记录', 'status': 403}
            
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
            return {'success': False, 'error': '获取提交记录失败', 'status': 500}
