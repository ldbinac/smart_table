"""
记录相关 Schema 定义
"""
from marshmallow import Schema, fields


class RecordCreateSchema(Schema):
    """记录创建验证模式"""
    values = fields.Dict(required=True, error_messages={'required': '字段值不能为空'})


class RecordUpdateSchema(Schema):
    """记录更新验证模式"""
    values = fields.Dict(required=True, error_messages={'required': '字段值不能为空'})


class BatchCreateSchema(Schema):
    """批量创建验证模式"""
    records = fields.List(fields.Dict(), required=True, error_messages={'required': '记录列表不能为空'})


class BatchUpdateSchema(Schema):
    """批量更新验证模式"""
    record_ids = fields.List(fields.String(), required=True, error_messages={'required': '记录ID列表不能为空'})
    values = fields.Dict(required=True, error_messages={'required': '字段值不能为空'})


record_create_schema = RecordCreateSchema()
record_update_schema = RecordUpdateSchema()
batch_create_schema = BatchCreateSchema()
batch_update_schema = BatchUpdateSchema()
