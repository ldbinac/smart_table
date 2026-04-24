"""
视图管理路由模块
"""
from flask import Blueprint, request, g
from marshmallow import Schema, fields, validate

from app.extensions import db
from app.services.view_service import ViewService
from app.services.table_service import TableService
from app.utils.response import success_response, error_response
from app.utils.decorators import jwt_required, role_required

views_bp = Blueprint('views', __name__)
# 禁用严格斜杠，允许带或不带斜杠的URL
views_bp.strict_slashes = False


class ViewCreateSchema(Schema):
    """视图创建验证模式"""
    name = fields.String(required=True, validate=validate.Length(min=1, max=100),
                        error_messages={'required': '视图名称不能为空'})
    type = fields.String(required=True, validate=validate.OneOf([
        'table', 'gallery', 'kanban', 'gantt', 'calendar', 'form', 'timeline', 'list'
    ]), error_messages={'required': '视图类型不能为空'})
    config = fields.Dict(missing=dict)
    filters = fields.List(fields.Dict(), missing=list)
    sorts = fields.List(fields.Dict(), missing=list)
    group_bys = fields.List(fields.String(), missing=list)
    description = fields.String(missing='')
    # 新增字段支持
    hidden_fields = fields.List(fields.String(), missing=list)
    frozen_fields = fields.List(fields.String(), missing=list)
    row_height = fields.String(missing='medium', validate=validate.OneOf(['small', 'medium', 'large']))
    is_default = fields.Boolean(missing=False)
    field_widths = fields.Dict(missing=dict)
    order = fields.Integer(missing=0)


class ViewUpdateSchema(Schema):
    """视图更新验证模式"""
    name = fields.String(validate=validate.Length(min=1, max=100))
    config = fields.Dict()
    filters = fields.List(fields.Dict())
    sorts = fields.List(fields.Dict())
    group_bys = fields.List(fields.String())
    group_config = fields.Dict()
    hidden_fields = fields.List(fields.String())
    frozen_fields = fields.List(fields.String())
    row_height = fields.String(validate=validate.OneOf(['small', 'medium', 'large']))
    is_default = fields.Boolean()
    field_widths = fields.Dict()
    form_config = fields.Dict()
    order = fields.Integer()
    description = fields.String()


class ViewDuplicateSchema(Schema):
    """视图复制验证模式"""
    name = fields.String(validate=validate.Length(min=1, max=100))


# 初始化验证模式
view_create_schema = ViewCreateSchema()
view_update_schema = ViewUpdateSchema()
view_duplicate_schema = ViewDuplicateSchema()


@views_bp.route('/tables/<table_id>/views', methods=['GET'])
@jwt_required
@role_required(['owner', 'admin', 'editor', 'commenter', 'viewer'])
def get_views(table_id) -> tuple:
    """
    获取表格视图列表
    ---
    tags:
      - Views
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
        description: 视图列表
    """
    # 检查表格是否存在
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)
    
    try:
        views = ViewService.get_table_views(table_id)
        return success_response([view.to_dict() for view in views])
    
    except Exception as e:
        return error_response(f'获取视图列表失败: {str(e)}', 500)


