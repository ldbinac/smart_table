"""
附件路由模块
处理文件上传、下载、预览和删除
"""
import os
from flask import Blueprint, request, g, send_file, current_app

from app.services.attachment_service import AttachmentService
from app.services.base_service import BaseService
from app.models.base import MemberRole
from app.utils.decorators import jwt_required, upload_rate_limit
from app.utils.response import (
    success_response, error_response, not_found_response,
    forbidden_response, paginated_response
)

attachments_bp = Blueprint('attachments', __name__)
# 禁用严格斜杠，允许带或不带斜杠的URL
attachments_bp.strict_slashes = False


@attachments_bp.route('/upload', methods=['POST'])
@jwt_required
@upload_rate_limit(max_uploads=20, window=3600)
def upload_attachment() -> tuple:
    """
    上传附件
    
    支持 multipart/form-data 格式上传
    
    请求参数:
        - file: 文件数据（必填）
        - base_id: 所属基础数据 ID（可选）
        
    返回:
        上传成功的附件信息
    """
    user_id = g.current_user_id
    
    # 检查是否有文件
    if 'file' not in request.files:
        return error_response('请选择要上传的文件', code=400)
    
    file = request.files['file']
    
    # 检查文件名
    if file.filename == '':
        return error_response('文件名不能为空', code=400)
    
    # 获取基础数据 ID（如果有）
    base_id = request.form.get('base_id') or request.args.get('base_id')
    
    # 如果指定了基础数据，检查权限
    if base_id:
        if not BaseService.check_permission(base_id, user_id, MemberRole.EDITOR):
            return forbidden_response('您没有权限上传文件到此基础数据')
    
    # 准备附件数据
    data = {
        'filename': file.filename,
        'base_id': base_id
    }
    
    try:
        # 上传附件
        attachment = AttachmentService.upload_attachment(file, data, user_id)
        
        return success_response(
            data=attachment.to_dict(include_urls=True),
            message='文件上传成功',
            code=201
        )
    except ValueError as e:
        return error_response(str(e), code=400)
    except Exception as e:
        current_app.logger.error(f'文件上传失败: {str(e)}')
        return error_response('文件上传失败，请稍后重试', code=500)


@attachments_bp.route('/<uuid:attachment_id>', methods=['GET'])
@jwt_required
def get_attachment(attachment_id) -> tuple:
    """
    获取附件详情
    
    参数:
        attachment_id: 附件 ID
        
    返回:
        附件详细信息
    """
    user_id = g.current_user_id
    
    attachment = AttachmentService.get_attachment(str(attachment_id))
    if not attachment:
        return not_found_response('附件')
    
    # 如果附件属于某个基础数据，检查权限
    if attachment.base_id:
        if not BaseService.check_permission(
            str(attachment.base_id), user_id, MemberRole.VIEWER
        ):
            return forbidden_response('您没有权限查看此附件')
    
    return success_response(
        data=attachment.to_dict(include_urls=True),
        message='获取附件成功'
    )


@attachments_bp.route('/<uuid:attachment_id>/download', methods=['GET'])
@jwt_required
def download_attachment(attachment_id) -> tuple:
    """
    下载附件
    
    参数:
        attachment_id: 附件 ID
        
    返回:
        文件下载响应
    """
    user_id = g.current_user_id
    
    attachment = AttachmentService.get_attachment(str(attachment_id))
    if not attachment:
        return not_found_response('附件')
    
    # 如果附件属于某个基础数据，检查权限
    if attachment.base_id:
        if not BaseService.check_permission(
            str(attachment.base_id), user_id, MemberRole.VIEWER
        ):
            return forbidden_response('您没有权限下载此附件')
    
    # 获取文件路径
    file_info = AttachmentService.get_attachment_file(str(attachment_id))
    if not file_info:
        return error_response('文件不存在或已被删除', code=404)
    
    file_path, original_name = file_info
    
    if not os.path.exists(file_path):
        return error_response('文件不存在或已被删除', code=404)
    
    try:
        return send_file(
            file_path,
            as_attachment=True,
            download_name=original_name,
            mimetype=attachment.mime_type
        )
    except Exception as e:
        current_app.logger.error(f'文件下载失败: {str(e)}')
        return error_response('文件下载失败，请稍后重试', code=500)


