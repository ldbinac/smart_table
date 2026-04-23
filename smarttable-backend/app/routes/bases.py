"""
基础数据路由模块
处理 Base（工作区/数据库）的 CRUD 操作和成员管理
"""
from flask import Blueprint, request, g

from app.services.base_service import BaseService
from app.models.base import MemberRole
from app.utils.decorators import jwt_required, query_rate_limit
from app.utils.response import (
    success_response, error_response, not_found_response, 
    forbidden_response, validation_error_response
)

bases_bp = Blueprint('bases', __name__)
# 禁用严格斜杠，允许带或不带斜杠的URL
bases_bp.strict_slashes = False


@bases_bp.route('/', methods=['GET'])
@jwt_required
@query_rate_limit(max_queries=100, window=60)
def get_bases() -> tuple:
    """
    获取当前用户的所有基础数据列表
    ---
    tags:
      - Bases
    security:
      - Bearer: []
    responses:
      200:
        description: 基础数据列表
    """
    user_id = g.current_user_id
    bases = BaseService.get_all_bases(user_id)
    
    # 转换为字典列表
    bases_data = [base.to_dict(include_stats=True) for base in bases]
    
    return success_response(
        data=bases_data,
        message='获取基础数据列表成功'
    )


@bases_bp.route('/', methods=['POST'])
@jwt_required
def create_base() -> tuple:
    """
    创建新基础数据
    ---
    tags:
      - Bases
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        schema:
          type: object
          properties:
            name:
              type: string
              description: 基础数据名称（可选，默认为"未命名基础数据"）
            description:
              type: string
              description: 描述（可选）
            icon:
              type: string
              description: 图标（可选）
            color:
              type: string
              description: 主题颜色（可选，默认#6366F1）
            is_personal:
              type: boolean
              description: 是否为个人空间（可选，默认False）
    responses:
      201:
        description: 创建的基础数据详情
    """
    data = request.get_json() or {}
    user_id = g.current_user_id
    
    # 验证名称长度
    name = data.get('name', '').strip()
    if name and len(name) > 100:
        return error_response('名称不能超过100个字符', code=400)
    
    # 创建基础数据
    base = BaseService.create_base(data, user_id)
    
    return success_response(
        data=base.to_dict(include_stats=True),
        message='基础数据创建成功',
        code=201
    )


@bases_bp.route('/<uuid:base_id>', methods=['GET'])
@jwt_required
def get_base(base_id) -> tuple:
    """
    获取单个基础数据详情
    ---
    tags:
      - Bases
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: 基础数据 ID
      - name: share_token
        in: query
        type: string
        description: 分享令牌（可选，用于通过分享链接访问）
    responses:
      200:
        description: 基础数据详情
      403:
        description: 无权限访问
      404:
        description: 基础数据不存在
    """
    user_id = g.current_user_id
    
    # 检查权限
    has_permission = BaseService.check_permission(str(base_id), user_id, MemberRole.VIEWER)
    
    # 如果不是成员，检查是否提供了有效的 share_token
    if not has_permission:
        share_token = request.args.get('share_token')
        if share_token:
            result = BaseService.verify_share_token_and_add_member(
                str(base_id), user_id, share_token
            )
            if result['success']:
                has_permission = True
            else:
                return forbidden_response(f'您没有权限访问此基础数据：{result.get("error", "")}')
        else:
            return forbidden_response('您没有权限访问此基础数据')
    
    base = BaseService.get_base(str(base_id))
    if not base:
        return not_found_response('基础数据')
    
    return success_response(
        data=base.to_dict(include_stats=True),
        message='获取基础数据成功'
    )


