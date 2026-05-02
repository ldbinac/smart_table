"""
字段路由模块
处理 Field 的 CRUD 操作、排序管理和类型查询
"""
from flask import Blueprint, request, g

from app.services.field_service import FieldService
from app.services.table_service import TableService
from app.services.link_service import LinkService
from app.models.base import MemberRole
from app.models.field import FieldType
from app.utils.decorators import authenticate, jwt_required
from app.utils.response import (
    success_response, error_response, not_found_response, forbidden_response
)

fields_bp = Blueprint('fields', __name__)
# 禁用严格斜杠，允许带或不带斜杠的URL
fields_bp.strict_slashes = False


@fields_bp.route('/tables/<uuid:table_id>/fields', methods=['GET'])
@jwt_required
def get_fields(table_id) -> tuple:
    """
    获取表格中的所有字段
    ---
    tags:
      - Fields
    security:
      - Bearer: []
    parameters:
      - name: table_id
        in: path
        type: string
        required: true
        description: 表格 ID
    responses:
      200:
        description: 字段列表
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
def create_field(table_id) -> tuple:
    """
    在表格中创建新字段
    ---
    tags:
      - Fields
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
        schema:
          type: object
          required:
            - type
          properties:
            name:
              type: string
              description: 字段名称（可选，默认为"未命名字段"）
            type:
              type: string
              description: 字段类型（必填）
            description:
              type: string
              description: 描述（可选）
            is_required:
              type: boolean
              description: 是否必填（可选，默认 False）
            options:
              type: object
              description: 字段选项（可选，选择类型字段必填）
            config:
              type: object
              description: 字段配置（可选）
            defaultValue:
              type: object
              description: 字段默认值（可选）
    responses:
      201:
        description: 创建的字段详情
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
    result = FieldService.create_field(str(table_id), data, user_id)
    
    if not result['success']:
        return error_response(result['error'], code=400)
    
    return success_response(
        data=result['field'],
        message='字段创建成功',
        code=201
    )


@fields_bp.route('/fields/<uuid:field_id>', methods=['GET'])
@jwt_required
def get_field(field_id) -> tuple:
    """
    获取单个字段详情
    ---
    tags:
      - Fields
    security:
      - Bearer: []
    parameters:
      - name: field_id
        in: path
        type: string
        required: true
        description: 字段 ID
    responses:
      200:
        description: 字段详情
      403:
        description: 无权限访问
      404:
        description: 字段不存在
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
def update_field(field_id) -> tuple:
    """
    更新字段
    ---
    tags:
      - Fields
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
        schema:
          type: object
          properties:
            name:
              type: string
              description: 新名称（可选）
            description:
              type: string
              description: 新描述（可选）
            type:
              type: string
              description: 新类型（可选，需要满足类型转换规则）
            is_required:
              type: boolean
              description: 是否必填（可选）
            options:
              type: object
              description: 字段选项（可选）
            config:
              type: object
              description: 字段配置（可选）
            defaultValue:
              type: object
              description: 字段默认值（可选）
    responses:
      200:
        description: 更新后的字段详情
      400:
        description: 请求数据验证失败
      403:
        description: 无权限修改
      404:
        description: 字段不存在
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
    result = FieldService.update_field(str(field_id), data, user_id)
    
    if not result['success']:
        return error_response(result['error'], code=400)
    
    return success_response(
        data=result['field'],
        message='字段更新成功'
    )


