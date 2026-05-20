"""
文档版本历史 REST API 路由模块
提供文档版本的查询、创建、恢复、删除功能
"""
from flask import Blueprint, request, g

from app.services.document_version_service import DocumentVersionService
from app.services.document_service import DocumentService
from app.services.permission_service import PermissionService
from app.utils.response import success_response as api_response, error_response as api_error
from app.utils.decorators import jwt_required

document_versions_bp = Blueprint('document_versions', __name__, url_prefix='/api')
document_version_service = DocumentVersionService()
document_service = DocumentService()
permission_service = PermissionService()


@document_versions_bp.route('/documents/<doc_id>/versions', methods=['GET'])
@jwt_required
def get_versions(doc_id):
    """获取文档的版本列表"""
    try:
        user_id = g.user_id
        doc = document_service.get_by_id(doc_id)
        if not doc:
            return api_error('文档不存在', 404)

        if not permission_service.can_access_base(user_id, doc.base_id):
            return api_error('无权访问', 403)

        versions = document_version_service.get_list_by_document(doc_id)
        return api_response({
            'items': [v.to_dict() for v in versions],
            'total': len(versions)
        })
    except Exception as e:
        return api_error(str(e), 500)


@document_versions_bp.route('/documents/<doc_id>/versions', methods=['POST'])
@jwt_required
def create_version(doc_id):
    """手动创建新版本"""
    try:
        user_id = g.user_id
        doc = document_service.get_by_id(doc_id)
        if not doc:
            return api_error('文档不存在', 404)

        if not permission_service.can_edit_base(user_id, doc.base_id):
            return api_error('无权编辑', 403)

        data = request.get_json()
        name = data.get('name', f'版本 #{document_version_service.get_version_count(doc_id) + 1}')
        change_summary = data.get('change_summary', '手动保存版本')

        version = document_version_service.create_version(
            document_id=doc_id,
            name=name,
            content=doc.content,
            content_format=doc.content_format,
            user_id=user_id,
            change_summary=change_summary
        )

        return api_response(version.to_dict(), 201)
    except Exception as e:
        return api_error(str(e), 500)


@document_versions_bp.route('/documents/<doc_id>/versions/<version_id>', methods=['GET'])
@jwt_required
def get_version(doc_id, version_id):
    """获取版本详情"""
    try:
        user_id = g.user_id
        doc = document_service.get_by_id(doc_id)
        if not doc:
            return api_error('文档不存在', 404)

        if not permission_service.can_access_base(user_id, doc.base_id):
            return api_error('无权访问', 403)

        version = document_version_service.get_by_id(version_id)
        if not version or str(version.document_id) != doc_id:
            return api_error('版本不存在', 404)

        result = version.to_dict()
        result['content'] = version.content

        return api_response(result)
    except Exception as e:
        return api_error(str(e), 500)


@document_versions_bp.route('/documents/<doc_id>/versions/<version_id>/restore', methods=['POST'])
@jwt_required
def restore_version(doc_id, version_id):
    """恢复到指定版本"""
    try:
        user_id = g.user_id
        doc = document_service.get_by_id(doc_id)
        if not doc:
            return api_error('文档不存在', 404)

        if not permission_service.can_edit_base(user_id, doc.base_id):
            return api_error('无权编辑', 403)

        version = document_version_service.get_by_id(version_id)
        if not version or str(version.document_id) != doc_id:
            return api_error('版本不存在', 404)

        # 恢复版本（会创建一个新版本记录）
        restored = document_version_service.restore_version(version_id, user_id)

        # 更新文档内容
        document_service.update(
            doc_id=doc_id,
            user_id=user_id,
            content=version.content,
            content_format=version.content_format
        )

        return api_response(restored.to_dict())
    except Exception as e:
        return api_error(str(e), 500)


@document_versions_bp.route('/documents/<doc_id>/versions/<version_id>', methods=['DELETE'])
@jwt_required
def delete_version(doc_id, version_id):
    """删除版本"""
    try:
        user_id = g.user_id
        doc = document_service.get_by_id(doc_id)
        if not doc:
            return api_error('文档不存在', 404)

        if not permission_service.can_edit_base(user_id, doc.base_id):
            return api_error('无权编辑', 403)

        version = document_version_service.get_by_id(version_id)
        if not version or str(version.document_id) != doc_id:
            return api_error('版本不存在', 404)

        document_version_service.delete_version(version_id)
        return api_response(None, 204)
    except Exception as e:
        return api_error(str(e), 500)