@bases_bp.route('/<uuid:base_id>', methods=['PUT'])
@jwt_required
def update_base(base_id) -> tuple:
    """
    更新基础数据
    ---
    tags:
      - Bases
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
              description: 新名称（可选）
            description:
              type: string
              description: 新描述（可选）
            icon:
              type: string
              description: 新图标（可选）
            color:
              type: string
              description: 新颜色（可选）
            is_personal:
              type: boolean
              description: 是否为个人空间（可选）
    responses:
      200:
        description: 更新后的基础数据详情
      400:
        description: 请求数据验证失败
      403:
        description: 无权限修改
      404:
        description: 基础数据不存在
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 EDITOR 或更高权限）
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限修改此基础数据')
    
    data = request.get_json() or {}
    
    # 验证名称长度
    if 'name' in data:
        name = data['name'].strip()
        if len(name) > 100:
            return error_response('名称不能超过100个字符', code=400)
        data['name'] = name
    
    base = BaseService.update_base(str(base_id), data)
    if not base:
        return not_found_response('基础数据')
    
    return success_response(
        data=base.to_dict(include_stats=True),
        message='基础数据更新成功'
    )


@bases_bp.route('/<uuid:base_id>', methods=['DELETE'])
@jwt_required
def delete_base(base_id) -> tuple:
    """
    删除基础数据（级联删除所有关联数据）
    ---
    tags:
      - Bases
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
        description: 删除成功
      403:
        description: 只有基础数据所有者可以删除
      404:
        description: 基础数据不存在
    """
    user_id = g.current_user_id
    
    # 检查权限（只有 OWNER 可以删除）
    base = BaseService.get_base(str(base_id))
    if not base:
        return not_found_response('基础数据')
    
    if str(base.owner_id) != str(user_id):
        return forbidden_response('只有基础数据所有者可以删除')
    
    success = BaseService.delete_base(str(base_id))
    if not success:
        return error_response('删除失败，请稍后重试', code=500)
    
    return success_response(message='基础数据删除成功')


@bases_bp.route('/<uuid:base_id>/star', methods=['POST'])
@jwt_required
def toggle_star(base_id) -> tuple:
    """
    切换基础数据的星标状态
    ---
    tags:
      - Bases
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
        description: 星标状态更新成功
        schema:
          type: object
          properties:
            is_starred:
              type: boolean
              description: 是否已星标
      403:
        description: 无权限访问
      404:
        description: 基础数据不存在
    """
    user_id = g.current_user_id
    
    # 检查权限
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限访问此基础数据')
    
    base = BaseService.toggle_star(str(base_id), user_id)
    if not base:
        return not_found_response('基础数据')
    
    return success_response(
        data={'is_starred': base.is_starred},
        message='星标状态更新成功'
    )


@bases_bp.route('/<uuid:base_id>/members', methods=['GET'])
@jwt_required
def get_members(base_id) -> tuple:
    """
    获取基础数据的所有成员
    ---
    tags:
      - Bases
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
        description: 成员列表
      403:
        description: 无权限访问
      404:
        description: 基础数据不存在
    """
    user_id = g.current_user_id
    
    # 检查权限
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限访问此基础数据')
    
    base = BaseService.get_base(str(base_id))
    if not base:
        return not_found_response('基础数据')
    
    members = BaseService.get_members(str(base_id))
    
    # 查找所有者是否已存在于成员列表中
    owner_index = None
    for idx, member in enumerate(members):
        if member.get('role') == 'owner' or member.get('user_id') == str(base.owner_id):
            owner_index = idx
            break
    
    if owner_index is not None:
        # 如果所有者已存在，将其移到第一位
        owner_data = members.pop(owner_index)
        members = [owner_data] + members
    else:
        # 如果成员列表中不包含所有者，则手动添加
        owner_data = {
            'id': None,
            'base_id': str(base_id),
            'user_id': str(base.owner_id),
            'role': 'owner',
            'invited_by': None,
            'joined_at': base.created_at.isoformat(),
            'user': base.owner.to_dict()
        }
        members = [owner_data] + members
    
    return success_response(
        data=members,
        message='获取成员列表成功'
    )


@bases_bp.route('/<uuid:base_id>/members', methods=['POST'])
@jwt_required
def add_member(base_id) -> tuple:
    """
    添加成员到基础数据
    ---
    tags:
      - Bases
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
            - email
          properties:
            email:
              type: string
              description: 被邀请用户邮箱
              example: "user@example.com"
            role:
              type: string
              enum: ['admin', 'editor', 'commenter', 'viewer']
              default: 'editor'
              description: 角色（可选，默认为 editor）
    responses:
      201:
        description: 新添加的成员信息
      400:
        description: 请求数据验证失败
      403:
        description: 无权限添加成员
      404:
        description: 基础数据不存在
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 ADMIN 或更高权限）
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.ADMIN):
        return forbidden_response('您没有权限添加成员')
    
    data = request.get_json() or {}
    
    # 验证必填字段
    email = data.get('email', '').strip().lower()
    if not email:
        return error_response('请提供被邀请用户的邮箱地址', code=400)
    
    role = data.get('role', 'editor').strip().lower()
    
    # 添加成员
    result = BaseService.add_member(
        base_id=str(base_id),
        email=email,
        role=role,
        invited_by=user_id
    )
    
    if not result['success']:
        return error_response(result['error'], code=400)
    
    return success_response(
        data=result['member'],
        message='添加成员成功',
        code=201
    )


