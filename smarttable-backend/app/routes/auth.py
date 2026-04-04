"""
认证路由模块
处理用户注册、登录、登出、令牌刷新、密码修改等认证相关功能
"""
from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import (
    jwt_required as flask_jwt_required,
    get_jwt_identity,
    get_jwt
)
from marshmallow import ValidationError

from app.extensions import db
from app.models.user import User, TokenBlocklist
from app.services.auth_service import AuthService
from app.schemas.user_schema import (
    user_registration_schema,
    user_login_schema,
    user_update_schema,
    change_password_schema,
    user_profile_schema
)
from app.utils.response import (
    success_response,
    error_response,
    validation_error_response,
    not_found_response,
    unauthorized_response
)
from app.utils.decorators import (
    rate_limit,
    record_login_attempt
)

auth_bp = Blueprint('auth', __name__)
# 禁用严格斜杠，允许带或不带斜杠的URL
auth_bp.strict_slashes = False


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    用户注册
    
    请求体:
        {
            "email": "user@example.com",
            "password": "Password123",
            "name": "用户名"
        }
    
    响应:
        201: 注册成功，返回用户信息和令牌
        400: 请求数据验证失败
        409: 邮箱已被注册
    """
    # 获取请求数据
    data = request.get_json()
    
    if not data:
        return error_response('请求体不能为空', code=400)
    
    # 验证输入数据
    try:
        validated_data = user_registration_schema.load(data)
    except ValidationError as err:
        return validation_error_response(err.messages)
    
    email = validated_data['email']
    password = validated_data['password']
    name = validated_data.get('name') or validated_data.get('username', '')
    
    # 调用服务层进行注册
    user, error = AuthService.register_user(email, password, name)
    
    if error:
        if '已被注册' in error:
            return error_response(error, code=409, error='email_already_exists')
        return error_response(error, code=500)
    
    # 生成令牌
    tokens = AuthService.generate_tokens(str(user.id))
    
    # 返回成功响应
    return success_response(
        data={
            'user': user.to_dict(include_email=True),
            'tokens': tokens
        },
        message='注册成功',
        code=201
    )


@auth_bp.route('/login', methods=['POST'])
@rate_limit(max_attempts=5, window=900)  # 5次尝试，15分钟锁定
def login():
    """
    用户登录
    
    请求体:
        {
            "email": "user@example.com",
            "password": "Password123"
        }
    
    响应:
        200: 登录成功，返回用户信息和令牌
        400: 请求数据验证失败
        401: 邮箱或密码错误，或账号被禁用
        429: 登录尝试次数过多，账户被锁定
    """
    # 获取请求数据
    data = request.get_json()
    
    if not data:
        record_login_attempt(success=False)
        return error_response('请求体不能为空', code=400)
    
    # 验证输入数据
    try:
        validated_data = user_login_schema.load(data)
    except ValidationError as err:
        record_login_attempt(success=False)
        return validation_error_response(err.messages)
    
    email = validated_data['email']
    password = validated_data['password']
    
    # 调用服务层进行认证
    user, error = AuthService.authenticate_user(email, password)
    
    if error:
        record_login_attempt(success=False)
        return error_response(error, code=401, error='authentication_failed')
    
    # 更新最后登录时间
    AuthService.update_last_login(str(user.id))
    
    # 记录登录成功，清除失败记录
    record_login_attempt(success=True)
    
    # 生成令牌
    tokens = AuthService.generate_tokens(str(user.id))
    
    # 返回成功响应
    return success_response(
        data={
            'user': user.to_dict(include_email=True),
            'tokens': tokens
        },
        message='登录成功'
    )


@auth_bp.route('/refresh', methods=['POST'])
@flask_jwt_required(refresh=True)
def refresh():
    """
    刷新访问令牌
    
    使用刷新令牌获取新的访问令牌
    
    请求头:
        Authorization: Bearer <refresh_token>
    
    响应:
        200: 刷新成功，返回新的访问令牌
        401: 刷新令牌无效或过期
    """
    # 获取用户 ID
    user_id = get_jwt_identity()
    
    # 调用服务层刷新令牌
    access_token, error = AuthService.refresh_access_token(user_id)
    
    if error:
        return unauthorized_response(error)
    
    return success_response(
        data={
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': AuthService.ACCESS_TOKEN_EXPIRES
        },
        message='令牌刷新成功'
    )


@auth_bp.route('/logout', methods=['POST'])
@flask_jwt_required()
def logout():
    """
    用户登出
    
    将当前访问令牌加入黑名单，使其失效
    
    请求头:
        Authorization: Bearer <access_token>
    
    响应:
        200: 登出成功
        401: 令牌无效
    """
    # 获取 JWT 信息
    jwt_payload = get_jwt()
    jti = jwt_payload['jti']
    user_id = get_jwt_identity()
    token_type = jwt_payload.get('type', 'access')
    
    # 计算令牌过期时间
    expires_timestamp = jwt_payload.get('exp')
    expires_at = datetime.utcfromtimestamp(expires_timestamp) if expires_timestamp else None
    
    # 调用服务层撤销令牌
    success, error = AuthService.logout_user(jti, user_id, token_type, expires_at)
    
    if not success:
        return error_response(error or '登出失败', code=500)
    
    return success_response(message='登出成功')


@auth_bp.route('/logout-all', methods=['POST'])
@flask_jwt_required()
def logout_all():
    """
    从所有设备登出
    
    撤销用户的所有令牌，强制从所有设备重新登录
    
    请求头:
        Authorization: Bearer <access_token>
    
    响应:
        200: 登出成功
        401: 令牌无效
    """
    user_id = get_jwt_identity()
    
    # 撤销当前令牌
    jwt_payload = get_jwt()
    jti = jwt_payload['jti']
    token_type = jwt_payload.get('type', 'access')
    AuthService.logout_user(jti, user_id, token_type)
    
    # 撤销用户的所有令牌
    AuthService.revoke_all_user_tokens(user_id)
    
    return success_response(message='已从所有设备登出')


@auth_bp.route('/me', methods=['GET'])
@flask_jwt_required()
def get_current_user():
    """
    获取当前用户信息
    
    请求头:
        Authorization: Bearer <access_token>
    
    响应:
        200: 获取成功，返回用户信息
        401: 令牌无效
        404: 用户不存在
    """
    user_id = get_jwt_identity()
    
    # 调用服务层获取用户信息
    user = AuthService.get_current_user(user_id)
    
    if not user:
        return not_found_response('用户')
    
    return success_response(
        data=user.to_dict(include_email=True),
        message='获取成功'
    )


@auth_bp.route('/me', methods=['PUT'])
@flask_jwt_required()
def update_current_user():
    """
    更新当前用户信息
    
    请求头:
        Authorization: Bearer <access_token>
    
    请求体:
        {
            "name": "新用户名",
            "avatar": "https://example.com/avatar.jpg"
        }
    
    响应:
        200: 更新成功，返回更新后的用户信息
        400: 请求数据验证失败
        401: 令牌无效
        404: 用户不存在
    """
    user_id = get_jwt_identity()
    
    # 获取用户
    user = AuthService.get_current_user(user_id)
    
    if not user:
        return not_found_response('用户')
    
    # 获取请求数据
    data = request.get_json()
    
    if not data:
        return error_response('请求体不能为空', code=400)
    
    # 验证输入数据
    try:
        validated_data = user_update_schema.load(data, partial=True)
    except ValidationError as err:
        return validation_error_response(err.messages)
    
    # 更新用户信息
    try:
        if 'name' in validated_data:
            user.name = validated_data['name']
        if 'avatar' in validated_data:
            user.avatar = validated_data['avatar']
        
        db.session.commit()
        
        return success_response(
            data=user.to_dict(include_email=True),
            message='更新成功'
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f'更新失败: {str(e)}', code=500)


@auth_bp.route('/password', methods=['PUT'])
@flask_jwt_required()
def change_password():
    """
    修改密码
    
    请求头:
        Authorization: Bearer <access_token>
    
    请求体:
        {
            "old_password": "旧密码",
            "new_password": "新密码"
        }
    
    响应:
        200: 密码修改成功
        400: 请求数据验证失败或旧密码错误
        401: 令牌无效
        404: 用户不存在
    """
    user_id = get_jwt_identity()
    
    # 获取请求数据
    data = request.get_json()
    
    if not data:
        return error_response('请求体不能为空', code=400)
    
    # 验证输入数据
    try:
        validated_data = change_password_schema.load(data)
    except ValidationError as err:
        return validation_error_response(err.messages)
    
    old_password = validated_data['old_password']
    new_password = validated_data['new_password']
    
    # 调用服务层修改密码
    success, error = AuthService.change_password(user_id, old_password, new_password)
    
    if not success:
        if '旧密码错误' in error:
            return error_response(error, code=400, error='invalid_old_password')
        if '用户不存在' in error:
            return not_found_response('用户')
        return error_response(error, code=500)
    
    return success_response(
        message='密码修改成功，请使用新密码重新登录'
    )


@auth_bp.route('/check-email', methods=['GET'])
def check_email():
    """
    检查邮箱是否可用
    
    查询参数:
        email: 要检查的邮箱地址
    
    响应:
        200: 返回邮箱是否可用
    """
    email = request.args.get('email', '').strip().lower()
    
    if not email:
        return error_response('请提供邮箱地址', code=400)
    
    exists = AuthService.check_email_exists(email)
    
    return success_response(
        data={
            'available': not exists,
            'email': email
        },
        message='邮箱可用' if not exists else '邮箱已被注册'
    )


@auth_bp.route('/verify-token', methods=['GET'])
@flask_jwt_required()
def verify_token():
    """
    验证令牌有效性
    
    用于前端检查当前令牌是否仍然有效
    
    请求头:
        Authorization: Bearer <access_token>
    
    响应:
        200: 令牌有效
        401: 令牌无效或已过期
    """
    user_id = get_jwt_identity()
    user = AuthService.get_current_user(user_id)
    
    if not user:
        return not_found_response('用户')
    
    if not user.is_active():
        return unauthorized_response('用户账号已被禁用')
    
    return success_response(
        data={
            'valid': True,
            'user': user.to_dict(include_email=True)
        },
        message='令牌有效'
    )
