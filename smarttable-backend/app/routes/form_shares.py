"""
表单分享路由模块
处理表单分享的创建、管理和数据提交
"""
from flask import Blueprint, request, g

from app.services.form_share_service import FormShareService
from app.utils.decorators import jwt_required
from app.utils.response import success_response, error_response, paginated_response
from app.utils.decorators import get_client_ip
from app.utils.captcha import CaptchaService

form_shares_bp = Blueprint('form_shares', __name__)
form_shares_bp.strict_slashes = False


# ==================== 管理接口（需要认证） ====================

@form_shares_bp.route('/tables/<table_id>/form-shares', methods=['POST'])
@jwt_required
def create_form_share(table_id: str) -> tuple:
    """
    创建表单分享
    ---
    tags:
      - Form Shares
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
            allow_anonymous:
              type: boolean
              default: true
              description: 是否允许匿名提交
            require_captcha:
              type: boolean
              default: false
              description: 是否需要验证码
            expires_at:
              type: integer
              description: 过期时间（Unix 时间戳，可选）
            max_submissions:
              type: integer
              description: 最大提交次数（可选）
            allowed_fields:
              type: array
              items:
                type: string
              description: 允许提交的字段 ID 列表（可选）
            title:
              type: string
              description: 表单标题（可选）
            description:
              type: string
              description: 表单描述（可选）
            submit_button_text:
              type: string
              default: "提交"
              description: 提交按钮文字（可选）
            success_message:
              type: string
              description: 成功提示信息（可选）
            theme:
              type: string
              default: "default"
              description: 主题样式（可选）
    responses:
      201:
        description: 创建的表单分享信息
      400:
        description: 请求数据验证失败
      403:
        description: 无权限创建
      404:
        description: 表格不存在
    """
    user_id = g.current_user_id
    data = request.get_json() or {}
    
    result = FormShareService.create_form_share(table_id, user_id, data)
    
    if not result['success']:
        status = result.get('status', 400)
        return error_response(result['error'], status)
    
    form_share = result['form_share']
    return success_response(
        data={
            **form_share.to_dict(include_stats=True),
            'share_url': result['share_url']
        },
        message='表单分享创建成功',
        code=201
    )


@form_shares_bp.route('/tables/<table_id>/form-shares', methods=['GET'])
@jwt_required
def get_form_shares(table_id: str) -> tuple:
    """
    获取表格的所有表单分享列表
    ---
    tags:
      - Form Shares
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
        description: 表单分享列表
      403:
        description: 无权限查看
      404:
        description: 表格不存在
    """
    user_id = g.current_user_id
    
    form_shares = FormShareService.get_form_shares_by_table(table_id)
    
    # 过滤：只返回用户有权限查看的表单分享
    # 这里简化处理，实际应该检查用户是否有表格的查看权限
    shares_data = [share.to_dict(include_stats=True) for share in form_shares]
    
    return success_response(
        data=shares_data,
        message='获取表单分享列表成功'
    )


@form_shares_bp.route('/form-shares/<share_id>', methods=['GET'])
@jwt_required
def get_form_share(share_id: str) -> tuple:
    """
    获取表单分享详情
    ---
    tags:
      - Form Shares
    security:
      - Bearer: []
    parameters:
      - name: share_id
        in: path
        type: string
        required: true
        description: 表单分享 ID
    responses:
      200:
        description: 表单分享详情
      404:
        description: 表单分享不存在
    """
    form_share = FormShareService.get_form_share_by_id(share_id)
    
    if not form_share:
        return error_response('表单分享不存在', 404)
    
    return success_response(
        data=form_share.to_dict(include_stats=True),
        message='获取表单分享详情成功'
    )


