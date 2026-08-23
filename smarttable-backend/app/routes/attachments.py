"""
附件路由模块
处理文件上传、下载、预览和删除
"""
import os
import traceback
from flask import Blueprint, request, g, send_file, current_app, send_from_directory

from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from app.services.attachment_service import AttachmentService
from app.services.base_service import BaseService
from app.services.form_share_service import FormShareService
from app.models.base import MemberRole
from app.utils.decorators import jwt_required, upload_rate_limit
from app.utils.response import (
    success_response, error_response, not_found_response,
    forbidden_response, paginated_response, unauthorized_response
)

attachments_bp = Blueprint('attachments', __name__)
# 禁用严格斜杠，允许带或不带斜杠的URL
attachments_bp.strict_slashes = False


@attachments_bp.route('/upload', methods=['POST'])
@upload_rate_limit(max_uploads=30, window=300)
def upload_attachment() -> tuple:
    """
    上传附件
    ---
    tags:
      - Attachments
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: 文件数据
      - name: base_id
        in: formData
        type: string
        description: 所属基础数据 ID（可选）
      - name: form_share_token
        in: formData
        type: string
        description: 表单分享令牌（开启匿名提交时用于免登录上传附件）
    responses:
      201:
        description: 上传成功的附件信息
      401:
        description: 需要登录
      403:
        description: 无权上传或该表单不允许匿名上传
    """
    # 鉴权：优先使用 JWT；匿名提交场景支持携带表单分享令牌
    user_id = None
    anonymous = False
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            user_id = str(identity)
    except Exception:
        user_id = None

    if not user_id:
        form_share_token = request.form.get('form_share_token') or request.args.get('form_share_token')
        if not form_share_token:
            return unauthorized_response('log_first')
        valid, form_share, error = FormShareService.validate_form_share(form_share_token)
        if not valid:
            status = 403 if error in ('form_share_been_invalidated', 'form_share_expired', 'submission_limit_reached') else 404
            return error_response(error or 'form_share_invalid', code=status)
        if not form_share.allow_anonymous:
            return forbidden_response('form_does_not_allow_anonymous_file_uploads')
        user_id = str(form_share.created_by)
        anonymous = True

    # 检查是否有文件
    if 'file' not in request.files:
        return error_response('select_file_upload', code=400)
    
    file = request.files['file']
    
    # 检查文件名
    if file.filename == '':
        return error_response('file_name_empty', code=400)
    
    # 获取基础数据 ID（如果有）
    base_id = request.form.get('base_id') or request.args.get('base_id')
    
    # 如果指定了基础数据，检查权限（匿名上传跳过基础数据权限校验，由表单分享授权）
    if base_id and not anonymous:
        if not BaseService.check_permission(base_id, user_id, MemberRole.EDITOR):
            return forbidden_response('do_not_permission_upload_files_base')
    
    # 准备附件数据
    data = {
        'filename': file.filename
    }
    
    try:
        # 上传附件
        attachment = AttachmentService.upload_attachment(file, data, user_id)

        return success_response(
            data={'attachment': attachment.to_dict(include_urls=True)},
            message='file_uploaded_successfully',
            code=201
        )
    except ValueError as e:
        return error_response(str(e), code=400)
    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 文件上传失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response('failed_upload_file_try_again_later', code=500, error='internal_server_error', request_id=request_id)


@attachments_bp.route('/<uuid:attachment_id>', methods=['GET'])
@jwt_required
def get_attachment(attachment_id) -> tuple:
    """
    获取附件详情
    ---
    tags:
      - Attachments
    security:
      - Bearer: []
    parameters:
      - name: attachment_id
        in: path
        type: string
        required: true
        description: 附件 ID
    responses:
      200:
        description: 附件详细信息
    """
    user_id = g.current_user_id
    
    attachment = AttachmentService.get_attachment(str(attachment_id))
    if not attachment:
        return not_found_response('attachment')

    # TODO: 需要通过 record_id 关联到基础数据进行权限检查
    # 当前简化处理：所有登录用户都可以查看附件

    return success_response(
        data=attachment.to_dict(include_urls=True),
        message='fetched_attachment_successfully'
    )