@fields_bp.route('/fields/<uuid:field_id>', methods=['DELETE'])
@jwt_required
def delete_field(field_id) -> tuple:
    """
    删除字段
    ---
    tags:
      - Fields
    security:
      - Bearer: []
    description: 注意：主字段和系统字段类型不能被删除
    parameters:
      - name: field_id
        in: path
        type: string
        required: true
        description: 字段 ID
    responses:
      200:
        description: 删除成功
      400:
        description: 主字段或系统字段不能被删除
      403:
        description: 无权限删除
      404:
        description: 字段不存在
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not FieldService.check_permission(str(field_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限删除此字段')
    
    field = FieldService.get_field(str(field_id))
    if not field:
        return not_found_response('字段')
    
    result = FieldService.delete_field(str(field_id), user_id)
    
    if not result['success']:
        return error_response(result['error'], code=400)
    
    return success_response(message='字段删除成功')


@fields_bp.route('/fields/reorder', methods=['POST'])
@jwt_required
def reorder_fields() -> tuple:
    """
    批量重新排序字段
    ---
    tags:
      - Fields
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - table_id
            - orders
          properties:
            table_id:
              type: string
              description: 表格 ID
            orders:
              type: array
              description: 排序列表
              items:
                type: object
                properties:
                  field_id:
                    type: string
                    description: 字段 ID
                  order:
                    type: integer
                    description: 排序顺序
    responses:
      200:
        description: 排序成功
      400:
        description: 参数错误
      403:
        description: 无权限
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
def duplicate_field(field_id) -> tuple:
    """
    复制字段
    ---
    tags:
      - Fields
    security:
      - Bearer: []
    parameters:
      - name: field_id
        in: path
        type: string
        required: true
        description: 源字段 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            name:
              type: string
              description: 新字段名称
    responses:
      201:
        description: 字段复制成功
      403:
        description: 无权限
      404:
        description: 字段不存在
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
def get_field_types() -> tuple:
    """
    获取所有支持的字段类型信息
    ---
    tags:
      - Fields
    security:
      - Bearer: []
    responses:
      200:
        description: 字段类型列表
    """
    types = FieldService.get_all_field_types()
    
    return success_response(
        data=types,
        message='获取字段类型列表成功'
    )


@fields_bp.route('/fields/types/<field_type>', methods=['GET'])
@jwt_required
def get_field_type_detail(field_type) -> tuple:
    """
    获取特定字段类型的详细信息
    ---
    tags:
      - Fields
    security:
      - Bearer: []
    parameters:
      - name: field_type
        in: path
        type: string
        required: true
        description: 字段类型标识
    responses:
      200:
        description: 字段类型详细信息
    """
    type_info = FieldService.get_field_type_info(field_type)
    
    return success_response(
        data=type_info,
        message='获取字段类型详情成功'
    )


@fields_bp.route('/fields/<uuid:field_id>/validate', methods=['POST'])
@jwt_required
def validate_field_value(field_id) -> tuple:
    """
    验证字段值
    ---
    tags:
      - Fields
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
            - value
          properties:
            value:
              type: object
              description: 待验证的值
    responses:
      200:
        description: 验证通过
      400:
        description: 验证失败
      403:
        description: 无权限
      404:
        description: 字段不存在
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


# ==================== 关联字段 API ====================

