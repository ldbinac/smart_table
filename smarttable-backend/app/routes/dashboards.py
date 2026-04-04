"""
仪表盘路由模块
处理 Dashboard 的 CRUD 操作、组件管理和布局配置
"""
from flask import Blueprint, request, g

from app.services.dashboard_service import DashboardService
from app.services.base_service import BaseService
from app.models.base import MemberRole
from app.utils.decorators import jwt_required
from app.utils.response import (
    success_response, error_response, not_found_response,
    forbidden_response, validation_error_response
)

dashboards_bp = Blueprint('dashboards', __name__)
# 禁用严格斜杠，允许带或不带斜杠的URL
dashboards_bp.strict_slashes = False


# ==================== 基础数据下的仪表盘操作 ====================

@dashboards_bp.route('/bases/<uuid:base_id>/dashboards', methods=['GET'])
@jwt_required
def get_base_dashboards(base_id):
    """
    获取基础数据下的所有仪表盘
    
    参数:
        base_id: 基础数据 ID
        
    返回:
        仪表盘列表
    """
    user_id = g.current_user_id
    
    # 检查权限
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限访问此基础数据')
    
    dashboards = DashboardService.get_all_dashboards(str(base_id))
    
    return success_response(
        data=[d.to_dict(include_widgets=False) for d in dashboards],
        message='获取仪表盘列表成功'
    )


