"""
记录管理路由模块
"""
from flask import Blueprint, request, g
from marshmallow import Schema, fields, validate

from app.services.record_service import RecordService
from app.services.table_service import TableService
from app.services.formula_service import FormulaService
from app.utils.response import success_response, error_response, paginated_response
from app.utils.decorators import jwt_required, role_required

records_bp = Blueprint('records', __name__)
# 禁用严格斜杠，允许带或不带斜杠的URL
records_bp.strict_slashes = False


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


# 初始化验证模式
record_create_schema = RecordCreateSchema()
record_update_schema = RecordUpdateSchema()
batch_create_schema = BatchCreateSchema()
batch_update_schema = BatchUpdateSchema()


@records_bp.route('/tables/<table_id>/records', methods=['GET'])
@jwt_required
@role_required(['owner', 'admin', 'editor', 'commenter', 'viewer'])
def get_records(table_id):
    """
    获取表格记录列表
    
    支持分页和搜索
    """
    # 检查表格是否存在
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    
    # 限制每页数量
    if per_page > 100:
        per_page = 100
    
    try:
        if search:
            # 搜索记录
            records = RecordService.search_records(table_id, search)
            total = len(records)
            # 手动分页
            start = (page - 1) * per_page
            end = start + per_page
            records = records[start:end]
        else:
            # 分页查询
            records, total = RecordService.get_table_records(
                table_id, page=page, per_page=per_page
            )
        
        # 序列化记录数据
        items = []
        for record in records:
            item = record.to_dict()
            # 如果有公式字段，计算公式值
            item['computed_values'] = FormulaService.compute_record_formulas(
                table_id, record.values
            )
            items.append(item)
        
        return paginated_response(items, total, page, per_page)
    
    except Exception as e:
        return error_response(f'获取记录列表失败: {str(e)}', 500)


