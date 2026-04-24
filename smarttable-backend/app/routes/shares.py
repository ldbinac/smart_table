"""
Base 分享路由模块
处理 Base 分享链接的创建、管理和访问
"""
from flask import Blueprint, request, g

from app.models.base import Base, MemberRole
from app.models.base_share import BaseShare
from app.models.base import BaseMember
from app.services.base_service import BaseService
from app.services.share_service import ShareService
from app.utils.decorators import jwt_required
from app.utils.response import (
    success_response, error_response, not_found_response,
    forbidden_response
)

shares_bp = Blueprint('shares', __name__)
shares_bp.strict_slashes = False


@shares_bp.route('/bases/<uuid:base_id>/shares', methods=['POST'])
@jwt_required
def create_share(base_id) -> tuple:
    """
    创建 Base 分享链接
    ---
    tags:
      - Shares
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: Base ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - permission
          properties:
            permission:
              type: string
              enum: ['view', 'edit']
              description: 分享权限
            expires_at:
              type: integer
              description: 过期时间（Unix 时间戳，可选）
    responses:
      201:
        description: 创建的分享信息
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 ADMIN 或更高权限）
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.ADMIN):
        return forbidden_response('您没有权限创建分享链接')
    
    data = request.get_json() or {}
    result = ShareService.create_share(str(base_id), user_id, data)
    
    if not result['success']:
        return error_response(result['error'], code=400)
    
    return success_response(
        data=result['share'].to_dict(),
        message='分享链接创建成功',
        code=201
    )


@shares_bp.route('/bases/<uuid:base_id>/shares', methods=['GET'])
@jwt_required
def get_shares(base_id) -> tuple:
    """
    获取 Base 的所有分享链接列表
    ---
    tags:
      - Shares
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: Base ID
    responses:
      200:
        description: 分享链接列表
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 ADMIN 或更高权限）
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.ADMIN):
        return forbidden_response('您没有权限查看分享列表')
    
    shares = ShareService.get_shares_by_base(str(base_id))
    shares_data = [share.to_dict() for share in shares]
    
    return success_response(
        data=shares_data,
        message='获取分享列表成功'
    )


@shares_bp.route('/shares/<share_id>', methods=['PUT'])
@jwt_required
def update_share(share_id) -> tuple:
    """
    更新分享链接（启用/禁用）
    ---
    tags:
      - Shares
    security:
      - Bearer: []
    parameters:
      - name: share_id
        in: path
        type: string
        required: true
        description: 分享 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            is_active:
              type: boolean
              description: 是否激活
            permission:
              type: string
              enum: ['view', 'edit']
              description: 权限级别
            expires_at:
              type: integer
              description: 过期时间（Unix 时间戳）
    responses:
      200:
        description: 更新后的分享信息
      403:
        description: 无权限
      404:
        description: 分享链接不存在
    """
    user_id = g.current_user_id
    
    # 查找分享并检查权限
    share = BaseShare.query.get(share_id)
    if not share:
        return not_found_response('分享链接')
    
    if not BaseService.check_permission(share.base_id, user_id, MemberRole.ADMIN):
        return forbidden_response('您没有权限更新此分享链接')
    
    data = request.get_json() or {}
    result = ShareService.update_share(str(share_id), user_id, data)
    
    if not result['success']:
        status_code = result.get('status', 400)
        if status_code == 404:
            return not_found_response('分享链接')
        return error_response(result['error'], code=status_code)
    
    return success_response(
        data=result['share'].to_dict(),
        message='分享链接更新成功'
    )


@shares_bp.route('/shares/<share_id>', methods=['DELETE'])
@jwt_required
def delete_share(share_id) -> tuple:
    """
    删除分享链接
    ---
    tags:
      - Shares
    security:
      - Bearer: []
    parameters:
      - name: share_id
        in: path
        type: string
        required: true
        description: 分享 ID
    responses:
      200:
        description: 删除成功
      403:
        description: 无权限
      404:
        description: 分享链接不存在
    """
    user_id = g.current_user_id
    
    # 查找分享并检查权限
    share = BaseShare.query.get(share_id)
    if not share:
        return not_found_response('分享链接')
    
    if not BaseService.check_permission(share.base_id, user_id, MemberRole.ADMIN):
        return forbidden_response('您没有权限删除此分享链接')
    
    result = ShareService.delete_share(str(share_id), user_id)
    
    if not result['success']:
        status_code = result.get('status', 400)
        if status_code == 404:
            return not_found_response('分享链接')
        return error_response(result['error'], code=status_code)
    
    return success_response(message='分享链接删除成功')


@shares_bp.route('/share/<share_token>', methods=['GET'])
def access_share(share_token) -> tuple:
    """
    通过分享令牌访问 Base
    ---
    tags:
      - Shares
    parameters:
      - name: share_token
        in: path
        type: string
        required: true
        description: 分享令牌
    responses:
      200:
        description: Base 信息和访问权限
      403:
        description: 分享链接已禁用或过期
      404:
        description: 分享链接不存在
    """
    result = ShareService.access_share(share_token)
    
    if not result['success']:
        status_code = result.get('status', 404)
        if status_code == 403:
            return error_response(result['error'], code=403)
        return not_found_response('分享链接')
    
    return success_response(
        data={
            'base': result['base'].to_dict(include_stats=True),
            'permission': result['permission'],
            'share_token': share_token
        },
        message='访问成功'
    )


@shares_bp.route('/bases/shared-with-me', methods=['GET'])
@jwt_required
def get_shared_with_me() -> tuple:
    """
    获取分享给当前用户的所有 Base
    ---
    tags:
      - Shares
    security:
      - Bearer: []
    responses:
      200:
        description: Base 列表
    """
    user_id = g.current_user_id
    
    # 查询当前用户是成员的 Base
    memberships = BaseMember.query.filter_by(user_id=str(user_id)).all()
    
    base_ids = [str(membership.base_id) for membership in memberships]
    
    if not base_ids:
        return success_response(
            data=[],
            message='暂无分享给您的 Base'
        )
    
    # 查询 Base 信息
    bases = Base.query.filter(Base.id.in_(base_ids)).all()
    bases_data = [base.to_dict(include_stats=True) for base in bases]
    
    return success_response(
        data=bases_data,
        message='获取分享给您的 Base 成功'
    )


@shares_bp.route('/bases/shared-by-me', methods=['GET'])
@jwt_required
def get_shared_by_me() -> tuple:
    """
    获取当前用户创建的所有分享
    ---
    tags:
      - Shares
    security:
      - Bearer: []
    responses:
      200:
        description: 分享列表
    """
    user_id = g.current_user_id
    
    shares_data = ShareService.get_shared_by_me(user_id)
    
    return success_response(
        data=shares_data,
        message='获取您创建的分享成功'
    )
