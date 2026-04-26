"""
用户管理路由模块
提供用户搜索、查询等接口
"""
from flask import Blueprint, request, g
from sqlalchemy import or_, func

from app.extensions import db
from app.models.user import User, UserStatus
from app.utils.decorators import jwt_required
from app.utils.response import success_response, error_response

users_bp = Blueprint('users', __name__)


@users_bp.route('/users/search', methods=['GET'])
@jwt_required
def search_users():
    """
    搜索用户
    
    查询参数:
        - query: 搜索关键词（匹配用户名或邮箱）
        - base_id: 可选，限制在指定基础的成员中搜索
        - page: 页码，默认 1
        - per_page: 每页数量，默认 20，最大 100
    
    返回:
        - users: 用户列表
        - total: 总数
    """
    # 获取查询参数
    query = request.args.get('query', '').strip()
    base_id = request.args.get('base_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # 限制每页数量
    if per_page > 100:
        per_page = 100
    if per_page < 1:
        per_page = 20
    if page < 1:
        page = 1
    
    # 构建查询
    user_query = db.session.query(User).filter(User.status == UserStatus.ACTIVE)
    
    # 如果指定了 base_id，只搜索该基础的成员
    if base_id:
        from app.models.base import BaseMember
        user_query = user_query.join(
            BaseMember, 
            BaseMember.user_id == User.id
        ).filter(BaseMember.base_id == base_id)
    
    # 如果有搜索关键词，按名称或邮箱搜索
    if query:
        search_pattern = f'%{query}%'
        user_query = user_query.filter(
            or_(
                func.lower(User.name).like(func.lower(search_pattern)),
                func.lower(User.email).like(func.lower(search_pattern))
            )
        )
    
    # 排序：优先显示最近登录的用户
    user_query = user_query.order_by(User.last_login_at.desc().nullslast())
    
    # 分页
    pagination = user_query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    
    # 构建响应数据
    users_data = [{
        'id': str(user.id),
        'name': user.name,
        'email': user.email,
        'avatar': user.avatar,
        'role': user.role.value if user.role else None,
        'status': user.status.value if user.status else None,
    } for user in users]
    
    return success_response({
        'users': users_data,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'total_pages': pagination.pages
    })


@users_bp.route('/users/<user_id>', methods=['GET'])
@jwt_required
def get_user(user_id):
    """
    根据ID获取用户信息
    
    路径参数:
        - user_id: 用户ID
    
    返回:
        - 用户详细信息
    """
    user = db.session.get(User, user_id)
    
    if not user:
        return error_response(message='用户不存在', code=404)
    
    return success_response({
        'id': str(user.id),
        'name': user.name,
        'email': user.email,
        'avatar': user.avatar,
        'role': user.role.value if user.role else None,
        'status': user.status.value if user.status else None,
        'email_verified': user.email_verified,
        'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
        'created_at': user.created_at.isoformat() if user.created_at else None,
    })


@users_bp.route('/users/batch', methods=['POST'])
@jwt_required
def get_users_batch():
    """
    批量获取用户信息
    
    请求体:
        - ids: 用户ID列表
    
    返回:
        - 用户列表
    """
    data = request.get_json()
    
    if not data or 'ids' not in data:
        return error_response(message='缺少用户ID列表', code=400)
    
    user_ids = data['ids']
    
    if not isinstance(user_ids, list):
        return error_response(message='ids 必须是数组', code=400)
    
    if len(user_ids) > 100:
        return error_response(message='一次最多查询100个用户', code=400)
    
    # 查询用户
    users = db.session.query(User).filter(
        User.id.in_(user_ids),
        User.status == UserStatus.ACTIVE
    ).all()
    
    users_data = [{
        'id': str(user.id),
        'name': user.name,
        'email': user.email,
        'avatar': user.avatar,
        'role': user.role.value if user.role else None,
        'status': user.status.value if user.status else None,
    } for user in users]
    
    return success_response(users_data)