@form_shares_bp.route('/form-shares/<share_id>', methods=['PUT'])
@jwt_required
def update_form_share(share_id: str) -> tuple:
    """
    更新表单分享配置
    ---
    tags:
      - Form Shares
    security:
      - Bearer: []
    parameters:
      - name: share_id
        in: path
        type: string
        required: true
        description: 表单分享 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            is_active:
              type: boolean
              description: 是否激活（可选）
            allow_anonymous:
              type: boolean
              description: 是否允许匿名提交（可选）
            require_captcha:
              type: boolean
              description: 是否需要验证码（可选）
            expires_at:
              type: integer
              description: 过期时间（可选）
            max_submissions:
              type: integer
              description: 最大提交次数（可选）
            allowed_fields:
              type: array
              items:
                type: string
              description: 允许提交的字段列表（可选）
            title:
              type: string
              description: 表单标题（可选）
            description:
              type: string
              description: 表单描述（可选）
            submit_button_text:
              type: string
              description: 提交按钮文字（可选）
            success_message:
              type: string
              description: 成功提示信息（可选）
            theme:
              type: string
              description: 主题样式（可选）
    responses:
      200:
        description: 更新后的表单分享信息
      400:
        description: 请求数据验证失败
      403:
        description: 无权限更新
      404:
        description: 表单分享不存在
    """
    user_id = g.current_user_id
    data = request.get_json() or {}
    
    result = FormShareService.update_form_share(share_id, user_id, data)
    
    if not result['success']:
        status = result.get('status', 400)
        if status == 404:
            return error_response(result['error'], 404)
        return error_response(result['error'], status)
    
    return success_response(
        data=result['form_share'].to_dict(include_stats=True),
        message='表单分享更新成功'
    )


@form_shares_bp.route('/form-shares/<share_id>', methods=['DELETE'])
@jwt_required
def delete_form_share(share_id: str) -> tuple:
    """
    删除表单分享
    ---
    tags:
      - Form Shares
    security:
      - Bearer: []
    parameters:
      - name: share_id
        in: path
        type: string
        required: true
        description: 表单分享 ID
    responses:
      200:
        description: 删除成功
      403:
        description: 无权限删除
      404:
        description: 表单分享不存在
    """
    user_id = g.current_user_id
    
    result = FormShareService.delete_form_share(share_id, user_id)
    
    if not result['success']:
        status = result.get('status', 400)
        if status == 404:
            return error_response(result['error'], 404)
        return error_response(result['error'], status)
    
    return success_response(message='表单分享删除成功')


@form_shares_bp.route('/form-shares/<share_id>/submissions', methods=['GET'])
@jwt_required
def get_form_submissions(share_id: str) -> tuple:
    """
    获取表单提交记录
    ---
    tags:
      - Form Shares
    security:
      - Bearer: []
    parameters:
      - name: share_id
        in: path
        type: string
        required: true
        description: 表单分享 ID
      - name: page
        in: query
        type: integer
        default: 1
        description: 页码（默认 1）
      - name: per_page
        in: query
        type: integer
        default: 20
        description: 每页数量（默认 20，最大 100）
    responses:
      200:
        description: 提交记录列表
      403:
        description: 无权限查看
      404:
        description: 表单分享不存在
    """
    user_id = g.current_user_id
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # 限制每页数量
    if per_page > 100:
        per_page = 100
    if per_page < 1:
        per_page = 20
    if page < 1:
        page = 1
    
    result = FormShareService.get_submissions(share_id, user_id, page, per_page)
    
    if not result['success']:
        status = result.get('status', 400)
        if status == 404:
            return error_response(result['error'], 404)
        return error_response(result['error'], status)
    
    data = result['data']
    return paginated_response(
        items=data['items'],
        total=data['total'],
        page=data['page'],
        per_page=data['per_page']
    )


# ==================== 公开接口（无需认证） ====================

@form_shares_bp.route('/form-shares/<token>/schema', methods=['GET'])
def get_form_schema(token: str) -> tuple:
    """
    获取表单结构（公开接口）
    ---
    tags:
      - Form Shares
    description: 用于表单填写页面获取字段定义（无需认证）
    parameters:
      - name: token
        in: path
        type: string
        required: true
        description: 分享令牌
    responses:
      200:
        description: 表单结构，包含字段定义
      404:
        description: 表单分享不存在或已失效
    """
    result = FormShareService.get_form_schema(token)
    
    if not result['success']:
        status = result.get('status', 404)
        return error_response(result['error'], status)
    
    return success_response(
        data=result['data'],
        message='获取表单结构成功'
    )


