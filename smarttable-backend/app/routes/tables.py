"""
表格路由模块
处理 Table 的 CRUD 操作和排序
"""
from flask import Blueprint, request, g

from app.services.table_service import TableService
from app.services.table_folder_service import TableFolderService
from app.services.base_service import BaseService
from app.models.base import MemberRole
from app.utils.decorators import jwt_required, form_share_or_jwt
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
        return forbidden_response('no_permission_access_base')
    
    tables = TableService.get_all_tables(str(base_id))
    
    # 转换为字典列表
    tables_data = [table.to_dict(include_stats=True) for table in tables]
    
    return success_response(
        data=tables_data,
        message='fetched_table_list_successfully'
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
    
    # 检查权限（需要 ADMIN 或更高权限）
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.ADMIN):
        return forbidden_response('do_not_permission_create_table_base')
    
    data = request.get_json() or {}
    
    # 验证名称长度
    if 'name' in data:
        name = data['name'].strip()
        if len(name) > 100:
            return error_response('table_name_exceed_characters', code=400)
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
        message='table_created_successfully',
        code=201
    )


@tables_bp.route('/tables/<uuid:table_id>', methods=['GET'])
@form_share_or_jwt(table_param='table_id')
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
    table = TableService.get_table(str(table_id))
    if not table:
        return not_found_response('table')
    
    return success_response(
        data=table.to_dict(include_stats=True),
        message='fetched_table_successfully'
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
    
    # 检查权限（需要 ADMIN 或更高权限）
    if not TableService.check_permission(str(table_id), user_id, MemberRole.ADMIN):
        return forbidden_response('do_not_permission_modify_table')
    
    data = request.get_json() or {}

    # 验证名称长度
    if 'name' in data:
        name = data['name'].strip()
        if len(name) > 100:
            return error_response('table_name_exceed_characters', code=400)
        data['name'] = name

    table = TableService.get_table(str(table_id))
    if not table:
        return not_found_response('table')

    # 空串 folder_id 归一化为 None（表示移出文件夹），避免非法 UUID 触发数据库错误
    if 'folder_id' in data and not data['folder_id']:
        data['folder_id'] = None

    # 校验 folder_id 归属：文件夹必须属于该表所在 Base（置空 null 直接放行）
    if data.get('folder_id'):
        folder = TableFolderService.get_folder(data['folder_id'])
        if not folder or str(folder.base_id) != str(table.base_id):
            return error_response('folder_not_in_base', code=400)

    table = TableService.update_table(str(table_id), data)
    if not table:
        return not_found_response('table')
    
    return success_response(
        data=table.to_dict(include_stats=True),
        message='table_updated_successfully'
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
    
    # 检查权限（需要 ADMIN 或更高权限）
    if not TableService.check_permission(str(table_id), user_id, MemberRole.ADMIN):
        return forbidden_response('do_not_permission_delete_table')
    
    table = TableService.get_table(str(table_id))
    if not table:
        return not_found_response('table')
    
    success = TableService.delete_table(str(table_id))
    if not success:
        return error_response('deletion_failed_try_again_later', code=500)
    
    return success_response(message='table_deleted_successfully')


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
    
    # 检查权限（需要 ADMIN 或更高权限）
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.ADMIN):
        return forbidden_response('do_not_permission_modify_base')
    
    data = request.get_json() or {}
    table_orders = data.get('orders', [])
    
    if not table_orders:
        return error_response('provide_sort_data', code=400)
    
    success = TableService.reorder_tables(str(base_id), table_orders)
    if not success:
        return error_response('failed_reorder_try_again_later', code=500)
    
    return success_response(message='table_order_updated_successfully')


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
    
    # 检查权限（需要 ADMIN 或更高权限）
    if not TableService.check_permission(str(table_id), user_id, MemberRole.ADMIN):
        return forbidden_response('do_not_permission_copy_table')
    
    source_table = TableService.get_table(str(table_id))
    if not source_table:
        return not_found_response('table')
    
    data = request.get_json() or {}
    new_name = data.get('name')
    
    new_table = TableService.duplicate_table(str(table_id), new_name)
    if not new_table:
        return error_response('copy_failed_try_again_later', code=500)
    
    return success_response(
        data=new_table.to_dict(include_stats=True),
        message='table_copied_successfully',
        code=201
    )


# ==================== 数据表文件夹 ====================


@tables_bp.route('/bases/<uuid:base_id>/table-folders', methods=['GET'])
@jwt_required
def get_table_folders(base_id) -> tuple:
    """获取 Base 内所有数据表文件夹（按 order 排序）"""
    user_id = g.current_user_id

    if not BaseService.check_permission(str(base_id), user_id, MemberRole.VIEWER):
        return forbidden_response('no_permission_access_base')

    folders = TableFolderService.get_folders_by_base(str(base_id))
    return success_response(
        data=[folder.to_dict() for folder in folders],
        message='fetched_table_folder_list_successfully'
    )


@tables_bp.route('/bases/<uuid:base_id>/table-folders', methods=['POST'])
@jwt_required
def create_table_folder(base_id) -> tuple:
    """
    创建数据表文件夹（单层结构，不支持嵌套）
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
            - name
          properties:
            name:
              type: string
              description: 文件夹名称
    responses:
      201:
        description: 创建的文件夹详情
      400:
        description: 请求数据验证失败
      403:
        description: 无权限
    """
    user_id = g.current_user_id

    if not BaseService.check_permission(str(base_id), user_id, MemberRole.ADMIN):
        return forbidden_response('do_not_permission_modify_base')

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return error_response('folder_name_required', code=400)
    if len(name) > 100:
        return error_response('folder_name_exceed_characters', code=400)

    folder = TableFolderService.create_folder(str(base_id), {'name': name})
    return success_response(
        data=folder.to_dict(),
        message='table_folder_created_successfully',
        code=201
    )


@tables_bp.route('/table-folders/<uuid:folder_id>', methods=['PUT'])
@jwt_required
def update_table_folder(folder_id) -> tuple:
    """
    更新数据表文件夹（重命名/排序）
    ---
    tags:
      - Tables
    security:
      - Bearer: []
    parameters:
      - name: folder_id
        in: path
        type: string
        required: true
        description: 文件夹 ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: 新名称（可选）
            order:
              type: integer
              description: 排序序号（可选）
    responses:
      200:
        description: 更新后的文件夹详情
      403:
        description: 无权限
      404:
        description: 文件夹不存在
    """
    user_id = g.current_user_id

    folder = TableFolderService.get_folder(str(folder_id))
    if not folder:
        return not_found_response('table_folder_not_found')

    if not BaseService.check_permission(str(folder.base_id), user_id, MemberRole.ADMIN):
        return forbidden_response('do_not_permission_modify_base')

    data = request.get_json() or {}
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return error_response('folder_name_required', code=400)
        if len(name) > 100:
            return error_response('folder_name_exceed_characters', code=400)
        data['name'] = name

    folder = TableFolderService.update_folder(str(folder_id), data)
    if not folder:
        return not_found_response('table_folder_not_found')

    return success_response(
        data=folder.to_dict(),
        message='table_folder_updated_successfully'
    )


@tables_bp.route('/table-folders/<uuid:folder_id>', methods=['DELETE'])
@jwt_required
def delete_table_folder(folder_id) -> tuple:
    """
    删除数据表文件夹（仅允许删除空文件夹）
    ---
    tags:
      - Tables
    security:
      - Bearer: []
    parameters:
      - name: folder_id
        in: path
        type: string
        required: true
        description: 文件夹 ID
    responses:
      200:
        description: 删除成功
      403:
        description: 无权限
      404:
        description: 文件夹不存在
      409:
        description: 文件夹非空
    """
    user_id = g.current_user_id

    folder = TableFolderService.get_folder(str(folder_id))
    if not folder:
        return not_found_response('table_folder_not_found')

    if not BaseService.check_permission(str(folder.base_id), user_id, MemberRole.ADMIN):
        return forbidden_response('do_not_permission_modify_base')

    success, error = TableFolderService.delete_folder(str(folder_id))
    if not success:
        if error == 'folder_not_empty':
            return error_response('folder_not_empty', code=409)
        return not_found_response('table_folder_not_found')

    return success_response(message='table_folder_deleted_successfully')
