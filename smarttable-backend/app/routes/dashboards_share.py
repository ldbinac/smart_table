"""
仪表盘分享路由
"""
from flask import Blueprint, request, g
from app.utils.decorators import jwt_required
from app.utils.response import success_response, error_response, not_found_response, forbidden_response
from app.services.dashboard_share_service import DashboardShareService
from app.services.base_service import BaseService
from app.models.dashboard import Dashboard
from app.models.base import MemberRole

dashboards_share_bp = Blueprint('dashboards_share', __name__)


@dashboards_share_bp.route('/dashboards/<uuid:dashboard_id>/shares', methods=['GET'])
@jwt_required
def get_dashboard_shares(dashboard_id):
    """
    获取仪表盘的所有分享链接
    
    参数:
        dashboard_id: 仪表盘 ID
        
    返回:
        分享链接列表
    """
    user_id = g.current_user_id
    
    # 获取仪表盘
    dashboard = Dashboard.query.get(str(dashboard_id))
    if not dashboard:
        return not_found_response('仪表盘')
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(dashboard.base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限管理此仪表盘的分享')
    
    shares = DashboardShareService.get_shares_by_dashboard(str(dashboard_id))
    
    return success_response(
        data=[share.to_dict() for share in shares],
        message='获取分享链接列表成功'
    )


@dashboards_share_bp.route('/dashboards/<uuid:dashboard_id>/shares', methods=['POST'])
@jwt_required
def create_dashboard_share(dashboard_id):
    """
    创建仪表盘分享链接
    
    参数:
        dashboard_id: 仪表盘 ID
        
    请求体:
        - requireAccessCode: 是否需要访问密码（可选，默认 false）
        - expiresInHours: 过期时间（小时）（可选）
        - maxAccessCount: 最大访问次数（可选）
        - permission: 分享权限（view/edit，默认 view）
        
    返回:
        创建的分享链接信息
    """
    user_id = g.current_user_id
    
    # 获取仪表盘
    dashboard = Dashboard.query.get(str(dashboard_id))
    if not dashboard:
        return not_found_response('仪表盘')
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(dashboard.base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限创建分享链接')
    
    data = request.get_json() or {}
    
    try:
        share = DashboardShareService.create_share(
            dashboard_id=str(dashboard_id),
            user_id=user_id,
            require_access_code=data.get('requireAccessCode', False),
            expires_in_hours=data.get('expiresInHours'),
            max_access_count=data.get('maxAccessCount'),
            permission=data.get('permission', 'view')
        )
        
        return success_response(
            data=share.to_dict(),
            message='分享链接创建成功',
            code=201
        )
    except Exception as e:
        return error_response(f'创建分享链接失败：{str(e)}', 500)


@dashboards_share_bp.route('/shares/<uuid:share_id>', methods=['DELETE'])
@jwt_required
def delete_dashboard_share(share_id):
    """
    删除分享链接
    
    参数:
        share_id: 分享 ID
        
    返回:
        删除结果
    """
    user_id = g.current_user_id
    
    share = DashboardShare.query.get(str(share_id))
    if not share:
        return not_found_response('分享链接')
    
    # 获取仪表盘
    dashboard = Dashboard.query.get(str(share.dashboard_id))
    if not dashboard:
        return not_found_response('仪表盘')
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(dashboard.base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限删除此分享链接')
    
    success = DashboardShareService.delete_share(str(share_id))
    
    if success:
        return success_response(message='分享链接删除成功')
    else:
        return error_response('删除分享链接失败', 500)


@dashboards_share_bp.route('/shares/<uuid:share_id>/deactivate', methods=['POST'])
@jwt_required
def deactivate_dashboard_share(share_id):
    """
    禁用分享链接
    
    参数:
        share_id: 分享 ID
        
    返回:
        禁用结果
    """
    user_id = g.current_user_id
    
    share = DashboardShare.query.get(str(share_id))
    if not share:
        return not_found_response('分享链接')
    
    # 获取仪表盘
    dashboard = Dashboard.query.get(str(share.dashboard_id))
    if not dashboard:
        return not_found_response('仪表盘')
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(dashboard.base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限禁用此分享链接')
    
    success = DashboardShareService.deactivate_share(str(share_id))
    
    if success:
        return success_response(message='分享链接已禁用')
    else:
        return error_response('禁用分享链接失败', 500)


# ==================== 公开访问接口（不需要登录） ====================

@dashboards_share_bp.route('/shares/<token>/validate', methods=['POST'])
def validate_dashboard_share(token):
    """
    验证分享链接（公开接口，用于分享页面）
    
    参数:
        token: 分享令牌
        
    请求体:
        - accessCode: 访问密码（可选）
        
    返回:
        验证结果和仪表盘信息（如果有效），包括所有相关表和字段数据
    """
    data = request.get_json() or {}
    access_code = data.get('accessCode')
    
    valid, share, error = DashboardShareService.validate_share(token, access_code)
    
    if not valid:
        return error_response(error or '分享链接无效', 400)
    
    # 记录访问
    DashboardShareService.record_access(str(share.id))
    
    # 返回仪表盘信息（不包含敏感数据）
    dashboard_data = share.dashboard.to_dict(include_widgets=True)
    
    # 收集所有相关的表 ID
    widgets = share.dashboard.widgets or []
    table_ids = list(set([w.get('tableId') for w in widgets if w.get('tableId')]))
    
    # 获取所有表及其字段数据
    from app.models.table import Table
    from app.models.field import Field
    from app.models.record import Record
    
    tables_data = []
    for table_id in table_ids:
        table = Table.query.get(table_id)
        if table:
            table_dict = table.to_dict()
            # 获取表的字段
            fields = Field.query.filter_by(table_id=table_id).all()
            table_dict['fields'] = [f.to_dict() for f in fields]
            
            # 获取表的记录（限制数量，避免数据量过大）
            records = Record.query.filter_by(table_id=table_id).limit(1000).all()
            table_dict['records'] = [r.to_dict() for r in records]
            
            tables_data.append(table_dict)
    
    return success_response(
        data={
            'share': share.to_dict(),
            'dashboard': dashboard_data,
            'tables': tables_data  # 新增：返回所有相关表的数据
        },
        message='验证成功'
    )


@dashboards_share_bp.route('/shares/<token>/dashboard', methods=['GET'])
def get_shared_dashboard(token):
    """
    获取分享的仪表盘数据（公开接口，用于分享页面）
    
    参数:
        token: 分享令牌
        
    返回:
        仪表盘数据和组件信息
    """
    share = DashboardShareService.get_share_by_token(token)
    
    if not share or not share.is_active:
        return not_found_response('分享链接不存在或已失效')
    
    # 检查是否过期
    if share.expires_at and __import__('time').time() > share.expires_at:
        return error_response('分享链接已过期', 400)
    
    # 返回仪表盘数据
    dashboard_data = share.dashboard.to_dict(include_widgets=True)
    
    return success_response(
        data=dashboard_data,
        message='获取成功'
    )
