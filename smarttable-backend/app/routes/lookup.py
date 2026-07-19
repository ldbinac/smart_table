"""
查找字段路由模块

提供三个接口：
- POST /tables/<table_id>/fields/lookup：创建查找字段
- PUT /fields/<field_id>/lookup：更新查找字段
- POST /fields/<field_id>/lookup/preview：预览查找结果
"""
from flask import Blueprint, request, g

from app.services.field_service import FieldService
from app.services.lookup_service import LookupService
from app.services.table_service import TableService
from app.models.base import MemberRole
from app.models.field import FieldType
from app.utils.decorators import jwt_required
from app.utils.response import success_response, error_response

lookup_bp = Blueprint('lookup', __name__)
lookup_bp.strict_slashes = False


@lookup_bp.route('/tables/<table_id>/fields/lookup', methods=['POST'])
@jwt_required
def create_lookup_field(table_id) -> tuple:
    """
    创建查找字段
    ---
    tags:
      - Lookup
    security:
      - Bearer: []
    parameters:
      - name: table_id
        in: path
        type: string
        required: true
        description: 表格 ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
            - config
          properties:
            name:
              type: string
              description: 字段名称
            description:
              type: string
              description: 字段描述
            config:
              type: object
              description: 查找字段配置
    responses:
      200:
        description: 创建成功
      400:
        description: 参数错误
      403:
        description: 无权限
      404:
        description: 表格不存在
    """
    # 校验表格存在
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)

    # 权限校验
    if not TableService.check_permission(str(table_id), g.current_user_id, MemberRole.EDITOR):
        return error_response('无权创建字段', 403)

    json_data = request.get_json() or {}
    name = json_data.get('name')
    description = json_data.get('description')
    config = json_data.get('config') or {}

    if not name or not name.strip():
        return error_response('字段名称不能为空', 400)

    # 配置校验
    is_valid, error_msg = LookupService.validate_config(config, str(table_id))
    if not is_valid:
        return error_response(error_msg, 400)

    result = FieldService.create_field(
        str(table_id),
        {
            'name': name,
            'type': FieldType.LOOKUP.value,
            'description': description,
            'config': config,
        },
        user_id=g.current_user_id,
    )

    if not result.get('success'):
        return error_response(result.get('error', '创建查找字段失败'), 400)

    return success_response(data=result['field'], message='创建查找字段成功')


@lookup_bp.route('/fields/<field_id>/lookup', methods=['PUT'])
@jwt_required
def update_lookup_field(field_id) -> tuple:
    """
    更新查找字段
    ---
    tags:
      - Lookup
    security:
      - Bearer: []
    parameters:
      - name: field_id
        in: path
        type: string
        required: true
        description: 字段 ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            description:
              type: string
            config:
              type: object
    responses:
      200:
        description: 更新成功
      400:
        description: 参数错误
      403:
        description: 无权限
      404:
        description: 字段不存在
    """
    field = FieldService.get_field(field_id)
    if not field:
        return error_response('字段不存在', 404)

    # 权限校验
    if not TableService.check_permission(str(field.table_id), g.current_user_id, MemberRole.EDITOR):
        return error_response('无权更新字段', 403)

    json_data = request.get_json() or {}
    name = json_data.get('name')
    description = json_data.get('description')
    config = json_data.get('config') or {}

    # 配置校验
    is_valid, error_msg = LookupService.validate_config(config, str(field.table_id))
    if not is_valid:
        return error_response(error_msg, 400)

    update_data = {'config': config}
    if name is not None:
        update_data['name'] = name
    if description is not None:
        update_data['description'] = description

    result = FieldService.update_field(
        str(field_id),
        update_data,
        user_id=g.current_user_id,
    )

    if not result.get('success'):
        return error_response(result.get('error', '更新查找字段失败'), 400)

    return success_response(data=result['field'], message='更新查找字段成功')


@lookup_bp.route('/fields/<field_id>/lookup/preview', methods=['POST'])
@jwt_required
def preview_lookup_field(field_id) -> tuple:
    """
    预览查找结果
    ---
    tags:
      - Lookup
    security:
      - Bearer: []
    parameters:
      - name: field_id
        in: path
        type: string
        required: true
        description: 字段 ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - record_id
          properties:
            record_id:
              type: string
              description: 当前表记录 ID
            config:
              type: object
              description: 可选，未提供则使用字段当前配置
    responses:
      200:
        description: 预览结果
      403:
        description: 无权限
      404:
        description: 字段不存在
    """
    field = FieldService.get_field(field_id)
    if not field:
        return error_response('字段不存在', 404)

    # 权限校验（VIEWER 即可）
    if not TableService.check_permission(str(field.table_id), g.current_user_id, MemberRole.VIEWER):
        return error_response('无权访问该字段', 403)

    json_data = request.get_json() or {}
    record_id = json_data.get('record_id')
    config = json_data.get('config')

    if not record_id:
        return error_response('record_id 不能为空', 400)

    # 未提供 config 则使用字段当前配置
    use_config = config if config else (field.config or {})

    result = LookupService.preview_lookup_value(record_id, use_config)
    return success_response(data={'value': result})
