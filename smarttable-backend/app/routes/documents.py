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
    """
    获取 Base 下的文档列表
    ---
    tags:
      - Documents
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: 数据基础 ID
    responses:
      200:
        description: 文档列表，包含 items 和 total 字段
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 200
            data:
              type: object
              properties:
                items:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: string
                        description: 文档 ID
                      base_id:
                        type: string
                        description: 所属数据基础 ID
                      name:
                        type: string
                        description: 文档名称
                      content:
                        type: string
                        description: 文档内容
                      content_format:
                        type: string
                        enum: [delta, markdown]
                        description: 内容格式
                      order:
                        type: integer
                        description: 排序序号
                      is_pinned:
                        type: boolean
                        description: 是否置顶
                      created_by:
                        type: string
                        description: 创建者 ID
                      updated_by:
                        type: string
                        description: 最后更新者 ID
                      created_at:
                        type: string
                        format: date-time
                        description: 创建时间
                      updated_at:
                        type: string
                        format: date-time
                        description: 更新时间
                total:
                  type: integer
                  description: 文档总数
      403:
        description: 无权访问该数据基础
      500:
        description: 服务器内部错误
    """
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
    """
    创建新文档
    ---
    tags:
      - Documents
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: path
        type: string
        required: true
        description: 数据基础 ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: 文档名称（可选，默认"未命名文档"）
            content:
              type: string
              description: 文档内容（可选，默认空字符串）
            content_format:
              type: string
              enum: [delta, markdown]
              description: 内容格式（可选，默认"delta"）
    responses:
      201:
        description: 创建成功的文档详情
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 201
            data:
              type: object
              description: 完整文档对象（包含 content 字段）
      400:
        description: 每个数据基础最多创建 10 个文档
      403:
        description: 无权编辑该数据基础
      500:
        description: 服务器内部错误
    """
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
    """
    获取单个文档详情
    ---
    tags:
      - Documents
    security:
      - Bearer: []
    parameters:
      - name: doc_id
        in: path
        type: string
        required: true
        description: 文档 ID
    responses:
      200:
        description: 文档详情（包含完整内容）
      403:
        description: 无权访问该文档所在的数据基础
      404:
        description: 文档不存在
      500:
        description: 服务器内部错误
    """
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
    """
    更新文档
    ---
    tags:
      - Documents
    security:
      - Bearer: []
    parameters:
      - name: doc_id
        in: path
        type: string
        required: true
        description: 文档 ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: 文档名称
            content:
              type: string
              description: 文档内容
            content_format:
              type: string
              enum: [delta, markdown]
              description: 内容格式
            is_pinned:
              type: boolean
              description: 是否置顶
            order:
              type: integer
              description: 排序序号
            expected_updated_at:
              type: string
              format: date-time
              description: 乐观锁：上次更新时间的 ISO 格式，用于检测冲突
    responses:
      200:
        description: 更新成功的文档详情（包含完整内容）
      403:
        description: 无权编辑该文档所在的数据基础
      404:
        description: 文档不存在
      409:
        description: 文档已被他人修改，请刷新后重试（乐观锁冲突）
      500:
        description: 服务器内部错误
    """
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
    """
    删除文档
    ---
    tags:
      - Documents
    security:
      - Bearer: []
    parameters:
      - name: doc_id
        in: path
        type: string
        required: true
        description: 文档 ID
    responses:
      204:
        description: 删除成功，无返回内容
      403:
        description: 无权编辑该文档所在的数据基础
      404:
        description: 文档不存在
      500:
        description: 服务器内部错误
    """
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
    """
    导出 PDF（后端渲染或前端渲染）
    ---
    tags:
      - Documents
    security:
      - Bearer: []
    parameters:
      - name: doc_id
        in: path
        type: string
        required: true
        description: 文档 ID
      - name: body
        in: body
        required: false
        schema:
          type: object
          properties:
            export_type:
              type: string
              enum: [backend, frontend]
              description: 导出方式（可选，默认"backend"。backend 直接返回下载 URL，frontend 返回 HTML 内容供前端渲染）
    responses:
      200:
        description: 导出结果。backend 模式返回下载 URL 和文件名；frontend 模式返回 HTML 内容和文件名
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 200
            data:
              type: object
              properties:
                type:
                  type: string
                  description: 导出方式（仅 frontend 模式返回）
                html:
                  type: string
                  description: HTML 内容（仅 frontend 模式返回）
                download_url:
                  type: string
                  description: 文件下载 URL（仅 backend 模式返回）
                filename:
                  type: string
                  description: 导出文件名
      403:
        description: 无权访问该文档所在的数据基础
      404:
        description: 文档不存在
      500:
        description: 服务器内部错误
    """
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
    """
    下载 PDF 文件（后端渲染）
    ---
    tags:
      - Documents
    security:
      - Bearer: []
    parameters:
      - name: doc_id
        in: path
        type: string
        required: true
        description: 文档 ID
    responses:
      200:
        description: 返回 PDF 文件二进制流
        produces:
          - application/pdf
      403:
        description: 无权访问该文档所在的数据基础
      404:
        description: 文档不存在
      503:
        description: PDF 导出功能暂不可用，缺少 WeasyPrint 依赖
      500:
        description: 服务器内部错误
    """
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