@attachments_bp.route('/<uuid:attachment_id>/download', methods=['GET'])
@jwt_required
def download_attachment(attachment_id) -> tuple:
    """
    下载附件
    ---
    tags:
      - Attachments
    security:
      - Bearer: []
    parameters:
      - name: attachment_id
        in: path
        type: string
        required: true
        description: 附件 ID
    responses:
      200:
        description: 文件下载响应
      404:
        description: 附件或文件不存在
      500:
        description: 下载失败
    """
    user_id = g.current_user_id
    
    attachment = AttachmentService.get_attachment(str(attachment_id))
    if not attachment:
        return not_found_response('attachment')

    # TODO: 需要通过 record_id 关联到基础数据进行权限检查
    # 当前简化处理：所有登录用户都可以下载附件

    # 获取文件路径
    file_info = AttachmentService.get_attachment_file(str(attachment_id))
    if not file_info:
        return error_response('file_does_not_exist_been_deleted', code=404)
    
    file_path, original_name = file_info
    
    if not os.path.exists(file_path):
        return error_response('file_does_not_exist_been_deleted', code=404)
    
    try:
        return send_file(
            file_path,
            as_attachment=True,
            download_name=original_name,
            mimetype=attachment.mime_type
        )
    except Exception as e:
        current_app.logger.error(f'文件下载失败: {str(e)}')
        return error_response('failed_download_file_try_again_later', code=500)


@attachments_bp.route('/<uuid:attachment_id>/preview', methods=['GET'])
@jwt_required
def preview_attachment(attachment_id) -> tuple:
    """
    预览附件（内联显示）
    ---
    tags:
      - Attachments
    security:
      - Bearer: []
    parameters:
      - name: attachment_id
        in: path
        type: string
        required: true
        description: 附件 ID
    responses:
      200:
        description: 文件预览响应
      400:
        description: 此文件类型不支持预览
      404:
        description: 附件或文件不存在
      500:
        description: 预览失败
    """
    user_id = g.current_user_id
    
    attachment = AttachmentService.get_attachment(str(attachment_id))
    if not attachment:
        return not_found_response('attachment')

    # TODO: 需要通过 record_id 关联到基础数据进行权限检查
    # 当前简化处理：所有登录用户都可以预览附件

    # 检查是否可以预览
    if not attachment.is_previewable():
        return error_response('file_type_does_not_support_preview', code=400)

    # 获取文件路径
    file_info = AttachmentService.get_attachment_file(str(attachment_id))
    if not file_info:
        return error_response('file_does_not_exist_been_deleted', code=404)
    
    file_path, original_name = file_info
    
    if not os.path.exists(file_path):
        return error_response('file_does_not_exist_been_deleted', code=404)
    
    try:
        return send_file(
            file_path,
            as_attachment=False,
            download_name=original_name,
            mimetype=attachment.mime_type
        )
    except Exception as e:
        current_app.logger.error(f'文件预览失败: {str(e)}')
        return error_response('failed_preview_file_try_again_later', code=500)


@attachments_bp.route('/<uuid:attachment_id>', methods=['DELETE'])
@jwt_required
def delete_attachment(attachment_id) -> tuple:
    """
    删除附件
    ---
    tags:
      - Attachments
    security:
      - Bearer: []
    parameters:
      - name: attachment_id
        in: path
        type: string
        required: true
        description: 附件 ID
    responses:
      200:
        description: 删除成功
      403:
        description: 无权限
      404:
        description: 附件不存在
      500:
        description: 删除失败
    """
    user_id = g.current_user_id
    
    attachment = AttachmentService.get_attachment(str(attachment_id))
    if not attachment:
        return not_found_response('attachment')

    # 检查权限：附件上传者可以删除
    # TODO: 需要通过 record_id 关联到基础数据进行权限检查
    can_delete = False

    if attachment.uploaded_by and str(attachment.uploaded_by) == user_id:
        can_delete = True

    if not can_delete:
        return forbidden_response('do_not_permission_delete_attachment')
    
    success = AttachmentService.delete_attachment(str(attachment_id))
    if not success:
        return error_response('deletion_failed_try_again_later', code=500)
    
    return success_response(message='attachment_deleted_successfully')