@attachments_bp.route('/<uuid:attachment_id>/preview', methods=['GET'])
@jwt_required
def preview_attachment(attachment_id) -> tuple:
    """
    预览附件（内联显示）
    
    参数:
        attachment_id: 附件 ID
        
    返回:
        文件预览响应
    """
    user_id = g.current_user_id
    
    attachment = AttachmentService.get_attachment(str(attachment_id))
    if not attachment:
        return not_found_response('附件')
    
    # 如果附件属于某个基础数据，检查权限
    if attachment.base_id:
        if not BaseService.check_permission(
            str(attachment.base_id), user_id, MemberRole.VIEWER
        ):
            return forbidden_response('您没有权限预览此附件')
    
    # 检查是否可以预览
    if not attachment.is_previewable():
        return error_response('此文件类型不支持预览', code=400)
    
    # 获取文件路径
    file_info = AttachmentService.get_attachment_file(str(attachment_id))
    if not file_info:
        return error_response('文件不存在或已被删除', code=404)
    
    file_path, original_name = file_info
    
    if not os.path.exists(file_path):
        return error_response('文件不存在或已被删除', code=404)
    
    try:
        return send_file(
            file_path,
            as_attachment=False,
            download_name=original_name,
            mimetype=attachment.mime_type
        )
    except Exception as e:
        current_app.logger.error(f'文件预览失败: {str(e)}')
        return error_response('文件预览失败，请稍后重试', code=500)


@attachments_bp.route('/<uuid:attachment_id>', methods=['DELETE'])
@jwt_required
def delete_attachment(attachment_id) -> tuple:
    """
    删除附件
    
    参数:
        attachment_id: 附件 ID
        
    返回:
        删除结果
    """
    user_id = g.current_user_id
    
    attachment = AttachmentService.get_attachment(str(attachment_id))
    if not attachment:
        return not_found_response('附件')
    
    # 检查权限：附件上传者、基础数据编辑者或管理员可以删除
    can_delete = False
    
    if attachment.uploaded_by and str(attachment.uploaded_by) == user_id:
        can_delete = True
    elif attachment.base_id:
        if BaseService.check_permission(
            str(attachment.base_id), user_id, MemberRole.EDITOR
        ):
            can_delete = True
    
    if not can_delete:
        return forbidden_response('您没有权限删除此附件')
    
    success = AttachmentService.delete_attachment(str(attachment_id))
    if not success:
        return error_response('删除失败，请稍后重试', code=500)
    
    return success_response(message='附件删除成功')


@attachments_bp.route('/bases/<uuid:base_id>', methods=['GET'])
@jwt_required
def get_base_attachments(base_id) -> tuple:
    """
    获取基础数据下的附件列表
    
    参数:
        base_id: 基础数据 ID
        
    查询参数:
        - file_type: 文件类型筛选（可选）
        - page: 页码（可选，默认1）
        - per_page: 每页数量（可选，默认20）
        
    返回:
        附件列表（分页）
    """
    user_id = g.current_user_id
    
    # 检查权限
    if not BaseService.check_permission(str(base_id), user_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限访问此基础数据')
    
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
        message='获取附件列表成功'
    )


@attachments_bp.route('/<uuid:attachment_id>/thumbnail', methods=['GET'])
@jwt_required
def get_thumbnail(attachment_id) -> tuple:
    """
    获取附件缩略图
    
    参数:
        attachment_id: 附件 ID
        
    返回:
        缩略图文件
    """
    user_id = g.current_user_id
    
    attachment = AttachmentService.get_attachment(str(attachment_id))
    if not attachment:
        return not_found_response('附件')
    
    # 如果附件属于某个基础数据，检查权限
    if attachment.base_id:
        if not BaseService.check_permission(
            str(attachment.base_id), user_id, MemberRole.VIEWER
        ):
            return forbidden_response('您没有权限查看此附件')
    
    # 检查是否有缩略图
    if not attachment.thumbnail_url:
        return error_response('此文件没有缩略图', code=404)
    
    # 获取缩略图路径
    thumbnail_filename = os.path.basename(attachment.thumbnail_url)
    thumbnail_path = AS.get_file_path(thumbnail_filename)
    
    if not os.path.exists(thumbnail_path):
        return error_response('缩略图不存在', code=404)
    
    try:
        return send_file(
            thumbnail_path,
            mimetype='image/jpeg'
        )
    except Exception as e:
        current_app.logger.error(f'缩略图获取失败: {str(e)}')
        return error_response('缩略图获取失败', code=500)
