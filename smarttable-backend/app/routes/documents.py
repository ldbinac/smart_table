"""
文档 REST API 路由模块
提供文档的 CRUD 和导出功能
"""
import tempfile

from flask import Blueprint, request, g, send_file

from app.services.document_service import DocumentService
from app.services.document_export_service import DocumentExportService
from app.services.permission_service import PermissionService
from app.utils.response import success_response as api_response, error_response as api_error
from app.utils.decorators import jwt_required

documents_bp = Blueprint('documents', __name__, url_prefix='/api')
document_service = DocumentService()
document_export_service = DocumentExportService()
permission_service = PermissionService()


@documents_bp.route('/bases/<base_id>/documents', methods=['GET'])
@jwt_required
def get_documents(base_id):
    """获取 Base 下的文档列表"""
    try:
        user_id = g.user_id
        if not permission_service.can_access_base(user_id, base_id):
            return api_error('无权访问', 403)

        docs = document_service.get_list_by_base(base_id)
        return api_response({
            'items': [d.to_dict() for d in docs],
            'total': len(docs)
        })
    except Exception as e:
        return api_error(str(e), 500)


@documents_bp.route('/bases/<base_id>/documents', methods=['POST'])
@jwt_required
def create_document(base_id):
    """创建新文档"""
    try:
        user_id = g.user_id
        if not permission_service.can_edit_base(user_id, base_id):
            return api_error('无权编辑', 403)

        data = request.get_json()
        count = document_service.get_count_by_base(base_id)
        if count >= 10:
            return api_error('每个 Base 最多创建 10 个文档', 400)

        doc = document_service.create(
            base_id=base_id,
            name=data.get('name', '未命名文档'),
            content=data.get('content', ''),
            content_format=data.get('content_format', 'delta'),
            created_by=user_id
        )
        return api_response(doc.to_dict(include_content=True), 201)
    except Exception as e:
        return api_error(str(e), 500)


@documents_bp.route('/documents/<doc_id>', methods=['GET'])
@jwt_required
def get_document(doc_id):
    """获取单个文档详情"""
    try:
        user_id = g.user_id
        doc = document_service.get_by_id(doc_id)
        if not doc:
            return api_error('文档不存在', 404)

        if not permission_service.can_access_base(user_id, doc.base_id):
            return api_error('无权访问', 403)

        return api_response(doc.to_dict(include_content=True))
    except Exception as e:
        return api_error(str(e), 500)


@documents_bp.route('/documents/<doc_id>', methods=['PUT'])
@jwt_required
def update_document(doc_id):
    """更新文档"""
    try:
        user_id = g.user_id
        doc = document_service.get_by_id(doc_id)
        if not doc:
            return api_error('文档不存在', 404)

        if not permission_service.can_edit_base(user_id, doc.base_id):
            return api_error('无权编辑', 403)

        data = request.get_json()
        expected_updated_at = data.pop('expected_updated_at', None)

        # 乐观锁检查
        if expected_updated_at:
            current_updated_at = doc.updated_at.isoformat() if doc.updated_at else None
            if current_updated_at != expected_updated_at:
                return api_error('文档已被他人修改，请刷新后重试', 409)

        updated = document_service.update(doc_id=doc_id, user_id=user_id, **data)
        return api_response(updated.to_dict(include_content=True))
    except Exception as e:
        return api_error(str(e), 500)


@documents_bp.route('/documents/<doc_id>', methods=['DELETE'])
@jwt_required
def delete_document(doc_id):
    """删除文档"""
    try:
        user_id = g.user_id
        doc = document_service.get_by_id(doc_id)
        if not doc:
            return api_error('文档不存在', 404)

        if not permission_service.can_edit_base(user_id, doc.base_id):
            return api_error('无权编辑', 403)

        document_service.delete(doc_id)
        return api_response(None, 204)
    except Exception as e:
        return api_error(str(e), 500)


@documents_bp.route('/documents/<doc_id>/export-pdf', methods=['POST'])
@jwt_required
def export_pdf(doc_id):
    """导出 PDF"""
    try:
        user_id = g.user_id
        doc = document_service.get_by_id(doc_id)
        if not doc:
            return api_error('文档不存在', 404)

        if not permission_service.can_access_base(user_id, doc.base_id):
            return api_error('无权访问', 403)

        data = request.get_json() or {}
        export_type = data.get('export_type', 'backend')

        result = document_export_service.export_pdf(doc, export_type)

        if result['type'] == 'frontend':
            return api_response(result)

        return api_response({
            'download_url': result['download_url'],
            'filename': result['filename']
        })
    except Exception as e:
        return api_error(str(e), 500)


@documents_bp.route('/documents/<doc_id>/download-pdf', methods=['GET'])
@jwt_required
def download_pdf(doc_id):
    """下载 PDF 文件"""
    try:
        user_id = g.user_id
        doc = document_service.get_by_id(doc_id)
        if not doc:
            return api_error('文档不存在', 404)

        if not permission_service.can_access_base(user_id, doc.base_id):
            return api_error('无权访问', 403)

        html_content = document_export_service._convert_to_html(doc)

        try:
            from weasyprint import HTML as WeasyHTML
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                WeasyHTML(string=html_content).write_pdf(tmp.name)
                return send_file(
                    tmp.name,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=f'{doc.name}.pdf'
                )
        except ImportError:
            return api_error('PDF 导出功能暂不可用，请安装 WeasyPrint 依赖', 503)
    except Exception as e:
        return api_error(str(e), 500)