@fields_bp.route('/fields/link', methods=['POST'])
@jwt_required
def create_link_field() -> tuple:
    """
    创建关联字段
    ---
    tags:
      - Fields
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - table_id
            - name
            - target_table_id
            - relationship_type
          properties:
            table_id:
              type: string
              description: 源表 ID
            name:
              type: string
              description: 字段名称
            target_table_id:
              type: string
              description: 目标表 ID
            relationship_type:
              type: string
              enum: ['one_to_one', 'one_to_many', 'many_to_one', 'many_to_many']
              description: 关联类型
            display_field_id:
              type: string
              description: 显示字段 ID
            bidirectional:
              type: boolean
              description: 是否双向关联
            description:
              type: string
              description: 字段描述
    responses:
      201:
        description: 创建的字段和关联关系详情
      400:
        description: 参数错误
      403:
        description: 无权限
    """
    user_id = g.current_user_id
    data = request.get_json() or {}
    
    # 验证必填字段
    table_id = data.get('table_id')
    target_table_id = data.get('target_table_id')
    relationship_type = data.get('relationship_type')
    
    if not table_id:
        return error_response('请提供表格ID', code=400)
    if not target_table_id:
        return error_response('请提供目标表ID', code=400)
    if not relationship_type:
        return error_response('请提供关联类型', code=400)
    valid_types = ['one_to_one', 'one_to_many', 'many_to_one', 'many_to_many']
    if relationship_type not in valid_types:
        return error_response(f'关联类型必须是: {", ".join(valid_types)}', code=400)
    
    if not TableService.check_permission(str(table_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限在此表格中创建字段')
    
    result = LinkService.create_link_field(str(table_id), data, user_id)
    
    if not result['success']:
        return error_response(result['error'], code=400)
    
    return success_response(
        data={
            'field': result['field'],
            'inverse_field': result.get('inverse_field'),
            'link_relation': result.get('link_relation')
        },
        message='关联字段创建成功',
        code=201
    )


@fields_bp.route('/fields/<uuid:field_id>/link', methods=['PUT'])
@jwt_required
def update_link_field(field_id) -> tuple:
    """
    更新关联字段配置
    ---
    tags:
      - Fields
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
        schema:
          type: object
          properties:
            relationship_type:
              type: string
              enum: ['one_to_one', 'one_to_many', 'many_to_one']
              description: 关联类型
            display_field_id:
              type: string
              description: 显示字段 ID
            bidirectional:
              type: boolean
              description: 是否双向关联
            name:
              type: string
              description: 字段名称
            description:
              type: string
              description: 字段描述
    responses:
      200:
        description: 更新后的字段详情
      400:
        description: 参数错误或不是关联字段
      403:
        description: 无权限
      404:
        description: 字段不存在
    """
    user_id = g.current_user_id
    
    # 检查权限
    if not FieldService.check_permission(str(field_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限修改此字段')
    
    field = FieldService.get_field(str(field_id))
    if not field:
        return not_found_response('字段')
    
    # 检查是否为关联字段（支持 'link' 和 'link_to_record' 两种类型）
    if field.type not in [FieldType.LINK_TO_RECORD.value, 'link']:
        return error_response('该字段不是关联字段', code=400)
    
    data = request.get_json() or {}
    
    try:
        # 1. 更新字段基本信息
        field_data = {}
        if 'name' in data:
            field_data['name'] = data['name']
        if 'description' in data:
            field_data['description'] = data['description']
        if 'display_field_id' in data:
            field_data['config'] = field.config or {}
            field_data['config']['displayFieldId'] = data['display_field_id']
        
        if field_data:
            result = FieldService.update_field(str(field_id), field_data, user_id)
            if not result['success']:
                return error_response(result['error'], code=400)
        
        if 'relationship_type' in data:
            rel_result = LinkService.update_link_field_relationship(
                str(field_id),
                data['relationship_type'],
                user_id
            )
            if not rel_result['success']:
                return error_response(rel_result['error'], code=400)
        elif 'bidirectional' in data:
            link_relation = LinkService.get_link_relation_by_field(str(field_id))
            if link_relation:
                link_data = {'bidirectional': data['bidirectional']}
                LinkService.update_link_relation(str(link_relation.id), link_data)

        updated_field = FieldService.get_field(str(field_id))
        
        return success_response(
            data=updated_field.to_dict(),
            message='关联字段更新成功'
        )
    
    except Exception as e:
        return error_response(f'更新关联字段失败: {str(e)}', code=500)


@fields_bp.route('/fields/<uuid:field_id>/link', methods=['DELETE'])
@jwt_required
def delete_link_field(field_id) -> tuple:
    """
    删除关联字段
    ---
    tags:
      - Fields
    security:
      - Bearer: []
    description: 同时删除关联的 LinkRelation 记录
    parameters:
      - name: field_id
        in: path
        type: string
        required: true
        description: 字段 ID
    responses:
      200:
        description: 删除成功
      403:
        description: 无权限
      404:
        description: 字段不存在
      500:
        description: 删除失败
    """
    user_id = g.current_user_id
    
    # 检查权限
    if not FieldService.check_permission(str(field_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限删除此字段')
    
    field = FieldService.get_field(str(field_id))
    if not field:
        return not_found_response('字段')
    
    try:
        # 1. 删除关联关系（会级联删除关联值）
        link_relation = LinkService.get_link_relation_by_field(str(field_id))
        if link_relation and link_relation[0]:
            LinkService.delete_link_relation(link_relation[0].id)
        
        # 2. 删除字段
        result = FieldService.delete_field(str(field_id), user_id)
        if not result['success']:
            return error_response(result['error'], code=400)
        
        return success_response(message='关联字段删除成功')
    
    except Exception as e:
        return error_response(f'删除关联字段失败: {str(e)}', code=500)


@fields_bp.route('/tables/<uuid:table_id>/links', methods=['GET'])
@jwt_required
def get_table_link_relations(table_id) -> tuple:
    """
    获取表格的所有关联关系
    ---
    tags:
      - Fields
    security:
      - Bearer: []
    parameters:
      - name: table_id
        in: path
        type: string
        required: true
        description: 表格 ID
    responses:
      200:
        description: 关联关系列表
      403:
        description: 无权限
      500:
        description: 获取失败
    """
    user_id = g.current_user_id
    
    # 检查权限
    if not TableService.check_permission(str(table_id), user_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限访问此表格')
    
    try:
        link_relations = LinkService.get_table_link_relations(str(table_id))
        
        return success_response(
            data=[link.to_dict(include_related=True) for link in link_relations],
            message='获取关联关系列表成功'
        )
    
    except Exception as e:
        return error_response(f'获取关联关系列表失败: {str(e)}', code=500)