@views_bp.route('/tables/<table_id>/views', methods=['POST'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def create_view(table_id) -> tuple:
    """
    创建视图
    ---
    tags:
      - Views
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
            - type
          properties:
            name:
              type: string
              description: 视图名称
            type:
              type: string
              enum: ['table', 'gallery', 'kanban', 'gantt', 'calendar', 'form', 'timeline', 'list']
              description: 视图类型
            config:
              type: object
              description: 视图配置
            filters:
              type: array
              description: 过滤器
            sorts:
              type: array
              description: 排序规则
            group_bys:
              type: array
              description: 分组字段
            description:
              type: string
              description: 视图描述
    responses:
      201:
        description: 视图创建成功
    """
    # 检查表格是否存在
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)
    
    # 验证请求数据
    json_data = request.get_json()
    if not json_data:
        return error_response('请求数据不能为空', 400)
    
    errors = view_create_schema.validate(json_data)
    if errors:
        return error_response('数据验证失败', 400, errors)
    
    try:
        # 处理表单配置：将 config 中的表单特定配置提取到 form_config
        form_config = {}
        if 'config' in json_data and isinstance(json_data['config'], dict):
            config = json_data['config']
            # 表单特定的配置字段
            form_config_fields = ['title', 'description', 'submitButtonText', 
                                 'visibleFieldIds', 'successMessage', 'allowMultipleSubmit']
            
            # 提取表单特定配置
            for field in form_config_fields:
                if field in config:
                    form_config[field] = config[field]
        
        view = ViewService.create_view(
            table_id=table_id,
            name=json_data['name'],
            view_type=json_data['type'],
            config=json_data.get('config', {}),
            filters=json_data.get('filters', []),
            sorts=json_data.get('sorts', []),
            group_bys=json_data.get('group_bys', [])
        )
        
        # 更新其他可选字段
        if json_data.get('description'):
            view.description = json_data['description']
        if json_data.get('hidden_fields') is not None:
            view.hidden_fields = json_data['hidden_fields']
        if json_data.get('frozen_fields') is not None:
            view.frozen_fields = json_data['frozen_fields']
        if json_data.get('row_height'):
            view.row_height = json_data['row_height']
        if json_data.get('is_default') is not None:
            view.is_default = json_data['is_default']
        if json_data.get('field_widths'):
            view.field_widths = json_data['field_widths']
        if json_data.get('order') is not None:
            view.order = json_data['order']
        # 保存表单配置
        if form_config:
            view.form_config = form_config
        
        db.session.commit()
        
        return success_response(view.to_dict(), '视图创建成功', 201)
    
    except Exception as e:
        return error_response(f'创建视图失败：{str(e)}', 500)


@views_bp.route('/views/<view_id>', methods=['GET'])
@jwt_required
@role_required(['owner', 'admin', 'editor', 'commenter', 'viewer'])
def get_view(view_id) -> tuple:
    """
    获取视图详情
    ---
    tags:
      - Views
    security:
      - Bearer: []
    parameters:
      - name: view_id
        in: path
        type: string
        required: true
        description: 视图 ID
    responses:
      200:
        description: 视图详情
      404:
        description: 视图不存在
    """
    view = ViewService.get_view_by_id(view_id)
    if not view:
        return error_response('视图不存在', 404)
    
    try:
        return success_response(view.to_dict())
    except Exception as e:
        return error_response(f'获取视图详情失败: {str(e)}', 500)


@views_bp.route('/views/<view_id>', methods=['PUT'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def update_view(view_id) -> tuple:
    """
    更新视图
    ---
    tags:
      - Views
    security:
      - Bearer: []
    parameters:
      - name: view_id
        in: path
        type: string
        required: true
        description: 视图 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            name:
              type: string
              description: 视图名称
            config:
              type: object
              description: 视图配置
            filters:
              type: array
              description: 过滤器
            sorts:
              type: array
              description: 排序规则
            group_bys:
              type: array
              description: 分组字段
            hidden_fields:
              type: array
              description: 隐藏字段
            frozen_fields:
              type: array
              description: 冻结字段
            row_height:
              type: string
              enum: ['small', 'medium', 'large']
              description: 行高
            is_default:
              type: boolean
              description: 是否设为默认
            field_widths:
              type: object
              description: 字段宽度配置
            form_config:
              type: object
              description: 表单配置
            order:
              type: integer
              description: 排序顺序
            description:
              type: string
              description: 视图描述
    responses:
      200:
        description: 视图更新成功
      400:
        description: 参数错误
      404:
        description: 视图不存在
    """
    view = ViewService.get_view_by_id(view_id)
    if not view:
        return error_response('视图不存在', 404)
    
    # 验证请求数据
    json_data = request.get_json()
    if not json_data:
        return error_response('请求数据不能为空', 400)
    
    errors = view_update_schema.validate(json_data)
    if errors:
        return error_response('数据验证失败', 400, errors)
    
    try:
        # 处理表单配置：将 config 中的表单特定配置提取到 form_config
        if 'config' in json_data and isinstance(json_data['config'], dict):
            config = json_data['config']
            
            # 表单特定的配置字段
            form_config_fields = ['title', 'description', 'submitButtonText', 
                                 'visibleFieldIds', 'successMessage', 'allowMultipleSubmit']
            
            # 检查是否有表单特定配置
            has_form_config = any(field in config for field in form_config_fields)
            
            if has_form_config:
                # 提取表单特定配置
                form_config = {}
                for field in form_config_fields:
                    if field in config:
                        form_config[field] = config[field]
                
                # 将 form_config 添加到 json_data 中，供 update_view 使用
                if form_config:
                    # 合并到现有的 form_config
                    existing_form_config = view.form_config or {}
                    existing_form_config.update(form_config)
                    json_data['form_config'] = existing_form_config
        
        view = ViewService.update_view(view, **json_data)
        return success_response(view.to_dict(), '视图更新成功')
    
    except Exception as e:
        return error_response(f'更新视图失败：{str(e)}', 500)


@views_bp.route('/views/<view_id>', methods=['DELETE'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def delete_view(view_id) -> tuple:
    """
    删除视图
    ---
    tags:
      - Views
    security:
      - Bearer: []
    parameters:
      - name: view_id
        in: path
        type: string
        required: true
        description: 视图 ID
    responses:
      200:
        description: 删除成功
      400:
        description: 默认视图不能删除
      404:
        description: 视图不存在
    """
    view = ViewService.get_view_by_id(view_id)
    if not view:
        return error_response('视图不存在', 404)
    
    try:
        success = ViewService.delete_view(view)
        if success:
            return success_response(None, '视图删除成功')
        else:
            return error_response('默认视图不能删除', 400)
    
    except Exception as e:
        return error_response(f'删除视图失败: {str(e)}', 500)


@views_bp.route('/views/<view_id>/duplicate', methods=['POST'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def duplicate_view(view_id) -> tuple:
    """
    复制视图
    ---
    tags:
      - Views
    security:
      - Bearer: []
    parameters:
      - name: view_id
        in: path
        type: string
        required: true
        description: 视图 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            name:
              type: string
              description: 新视图名称
    responses:
      201:
        description: 视图复制成功
      400:
        description: 参数错误
      404:
        description: 视图不存在
    """
    view = ViewService.get_view_by_id(view_id)
    if not view:
        return error_response('视图不存在', 404)
    
    # 验证请求数据
    json_data = request.get_json() or {}
    errors = view_duplicate_schema.validate(json_data)
    if errors:
        return error_response('数据验证失败', 400, errors)
    
    try:
        new_view = ViewService.duplicate_view(
            view, 
            new_name=json_data.get('name')
        )
        return success_response(new_view.to_dict(), '视图复制成功', 201)
    
    except Exception as e:
        return error_response(f'复制视图失败: {str(e)}', 500)


@views_bp.route('/tables/<table_id>/views/reorder', methods=['PUT'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def reorder_views(table_id) -> tuple:
    """
    重新排序视图
    ---
    tags:
      - Views
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
            - view_orders
          properties:
            view_orders:
              type: array
              description: 视图排序列表
              items:
                type: object
                properties:
                  id:
                    type: string
                    description: 视图 ID
                  order:
                    type: integer
                    description: 排序顺序
    responses:
      200:
        description: 排序更新成功
      400:
        description: 参数错误
      404:
        description: 表格不存在
    """
    # 检查表格是否存在
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)
    
    json_data = request.get_json()
    if not json_data or 'view_orders' not in json_data:
        return error_response('view_orders不能为空', 400)
    
    view_orders = json_data['view_orders']
    
    try:
        
        for item in view_orders:
            view_id = item.get('id')
            order = item.get('order')
            
            if view_id is not None and order is not None:
                view = ViewService.get_view_by_id(view_id)
                if view and view.table_id == table_id:
                    view.order = order
        
        db.session.commit()
        
        # 返回更新后的视图列表
        views = ViewService.get_table_views(table_id)
        return success_response([view.to_dict() for view in views], '视图排序更新成功')
    
    except Exception as e:
        db.session.rollback()
        return error_response(f'更新视图排序失败: {str(e)}', 500)


@views_bp.route('/tables/<table_id>/views/<view_id>/set-default', methods=['PUT'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def set_default_view(table_id, view_id) -> tuple:
    """
    设置默认视图
    ---
    tags:
      - Views
    security:
      - Bearer: []
    description: 将指定视图设为该表格的默认视图，同时取消其他视图的默认状态
    parameters:
      - name: table_id
        in: path
        type: string
        required: true
        description: 表格 ID
      - name: view_id
        in: path
        type: string
        required: true
        description: 视图 ID
    responses:
      200:
        description: 设置成功
      404:
        description: 表格或视图不存在
    """
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)
    
    view = ViewService.get_view_by_id(view_id)
    if not view or view.table_id != table_id:
        return error_response('视图不存在或不属于该表格', 404)
    
    try:
        
        View.query.filter_by(table_id=table_id).update({'is_default': False})
        
        view.is_default = True
        db.session.commit()
        
        return success_response(view.to_dict(), '已设置为默认视图')
    
    except Exception as e:
        db.session.rollback()
        return error_response(f'设置默认视图失败: {str(e)}', 500)


@views_bp.route('/views/types', methods=['GET'])
@jwt_required
def get_view_types() -> tuple:
    """
    获取支持的视图类型列表
    ---
    tags:
      - Views
    security:
      - Bearer: []
    description: 返回所有可用的视图类型及其配置说明
    responses:
      200:
        description: 视图类型列表
    """
    view_types = [
        {
            'type': 'grid',
            'name': '表格视图',
            'description': '以表格形式展示数据，支持行列操作',
            'icon': 'table',
            'config_schema': {
                'frozen_columns': {'type': 'number', 'default': 0, 'description': '冻结列数'},
                'row_height': {'type': 'string', 'enum': ['short', 'medium', 'tall'], 'default': 'medium'}
            }
        },
        {
            'type': 'gallery',
            'name': '画廊视图',
            'description': '以卡片画廊形式展示数据，适合图片展示',
            'icon': 'images',
            'config_schema': {
                'card_cover_field': {'type': 'string', 'description': '封面图片字段'},
                'card_title_field': {'type': 'string', 'description': '标题字段'},
                'card_size': {'type': 'string', 'enum': ['small', 'medium', 'large'], 'default': 'medium'}
            }
        },
        {
            'type': 'kanban',
            'name': '看板视图',
            'description': '以看板形式展示数据，适合任务管理',
            'icon': 'columns',
            'config_schema': {
                'group_by_field': {'type': 'string', 'required': True, 'description': '分组字段'},
                'stack_by_field': {'type': 'string', 'description': '堆叠字段'}
            }
        },
        {
            'type': 'gantt',
            'name': '甘特图视图',
            'description': '以甘特图形式展示项目进度',
            'icon': 'stream',
            'config_schema': {
                'start_date_field': {'type': 'string', 'required': True, 'description': '开始日期字段'},
                'end_date_field': {'type': 'string', 'required': True, 'description': '结束日期字段'},
                'progress_field': {'type': 'string', 'description': '进度字段'}
            }
        },
        {
            'type': 'calendar',
            'name': '日历视图',
            'description': '以日历形式展示数据',
            'icon': 'calendar',
            'config_schema': {
                'date_field': {'type': 'string', 'required': True, 'description': '日期字段'},
                'title_field': {'type': 'string', 'description': '标题字段'}
            }
        },
        {
            'type': 'form',
            'name': '表单视图',
            'description': '以表单形式展示单条记录',
            'icon': 'file-text',
            'config_schema': {
                'layout': {'type': 'string', 'enum': ['single', 'double'], 'default': 'single'},
                'show_header': {'type': 'boolean', 'default': True}
            }
        }
    ]
    
    return success_response(view_types)
