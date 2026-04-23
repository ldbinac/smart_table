"""
管理员用户管理 API 路由模块
处理管理员用户管理系统的所有功能，包括用户管理、操作日志、系统配置等
"""
import csv
import io
from datetime import datetime
from typing import Optional

from flask import Blueprint, request, g, make_response, current_app
from marshmallow import ValidationError

from app.services.admin_service import AdminService
from app.services.email_config_service import EmailConfigService
from app.models.log import AdminActionType, EntityType
from app.models.user import UserRole
from app.schemas.admin_schema import (
    user_create_schema,
    user_update_schema,
    user_status_update_schema,
    password_reset_schema,
    system_config_update_schema,
    system_config_batch_update_schema,
    email_config_verify_schema,
    email_config_test_schema
)
from app.utils.decorators import jwt_required, admin_required, get_client_ip, get_user_agent
from app.utils.response import (
    success_response,
    error_response,
    validation_error_response,
    not_found_response,
    paginated_response
)

admin_bp = Blueprint('admin', __name__)
admin_bp.strict_slashes = False


@admin_bp.route('/users', methods=['GET'])
@jwt_required
@admin_required
def get_users() -> tuple:
    """
    获取所有用户（分页）
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    description: 获取所有用户列表（需要管理员权限）
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
      - name: search
        in: query
        type: string
        description: 搜索关键词（支持邮箱和姓名）
      - name: role
        in: query
        type: string
        enum: ['owner', 'admin', 'workspace_admin', 'editor', 'commenter', 'viewer']
        description: 角色过滤
      - name: status
        in: query
        type: string
        enum: ['active', 'inactive', 'suspended']
        description: 状态过滤
    responses:
      200:
        description: 返回分页用户列表
      401:
        description: 未授权访问
      403:
        description: 权限不足
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', None)
        role = request.args.get('role', None)
        status = request.args.get('status', None)
        
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20
        
        result = AdminService.get_all_users(
            page=page,
            per_page=per_page,
            search=search,
            role=role,
            status=status
        )
        
        return paginated_response(
            items=result['users'],
            total=result['total'],
            page=result['page'],
            per_page=result['per_page'],
            message='获取用户列表成功'
        )
        
    except Exception as e:
        return error_response(f'获取用户列表失败：{str(e)}', code=500)


@admin_bp.route('/users', methods=['POST'])
@jwt_required
@admin_required
def create_user() -> tuple:
    """
    创建用户
    
    请求体:
        {
            "email": "user@example.com",
            "password": "Password123",
            "name": "用户名",
            "role": "editor" (可选，默认 editor)
        }
    
    响应:
        201: 创建成功，返回用户信息
        400: 请求数据验证失败
        401: 未授权访问
        403: 权限不足
        409: 邮箱已被注册
    """
    data = request.get_json()
    
    if not data:
        return error_response('请求体不能为空', code=400)
    
    try:
        validated_data = user_create_schema.load(data)
    except ValidationError as err:
        return validation_error_response(err.messages)
    
    email = validated_data['email']
    password = validated_data['password']
    name = validated_data['name']
    role = validated_data.get('role', 'editor')
    
    user_info, error = AdminService.create_user(
        email=email,
        password=password,
        name=name,
        role=role,
        must_change_password=True
    )
    
    if error:
        if '已被注册' in error:
            return error_response(error, code=409, error='email_already_exists')
        return error_response(error, code=500)
    
    AdminService.log_operation(
        user_id=g.current_user_id,
        action=AdminActionType.CREATE.value,
        entity_type=EntityType.USER.value,
        entity_id=user_info['id'],
        new_value=user_info,
        ip_address=get_client_ip(),
        user_agent=get_user_agent()
    )
    
    return success_response(
        data=user_info,
        message='用户创建成功',
        code=201
    )


@admin_bp.route('/users/<user_id>', methods=['GET'])
@jwt_required
@admin_required
def get_user(user_id) -> tuple:
    """
    获取用户详情
    
    路径参数:
        user_id: 用户 ID
    
    响应:
        200: 返回用户详情
        401: 未授权访问
        403: 权限不足
        404: 用户不存在
    """
    user_info = AdminService.get_user(user_id)
    
    if not user_info:
        return not_found_response('用户')
    
    return success_response(
        data=user_info,
        message='获取用户信息成功'
    )


@admin_bp.route('/users/<user_id>', methods=['PUT'])
@jwt_required
@admin_required
def update_user(user_id) -> tuple:
    """
    更新用户信息
    
    路径参数:
        user_id: 用户 ID
    
    请求体:
        {
            "email": "newemail@example.com" (可选),
            "name": "新用户名" (可选),
            "role": "admin" (可选),
            "status": "active" (可选)
        }
    
    响应:
        200: 更新成功，返回用户信息
        400: 请求数据验证失败
        401: 未授权访问
        403: 权限不足
        404: 用户不存在
    """
    data = request.get_json()
    
    if not data:
        return error_response('请求体不能为空', code=400)
    
    try:
        validated_data = user_update_schema.load(data, partial=True)
    except ValidationError as err:
        return validation_error_response(err.messages)
    
    old_user_info = AdminService.get_user(user_id)
    if not old_user_info:
        return not_found_response('用户')
    
    user_info, error = AdminService.update_user(user_id=user_id, data=validated_data)
    
    if error:
        if '用户不存在' in error:
            return not_found_response('用户')
        return error_response(error, code=500)
    
    AdminService.log_operation(
        user_id=g.current_user_id,
        action=AdminActionType.UPDATE.value,
        entity_type=EntityType.USER.value,
        entity_id=user_id,
        old_value=old_user_info,
        new_value=user_info,
        ip_address=get_client_ip(),
        user_agent=get_user_agent()
    )
    
    return success_response(
        data=user_info,
        message='用户信息更新成功'
    )


@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@jwt_required
@admin_required
def delete_user(user_id) -> tuple:
    """
    删除用户（软删除）
    
    路径参数:
        user_id: 用户 ID
    
    响应:
        200: 删除成功
        401: 未授权访问
        403: 权限不足
        404: 用户不存在
    """
    old_user_info = AdminService.get_user(user_id)
    if not old_user_info:
        return not_found_response('用户')
    
    success, error = AdminService.delete_user(user_id)
    
    if not success:
        if '用户不存在' in error:
            return not_found_response('用户')
        return error_response(error, code=500)
    
    AdminService.log_operation(
        user_id=g.current_user_id,
        action=AdminActionType.DELETE.value,
        entity_type=EntityType.USER.value,
        entity_id=user_id,
        old_value=old_user_info,
        ip_address=get_client_ip(),
        user_agent=get_user_agent()
    )
    
    return success_response(
        message='用户删除成功'
    )


@admin_bp.route('/users/<user_id>/status', methods=['PUT'])
@jwt_required
@admin_required
def update_user_status(user_id) -> tuple:
    """
    更新用户状态
    
    路径参数:
        user_id: 用户 ID
    
    请求体:
        {
            "status": "active" (active, inactive, suspended)
        }
    
    响应:
        200: 更新成功，返回用户信息
        400: 请求数据验证失败
        401: 未授权访问
        403: 权限不足
        404: 用户不存在
    """
    data = request.get_json()
    
    if not data:
        return error_response('请求体不能为空', code=400)
    
    try:
        validated_data = user_status_update_schema.load(data)
    except ValidationError as err:
        return validation_error_response(err.messages)
    
    old_user_info = AdminService.get_user(user_id)
    if not old_user_info:
        return not_found_response('用户')
    
    status = validated_data['status'].lower()
    
    if status == 'suspended':
        user_info, error = AdminService.suspend_user(user_id)
        action = AdminActionType.SUSPEND
    elif status == 'active':
        user_info, error = AdminService.activate_user(user_id)
        action = AdminActionType.ACTIVATE
    else:
        return error_response('无效的状态值', code=400)
    
    if error:
        if '用户不存在' in error:
            return not_found_response('用户')
        return error_response(error, code=500)
    
    AdminService.log_operation(
        user_id=g.current_user_id,
        action=action.value,
        entity_type=EntityType.USER.value,
        entity_id=user_id,
        old_value=old_user_info,
        new_value=user_info,
        ip_address=get_client_ip(),
        user_agent=get_user_agent()
    )
    
    return success_response(
        data=user_info,
        message='用户状态更新成功'
    )


@admin_bp.route('/users/<user_id>/reset-password', methods=['POST'])
@jwt_required
@admin_required
def reset_user_password(user_id) -> tuple:
    """
    重置用户密码
    
    路径参数:
        user_id: 用户 ID
    
    请求体:
        {
            "temporary_password": "TempPass123" (可选，不提供则自动生成)
        }
    
    响应:
        200: 重置成功，返回临时密码
        400: 请求数据验证失败
        401: 未授权访问
        403: 权限不足
        404: 用户不存在
    """
    data = request.get_json() or {}
    
    try:
        validated_data = password_reset_schema.load(data)
    except ValidationError as err:
        return validation_error_response(err.messages)
    
    temporary_password = validated_data.get('temporary_password')
    
    old_user_info = AdminService.get_user(user_id)
    if not old_user_info:
        return not_found_response('用户')
    
    temp_pwd, error = AdminService.reset_password(
        user_id=user_id,
        temporary_password=temporary_password
    )
    
    if error:
        if '用户不存在' in error:
            return not_found_response('用户')
        return error_response(error, code=500)
    
    AdminService.log_operation(
        user_id=g.current_user_id,
        action=AdminActionType.RESET_PASSWORD.value,
        entity_type=EntityType.USER.value,
        entity_id=user_id,
        old_value={'password_reset': True},
        new_value={'password_reset': True, 'must_change_password': True},
        ip_address=get_client_ip(),
        user_agent=get_user_agent()
    )
    
    return success_response(
        data={'temporary_password': temp_pwd},
        message='密码重置成功，请通知用户及时修改密码'
    )


@admin_bp.route('/settings', methods=['GET'])
@jwt_required
@admin_required
def get_settings() -> tuple:
    """
    获取所有系统配置
    
    响应:
        200: 返回分组配置信息
        401: 未授权访问
        403: 权限不足
    
    示例返回:
        {
            "basic": {"site_name": "My Site", "site_url": "https://example.com"},
            "email": {"smtp_host": "smtp.example.com", "smtp_port": 587}
        }
    """
    try:
        configs = AdminService.get_all_configs()
        return success_response(
            data=configs,
            message='获取系统配置成功'
        )
    except Exception as e:
        return error_response(f'获取系统配置失败：{str(e)}', code=500)


@admin_bp.route('/settings', methods=['PUT'])
@jwt_required
@admin_required
def update_settings() -> tuple:
    """
    更新系统配置
    
    请求体:
        {
            "configs": [
                {
                    "key": "site_name",
                    "value": "My Site",
                    "group": "basic",
                    "description": "网站名称"
                }
            ]
        }
    
    响应:
        200: 更新成功，返回更新后的配置列表
        400: 请求数据验证失败
        401: 未授权访问
        403: 权限不足
    """
    data = request.get_json()
    
    if not data:
        return error_response('请求体不能为空', code=400)
    
    try:
        validated_data = system_config_batch_update_schema.load(data)
    except ValidationError as err:
        return validation_error_response(err.messages)
    
    configs = validated_data.get('configs', [])
    updated_configs = []
    
    for config_data in configs:
        key = config_data['key']
        value = config_data['value']
        group = config_data.get('group', 'basic')
        description = config_data.get('description')
        
        # 如果是 SMTP 密码，进行加密
        if key == 'smtp_password' and value:
            try:
                secret_key = current_app.config.get('SECRET_KEY')
                value = EmailConfigService.encrypt_password(value, secret_key)
            except Exception as e:
                current_app.logger.error(f'加密 SMTP 密码失败: {str(e)}')
                return error_response('加密密码失败', code=500)
        
        old_value = AdminService.get_config(key)
        
        config = AdminService.update_config(
            key=key,
            value=value,
            group=group,
            description=description
        )
        
        updated_configs.append({
            'key': config.config_key,
            'value': config.config_value,
            'group': config.config_group,
            'description': config.description
        })
        
        AdminService.log_operation(
            user_id=g.current_user_id,
            action=AdminActionType.CONFIG_CHANGE.value,
            entity_type=EntityType.CONFIG.value,
            entity_id=None,
            old_value={'key': key, 'value': old_value},
            new_value={'key': key, 'value': value},
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
    
    return success_response(
        data={'configs': updated_configs},
        message='系统配置更新成功'
    )


@admin_bp.route('/operation-logs', methods=['GET'])
@jwt_required
@admin_required
def get_operation_logs() -> tuple:
    """
    获取操作日志（分页）
    
    查询参数:
        page: 页码，从 1 开始，默认 1
        per_page: 每页数量，默认 20
        user_id: 用户 ID 过滤
        action: 操作类型过滤（create, update, delete, suspend, activate, reset_password 等）
        entity_type: 实体类型过滤（user, config 等）
        start_date: 开始时间（ISO 8601 格式）
        end_date: 结束时间（ISO 8601 格式）
    
    响应:
        200: 返回分页操作日志列表
        401: 未授权访问
        403: 权限不足
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        user_id = request.args.get('user_id', None)
        action = request.args.get('action', None)
        entity_type = request.args.get('entity_type', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20
        
        start_date_dt = None
        end_date_dt = None
        
        if start_date:
            try:
                start_date_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                return error_response('开始时间格式错误', code=400)
        
        if end_date:
            try:
                end_date_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                return error_response('结束时间格式错误', code=400)
        
        result = AdminService.get_operation_logs(
            page=page,
            per_page=per_page,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            start_date=start_date_dt,
            end_date=end_date_dt
        )
        
        return paginated_response(
            items=result['logs'],
            total=result['total'],
            page=result['page'],
            per_page=result['per_page'],
            message='获取操作日志成功'
        )
        
    except Exception as e:
        return error_response(f'获取操作日志失败：{str(e)}', code=500)


@admin_bp.route('/operation-logs/export', methods=['GET'])
@jwt_required
@admin_required
def export_operation_logs() -> tuple:
    """
    导出操作日志为 CSV 文件
    
    查询参数:
        user_id: 用户 ID 过滤
        action: 操作类型过滤
        entity_type: 实体类型过滤
        start_date: 开始时间（ISO 8601 格式）
        end_date: 结束时间（ISO 8601 格式）
    
    响应:
        200: 返回 CSV 文件
        400: 时间格式错误
        401: 未授权访问
        403: 权限不足
    """
    try:
        user_id = request.args.get('user_id', None)
        action = request.args.get('action', None)
        entity_type = request.args.get('entity_type', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        
        start_date_dt = None
        end_date_dt = None
        
        if start_date:
            try:
                start_date_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                return error_response('开始时间格式错误', code=400)
        
        if end_date:
            try:
                end_date_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                return error_response('结束时间格式错误', code=400)
        
        csv_content = AdminService.export_operation_logs(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            start_date=start_date_dt,
            end_date=end_date_dt
        )
        
        output = io.BytesIO()
        output.write(csv_content.encode('utf-8-sig'))
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=operation_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        
        AdminService.log_operation(
            user_id=g.current_user_id,
            action=AdminActionType.EXPORT.value,
            entity_type=EntityType.USER.value,
            entity_id=None,
            new_value={'export_type': 'operation_logs'},
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        
        return response
        
    except Exception as e:
        return error_response(f'导出操作日志失败：{str(e)}', code=500)


@admin_bp.route('/roles', methods=['GET'])
@jwt_required
@admin_required
def get_roles() -> tuple:
    """
    获取所有角色及其描述
    
    响应:
        200: 返回角色列表
        401: 未授权访问
        403: 权限不足
    
    返回示例:
        [
            {
                "value": "owner",
                "name": "所有者",
                "description": "系统最高权限，可以执行所有操作"
            },
            {
                "value": "admin",
                "name": "管理员",
                "description": "管理员权限，可以管理用户和系统配置"
            }
        ]
    """
    
    roles_info = {
        UserRole.OWNER.value: {
            'value': UserRole.OWNER.value,
            'name': '所有者',
            'description': '系统最高权限，可以执行所有操作'
        },
        UserRole.ADMIN.value: {
            'value': UserRole.ADMIN.value,
            'name': '管理员',
            'description': '管理员权限，可以管理用户和系统配置'
        },
        UserRole.WORKSPACE_ADMIN.value: {
            'value': UserRole.WORKSPACE_ADMIN.value,
            'name': '工作区管理员',
            'description': '工作区级别管理员权限'
        },
        UserRole.EDITOR.value: {
            'value': UserRole.EDITOR.value,
            'name': '编辑者',
            'description': '可以查看和编辑数据'
        },
        UserRole.COMMENTER.value: {
            'value': UserRole.COMMENTER.value,
            'name': '评论者',
            'description': '可以查看数据和添加评论'
        },
        UserRole.VIEWER.value: {
            'value': UserRole.VIEWER.value,
            'name': '查看者',
            'description': '仅可以查看数据'
        }
    }
    
    roles_list = list(roles_info.values())
    
    return success_response(
        data=roles_list,
        message='获取角色列表成功'
    )


@admin_bp.route('/email/verify-config', methods=['POST'])
@jwt_required
@admin_required
def verify_email_config() -> tuple:
    """
    验证邮件配置有效性
    
    请求体:
        {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "user@example.com",
            "smtp_password": "password",
            "smtp_use_tls": true (可选，默认 true),
            "smtp_use_ssl": false (可选，默认 false),
            "from_email": "noreply@example.com",
            "from_name": "SmartTable" (可选)
        }
    
    响应:
        200: 配置有效
        400: 请求数据验证失败或配置无效
        401: 未授权访问
        403: 权限不足
    """
    data = request.get_json()
    
    if not data:
        return error_response('请求体不能为空', code=400)
    
    try:
        validated_data = email_config_verify_schema.load(data)
    except ValidationError as err:
        return validation_error_response(err.messages)
    
    is_valid, error = AdminService.verify_email_config(validated_data)
    
    if not is_valid:
        return error_response(error, code=400, error='invalid_email_config')
    
    return success_response(
        message='邮件配置验证成功'
    )


@admin_bp.route('/email/test', methods=['POST'])
@jwt_required
@admin_required
def send_test_email() -> tuple:
    """
    发送测试邮件
    
    请求体:
        {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "user@example.com",
            "smtp_password": "password",
            "smtp_use_tls": true (可选，默认 true),
            "smtp_use_ssl": false (可选，默认 false),
            "from_email": "noreply@example.com",
            "from_name": "SmartTable" (可选),
            "test_email": "test@example.com"
        }
    
    响应:
        200: 发送成功
        400: 请求数据验证失败或发送失败
        401: 未授权访问
        403: 权限不足
    """
    from flask import current_app
    
    data = request.get_json()
    
    if not data:
        return error_response('请求体不能为空', code=400)
    
    try:
        validated_data = email_config_test_schema.load(data)
    except ValidationError as err:
        return validation_error_response(err.messages)
    
    test_email = validated_data.pop('test_email')
    secret_key = current_app.config.get('SECRET_KEY')
    
    if not secret_key:
        return error_response('服务器未配置加密密钥', code=500)
    
    success, error = AdminService.send_test_email(
        config_data=validated_data,
        test_email=test_email,
        secret_key=secret_key
    )
    
    if not success:
        return error_response(error, code=400, error='send_test_email_failed')
    
    AdminService.log_operation(
        user_id=g.current_user_id,
        action=AdminActionType.CONFIG_CHANGE.value,
        entity_type=EntityType.CONFIG.value,
        entity_id=None,
        new_value={'action': 'send_test_email', 'test_email': test_email},
        ip_address=get_client_ip(),
        user_agent=get_user_agent()
    )
    
    return success_response(
        message=f'测试邮件已发送至 {test_email}'
    )
