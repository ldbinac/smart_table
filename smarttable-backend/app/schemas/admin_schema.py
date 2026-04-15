"""
管理员相关 Schema 定义
"""
from marshmallow import Schema, fields, validate


class UserCreateSchema(Schema):
    """用户创建 Schema"""
    email = fields.Email(required=True, description='邮箱地址')
    password = fields.String(required=True, description='密码')
    name = fields.String(required=True, validate=validate.Length(min=1, max=100), description='用户姓名')
    role = fields.String(load_default='editor', description='用户角色')


class UserUpdateSchema(Schema):
    """用户更新 Schema"""
    email = fields.Email(allow_none=True, description='邮箱地址')
    name = fields.String(allow_none=True, validate=validate.Length(min=1, max=100), description='用户姓名')
    role = fields.String(allow_none=True, description='用户角色')
    status = fields.String(allow_none=True, description='用户状态')


class UserStatusUpdateSchema(Schema):
    """用户状态更新 Schema"""
    status = fields.String(required=True, description='用户状态')


class PasswordResetSchema(Schema):
    """密码重置 Schema"""
    temporary_password = fields.String(allow_none=True, description='临时密码')


class SystemConfigUpdateSchema(Schema):
    """系统配置更新 Schema"""
    key = fields.String(required=True, description='配置键')
    value = fields.Raw(required=True, description='配置值')
    group = fields.String(allow_none=True, description='配置分组')
    description = fields.String(allow_none=True, description='配置描述')


class SystemConfigBatchUpdateSchema(Schema):
    """系统配置批量更新 Schema"""
    configs = fields.List(fields.Nested(SystemConfigUpdateSchema), required=True, description='配置列表')


class EmailConfigVerifySchema(Schema):
    """邮件配置验证 Schema"""
    smtp_host = fields.String(required=True, description='SMTP 服务器地址')
    smtp_port = fields.Integer(required=True, validate=validate.Range(min=1, max=65535), description='SMTP 端口')
    smtp_username = fields.String(required=True, description='SMTP 用户名')
    smtp_password = fields.String(required=True, description='SMTP 密码')
    smtp_use_tls = fields.Boolean(load_default=True, description='是否使用 TLS')
    smtp_use_ssl = fields.Boolean(load_default=False, description='是否使用 SSL')
    from_email = fields.Email(required=True, description='发件人邮箱')
    from_name = fields.String(allow_none=True, description='发件人名称')


class EmailConfigTestSchema(Schema):
    """邮件配置测试 Schema"""
    smtp_host = fields.String(required=True, description='SMTP 服务器地址')
    smtp_port = fields.Integer(required=True, validate=validate.Range(min=1, max=65535), description='SMTP 端口')
    smtp_username = fields.String(required=True, description='SMTP 用户名')
    smtp_password = fields.String(required=True, description='SMTP 密码')
    smtp_use_tls = fields.Boolean(load_default=True, description='是否使用 TLS')
    smtp_use_ssl = fields.Boolean(load_default=False, description='是否使用 SSL')
    from_email = fields.Email(required=True, description='发件人邮箱')
    from_name = fields.String(allow_none=True, description='发件人名称')
    test_email = fields.Email(required=True, description='测试邮件接收地址')


user_create_schema = UserCreateSchema()
user_update_schema = UserUpdateSchema()
user_status_update_schema = UserStatusUpdateSchema()
password_reset_schema = PasswordResetSchema()
system_config_update_schema = SystemConfigUpdateSchema()
system_config_batch_update_schema = SystemConfigBatchUpdateSchema()
email_config_verify_schema = EmailConfigVerifySchema()
email_config_test_schema = EmailConfigTestSchema()