@dashboards_bp.route('/bases/<uuid:base_id>/dashboards', methods=['POST'])
@jwt_required
def create_base_dashboard(base_id):
    """
    在基础数据下创建新仪表盘
    
    参数:
        base_id: 基础数据 ID
        
    请求体:
        - name: 仪表盘名称（可选，默认"未命名仪表盘"）
        - description: 描述（可选）
        - is_default: 是否设为默认（可选，默认false）
        - layout: 布局配置（可选）
        
    返回:
        创建的仪表盘详情
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限创建仪表盘')
    
    data = request.get_json() or {}
    
    # 验证名称长度
    if 'name' in data:
        name = data['name'].strip()
        if len(name) > 100:
            return error_response('名称不能超过100个字符', code=400)
        data['name'] = name
    
    dashboard = DashboardService.create_dashboard(
        base_id=str(base_id),
        data=data,
        user_id=user_id
    )
    
    return success_response(
        data=dashboard.to_dict(include_widgets=True),
        message='仪表盘创建成功',
        code=201
    )


# ==================== 单个仪表盘操作 ====================

@dashboards_bp.route('/dashboards/<uuid:dashboard_id>', methods=['GET'])
@jwt_required
def get_dashboard(dashboard_id):
    """
    获取仪表盘详情
    
    参数:
        dashboard_id: 仪表盘 ID
        
    查询参数:
        - include_widgets: 是否包含组件列表（可选，默认true）
        
    返回:
        仪表盘详情
    """
    user_id = g.current_user_id
    
    dashboard = DashboardService.get_dashboard(str(dashboard_id))
    if not dashboard:
        return not_found_response('仪表盘')
    
    # 检查权限
    if not BaseService.check_permission(str(dashboard.base_id), user_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限访问此仪表盘')
    
    # 是否包含组件
    include_widgets = request.args.get('include_widgets', 'true').lower() == 'true'
    
    return success_response(
        data=dashboard.to_dict(include_widgets=include_widgets),
        message='获取仪表盘成功'
    )


@dashboards_bp.route('/dashboards/<uuid:dashboard_id>', methods=['PUT'])
@jwt_required
def update_dashboard(dashboard_id):
    """
    更新仪表盘
    
    参数:
        dashboard_id: 仪表盘 ID
        
    请求体:
        - name: 新名称（可选）
        - description: 新描述（可选）
        - is_default: 是否设为默认（可选）
        - layout: 布局配置（可选）
        
    返回:
        更新后的仪表盘详情
    """
    user_id = g.current_user_id
    
    dashboard = DashboardService.get_dashboard(str(dashboard_id))
    if not dashboard:
        return not_found_response('仪表盘')
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(dashboard.base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限修改此仪表盘')
    
    data = request.get_json() or {}
    
    # 验证名称长度
    if 'name' in data:
        name = data['name'].strip()
        if len(name) > 100:
            return error_response('名称不能超过100个字符', code=400)
        data['name'] = name
    
    updated_dashboard = DashboardService.update_dashboard(
        dashboard_id=str(dashboard_id),
        data=data
    )
    
    return success_response(
        data=updated_dashboard.to_dict(include_widgets=True),
        message='仪表盘更新成功'
    )


@dashboards_bp.route('/dashboards/<uuid:dashboard_id>', methods=['DELETE'])
@jwt_required
def delete_dashboard(dashboard_id):
    """
    删除仪表盘（级联删除所有组件）
    
    参数:
        dashboard_id: 仪表盘 ID
        
    返回:
        删除结果
    """
    user_id = g.current_user_id
    
    dashboard = DashboardService.get_dashboard(str(dashboard_id))
    if not dashboard:
        return not_found_response('仪表盘')
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(dashboard.base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限删除此仪表盘')
    
    success = DashboardService.delete_dashboard(str(dashboard_id))
    if not success:
        return error_response('删除失败，请稍后重试', code=500)
    
    return success_response(message='仪表盘删除成功')


# ==================== 组件管理 ====================

@dashboards_bp.route('/dashboards/<uuid:dashboard_id>/widgets', methods=['POST'])
@jwt_required
def add_widget(dashboard_id):
    """
    向仪表盘添加组件
    
    参数:
        dashboard_id: 仪表盘 ID
        
    请求体:
        - type: 组件类型（必填）
        - title: 组件标题（可选，默认"未命名组件"）
        - config: 组件配置（可选）
        - data_source: 数据源配置（可选）
        - position: 位置配置（可选）
        
    返回:
        创建的组件详情
    """
    user_id = g.current_user_id
    
    dashboard = DashboardService.get_dashboard(str(dashboard_id))
    if not dashboard:
        return not_found_response('仪表盘')
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(dashboard.base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限修改此仪表盘')
    
    data = request.get_json() or {}
    
    # 验证必填字段
    if not data.get('type'):
        return error_response('请提供组件类型', code=400)
    
    widget = DashboardService.add_widget(
        dashboard_id=str(dashboard_id),
        data=data
    )
    
    return success_response(
        data=widget.to_dict(),
        message='组件添加成功',
        code=201
    )


@dashboards_bp.route('/dashboards/<uuid:dashboard_id>/widgets', methods=['PUT'])
@jwt_required
def update_widgets_batch(dashboard_id):
    """
    批量更新仪表盘组件（支持新增、更新、排序）
    
    参数:
        dashboard_id: 仪表盘 ID
        
    请求体:
        - widgets: 组件列表，每个包含 id（可选，无则新建）和其他字段
        
    返回:
        更新后的组件列表
    """
    user_id = g.current_user_id
    
    dashboard = DashboardService.get_dashboard(str(dashboard_id))
    if not dashboard:
        return not_found_response('仪表盘')
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(dashboard.base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限修改此仪表盘')
    
    data = request.get_json() or {}
    widgets_data = data.get('widgets', [])
    
    if not isinstance(widgets_data, list):
        return error_response('widgets 必须是数组', code=400)
    
    updated_widgets = DashboardService.batch_update_widgets(
        dashboard_id=str(dashboard_id),
        widgets_data=widgets_data
    )
    
    return success_response(
        data=[w.to_dict() for w in updated_widgets],
        message='组件批量更新成功'
    )


@dashboards_bp.route('/dashboards/<uuid:dashboard_id>/widgets/<uuid:widget_id>', methods=['PUT'])
@jwt_required
def update_widget(dashboard_id, widget_id):
    """
    更新单个组件
    
    参数:
        dashboard_id: 仪表盘 ID
        widget_id: 组件 ID
        
    请求体:
        - title: 新标题（可选）
        - config: 新配置（可选）
        - data_source: 新数据源（可选）
        - position: 新位置（可选）
        - order: 新排序（可选）
        
    返回:
        更新后的组件详情
    """
    user_id = g.current_user_id
    
    dashboard = DashboardService.get_dashboard(str(dashboard_id))
    if not dashboard:
        return not_found_response('仪表盘')
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(dashboard.base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限修改此仪表盘')
    
    # 验证组件是否属于该仪表盘
    widget = DashboardService.get_widget(str(widget_id))
    if not widget or str(widget.dashboard_id) != str(dashboard_id):
        return not_found_response('组件')
    
    data = request.get_json() or {}
    
    updated_widget = DashboardService.update_widget(
        widget_id=str(widget_id),
        data=data
    )
    
    return success_response(
        data=updated_widget.to_dict(),
        message='组件更新成功'
    )


@dashboards_bp.route('/dashboards/<uuid:dashboard_id>/widgets/<uuid:widget_id>', methods=['DELETE'])
@jwt_required
def delete_widget(dashboard_id, widget_id):
    """
    删除组件
    
    参数:
        dashboard_id: 仪表盘 ID
        widget_id: 组件 ID
        
    返回:
        删除结果
    """
    user_id = g.current_user_id
    
    dashboard = DashboardService.get_dashboard(str(dashboard_id))
    if not dashboard:
        return not_found_response('仪表盘')
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(dashboard.base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限修改此仪表盘')
    
    # 验证组件是否属于该仪表盘
    widget = DashboardService.get_widget(str(widget_id))
    if not widget or str(widget.dashboard_id) != str(dashboard_id):
        return not_found_response('组件')
    
    success = DashboardService.delete_widget(str(widget_id))
    if not success:
        return error_response('删除失败，请稍后重试', code=500)
    
    return success_response(message='组件删除成功')


# ==================== 布局管理 ====================

@dashboards_bp.route('/dashboards/<uuid:dashboard_id>/layout', methods=['PUT'])
@jwt_required
def update_layout(dashboard_id):
    """
    更新仪表盘布局
    
    参数:
        dashboard_id: 仪表盘 ID
        
    请求体:
        - type: 布局类型（可选，'grid' 或 'free'）
        - config: 布局配置（可选，如网格列数、间距等）
        - widgets: 组件位置列表（可选）
            - id: 组件 ID
            - x, y: 位置坐标
            - w, h: 宽高
            - minW, minH, maxW, maxH: 尺寸限制（可选）
            
    返回:
        更新后的仪表盘详情
    """
    user_id = g.current_user_id
    
    dashboard = DashboardService.get_dashboard(str(dashboard_id))
    if not dashboard:
        return not_found_response('仪表盘')
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(dashboard.base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限修改此仪表盘')
    
    data = request.get_json() or {}
    
    # 验证布局类型
    if 'type' in data and data['type'] not in ['grid', 'free']:
        return error_response('布局类型必须是 grid 或 free', code=400)
    
    updated_dashboard = DashboardService.update_layout(
        dashboard_id=str(dashboard_id),
        layout_data=data
    )
    
    return success_response(
        data=updated_dashboard.to_dict(include_widgets=True),
        message='布局更新成功'
    )


# ==================== 其他操作 ====================

@dashboards_bp.route('/dashboards/<uuid:dashboard_id>/duplicate', methods=['POST'])
@jwt_required
def duplicate_dashboard(dashboard_id):
    """
    复制仪表盘
    
    参数:
        dashboard_id: 源仪表盘 ID
        
    请求体:
        - name: 新仪表盘名称（可选，默认添加"副本"后缀）
        
    返回:
        新创建的仪表盘详情
    """
    user_id = g.current_user_id
    
    dashboard = DashboardService.get_dashboard(str(dashboard_id))
    if not dashboard:
        return not_found_response('仪表盘')
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(dashboard.base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限复制此仪表盘')
    
    data = request.get_json() or {}
    new_name = data.get('name')
    
    new_dashboard = DashboardService.duplicate_dashboard(
        dashboard_id=str(dashboard_id),
        user_id=user_id,
        new_name=new_name
    )
    
    return success_response(
        data=new_dashboard.to_dict(include_widgets=True),
        message='仪表盘复制成功',
        code=201
    )


@dashboards_bp.route('/dashboards/<uuid:dashboard_id>/set-default', methods=['POST'])
@jwt_required
def set_default_dashboard(dashboard_id):
    """
    设置默认仪表盘
    
    参数:
        dashboard_id: 仪表盘 ID
        
    返回:
        更新后的仪表盘详情
    """
    user_id = g.current_user_id
    
    dashboard = DashboardService.get_dashboard(str(dashboard_id))
    if not dashboard:
        return not_found_response('仪表盘')
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(dashboard.base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限修改此仪表盘')
    
    updated_dashboard = DashboardService.set_default_dashboard(str(dashboard_id))
    
    return success_response(
        data=updated_dashboard.to_dict(include_widgets=False),
        message='默认仪表盘设置成功'
    )
