"""
Base 分享路由模块
处理 Base 分享链接的创建、管理和访问
"""
import uuid
from datetime import datetime
from flask import Blueprint, request, g

from app.models.base import Base, MemberRole
from app.models.base_share import BaseShare, SharePermission
from app.extensions import db
from app.utils.decorators import jwt_required
from app.utils.response import (
    success_response, error_response, not_found_response,
    forbidden_response
)

shares_bp = Blueprint('shares', __name__)
shares_bp.strict_slashes = False


@shares_bp.route('/bases/<uuid:base_id>/shares', methods=['POST'])
@jwt_required
def create_share(base_id):
    """
    创建 Base 分享链接
    
    Args:
        base_id: Base ID
    
    Request Body:
        - permission: 分享权限（必填，可选值：view/edit）
        - expires_at: 过期时间（可选，Unix 时间戳）
    
    Returns:
        创建的分享信息
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 ADMIN 或更高权限）
    from app.services.base_service import BaseService
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.ADMIN):
        return forbidden_response('您没有权限创建分享链接')
    
    data = request.get_json() or {}
    
    # 验证必填字段
    permission_str = data.get('permission', 'view').strip().lower()
    if permission_str not in ['view', 'edit']:
        return error_response('权限类型必须是 view 或 edit', code=400)
    
    permission = SharePermission(permission_str)
    
    # 获取过期时间（可选）
    expires_at = data.get('expires_at')
    if expires_at is not None:
        try:
            expires_at = int(expires_at)
            # 验证过期时间不能是过去的时间
            if expires_at < int(datetime.utcnow().timestamp()):
                return error_response('过期时间不能是过去的时间', code=400)
        except (ValueError, TypeError):
            return error_response('过期时间必须是有效的 Unix 时间戳', code=400)
    
    # 生成分享令牌
    share_token = str(uuid.uuid4())
    
    # 创建分享记录
    share = BaseShare(
        base_id=str(base_id),
        share_token=share_token,
        created_by=str(user_id),
        permission=permission,
        expires_at=expires_at
    )
    
    db.session.add(share)
    db.session.commit()
    
    return success_response(
        data=share.to_dict(),
        message='分享链接创建成功',
        code=201
    )


@shares_bp.route('/bases/<uuid:base_id>/shares', methods=['GET'])
@jwt_required
def get_shares(base_id):
    """
    获取 Base 的所有分享链接列表
    
    Args:
        base_id: Base ID
    
    Returns:
        分享链接列表
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 ADMIN 或更高权限）
    from app.services.base_service import BaseService
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.ADMIN):
        return forbidden_response('您没有权限查看分享列表')
    
    # 查询所有分享
    shares = BaseShare.query.filter_by(
        base_id=str(base_id)
    ).order_by(BaseShare.created_at.desc()).all()
    
    shares_data = [share.to_dict() for share in shares]
    
    return success_response(
        data=shares_data,
        message='获取分享列表成功'
    )


@shares_bp.route('/shares/<share_id>', methods=['PUT'])
@jwt_required
def update_share(share_id):
    """
    更新分享链接（启用/禁用）
    
    Args:
        share_id: 分享 ID
    
    Request Body:
        - is_active: 是否激活（可选）
        - permission: 权限级别（可选）
        - expires_at: 过期时间（可选）
    
    Returns:
        更新后的分享信息
    """
    user_id = g.current_user_id
    
    # 查找分享
    share = BaseShare.query.get(share_id)
    if not share:
        return not_found_response('分享链接')
    
    # 检查权限（需要 ADMIN 或更高权限）
    from app.services.base_service import BaseService
    if not BaseService.check_permission(share.base_id, user_id, MemberRole.ADMIN):
        return forbidden_response('您没有权限更新此分享链接')
    
    data = request.get_json() or {}
    
    # 更新字段
    if 'is_active' in data:
        share.is_active = bool(data['is_active'])
    
    if 'permission' in data:
        permission_str = data['permission'].strip().lower()
        if permission_str in ['view', 'edit']:
            share.permission = SharePermission(permission_str)
        else:
            return error_response('权限类型必须是 view 或 edit', code=400)
    
    if 'expires_at' in data:
        if data['expires_at'] is not None:
            try:
                expires_at = int(data['expires_at'])
                if expires_at < int(datetime.utcnow().timestamp()):
                    return error_response('过期时间不能是过去的时间', code=400)
                share.expires_at = expires_at
            except (ValueError, TypeError):
                return error_response('过期时间必须是有效的 Unix 时间戳', code=400)
        else:
            share.expires_at = None
    
    share.updated_at = datetime.utcnow()
    db.session.commit()
    
    return success_response(
        data=share.to_dict(),
        message='分享链接更新成功'
    )


@shares_bp.route('/shares/<share_id>', methods=['DELETE'])
@jwt_required
def delete_share(share_id):
    user_id = g.current_user_id
    
    # 查找分享
    share = BaseShare.query.get(share_id)
    if not share:
        return not_found_response('分享链接')
    
    # 检查权限（需要 ADMIN 或更高权限）
    from app.services.base_service import BaseService
    if not BaseService.check_permission(share.base_id, user_id, MemberRole.ADMIN):
        return forbidden_response('您没有权限删除此分享链接')
    
    # 删除分享
    db.session.delete(share)
    db.session.commit()
    
    return success_response(message='分享链接删除成功')


@shares_bp.route('/share/<share_token>', methods=['GET'])
def access_share(share_token):
    """
    通过分享令牌访问 Base
    
    Args:
        share_token: 分享令牌
    
    Returns:
        Base 信息和访问权限
    """
    # 查找分享
    share = BaseShare.query.filter_by(share_token=share_token).first()
    if not share:
        return not_found_response('分享链接')
    
    # 检查分享是否激活
    if not share.is_active:
        return error_response('该分享链接已失效', code=403)
    
    # 检查是否过期
    if share.expires_at is not None:
        if int(datetime.utcnow().timestamp()) > share.expires_at:
            return error_response('该分享链接已过期', code=403)
    
    # 更新访问次数和最后访问时间
    share.access_count += 1
    share.last_accessed_at = datetime.utcnow()
    db.session.commit()
    
    # 获取 Base 信息
    base = Base.query.get(share.base_id)
    if not base:
        return not_found_response('基础数据')
    
    # 返回 Base 信息和权限
    return success_response(
        data={
            'base': base.to_dict(include_stats=True),
            'permission': share.permission.value,
            'share_token': share_token
        },
        message='访问成功'
    )


@shares_bp.route('/bases/shared-with-me', methods=['GET'])
@jwt_required
def get_shared_with_me():
    """
    获取分享给当前用户的所有 Base
    
    Returns:
        Base 列表
    """
    user_id = g.current_user_id
    
    # 查询当前用户是成员的 Base
    from app.models.base import BaseMember
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
def get_shared_by_me():
    """
    获取当前用户创建的所有分享
    
    Returns:
        分享列表
    """
    user_id = g.current_user_id
    
    # 查询当前用户创建的分享
    shares = BaseShare.query.filter_by(
        created_by=str(user_id)
    ).order_by(BaseShare.created_at.desc()).all()
    
    shares_data = []
    for share in shares:
        base = Base.query.get(share.base_id)
        if base:
            share_data = share.to_dict()
            share_data['base'] = base.to_dict(include_stats=True)
            shares_data.append(share_data)
    
    return success_response(
        data=shares_data,
        message='获取您创建的分享成功'
    )
