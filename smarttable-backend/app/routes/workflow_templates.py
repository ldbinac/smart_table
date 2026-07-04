"""
工作流模板路由模块
处理工作流模板的列表查询、保存为模板以及从模板创建工作流
"""
from flask import Blueprint, request, g

from app.services.workflow_template_service import WorkflowTemplateService
from app.utils.decorators import jwt_required
from app.utils.response import (
    success_response, error_response, not_found_response,
    forbidden_response, paginated_response
)

workflow_templates_bp = Blueprint('workflow_templates', __name__)
# 禁用严格斜杠，允许带或不带斜杠的URL
workflow_templates_bp.strict_slashes = False


def _parse_bool(value):
    """将字符串查询参数解析为布尔值"""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('true', '1', 'yes', 'on')


@workflow_templates_bp.route('/', methods=['GET'])
@jwt_required
def list_workflow_templates() -> tuple:
    """
    获取工作流模板列表
    ---
    tags:
      - Workflow Templates
    security:
      - Bearer: []
    parameters:
      - name: category
        in: query
        type: string
        description: 按分类筛选（可选）
      - name: is_system
        in: query
        type: boolean
        description: 是否只显示系统模板（可选）
      - name: page
        in: query
        type: integer
        default: 1
        description: 页码（可选）
      - name: per_page
        in: query
        type: integer
        default: 20
        description: 每页数量（可选）
    responses:
      200:
        description: 工作流模板列表
    """
    category = request.args.get('category')
    is_system = _parse_bool(request.args.get('is_system'))

    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
    except (TypeError, ValueError):
        return error_response('分页参数必须是整数', code=400)

    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 1
    if per_page > 100:
        per_page = 100

    result = WorkflowTemplateService.list_templates(
        category=category,
        is_system=is_system,
        page=page,
        per_page=per_page
    )

    return paginated_response(
        items=result['items'],
        total=result['total'],
        page=result['page'],
        per_page=result['per_page'],
        message='获取工作流模板列表成功'
    )


@workflow_templates_bp.route('/', methods=['POST'])
@jwt_required
def save_workflow_as_template() -> tuple:
    """
    将工作流保存为模板
    ---
    tags:
      - Workflow Templates
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - workflow_id
            - name
          properties:
            workflow_id:
              type: string
              description: 工作流 ID
            name:
              type: string
              description: 模板名称
            description:
              type: string
              description: 模板描述（可选）
            category:
              type: string
              description: 模板分类（可选）
    responses:
      201:
        description: 模板创建成功
      400:
        description: 请求参数错误
      403:
        description: 无权限保存模板
      404:
        description: 工作流不存在
    """
    data = request.get_json() or {}
    user_id = g.current_user_id

    workflow_id = data.get('workflow_id')
    name = data.get('name', '').strip() if data.get('name') else ''
    description = data.get('description')
    category = data.get('category')

    if not workflow_id:
        return error_response('请提供工作流 ID', code=400)
    if not name:
        return error_response('请提供模板名称', code=400)
    if len(name) > 200:
        return error_response('模板名称不能超过200个字符', code=400)

    template_id = WorkflowTemplateService.save_as_template(
        workflow_id=workflow_id,
        name=name,
        description=description,
        category=category,
        created_by=user_id
    )

    if not template_id:
        return error_response('保存模板失败，请检查工作流是否存在或是否有权限', code=403)

    return success_response(
        data={'template_id': str(template_id)},
        message='工作流已保存为模板',
        code=201
    )


@workflow_templates_bp.route('/<uuid:template_id>/instantiate', methods=['POST'])
@jwt_required
def instantiate_workflow_template(template_id) -> tuple:
    """
    从模板创建工作流
    ---
    tags:
      - Workflow Templates
    security:
      - Bearer: []
    parameters:
      - name: template_id
        in: path
        type: string
        required: true
        description: 模板 ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - table_id
          properties:
            table_id:
              type: string
              description: 表格 ID
    responses:
      201:
        description: 工作流创建成功
      400:
        description: 请求参数错误
      403:
        description: 无权限从模板创建工作流
      404:
        description: 模板或表格不存在
    """
    data = request.get_json() or {}
    user_id = g.current_user_id

    table_id = data.get('table_id')
    if not table_id:
        return error_response('请提供表格 ID', code=400)

    workflow_id = WorkflowTemplateService.create_from_template(
        template_id=template_id,
        table_id=table_id,
        created_by=user_id
    )

    if not workflow_id:
        return error_response('从模板创建工作流失败，请检查模板、表格是否存在或是否有权限', code=403)

    return success_response(
        data={'workflow_id': str(workflow_id)},
        message='已从模板创建工作流',
        code=201
    )
