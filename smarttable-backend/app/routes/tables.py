"""
表格路由模块
处理 Table 的 CRUD 操作和排序
"""
from flask import Blueprint, request, g

from app.services.table_service import TableService
from app.services.base_service import BaseService
from app.models.base import MemberRole
from app.utils.decorators import jwt_required
from app.utils.response import (
    success_response, error_response, not_found_response, forbidden_response
)

tables_bp = Blueprint('tables', __name__)
# 禁用严格斜杠，允许带或不带斜杠的URL
tables_bp.strict_slashes = False


@tables_bp.route('/bases/<uuid:base_id>/tables', methods=['GET'])
@jwt_required
def get_tables(base_id) -> tuple:
    """
    获取基础数据中的所有表格
    ---
    tags:
      - Tables
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: 基础数据 ID
    responses:
      200:
        description: 表格列表
    """
    user_id = g.current_user_id
    
    # 检查权限
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限访问此基础数据')
    
    tables = TableService.get_all_tables(str(base_id))
    
    # 转换为字典列表
    tables_data = [table.to_dict(include_stats=True) for table in tables]
    
    return success_response(
        data=tables_data,
        message='获取表格列表成功'
    )


@tables_bp.route('/bases/<uuid:base_id>/tables', methods=['POST'])
@jwt_required
def create_table(base_id) -> tuple:
    """
    在基础数据中创建新表格
    ---
    tags:
      - Tables
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: 基础数据 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            name:
              type: string
              description: 表格名称（可选，默认为"未命名表格"）
            description:
              type: string
              description: 描述（可选）
            primary_field_name:
              type: string
              description: 主字段名称（可选，默认为"名称"）
            create_default_fields:
              type: boolean
              description: 是否创建默认字段（可选，默认为true。从模板创建时为false）
    responses:
      201:
        description: 创建的表格详情
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限在此基础数据中创建表格')
    
    data = request.get_json() or {}
    
    # 验证名称长度
    if 'name' in data:
        name = data['name'].strip()
        if len(name) > 100:
            return error_response('表格名称不能超过100个字符', code=400)
        data['name'] = name
    
    # 获取 create_default_fields 参数，默认为 True
    create_default_fields = data.pop('create_default_fields', True)
    
    # 创建表格
    table = TableService.create_table(
        str(base_id), 
        data, 
        create_default_fields=create_default_fields
    )
    
    return success_response(
        data=table.to_dict(include_stats=True),
        message='表格创建成功',
        code=201
    )


@tables_bp.route('/tables/<uuid:table_id>', methods=['GET'])
@jwt_required
def get_table(table_id) -> tuple:
    """
    获取单个表格详情
    ---
    tags:
      - Tables
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
        description: 表格详情
    """
    user_id = g.current_user_id
    
    # 检查权限
    if not TableService.check_permission(str(table_id), user_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限访问此表格')
    
    table = TableService.get_table(str(table_id))
    if not table:
        return not_found_response('表格')
    
    return success_response(
        data=table.to_dict(include_stats=True),
        message='获取表格成功'
    )


@tables_bp.route('/tables/<uuid:table_id>', methods=['PUT'])
@jwt_required
def update_table(table_id) -> tuple:
    """
    更新表格
    ---
    tags:
      - Tables
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
          properties:
            name:
              type: string
              description: 新名称（可选）
            description:
              type: string
              description: 新描述（可选）
    responses:
      200:
        description: 更新后的表格详情
      400:
        description: 请求数据验证失败
      403:
        description: 无权限修改
      404:
        description: 表格不存在
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not TableService.check_permission(str(table_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限修改此表格')
    
    data = request.get_json() or {}
    
    # 验证名称长度
    if 'name' in data:
        name = data['name'].strip()
        if len(name) > 100:
            return error_response('表格名称不能超过100个字符', code=400)
        data['name'] = name
    
    table = TableService.update_table(str(table_id), data)
    if not table:
        return not_found_response('表格')
    
    return success_response(
        data=table.to_dict(include_stats=True),
        message='表格更新成功'
    )


@tables_bp.route('/tables/<uuid:table_id>', methods=['DELETE'])
@jwt_required
def delete_table(table_id) -> tuple:
    """
    删除表格（级联删除关联的字段、记录、视图等）
    ---
    tags:
      - Tables
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
        description: 删除成功
      403:
        description: 无权限删除
      404:
        description: 表格不存在
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not TableService.check_permission(str(table_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限删除此表格')
    
    table = TableService.get_table(str(table_id))
    if not table:
        return not_found_response('表格')
    
    success = TableService.delete_table(str(table_id))
    if not success:
        return error_response('删除失败，请稍后重试', code=500)
    
    return success_response(message='表格删除成功')


@tables_bp.route('/bases/<uuid:base_id>/tables/reorder', methods=['POST'])
@jwt_required
def reorder_tables(base_id) -> tuple:
    """
    批量重新排序表格
    ---
    tags:
      - Tables
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: 基础数据 ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - orders
          properties:
            orders:
              type: array
              description: 排序列表，每个元素包含 table_id 和 order
              items:
                type: object
                properties:
                  table_id:
                    type: string
                    description: 表格ID
                  order:
                    type: integer
                    description: 排序序号
    responses:
      200:
        description: 排序成功
      400:
        description: 请求数据验证失败
      403:
        description: 无权限修改
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限修改此基础数据')
    
    data = request.get_json() or {}
    table_orders = data.get('orders', [])
    
    if not table_orders:
        return error_response('请提供排序数据', code=400)
    
    success = TableService.reorder_tables(str(base_id), table_orders)
    if not success:
        return error_response('排序失败，请稍后重试', code=500)
    
    return success_response(message='表格排序更新成功')


@tables_bp.route('/tables/<uuid:table_id>/duplicate', methods=['POST'])
@jwt_required
def duplicate_table(table_id) -> tuple:
    """
    复制表格（包括字段结构，不包括记录数据）
    ---
    tags:
      - Tables
    security:
      - Bearer: []
    parameters:
      - name: table_id
        in: path
        type: string
        required: true
        description: 源表格 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            name:
              type: string
              description: 新表格名称（可选）
    responses:
      201:
        description: 新创建的表格详情
      403:
        description: 无权限复制
      404:
        description: 表格不存在
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not TableService.check_permission(str(table_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限复制此表格')
    
    source_table = TableService.get_table(str(table_id))
    if not source_table:
        return not_found_response('表格')
    
    data = request.get_json() or {}
    new_name = data.get('name')
    
    new_table = TableService.duplicate_table(str(table_id), new_name)
    if not new_table:
        return error_response('复制失败，请稍后重试', code=500)
    
    return success_response(
        data=new_table.to_dict(include_stats=True),
        message='表格复制成功',
        code=201
    )
