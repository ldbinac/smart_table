"""
用户数据序列化 Schema
提供用户相关数据的验证和序列化功能
"""
import re
from marshmallow import Schema, fields, validate, post_load, validates, ValidationError

from app.models.user import UserRole, UserStatus


class UserSchema(Schema):
    """
    用户基础 Schema
    用于序列化用户数据
    """
    id = fields.String(dump_only=True, description='用户唯一标识')
    email = fields.Email(required=True, description='邮箱地址')
    name = fields.String(required=True, validate=validate.Length(min=1, max=100), description='用户姓名')
    avatar = fields.String(allow_none=True, description='头像 URL')
    role = fields.String(dump_only=True, description='用户角色')
    status = fields.String(dump_only=True, description='用户状态')
    email_verified = fields.Boolean(dump_only=True, description='邮箱是否已验证')
    last_login_at = fields.DateTime(dump_only=True, description='最后登录时间')
    created_at = fields.DateTime(dump_only=True, description='创建时间')
    updated_at = fields.DateTime(dump_only=True, description='更新时间')


class UserRegistrationSchema(Schema):
    """
    用户注册 Schema
    验证用户注册时的输入数据
    """
    email = fields.Email(
        required=True,
        error_messages={'required': '邮箱地址不能为空', 'invalid': '邮箱地址格式不正确'},
        description='邮箱地址'
    )
    password = fields.String(
        required=True,
        load_only=True,
        error_messages={'required': '密码不能为空'},
        description='密码（至少8位，包含大小写字母和数字）'
    )
    name = fields.String(
        load_only=True,
        validate=validate.Length(min=1, max=100, error='姓名长度必须在 1-100 个字符之间'),
        allow_none=True,
        description='用户姓名'
    )
    username = fields.String(
        load_only=True,
        validate=validate.Length(min=1, max=100, error='用户名长度必须在 1-100 个字符之间'),
        allow_none=True,
        description='用户名'
    )
    captcha = fields.String(
        load_only=True,
        allow_none=True,
        description='验证码（可选）'
    )
    
    @validates('name')
    def validate_name(self, value):
        """验证姓名"""
        if not value or len(value.strip()) == 0:
            # 如果没有提供name，尝试从username获取
            if hasattr(self, 'context') and self.context.get('username'):
                return
            raise ValidationError('姓名不能为空')
    
    @post_load
    def process_data(self, data, **kwargs):
        """处理数据，确保name字段有值"""
        # 如果提供了username但没有提供name，使用username作为name
        if not data.get('name') and data.get('username'):
            data['name'] = data['username']
        # 如果提供了name但没有提供username，使用name作为username
        if not data.get('username') and data.get('name'):
            data['username'] = data['name']
        return data
    
    @validates('password')
    def validate_password_strength(self, value):
        """
        验证密码强度
        要求：至少8位，包含至少一个大写字母、一个小写字母和一个数字
        """
        if len(value) < 8:
            raise ValidationError('密码长度至少为 8 位')
        
        if not re.search(r'[A-Z]', value):
            raise ValidationError('密码必须包含至少一个大写字母')
        
        if not re.search(r'[a-z]', value):
            raise ValidationError('密码必须包含至少一个小写字母')
        
        if not re.search(r'\d', value):
            raise ValidationError('密码必须包含至少一个数字')


class UserLoginSchema(Schema):
    """
    用户登录 Schema
    验证用户登录时的输入数据
    """
    email = fields.Email(
        required=True,
        error_messages={'required': '邮箱地址不能为空', 'invalid': '邮箱地址格式不正确'},
        description='邮箱地址'
    )
    password = fields.String(
        required=True,
        load_only=True,
        error_messages={'required': '密码不能为空'},
        description='密码'
    )
    captcha = fields.String(
        load_only=True,
        allow_none=True,
        description='验证码（可选）'
    )


class UserUpdateSchema(Schema):
    """
    用户信息更新 Schema
    验证用户更新个人资料时的输入数据
    """
    name = fields.String(
        validate=validate.Length(min=1, max=100, error='姓名长度必须在 1-100 个字符之间'),
        allow_none=True,
        description='用户姓名'
    )
    avatar = fields.String(
        allow_none=True,
        validate=validate.Regexp(
            r'^https?://.*$',
            error='头像 URL 必须是有效的 http 或 https 链接'
        ),
        description='头像 URL'
    )