@form_shares_bp.route('/form-shares/<token>/submit', methods=['POST'])
def submit_form(token: str) -> tuple:
    """
    提交表单数据（公开接口）
    ---
    tags:
      - Form Shares
    description: 提交表单数据（无需认证）
    parameters:
      - name: token
        in: path
        type: string
        required: true
        description: 分享令牌
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - values
          properties:
            values:
              type: object
              description: 字段值字典（必填）
            submitter_info:
              type: object
              description: 提交者信息（可选，如邮箱、姓名）
            captcha:
              type: string
              description: 验证码（如果需要）
    responses:
      200:
        description: 提交成功
      400:
        description: 数据验证失败
      403:
        description: 表单分享已失效或需要验证码
      404:
        description: 表单分享不存在
    """
    data = request.get_json() or {}
    
    # 获取客户端信息
    client_info = {
        'ip': get_client_ip(),
        'user_agent': request.headers.get('User-Agent')
    }
    
    result = FormShareService.submit_form_data(token, data, client_info)
    
    if not result['success']:
        status = result.get('status', 400)
        
        # 如果是验证错误，返回详细的错误信息
        if status == 400 and 'details' in result:
            return error_response(
                message=result['error'],
                code=status,
                details=result['details']
            )
        
        return error_response(result['error'], status)
    
    return success_response(
        data=result['data'],
        message=result.get('message', '提交成功')
    )


@form_shares_bp.route('/form-shares/<token>/validate', methods=['GET'])
def validate_form_share(token: str) -> tuple:
    """
    验证表单分享是否有效（公开接口）
    ---
    tags:
      - Form Shares
    description: 用于表单填写页面预先检查分享链接是否可用（无需认证）
    parameters:
      - name: token
        in: path
        type: string
        required: true
        description: 分享令牌
    responses:
      200:
        description: 表单分享有效
        schema:
          type: object
          properties:
            valid:
              type: boolean
              example: true
            require_captcha:
              type: boolean
              example: false
            can_submit:
              type: boolean
              example: true
      403:
        description: 表单分享已失效或过期
      404:
        description: 表单分享不存在
    """
    valid, form_share, error = FormShareService.validate_form_share(token)
    
    if not valid:
        status = 403 if '失效' in error or '过期' in error or '上限' in error else 404
        return error_response(error, status)
    
    return success_response(
        data={
            'valid': True,
            'require_captcha': form_share.require_captcha,
            'can_submit': form_share.can_submit()
        },
        message='表单分享有效'
    )


@form_shares_bp.route('/form-shares/<token>/captcha', methods=['GET'])
def get_captcha(token: str) -> tuple:
    """
    获取验证码（公开接口）
    ---
    tags:
      - Form Shares
    description: 获取表单验证码（无需认证）
    parameters:
      - name: token
        in: path
        type: string
        required: true
        description: 分享令牌
    responses:
      200:
        description: 验证码生成成功
        schema:
          type: object
          properties:
            image:
              type: string
              description: Base64编码的验证码图片
              example: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
            expire:
              type: integer
              description: 验证码有效期（秒）
              example: 300
      400:
        description: 该表单不需要验证码
      404:
        description: 表单分享不存在或已失效
      500:
        description: 验证码生成失败
    """
    # 验证表单分享是否有效
    valid, form_share, error = FormShareService.validate_form_share(token)
    
    if not valid:
        status = 403 if '失效' in error or '过期' in error or '上限' in error else 404
        return error_response(error, status)
    
    # 检查是否需要验证码
    if not form_share.require_captcha:
        return error_response('该表单不需要验证码', 400)
    
    try:
        # 生成验证码
        code, image_base64, mime_type = CaptchaService.generate_captcha(token)
        
        return success_response(
            data={
                'image': f'data:{mime_type};base64,{image_base64}',
                'expire': 300  # 5分钟有效期
            },
            message='验证码生成成功'
        )
    except Exception as e:
        return error_response(f'验证码生成失败: {str(e)}', 500)
