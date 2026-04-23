"""
认证路由模块
处理用户注册、登录、登出、令牌刷新、密码修改等认证相关功能
"""
from datetime import datetime
import logging

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
    user_profile_schema,
    password_reset_confirm_schema
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
from app.utils.captcha import CaptchaService

# 设置日志记录器
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)
# 禁用严格斜杠，允许带或不带斜杠的URL
auth_bp.strict_slashes = False


@auth_bp.route('/register', methods=['POST'])
@rate_limit(max_attempts=3, window=3600)
def register() -> tuple:
    """
    用户注册
    ---
    tags:
      - Auth
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
            - captcha
          properties:
            email:
              type: string
              example: "user@example.com"
            password:
              type: string
              example: "Password123"
            name:
              type: string
              example: "用户名"
            captcha:
              type: string
              example: "ABCD"
    responses:
      201:
        description: 注册成功，返回用户信息和令牌
      400:
        description: 请求数据验证失败
      403:
        description: 验证码错误
      409:
        description: 邮箱已被注册
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
    captcha = validated_data.get('captcha')
    
    # 验证验证码
    client_ip = request.remote_addr or 'unknown'
    captcha_token = f"auth:register:{client_ip}"
    
    if captcha:
        is_valid, error_msg = CaptchaService.verify_captcha(captcha_token, captcha)
        if not is_valid:
            # 记录验证码验证失败的日志
            logger.warning(
                f"注册验证码验证失败 - IP: {client_ip}, Email: {email}, Reason: {error_msg}"
            )
            return error_response(f'验证码错误: {error_msg}', code=403, error='captcha_invalid')
    else:
        # 未提供验证码
        logger.warning(f"注册尝试未提供验证码 - IP: {client_ip}, Email: {email}")
        return error_response('请输入验证码', code=403, error='captcha_required')
    
    # 调用服务层进行注册
    user, error = AuthService.register_user(email, password, name)
    
    if error:
        if '已被注册' in error:
            return error_response(error, code=409, error='email_already_exists')
        return error_response(error, code=500)
    
    # 记录注册成功日志
    logger.info(f"用户注册成功 - IP: {client_ip}, UserID: {user.id}, Email: {email}")
    
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
def login() -> tuple:
    """
    用户登录
    ---
    tags:
      - Auth
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
            - captcha
          properties:
            email:
              type: string
              example: "user@example.com"
            password:
              type: string
              example: "Password123"
            captcha:
              type: string
              example: "ABCD"
    responses:
      200:
        description: 登录成功，返回用户信息和令牌
      400:
        description: 请求数据验证失败
      401:
        description: 邮箱或密码错误，或账号被禁用
      403:
        description: 验证码错误
      429:
        description: 登录尝试次数过多，账户被锁定
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
    captcha = validated_data.get('captcha')
    
    # 验证验证码
    client_ip = request.remote_addr or 'unknown'
    captcha_token = f"auth:login:{client_ip}"
    
    if captcha:
        is_valid, error_msg = CaptchaService.verify_captcha(captcha_token, captcha)
        if not is_valid:
            # 记录验证码验证失败的日志
            logger.warning(
                f"登录验证码验证失败 - IP: {client_ip}, Email: {email}, Reason: {error_msg}"
            )
            record_login_attempt(success=False)
            return error_response(f'验证码错误: {error_msg}', code=403, error='captcha_invalid')
    else:
        # 未提供验证码
        logger.warning(f"登录尝试未提供验证码 - IP: {client_ip}, Email: {email}")
        record_login_attempt(success=False)
        return error_response('请输入验证码', code=403, error='captcha_required')
    
    # 调用服务层进行认证
    user, error = AuthService.authenticate_user(email, password)
    
    if error:
        record_login_attempt(success=False)
        return error_response(error, code=401, error='authentication_failed')
    
    # 更新最后登录时间
    AuthService.update_last_login(str(user.id))
    
    # 记录登录成功，清除失败记录
    record_login_attempt(success=True)
    
    # 记录成功登录日志
    logger.info(f"用户登录成功 - IP: {client_ip}, UserID: {user.id}, Email: {email}")
    
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
def refresh() -> tuple:
    """
    刷新访问令牌
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Bearer <refresh_token>
    responses:
      200:
        description: 刷新成功，返回新的访问令牌
      401:
        description: 刷新令牌无效或过期
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
def logout() -> tuple:
    """
    用户登出
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    description: 将当前访问令牌加入黑名单，使其失效
    responses:
      200:
        description: 登出成功
      401:
        description: 令牌无效
    """
    # 获取 JWT 信息
    jwt_payload = get_jwt()
    jti = jwt_payload['jti']
    user_id = get_jwt_identity()
    token_type = jwt_payload.get('type', 'access')
    
    # 调用服务层撤销令牌
    success, error = AuthService.logout_user(jti, user_id, token_type)
    
    if not success:
        return error_response(error or '登出失败', code=500)
    
    return success_response(message='登出成功')


@auth_bp.route('/logout-all', methods=['POST'])
@flask_jwt_required()
def logout_all() -> tuple:
    """
    从所有设备登出
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    description: 撤销用户的所有令牌，强制从所有设备重新登录
    responses:
      200:
        description: 登出成功
      401:
        description: 令牌无效
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
def get_current_user() -> tuple:
    """
    获取当前用户信息
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    responses:
      200:
        description: 获取成功，返回用户信息
      401:
        description: 令牌无效
      404:
        description: 用户不存在
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
def update_current_user() -> tuple:
    """
    更新当前用户信息
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        schema:
          type: object
          properties:
            name:
              type: string
              description: 新用户名
              example: "新用户名"
            avatar:
              type: string
              description: 头像URL
              example: "https://example.com/avatar.jpg"
    responses:
      200:
        description: 更新成功，返回更新后的用户信息
      400:
        description: 请求数据验证失败
      401:
        description: 令牌无效
      404:
        description: 用户不存在
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
def change_password() -> tuple:
    """
    修改密码
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - old_password
            - new_password
          properties:
            old_password:
              type: string
              description: 旧密码
              example: "OldPassword123"
            new_password:
              type: string
              description: 新密码（至少8位，包含大小写字母和数字）
              example: "NewPassword456"
    responses:
      200:
        description: 密码修改成功
      400:
        description: 请求数据验证失败或旧密码错误
      401:
        description: 令牌无效
      404:
        description: 用户不存在
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

    # 获取客户端信息用于日志记录
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')

    # 调用服务层修改密码
    success, error = AuthService.change_password(user_id, old_password, new_password, ip_address, user_agent)
    
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
@rate_limit(max_attempts=10, window=60)
def check_email() -> tuple:
    """
    检查邮箱是否可用
    ---
    tags:
      - Auth
    parameters:
      - name: email
        in: query
        type: string
        required: true
        description: 要检查的邮箱地址
        example: "user@example.com"
    responses:
      200:
        description: 返回邮箱是否可用
        schema:
          type: object
          properties:
            available:
              type: boolean
              description: 是否可用
            email:
              type: string
              description: 邮箱地址
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
def verify_token() -> tuple:
    """
    验证令牌有效性
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    description: 用于前端检查当前令牌是否仍然有效
    responses:
      200:
        description: 令牌有效
      401:
        description: 令牌无效或已过期
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


@auth_bp.route('/verify-email', methods=['GET'])
def verify_email() -> tuple:
    """
    验证邮箱
    ---
    tags:
      - Auth
    parameters:
      - name: token
        in: query
        type: string
        required: true
        description: 验证令牌
    responses:
      200:
        description: 验证成功
      400:
        description: 令牌无效或已过期
      404:
        description: 用户不存在
    """
    token = request.args.get('token')
    
    if not token:
        return error_response('请提供验证令牌', code=400)
    
    # 查找具有该验证令牌的用户
    user = User.query.filter_by(verification_token=token).first()
    
    if not user:
        return error_response('验证令牌无效', code=400, error='invalid_token')
    
    # 验证令牌
    if user.verify_email(token):
        return success_response(
            data={'email_verified': True},
            message='邮箱验证成功'
        )
    else:
        return error_response('验证令牌已过期', code=400, error='token_expired')


@auth_bp.route('/resend-verification', methods=['POST'])
@flask_jwt_required()
def resend_verification() -> tuple:
    """
    重新发送验证邮件
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    responses:
      200:
        description: 发送成功
      400:
        description: 邮箱已验证或邮件服务未启用
      401:
        description: 令牌无效
      404:
        description: 用户不存在
    """
    from app.services.email_config_service import EmailConfigService
    from app.services.email_sender_service import EmailSenderService
    
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return not_found_response('用户')
    
    if user.email_verified:
        return error_response('邮箱已验证', code=400, error='already_verified')
    
    # 检查邮件服务是否启用
    if not EmailConfigService.is_email_enabled():
        return error_response('邮件服务未启用', code=400, error='email_service_disabled')
    
    # 生成新的验证令牌
    verification_token = user.generate_verification_token()
    
    try:
        verification_link = f"{EmailConfigService.get_frontend_url()}/verify-email?token={verification_token}"
        EmailSenderService.send_email_quick(
            to_email=user.email,
            to_name=user.name,
            template_key='user_registration',
            template_data={
                'user_name': user.name,
                'verification_link': verification_link
            }
        )
        
        return success_response(
            message='验证邮件已发送，请查收'
        )
    except Exception as e:
        logger.error(f'发送验证邮件失败: {str(e)}')
        return error_response('发送验证邮件失败，请稍后重试', code=500)


@auth_bp.route('/forgot-password', methods=['POST'])
@rate_limit(max_attempts=3, window=300)  # 5分钟内最多3次
def forgot_password() -> tuple:
    """
    忘记密码 - 发送重置邮件
    ---
    tags:
      - Auth
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - email
            - captcha
          properties:
            email:
              type: string
              description: 用户邮箱
              example: "user@example.com"
            captcha:
              type: string
              description: 验证码
              example: "1234"
    responses:
      200:
        description: 如果邮箱存在，发送重置邮件
      400:
        description: 请求数据验证失败或验证码错误
    """
    from app.services.email_config_service import EmailConfigService
    from app.services.email_sender_service import EmailSenderService
    from app.utils.captcha import CaptchaService

    data = request.get_json()

    if not data:
        return error_response('请求体不能为空', code=400)

    email = data.get('email', '').strip().lower()
    captcha = data.get('captcha', '').strip()

    if not email:
        return error_response('请提供邮箱地址', code=400)

    # 验证验证码
    client_ip = request.remote_addr or 'unknown'
    captcha_token = f"auth:forgot_password:{client_ip}"
    is_valid, error_msg = CaptchaService.verify_captcha(captcha_token, captcha)

    if not is_valid:
        return error_response(error_msg, code=400)

    # 查找用户（不泄露用户是否存在）
    user = User.query.filter_by(email=email).first()

    # 即使用户不存在，也返回相同的消息（安全考虑）
    if not user:
        return success_response(
            message='如果该邮箱已注册，重置邮件将发送至您的邮箱'
        )

    # 检查邮件服务是否启用
    if not EmailConfigService.is_email_enabled():
        return success_response(
            message='如果该邮箱已注册，重置邮件将发送至您的邮箱'
        )

    # 生成重置令牌
    reset_token = user.generate_reset_token()

    try:
        reset_link = f"{EmailConfigService.get_frontend_url()}/reset-password?token={reset_token}"
        EmailSenderService.send_email_quick(
            to_email=user.email,
            to_name=user.name,
            template_key='password_reset',
            template_data={
                'user_name': user.name,
                'reset_link': reset_link
            }
        )

        return success_response(
            message='如果该邮箱已注册，重置邮件将发送至您的邮箱'
        )
    except Exception as e:
        logger.error(f'发送密码重置邮件失败: {str(e)}')
        return success_response(
            message='如果该邮箱已注册，重置邮件将发送至您的邮箱'
        )


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password() -> tuple:
    """
    重置密码
    ---
    tags:
      - Auth
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - token
            - new_password
          properties:
            token:
              type: string
              description: 重置令牌
              example: "reset_token_here"
            new_password:
              type: string
              description: 新密码（至少8位，包含大小写字母和数字）
              example: "NewPassword123"
    responses:
      200:
        description: 密码重置成功
      400:
        description: 令牌无效或已过期，或密码不符合要求
    """
    data = request.get_json()
    
    if not data:
        return error_response('请求体不能为空', code=400)
    
    # 使用 Schema 验证请求参数（包含密码强度验证）
    try:
        validated_data = password_reset_confirm_schema.load(data)
    except ValidationError as err:
        return validation_error_response(err.messages)
    
    token = validated_data.get('token')
    new_password = validated_data.get('new_password')
    
    # 查找具有该重置令牌的用户
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.verify_reset_token(token):
        return error_response('重置令牌无效或已过期', code=400, error='invalid_token')
    
    # 重置密码
    try:
        user.set_password(new_password)
        user.clear_reset_token()
        
        # 发送密码重置通知邮件
        from app.services.email_config_service import EmailConfigService
        from app.services.email_sender_service import EmailSenderService
        
        if EmailConfigService.is_email_enabled():
            try:
                EmailSenderService.send_email_quick(
                    to_email=user.email,
                    to_name=user.name,
                    template_key='password_changed',
                    template_data={
                        'user_name': user.name,
                        'operation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                )
            except Exception as e:
                logger.error(f'发送密码重置通知邮件失败: {str(e)}')
        
        return success_response(
            message='密码重置成功，请使用新密码登录'
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f'密码重置失败: {str(e)}')
        return error_response('密码重置失败，请稍后重试', code=500)