@bases_bp.route('/<uuid:base_id>/members/batch', methods=['POST'])
@jwt_required
def batch_add_members(base_id) -> tuple:
    """
    批量添加成员到基础数据
    ---
    tags:
      - Bases
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
            - members
          properties:
            members:
              type: array
              description: 成员列表（最多100个）
              items:
                type: object
                properties:
                  email:
                    type: string
                    description: 被邀请用户邮箱
                  role:
                    type: string
                    enum: ['admin', 'editor', 'commenter', 'viewer']
                    default: 'editor'
                    description: 角色
    responses:
      200:
        description: 添加结果统计和失败的成员列表
      400:
        description: 请求数据验证失败
      403:
        description: 无权限添加成员
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 ADMIN 或更高权限）
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.ADMIN):
        return forbidden_response('您没有权限添加成员')
    
    data = request.get_json() or {}
    members_data = data.get('members', [])
    
    if not members_data or not isinstance(members_data, list):
        return error_response('请提供成员列表', code=400)
    
    if len(members_data) > 100:
        return error_response('一次最多只能添加 100 个成员', code=400)
    
    results = {
        'success_count': 0,
        'failed_count': 0,
        'successful': [],
        'failed': []
    }
    
    for idx, member_data in enumerate(members_data):
        try:
            # 验证必填字段
            email = member_data.get('email', '').strip().lower()
            if not email:
                results['failed'].append({
                    'index': idx,
                    'email': member_data.get('email', '未知'),
                    'error': '邮箱地址不能为空'
                })
                results['failed_count'] += 1
                continue
            
            role = member_data.get('role', 'editor').strip().lower()
            
            # 添加成员
            member_result = BaseService.add_member(
                base_id=str(base_id),
                email=email,
                role=role,
                invited_by=user_id
            )
            
            if member_result['success']:
                results['successful'].append(member_result['member'])
                results['success_count'] += 1
            else:
                results['failed'].append({
                    'index': idx,
                    'email': email,
                    'error': member_result['error']
                })
                results['failed_count'] += 1
                
        except Exception as e:
            results['failed'].append({
                'index': idx,
                'email': member_data.get('email', '未知'),
                'error': str(e)
            })
            results['failed_count'] += 1
    
    return success_response(
        data=results,
        message=f'批量添加完成：成功 {results["success_count"]} 个，失败 {results["failed_count"]} 个'
    )


@bases_bp.route('/<uuid:base_id>/members/<uuid:user_id>', methods=['PUT'])
@jwt_required
def update_member(base_id, user_id) -> tuple:
    """
    更新成员角色
    ---
    tags:
      - Bases
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: 基础数据 ID
      - name: user_id
        in: path
        type: string
        required: true
        description: 成员用户 ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - role
          properties:
            role:
              type: string
              enum: ['admin', 'editor', 'commenter', 'viewer']
              description: 新角色
    responses:
      200:
        description: 更新后的成员信息
      400:
        description: 请求数据验证失败
      403:
        description: 无权限修改成员角色
      404:
        description: 基础数据或成员不存在
    """
    current_user_id = g.current_user_id
    
    # 检查权限（需要 ADMIN 或更高权限）
    if not BaseService.check_permission(str(base_id), current_user_id, MemberRole.ADMIN):
        return forbidden_response('您没有权限修改成员角色')
    
    # 不能修改自己的角色
    if str(user_id) == str(current_user_id):
        return error_response('不能修改自己的角色', code=400)
    
    data = request.get_json() or {}
    role = data.get('role', '').strip().lower()
    
    if not role:
        return error_response('请提供新角色', code=400)
    
    result = BaseService.update_member_role(
        base_id=str(base_id),
        user_id=str(user_id),
        new_role=role,
        updated_by=str(current_user_id)
    )
    
    if not result['success']:
        return error_response(result['error'], code=400)
    
    return success_response(
        data=result['member'],
        message='成员角色更新成功'
    )


@bases_bp.route('/<uuid:base_id>/members/<uuid:user_id>', methods=['DELETE'])
@jwt_required
def remove_member(base_id, user_id) -> tuple:
    """
    从基础数据中移除成员
    ---
    tags:
      - Bases
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: 基础数据 ID
      - name: user_id
        in: path
        type: string
        required: true
        description: 要移除的用户 ID
    responses:
      200:
        description: 成员移除成功
      400:
        description: 不能移除自己或所有者
      403:
        description: 无权限移除成员
      404:
        description: 基础数据或成员不存在
    """
    current_user_id = g.current_user_id
    
    # 检查权限（需要 ADMIN 或更高权限）
    if not BaseService.check_permission(str(base_id), current_user_id, MemberRole.ADMIN):
        return forbidden_response('您没有权限移除成员')
    
    # 不能移除自己
    if str(user_id) == str(current_user_id):
        return error_response('不能移除自己，如需退出请使用其他方式', code=400)
    
    # 不能移除所有者
    base = BaseService.get_base(str(base_id))
    if base and str(base.owner_id) == str(user_id):
        return error_response('不能移除基础数据所有者', code=400)
    
    success = BaseService.remove_member(str(base_id), str(user_id), removed_by=str(current_user_id))
    if not success:
        return error_response('成员不存在或移除失败', code=400)
    
    return success_response(message='成员移除成功')


@bases_bp.route('/<uuid:base_id>/copy', methods=['POST'])
@jwt_required
def copy_base(base_id) -> tuple:
    """
    复制基础数据（多维表格）
    ---
    tags:
      - Bases
    security:
      - Bearer: []
    description: |
      复制内容包括：Base 基本信息、所有数据表结构及字段配置、所有数据记录、所有视图配置、所有仪表盘配置
      排除内容：分享设置、访问权限设置、评论及协作历史记录
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: 源基础数据 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            name:
              type: string
              description: 新基础数据名称（可选，默认为"原名称+副本"）
    responses:
      201:
        description: 复制后的新基础数据详情
      403:
        description: 无权限复制
      404:
        description: 基础数据不存在
    """
    user_id = g.current_user_id
    
    # 检查权限（需要 VIEWER 或更高权限）
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限复制此基础数据')
    
    data = request.get_json() or {}
    new_name = data.get('name', '').strip()
    
    # 调用复制服务
    result = BaseService.copy_base(
        base_id=str(base_id),
        user_id=user_id,
        new_name=new_name if new_name else None
    )
    
    if not result['success']:
        return error_response(result['error'], code=400)
    
    return success_response(
        data=result['base'],
        message='复制成功',
        code=201
    )