@attachments_bp.route('/bases/<uuid:base_id>', methods=['GET'])
@jwt_required
def get_base_attachments(base_id) -> tuple:
    """
    获取基础数据下的附件列表
    ---
    tags:
      - Attachments
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: 基础数据 ID
      - name: file_type
        in: query
        type: string
        description: 文件类型筛选
      - name: page
        in: query
        type: integer
        default: 1
        description: 页码
      - name: per_page
        in: query
        type: integer
        default: 20
        description: 每页数量
    responses:
      200:
        description: 附件列表（分页）
      403:
        description: 无权限
    """
    user_id = g.current_user_id
    
    # 检查权限
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.VIEWER):
        return forbidden_response('no_permission_access_base')
    
    # 获取查询参数
    file_type = request.args.get('file_type')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # 限制每页数量
    if per_page > 100:
        per_page = 100
    
    # 获取附件列表
    attachments, total = AttachmentService.get_base_attachments(
        base_id=str(base_id),
        file_type=file_type,
        page=page,
        per_page=per_page
    )
    
    # 转换为字典列表
    attachments_data = [a.to_dict(include_urls=True) for a in attachments]
    
    return paginated_response(
        items=attachments_data,
        total=total,
        page=page,
        per_page=per_page,
        message='fetched_attachment_list_successfully'
    )


@attachments_bp.route('/<uuid:attachment_id>/thumbnail', methods=['GET'])
@jwt_required
def get_thumbnail(attachment_id) -> tuple:
    """
    获取附件缩略图
    ---
    tags:
      - Attachments
    security:
      - Bearer: []
    parameters:
      - name: attachment_id
        in: path
        type: string
        required: true
        description: 附件 ID
    responses:
      200:
        description: 缩略图文件
      403:
        description: 无权限
      404:
        description: 附件或缩略图不存在
      500:
        description: 获取失败
    """
    user_id = g.current_user_id
    
    attachment = AttachmentService.get_attachment(str(attachment_id))
    if not attachment:
        return not_found_response('attachment')
    
    # 如果附件属于某个基础数据，检查权限
    if attachment.base_id:
        if not BaseService.check_permission(
            str(attachment.base_id), user_id, MemberRole.VIEWER
        ):
            return forbidden_response('do_not_permission_view_attachment')
    
    # 检查是否有缩略图
    if not attachment.thumbnail_url:
        return error_response('file_no_thumbnail', code=404)
    
    # 获取缩略图路径
    thumbnail_filename = os.path.basename(attachment.thumbnail_url)
    thumbnail_path = AttachmentService.get_file_path(thumbnail_filename)
    
    if not os.path.exists(thumbnail_path):
        return error_response('thumbnail_does_not_exist', code=404)
    
    try:
        return send_file(
            thumbnail_path,
            mimetype='image/jpeg'
        )
    except Exception as e:
        current_app.logger.error(f'缩略图获取失败: {str(e)}')
        return error_response('failed_fetch_thumbnail', code=500)


@attachments_bp.route('/uploads/<path:filename>', methods=['GET'])
def serve_uploaded_file(filename) -> tuple:
    """
    提供上传文件的静态访问
    ---
    tags:
      - Attachments
    parameters:
      - name: filename
        in: path
        type: string
        required: true
        description: 文件路径（包含子目录）
    responses:
      200:
        description: 文件内容
      403:
        description: 无效的文件路径
      404:
        description: 文件不存在
      500:
        description: 访问失败
    """
    upload_path = AttachmentService.get_upload_path()
    file_path = os.path.join(upload_path, filename)

    # 安全检查：确保文件路径在 uploads 目录内
    real_upload_path = os.path.realpath(upload_path)
    real_file_path = os.path.realpath(file_path)

    if not real_file_path.startswith(real_upload_path):
        return error_response('invalid_file_path', code=403)

    if not os.path.exists(file_path):
        return error_response('file_does_not_exist', code=404)

    try:
        directory = os.path.dirname(file_path)
        basename = os.path.basename(file_path)
        return send_from_directory(directory, basename)
    except Exception as e:
        current_app.logger.error(f'文件访问失败: {str(e)}')
        return error_response('file_access_failed', code=500)