class ChangePasswordSchema(Schema):
    """
    修改密码 Schema
    验证用户修改密码时的输入数据
    """
    old_password = fields.String(
        required=True,
        load_only=True,
        error_messages={'required': '旧密码不能为空'},
        description='旧密码'
    )
    new_password = fields.String(
        required=True,
        load_only=True,
        error_messages={'required': '新密码不能为空'},
        description='新密码（至少8位，包含大小写字母和数字）'
    )
    
    @validates('new_password')
    def validate_new_password(self, value):
        """
        验证新密码强度
        """
        if len(value) < 8:
            raise ValidationError('新密码长度至少为 8 位')
        
        if not re.search(r'[A-Z]', value):
            raise ValidationError('新密码必须包含至少一个大写字母')
        
        if not re.search(r'[a-z]', value):
            raise ValidationError('新密码必须包含至少一个小写字母')
        
        if not re.search(r'\d', value):
            raise ValidationError('新密码必须包含至少一个数字')


class TokenRefreshSchema(Schema):
    """
    令牌刷新 Schema
    用于验证刷新令牌请求
    """
    refresh_token = fields.String(
        required=True,
        load_only=True,
        error_messages={'required': '刷新令牌不能为空'},
        description='刷新令牌'
    )


class TokenResponseSchema(Schema):
    """
    令牌响应 Schema
    用于序列化令牌响应数据
    """
    access_token = fields.String(description='访问令牌')
    refresh_token = fields.String(description='刷新令牌')
    token_type = fields.String(default='Bearer', description='令牌类型')
    expires_in = fields.Integer(description='访问令牌过期时间（秒）')


class UserResponseSchema(Schema):
    """
    用户响应 Schema
    用于序列化包含用户信息的响应数据
    """
    user = fields.Nested(UserSchema, description='用户信息')
    tokens = fields.Nested(TokenResponseSchema, description='令牌信息')


class UserProfileSchema(Schema):
    """
    用户资料 Schema
    用于序列化用户个人资料
    """
    id = fields.String(dump_only=True, description='用户唯一标识')
    email = fields.Email(dump_only=True, description='邮箱地址')
    name = fields.String(description='用户姓名')
    avatar = fields.String(allow_none=True, description='头像 URL')
    role = fields.String(dump_only=True, description='用户角色')
    status = fields.String(dump_only=True, description='用户状态')
    email_verified = fields.Boolean(dump_only=True, description='邮箱是否已验证')
    last_login_at = fields.DateTime(dump_only=True, description='最后登录时间')
    created_at = fields.DateTime(dump_only=True, description='创建时间')


class PasswordResetRequestSchema(Schema):
    """
    密码重置请求 Schema
    验证密码重置请求
    """
    email = fields.Email(
        required=True,
        error_messages={'required': '邮箱地址不能为空', 'invalid': '邮箱地址格式不正确'},
        description='注册时使用的邮箱地址'
    )


class PasswordResetConfirmSchema(Schema):
    """
    密码重置确认 Schema
    验证密码重置确认请求
    """
    token = fields.String(
        required=True,
        error_messages={'required': '重置令牌不能为空'},
        description='密码重置令牌'
    )
    new_password = fields.String(
        required=True,
        load_only=True,
        error_messages={'required': '新密码不能为空'},
        description='新密码'
    )
    
    @validates('new_password')
    def validate_new_password(self, value):
        """验证新密码强度"""
        if len(value) < 8:
            raise ValidationError('新密码长度至少为 8 位')
        
        if not re.search(r'[A-Z]', value):
            raise ValidationError('新密码必须包含至少一个大写字母')
        
        if not re.search(r'[a-z]', value):
            raise ValidationError('新密码必须包含至少一个小写字母')
        
        if not re.search(r'\d', value):
            raise ValidationError('新密码必须包含至少一个数字')


# 创建 Schema 实例（供直接使用）
user_schema = UserSchema()
users_schema = UserSchema(many=True)
user_registration_schema = UserRegistrationSchema()
user_login_schema = UserLoginSchema()
user_update_schema = UserUpdateSchema()
change_password_schema = ChangePasswordSchema()
token_response_schema = TokenResponseSchema()
user_response_schema = UserResponseSchema()
user_profile_schema = UserProfileSchema()
password_reset_request_schema = PasswordResetRequestSchema()
password_reset_confirm_schema = PasswordResetConfirmSchema()
