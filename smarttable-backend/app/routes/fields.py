"""
字段路由模块
处理 Field 的 CRUD 操作、排序管理和类型查询
"""
from flask import Blueprint, request, g

from app.services.field_service import FieldService
from app.services.table_service import TableService
from app.models.base import MemberRole
from app.utils.decorators import jwt_required
from app.utils.response import (
    success_response, error_response, not_found_response, forbidden_response
)

fields_bp = Blueprint('fields', __name__)


@fields_bp.route('/tables/<uuid:table_id>/fields', methods=['GET'])
@jwt_required
def get_fields(table_id):
    """
    获取表格中的所有字段
    
    Args:
        table_id: 表格 ID
    
    Returns:
        字段列表
    """
    user_id = g.current_user_id
    
    # 检查权限
    if not TableService.check_permission(str(table_id), user_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限访问此表格')
    
    fields = FieldService.get_all_fields(str(table_id))
    
    # 转换为字典列表
    fields_data = [field.to_dict() for field in fields]
    
    return success_response(
        data=fields_data,
        message='获取字段列表成功'
    )


@fields_bp.route('/tables/<uuid:table_id>/fields', methods=['POST'])
@jwt_required
def create_field(table_id):
    """
    在表格中创建新字段
    
    Args:
        table_id: 表格 ID
    
    Request Body:
        - name: 字段名称（可选，默认为"未命名字段"）
        - type: 字段类型（必填）
        - description: 描述（可选）
        - is_required: 是否必填（可选，默认False）
        - options: 字段选项（可选，选择类型字段必填）
            例如：{"choices": [{"id": "1", "name": "选项1", "color": "red"}]}
        - config: 字段配置（可选）
    
    Returns:
        创建的字段详情
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not TableService.check_permission(str(table_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限在此表格中创建字段')
    
    data = request.get_json() or {}
    
    # 验证必填字段
    if 'type' not in data:
        return error_response('字段类型不能为空', code=400)
    
    # 验证名称长度
    if 'name' in data:
        name = data['name'].strip()
        if len(name) > 100:
            return error_response('字段名称不能超过100个字符', code=400)
        data['name'] = name
    
    # 创建字段
    result = FieldService.create_field(str(table_id), data)
    
    if not result['success']:
        return error_response(result['error'], code=400)
    
    return success_response(
        data=result['field'],
        message='字段创建成功',
        code=201
    )


@fields_bp.route('/fields/<uuid:field_id>', methods=['GET'])
@jwt_required
def get_field(field_id):
    """
    获取单个字段详情
    
    Args:
        field_id: 字段 ID
    
    Returns:
        字段详情
    """
    user_id = g.current_user_id
    
    # 检查权限
    if not FieldService.check_permission(str(field_id), user_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限访问此字段')
    
    field = FieldService.get_field(str(field_id))
    if not field:
        return not_found_response('字段')
    
    return success_response(
        data=field.to_dict(),
        message='获取字段成功'
    )


@fields_bp.route('/fields/<uuid:field_id>', methods=['PUT'])
@jwt_required
def update_field(field_id):
    """
    更新字段
    
    Args:
        field_id: 字段 ID
    
    Request Body:
        - name: 新名称（可选）
        - description: 新描述（可选）
        - type: 新类型（可选，需要满足类型转换规则）
        - is_required: 是否必填（可选）
        - options: 字段选项（可选）
        - config: 字段配置（可选）
    
    Returns:
        更新后的字段详情
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not FieldService.check_permission(str(field_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限修改此字段')
    
    data = request.get_json() or {}
    
    # 验证名称长度
    if 'name' in data:
        name = data['name'].strip()
        if len(name) > 100:
            return error_response('字段名称不能超过100个字符', code=400)
        data['name'] = name
    
    # 更新字段
    result = FieldService.update_field(str(field_id), data)
    
    if not result['success']:
        return error_response(result['error'], code=400)
    
    return success_response(
        data=result['field'],
        message='字段更新成功'
    )


@fields_bp.route('/fields/<uuid:field_id>', methods=['DELETE'])
@jwt_required
def delete_field(field_id):
    """
    删除字段
    
    注意：主字段和系统字段类型不能被删除
    
    Args:
        field_id: 字段 ID
    
    Returns:
        删除结果
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not FieldService.check_permission(str(field_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限删除此字段')
    
    field = FieldService.get_field(str(field_id))
    if not field:
        return not_found_response('字段')
    
    result = FieldService.delete_field(str(field_id))
    
    if not result['success']:
        return error_response(result['error'], code=400)
    
    return success_response(message='字段删除成功')


@fields_bp.route('/fields/reorder', methods=['POST'])
@jwt_required
def reorder_fields():
    """
    批量重新排序字段
    
    Request Body:
        - table_id: 表格 ID（必填）
        - orders: 排序列表，每个元素包含 field_id 和 order（必填）
          例如：[{"field_id": "xxx", "order": 0}, {"field_id": "yyy", "order": 1}]
    
    Returns:
        排序结果
    """
    user_id = g.current_user_id
    data = request.get_json() or {}
    
    table_id = data.get('table_id')
    field_orders = data.get('orders', [])
    
    if not table_id:
        return error_response('请提供表格ID', code=400)
    
    if not field_orders:
        return error_response('请提供排序数据', code=400)
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not TableService.check_permission(str(table_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限修改此表格')
    
    success = FieldService.reorder_fields(str(table_id), field_orders)
    
    if not success:
        return error_response('排序失败，请稍后重试', code=500)
    
    return success_response(message='字段排序更新成功')


@fields_bp.route('/fields/<uuid:field_id>/duplicate', methods=['POST'])
@jwt_required
def duplicate_field(field_id):
    """
    复制字段
    
    Args:
        field_id: 源字段 ID
    
    Request Body:
        - name: 新字段名称（可选）
    
    Returns:
        新创建的字段详情
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not FieldService.check_permission(str(field_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限复制此字段')
    
    source_field = FieldService.get_field(str(field_id))
    if not source_field:
        return not_found_response('字段')
    
    data = request.get_json() or {}
    new_name = data.get('name')
    
    result = FieldService.duplicate_field(str(field_id), new_name)
    
    if not result['success']:
        return error_response(result['error'], code=500)
    
    return success_response(
        data=result['field'],
        message='字段复制成功',
        code=201
    )


@fields_bp.route('/fields/types', methods=['GET'])
@jwt_required
def get_field_types():
    """
    获取所有支持的字段类型信息
    
    Returns:
        字段类型列表，包含名称、图标、描述和可配置项
    """
    types = FieldService.get_all_field_types()
    
    return success_response(
        data=types,
        message='获取字段类型列表成功'
    )


@fields_bp.route('/fields/types/<field_type>', methods=['GET'])
@jwt_required
def get_field_type_detail(field_type):
    """
    获取特定字段类型的详细信息
    
    Args:
        field_type: 字段类型标识
    
    Returns:
        字段类型详细信息
    """
    type_info = FieldService.get_field_type_info(field_type)
    
    return success_response(
        data=type_info,
        message='获取字段类型详情成功'
    )


@fields_bp.route('/fields/<uuid:field_id>/validate', methods=['POST'])
@jwt_required
def validate_field_value(field_id):
    """
    验证字段值
    
    Args:
        field_id: 字段 ID
    
    Request Body:
        - value: 待验证的值（必填）
    
    Returns:
        验证结果
    """
    user_id = g.current_user_id
    
    # 检查权限
    if not FieldService.check_permission(str(field_id), user_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限访问此字段')
    
    field = FieldService.get_field(str(field_id))
    if not field:
        return not_found_response('字段')
    
    data = request.get_json() or {}
    value = data.get('value')
    
    result = FieldService.validate_field_value(str(field_id), value)
    
    if result['success']:
        return success_response(message='验证通过')
    else:
        return error_response(result['error'], code=400)
