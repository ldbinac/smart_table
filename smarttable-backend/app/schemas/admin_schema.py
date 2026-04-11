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


user_create_schema = UserCreateSchema()
user_update_schema = UserUpdateSchema()
user_status_update_schema = UserStatusUpdateSchema()
password_reset_schema = PasswordResetSchema()
system_config_update_schema = SystemConfigUpdateSchema()
system_config_batch_update_schema = SystemConfigBatchUpdateSchema()