@records_bp.route('/tables/<table_id>/records', methods=['POST'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def create_record(table_id):
    """
    创建记录
    """
    # 检查表格是否存在
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)
    
    # 验证请求数据
    json_data = request.get_json()
    if not json_data:
        return error_response('请求数据不能为空', 400)
    
    errors = record_create_schema.validate(json_data)
    if errors:
        return error_response('数据验证失败', 400, errors)
    
    try:
        # 创建记录
        record = RecordService.create_record(
            table_id=table_id,
            values=json_data['values'],
            created_by=g.current_user.id
        )
        
        result = record.to_dict()
        # 计算公式值
        result['computed_values'] = FormulaService.compute_record_formulas(
            table_id, record.values
        )
        
        return success_response(result, '记录创建成功', 201)
    
    except Exception as e:
        return error_response(f'创建记录失败: {str(e)}', 500)


@records_bp.route('/tables/<table_id>/records/batch', methods=['POST'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def batch_create_records(table_id):
    """
    批量创建记录
    """
    # 检查表格是否存在
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)
    
    # 验证请求数据
    json_data = request.get_json()
    if not json_data:
        return error_response('请求数据不能为空', 400)
    
    errors = batch_create_schema.validate(json_data)
    if errors:
        return error_response('数据验证失败', 400, errors)
    
    records_data = json_data.get('records', [])
    if len(records_data) > 1000:
        return error_response('单次批量创建记录数量不能超过1000条', 400)
    
    try:
        created_records = []
        for record_data in records_data:
            record = RecordService.create_record(
                table_id=table_id,
                values=record_data.get('values', {}),
                created_by=g.current_user.id
            )
            created_records.append(record.to_dict())
        
        return success_response({
            'created_count': len(created_records),
            'records': created_records
        }, f'成功创建 {len(created_records)} 条记录')
    
    except Exception as e:
        return error_response(f'批量创建记录失败: {str(e)}', 500)


@records_bp.route('/records/<record_id>', methods=['GET'])
@jwt_required
@role_required(['owner', 'admin', 'editor', 'commenter', 'viewer'])
def get_record(record_id):
    """
    获取记录详情
    """
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)
    
    try:
        result = record.to_dict()
        # 计算公式值
        result['computed_values'] = FormulaService.compute_record_formulas(
            record.table_id, record.values
        )
        
        return success_response(result)
    except Exception as e:
        return error_response(f'获取记录详情失败: {str(e)}', 500)


@records_bp.route('/records/<record_id>', methods=['PUT'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def update_record(record_id):
    """
    更新记录
    """
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)
    
    # 验证请求数据
    json_data = request.get_json()
    if not json_data:
        return error_response('请求数据不能为空', 400)
    
    errors = record_update_schema.validate(json_data)
    if errors:
        return error_response('数据验证失败', 400, errors)
    
    try:
        record = RecordService.update_record(
            record=record,
            values=json_data['values'],
            updated_by=g.current_user.id
        )
        
        result = record.to_dict()
        # 计算公式值
        result['computed_values'] = FormulaService.compute_record_formulas(
            record.table_id, record.values
        )
        
        return success_response(result, '记录更新成功')
    
    except Exception as e:
        return error_response(f'更新记录失败: {str(e)}', 500)


@records_bp.route('/records/batch', methods=['PUT'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def batch_update_records():
    """
    批量更新记录
    """
    # 验证请求数据
    json_data = request.get_json()
    if not json_data:
        return error_response('请求数据不能为空', 400)
    
    errors = batch_update_schema.validate(json_data)
    if errors:
        return error_response('数据验证失败', 400, errors)
    
    record_ids = json_data.get('record_ids', [])
    values = json_data.get('values', {})
    
    if len(record_ids) > 1000:
        return error_response('单次批量更新记录数量不能超过1000条', 400)
    
    try:
        updated_count = 0
        failed_ids = []
        
        for record_id in record_ids:
            record = RecordService.get_record_by_id(record_id)
            if record:
                RecordService.update_record(
                    record=record,
                    values=values,
                    updated_by=g.current_user.id
                )
                updated_count += 1
            else:
                failed_ids.append(record_id)
        
        return success_response({
            'updated_count': updated_count,
            'failed_ids': failed_ids
        }, f'成功更新 {updated_count} 条记录')
    
    except Exception as e:
        return error_response(f'批量更新记录失败: {str(e)}', 500)


@records_bp.route('/records/<record_id>', methods=['DELETE'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def delete_record(record_id):
    """
    删除记录
    """
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)
    
    try:
        success = RecordService.delete_record(record)
        if success:
            return success_response(None, '记录删除成功')
        else:
            return error_response('删除记录失败', 500)
    
    except Exception as e:
        return error_response(f'删除记录失败: {str(e)}', 500)


@records_bp.route('/records/batch', methods=['DELETE'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def batch_delete_records():
    """
    批量删除记录
    """
    # 验证请求数据
    json_data = request.get_json()
    if not json_data:
        return error_response('请求数据不能为空', 400)
    
    record_ids = json_data.get('record_ids', [])
    if not record_ids:
        return error_response('记录ID列表不能为空', 400)
    
    if len(record_ids) > 1000:
        return error_response('单次批量删除记录数量不能超过1000条', 400)
    
    try:
        deleted_count = 0
        failed_ids = []
        
        for record_id in record_ids:
            record = RecordService.get_record_by_id(record_id)
            if record:
                success = RecordService.delete_record(record)
                if success:
                    deleted_count += 1
                else:
                    failed_ids.append(record_id)
            else:
                failed_ids.append(record_id)
        
        return success_response({
            'deleted_count': deleted_count,
            'failed_ids': failed_ids
        }, f'成功删除 {deleted_count} 条记录')
    
    except Exception as e:
        return error_response(f'批量删除记录失败: {str(e)}', 500)


@records_bp.route('/records/<record_id>/compute', methods=['POST'])
@jwt_required
@role_required(['owner', 'admin', 'editor', 'commenter', 'viewer'])
def compute_formulas(record_id):
    """
    计算记录的公式值
    
    用于实时预览公式计算结果
    """
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)
    
    # 获取预览值（可能包含未保存的修改）
    json_data = request.get_json() or {}
    preview_values = json_data.get('preview_values', {})
    
    # 合并预览值和实际值
    values = {**(record.values or {}), **preview_values}
    
    try:
        computed_values = FormulaService.compute_record_formulas(
            record.table_id, values
        )
        
        return success_response({
            'computed_values': computed_values
        })
    
    except Exception as e:
        return error_response(f'公式计算失败: {str(e)}', 500)
