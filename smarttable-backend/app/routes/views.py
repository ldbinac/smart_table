"""
视图管理路由模块
"""
from flask import Blueprint, request, g
from marshmallow import Schema, fields, validate

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
        'grid', 'gallery', 'kanban', 'gantt', 'calendar', 'form'
    ]), error_messages={'required': '视图类型不能为空'})
    config = fields.Dict(missing=dict)
    filters = fields.List(fields.Dict(), missing=list)
    sorts = fields.List(fields.Dict(), missing=list)
    description = fields.String(missing='')


class ViewUpdateSchema(Schema):
    """视图更新验证模式"""
    name = fields.String(validate=validate.Length(min=1, max=100))
    config = fields.Dict()
    filters = fields.List(fields.Dict())
    sorts = fields.List(fields.Dict())
    hidden_fields = fields.List(fields.String())
    field_widths = fields.Dict()
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
def get_views(table_id):
    """
    获取表格视图列表
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
def create_view(table_id):
    """
    创建视图
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
        view = ViewService.create_view(
            table_id=table_id,
            name=json_data['name'],
            view_type=json_data['type'],
            config=json_data.get('config', {}),
            filters=json_data.get('filters', []),
            sorts=json_data.get('sorts', [])
        )
        
        # 更新描述（如果提供）
        if json_data.get('description'):
            view.description = json_data['description']
            from app.extensions import db
            db.session.commit()
        
        return success_response(view.to_dict(), '视图创建成功', 201)
    
    except Exception as e:
        return error_response(f'创建视图失败: {str(e)}', 500)


@views_bp.route('/views/<view_id>', methods=['GET'])
@jwt_required
@role_required(['owner', 'admin', 'editor', 'commenter', 'viewer'])
def get_view(view_id):
    """
    获取视图详情
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
def update_view(view_id):
    """
    更新视图
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
        view = ViewService.update_view(view, **json_data)
        return success_response(view.to_dict(), '视图更新成功')
    
    except Exception as e:
        return error_response(f'更新视图失败: {str(e)}', 500)


@views_bp.route('/views/<view_id>', methods=['DELETE'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def delete_view(view_id):
    """
    删除视图
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
def duplicate_view(view_id):
    """
    复制视图
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
def reorder_views(table_id):
    """
    重新排序视图
    
    请求体: {"view_orders": [{"id": "view_id", "order": 1}, ...]}
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
        from app.extensions import db
        
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
def set_default_view(table_id, view_id):
    """
    设置默认视图（任务 19.6）
    
    将指定视图设为该表格的默认视图，同时取消其他视图的默认状态
    """
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)
    
    view = ViewService.get_view_by_id(view_id)
    if not view or view.table_id != table_id:
        return error_response('视图不存在或不属于该表格', 404)
    
    try:
        from app.extensions import db
        from app.models.view import View
        
        View.query.filter_by(table_id=table_id).update({'is_default': False})
        
        view.is_default = True
        db.session.commit()
        
        return success_response(view.to_dict(), '已设置为默认视图')
    
    except Exception as e:
        db.session.rollback()
        return error_response(f'设置默认视图失败: {str(e)}', 500)


@views_bp.route('/views/types', methods=['GET'])
@jwt_required
def get_view_types():
    """
    获取支持的视图类型列表
    
    返回所有可用的视图类型及其配置说明
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
