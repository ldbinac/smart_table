"""
记录管理路由模块
"""
from flask import Blueprint, request, g, current_app
from marshmallow import Schema, fields, validate

from app.services.record_service import RecordService
from app.services.table_service import TableService
from app.services.formula_service import FormulaService
from app.services.link_service import LinkService
from app.services.field_service import FieldService
from app.services.permission_service import PermissionService
from app.utils.response import success_response, error_response, paginated_response
from app.utils.decorators import jwt_required, role_required
from app.models.record_history import RecordHistory
from app.models.field import FieldType
from app.models.base import MemberRole

records_bp = Blueprint('records', __name__)
# 禁用严格斜杠，允许带或不带斜杠的URL
records_bp.strict_slashes = False


class RecordCreateSchema(Schema):
    """记录创建验证模式"""
    values = fields.Dict(required=True, error_messages={'required': '字段值不能为空'})


class RecordUpdateSchema(Schema):
    """记录更新验证模式"""
    values = fields.Dict(required=True, error_messages={'required': '字段值不能为空'})


class BatchCreateSchema(Schema):
    """批量创建验证模式"""
    records = fields.List(fields.Dict(), required=True, error_messages={'required': '记录列表不能为空'})


class BatchUpdateSchema(Schema):
    """批量更新验证模式"""
    record_ids = fields.List(fields.String(), required=True, error_messages={'required': '记录ID列表不能为空'})
    values = fields.Dict(required=True, error_messages={'required': '字段值不能为空'})


# 初始化验证模式
record_create_schema = RecordCreateSchema()
record_update_schema = RecordUpdateSchema()
batch_create_schema = BatchCreateSchema()
batch_update_schema = BatchUpdateSchema()


@records_bp.route('/tables/<table_id>/records', methods=['GET'])
@jwt_required
def get_records(table_id):
    """
    获取表格记录列表
    
    支持分页和搜索
    """
    # 检查表格是否存在
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)
    
    # 资源级权限检查
    if not PermissionService.check_permission(
        str(table.base_id), g.current_user.id, MemberRole.VIEWER
    ):
        return error_response('无权访问该表格', 403)
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    
    # 限制每页数量
    if per_page > 100:
        per_page = 100
    
    try:
        if search:
            # 搜索记录
            records = RecordService.search_records(table_id, search)
            total = len(records)
            # 手动分页
            start = (page - 1) * per_page
            end = start + per_page
            records = records[start:end]
        else:
            # 分页查询
            records, total = RecordService.get_table_records(
                table_id, page=page, per_page=per_page
            )
        
        # 获取表格的所有关联字段（支持 'link' 和 'link_to_record' 两种类型）
        link_fields = FieldService.get_fields_by_type(table_id, FieldType.LINK_TO_RECORD.value)
        link_fields_link = FieldService.get_fields_by_type(table_id, 'link')
        link_fields = link_fields + link_fields_link
        
        # 序列化记录数据
        items = []
        for record in records:
            item = record.to_dict()
            
            # 填充关联字段数据
            if link_fields:
                record_links = LinkService.get_record_links(str(record.id))
                for field in link_fields:
                    field_id = str(field.id)
                    if field_id in record_links:
                        # 获取关联的记录ID列表
                        linked_ids = [
                            link['target_record_id'] 
                            for link in record_links[field_id]
                            if link.get('direction') == 'outgoing'
                        ]
                        item['values'][field_id] = linked_ids
            
            # 如果有公式字段，计算公式值
            item['computed_values'] = FormulaService.compute_record_formulas(
                table_id, record.values
            )
            items.append(item)
        
        return paginated_response(items, total, page, per_page)
    
    except Exception as e:
        return error_response(f'获取记录列表失败: {str(e)}', 500)


@records_bp.route('/tables/<table_id>/records', methods=['POST'])
@jwt_required
def create_record(table_id):
    """
    创建记录
    """
    # 检查表格是否存在
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)
    
    # 资源级权限检查
    if not PermissionService.check_permission(
        str(table.base_id), g.current_user.id, MemberRole.EDITOR
    ):
        return error_response('无权在该表格中创建记录', 403)
    
    # 验证请求数据
    json_data = request.get_json()
    if not json_data:
        return error_response('请求数据不能为空', 400)
    
    errors = record_create_schema.validate(json_data)
    if errors:
        return error_response('数据验证失败', 400, errors)
    
    try:
        # 创建记录
        record = RecordService.create_record(
            table_id=table_id,
            values=json_data['values'],
            created_by=g.current_user.id
        )
        
        result = record.to_dict()
        # 计算公式值
        result['computed_values'] = FormulaService.compute_record_formulas(
            table_id, record.values
        )
        
        return success_response(result, '记录创建成功', 201)
    
    except Exception as e:
        return error_response(f'创建记录失败: {str(e)}', 500)


@records_bp.route('/tables/<table_id>/records/batch', methods=['POST'])
@jwt_required
def batch_create_records(table_id):
    """
    批量创建记录
    """
    # 检查表格是否存在
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)
    
    # 资源级权限检查
    if not PermissionService.check_permission(
        str(table.base_id), g.current_user.id, MemberRole.EDITOR
    ):
        return error_response('无权在该表格中创建记录', 403)
    
    # 验证请求数据
    json_data = request.get_json()
    if not json_data:
        return error_response('请求数据不能为空', 400)
    
    errors = batch_create_schema.validate(json_data)
    if errors:
        return error_response('数据验证失败', 400, errors)
    
    records_data = json_data.get('records', [])
    if len(records_data) > 1000:
        return error_response('单次批量创建记录数量不能超过1000条', 400)
    
    try:
        created_records = []
        for record_data in records_data:
            record = RecordService.create_record(
                table_id=table_id,
                values=record_data.get('values', {}),
                created_by=g.current_user.id
            )
            created_records.append(record.to_dict())
        
        return success_response({
            'created_count': len(created_records),
            'records': created_records
        }, f'成功创建 {len(created_records)} 条记录')
    
    except Exception as e:
        return error_response(f'批量创建记录失败: {str(e)}', 500)


@records_bp.route('/records/<record_id>', methods=['GET'])
@jwt_required
def get_record(record_id):
    """
    获取记录详情
    """
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)
    
    # 资源级权限检查
    table = TableService.get_table_by_id(record.table_id)
    if table and not PermissionService.check_permission(
        str(table.base_id), g.current_user.id, MemberRole.VIEWER
    ):
        return error_response('无权访问该记录', 403)
    
    try:
        result = record.to_dict()
        # 计算公式值
        result['computed_values'] = FormulaService.compute_record_formulas(
            record.table_id, record.values
        )
        
        return success_response(result)
    except Exception as e:
        return error_response(f'获取记录详情失败: {str(e)}', 500)


@records_bp.route('/records/<record_id>', methods=['PUT'])
@jwt_required
def update_record(record_id):
    """
    更新记录
    """
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)
    
    # 资源级权限检查
    table = TableService.get_table_by_id(record.table_id)
    if table and not PermissionService.check_permission(
        str(table.base_id), g.current_user.id, MemberRole.EDITOR
    ):
        return error_response('无权修改该记录', 403)
    
    # 验证请求数据
    json_data = request.get_json()
    if not json_data:
        return error_response('请求数据不能为空', 400)
    
    errors = record_update_schema.validate(json_data)
    if errors:
        return error_response('数据验证失败', 400, errors)
    
    try:
        record = RecordService.update_record(
            record=record,
            values=json_data['values'],
            updated_by=g.current_user.id
        )
        
        result = record.to_dict()
        # 计算公式值
        result['computed_values'] = FormulaService.compute_record_formulas(
            record.table_id, record.values
        )
        
        return success_response(result, '记录更新成功')
    
    except Exception as e:
        return error_response(f'更新记录失败: {str(e)}', 500)


@records_bp.route('/records/batch', methods=['PUT'])
@jwt_required
def batch_update_records():
    """
    批量更新记录
    """
    # 验证请求数据
    json_data = request.get_json()
    if not json_data:
        return error_response('请求数据不能为空', 400)
    
    errors = batch_update_schema.validate(json_data)
    if errors:
        return error_response('数据验证失败', 400, errors)
    
    record_ids = json_data.get('record_ids', [])
    values = json_data.get('values', {})
    
    if len(record_ids) > 1000:
        return error_response('单次批量更新记录数量不能超过1000条', 400)
    
    # 收集所有记录的 base_id 并进行权限检查
    base_ids_checked = set()
    for record_id in record_ids:
        record = RecordService.get_record_by_id(record_id)
        if record:
            table = TableService.get_table_by_id(record.table_id)
            if table and str(table.base_id) not in base_ids_checked:
                if not PermissionService.check_permission(
                    str(table.base_id), g.current_user.id, MemberRole.EDITOR
                ):
                    return error_response(f'无权修改表格 {table.base_id} 中的记录', 403)
                base_ids_checked.add(str(table.base_id))
    
    try:
        updated_count = 0
        failed_ids = []
        
        for record_id in record_ids:
            record = RecordService.get_record_by_id(record_id)
            if record:
                RecordService.update_record(
                    record=record,
                    values=values,
                    updated_by=g.current_user.id
                )
                updated_count += 1
            else:
                failed_ids.append(record_id)
        
        return success_response({
            'updated_count': updated_count,
            'failed_ids': failed_ids
        }, f'成功更新 {updated_count} 条记录')
    
    except Exception as e:
        return error_response(f'批量更新记录失败: {str(e)}', 500)


@records_bp.route('/records/<record_id>', methods=['DELETE'])
@jwt_required
def delete_record(record_id):
    """
    删除记录
    """
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)
    
    # 资源级权限检查
    table = TableService.get_table_by_id(record.table_id)
    if table and not PermissionService.check_permission(
        str(table.base_id), g.current_user.id, MemberRole.EDITOR
    ):
        return error_response('无权删除该记录', 403)
    
    try:
        success = RecordService.delete_record(record)
        if success:
            return success_response(None, '记录删除成功')
        else:
            return error_response('删除记录失败', 500)
    
    except Exception as e:
        return error_response(f'删除记录失败: {str(e)}', 500)


@records_bp.route('/records/batch', methods=['DELETE'])
@jwt_required
def batch_delete_records():
    """
    批量删除记录
    """
    # 验证请求数据
    json_data = request.get_json()
    if not json_data:
        return error_response('请求数据不能为空', 400)
    
    record_ids = json_data.get('record_ids', [])
    if not record_ids:
        return error_response('记录ID列表不能为空', 400)
    
    if len(record_ids) > 1000:
        return error_response('单次批量删除记录数量不能超过1000条', 400)
    
    # 收集所有记录的 base_id 并进行权限检查
    base_ids_checked = set()
    for record_id in record_ids:
        record = RecordService.get_record_by_id(record_id)
        if record:
            table = TableService.get_table_by_id(record.table_id)
            if table and str(table.base_id) not in base_ids_checked:
                if not PermissionService.check_permission(
                    str(table.base_id), g.current_user.id, MemberRole.EDITOR
                ):
                    return error_response(f'无权删除表格 {table.base_id} 中的记录', 403)
                base_ids_checked.add(str(table.base_id))
    
    try:
        deleted_count = 0
        failed_ids = []
        
        for record_id in record_ids:
            record = RecordService.get_record_by_id(record_id)
            if record:
                success = RecordService.delete_record(record)
                if success:
                    deleted_count += 1
                else:
                    failed_ids.append(record_id)
            else:
                failed_ids.append(record_id)
        
        return success_response({
            'deleted_count': deleted_count,
            'failed_ids': failed_ids
        }, f'成功删除 {deleted_count} 条记录')
    
    except Exception as e:
        return error_response(f'批量删除记录失败: {str(e)}', 500)


@records_bp.route('/records/<record_id>/compute', methods=['POST'])
@jwt_required
@role_required(['owner', 'admin', 'editor', 'commenter', 'viewer'])
def compute_formulas(record_id):
    """
    计算记录的公式值
    
    用于实时预览公式计算结果
    """
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)
    
    # 获取预览值（可能包含未保存的修改）
    json_data = request.get_json() or {}
    preview_values = json_data.get('preview_values', {})
    
    # 合并预览值和实际值
    values = {**(record.values or {}), **preview_values}
    
    try:
        computed_values = FormulaService.compute_record_formulas(
            record.table_id, values
        )
        
        return success_response({
            'computed_values': computed_values
        })
    
    except Exception as e:
        return error_response(f'公式计算失败: {str(e)}', 500)


@records_bp.route('/records/<record_id>/history', methods=['GET'])
@jwt_required
@role_required(['owner', 'admin', 'editor', 'commenter', 'viewer'])
def get_record_history(record_id):
    """
    获取记录变更历史
    
    支持分页查询，按时间倒序排列
    """
    # 检查记录是否存在
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 20, type=int)
    
    # 限制每页数量
    if size > 100:
        size = 100
    if size < 1:
        size = 20
    if page < 1:
        page = 1
    
    try:
        # 查询变更历史，按时间倒序
        from app.extensions import db
        
        query = RecordHistory.query.filter_by(record_id=record_id) \
            .order_by(RecordHistory.changed_at.desc())
        
        # 获取总数
        total = query.count()
        
        # 分页
        histories = query.offset((page - 1) * size).limit(size).all()
        
        # 序列化
        items = [h.to_dict() for h in histories]
        
        return paginated_response(items, total, page, size)
    
    except Exception as e:
        return error_response(f'获取变更历史失败: {str(e)}', 500)


# ==================== 关联记录 API ====================

@records_bp.route('/records/<record_id>/links', methods=['GET'])
@jwt_required
@role_required(['owner', 'admin', 'editor', 'commenter', 'viewer'])
def get_record_links(record_id):
    """
    获取记录的关联数据
    
    返回该记录所有关联字段的关联数据
    
    Args:
        record_id: 记录 ID
    
    Returns:
        关联数据，按 outbound 和 inbound 分组
    """
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)
    
    try:
        # 获取记录的所有关联信息
        links = LinkService.get_record_links(record_id)
        
        # 转换为前端期望的格式
        outbound = []
        inbound = []
        
        for field_id, link_list in links.items():
            for link in link_list:
                if link.get('direction') == 'outgoing':
                    # 找到或创建 outbound 条目
                    existing = next((o for o in outbound if o['field_id'] == field_id), None)
                    if not existing:
                        field = FieldService.get_field(field_id)
                        existing = {
                            'field_id': field_id,
                            'field_name': field.name if field else '未知字段',
                            'target_table_id': str(field.config.get('linkedTableId')) if field and field.config else None,
                            'target_table_name': None,
                            'linked_records': []
                        }
                        outbound.append(existing)
                    existing['linked_records'].append({
                        'record_id': link['target_record_id'],
                        'display_value': link.get('target_record') or link['target_record_id']
                    })
                elif link.get('direction') == 'incoming':
                    # 找到或创建 inbound 条目
                    existing = next((i for i in inbound if i['field_id'] == field_id), None)
                    if not existing:
                        field = FieldService.get_field(field_id)
                        existing = {
                            'field_id': field_id,
                            'field_name': field.name if field else '未知字段',
                            'source_table_id': None,
                            'source_table_name': None,
                            'linked_records': []
                        }
                        inbound.append(existing)
                    existing['linked_records'].append({
                        'record_id': link['source_record_id'],
                        'display_value': link.get('source_record') or link['source_record_id']
                    })
        
        return success_response(
            data={'outbound': outbound, 'inbound': inbound},
            message='获取关联数据成功'
        )
    
    except Exception as e:
        return error_response(f'获取关联数据失败: {str(e)}', 500)


@records_bp.route('/records/<record_id>/links/<field_id>', methods=['PUT'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def update_record_link(record_id, field_id):
    """
    更新记录的关联值
    
    Args:
        record_id: 记录 ID
        field_id: 关联字段 ID
    
    Request Body:
        - target_record_ids: 目标记录 ID 列表（必填）
    
    Returns:
        更新结果
    """
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)
    
    field = FieldService.get_field(field_id)
    if not field:
        return error_response('字段不存在', 404)
    
    # 检查是否为关联字段（支持 'link' 和 'link_to_record' 两种类型）
    if field.type not in [FieldType.LINK_TO_RECORD.value, 'link']:
        return error_response('该字段不是关联字段', 400)
    
    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)
    
    target_record_ids = data.get('target_record_ids', [])
    if not isinstance(target_record_ids, list):
        return error_response('target_record_ids 必须是数组', 400)
    
    try:
        # 获取字段配置中的目标表ID
        field_config = field.config or {}
        target_table_id = field_config.get('linkedTableId')
        
        if not target_table_id:
            return error_response('字段配置缺少关联表ID', 400)
        
        # 获取关联关系（使用目标表ID进行精确匹配）
        link_relation = LinkService.get_link_relation_by_field(field_id, target_table_id)
        if not link_relation:
            # 尝试根据字段配置自动创建关联关系
            relationship_type = field_config.get('relationshipType', 'one_to_many')
            bidirectional = field_config.get('bidirectional', False)

            # 创建关联关系
            link_data = {
                'source_table_id': str(field.table_id),
                'target_table_id': str(target_table_id),
                'source_field_id': field_id,
                'target_field_id': None,  # 暂时不设置反向字段
                'relationship_type': relationship_type,
                'bidirectional': bidirectional
            }

            link_result = LinkService.create_link_relation(link_data)
            if not link_result[0]:
                return error_response(f'自动创建关联关系失败: {link_result[1]}', 400)

            link_relation = link_result[0]
            current_app.logger.info(f'[update_record_links] 自动创建关联关系: {link_relation.id}')

        
        # 验证一对一约束
        if link_relation.relationship_type == 'one_to_one' and len(target_record_ids) > 1:
            return error_response('一对一关联只能关联一条记录', 400)
        
        # 更新关联值
        result = LinkService.update_link_values(
            link_relation_id=link_relation.id,
            source_record_id=record_id,
            target_record_ids=target_record_ids,
            updated_by=g.current_user.id
        )
        
        if not result[0]:
            return error_response(result[1], 400)
        
        return success_response(
            data={'updated_count': result[0]},
            message='关联值更新成功'
        )
    
    except Exception as e:
        return error_response(f'更新关联值失败: {str(e)}', 500)


@records_bp.route('/tables/<table_id>/records/search', methods=['GET'])
@jwt_required
@role_required(['owner', 'admin', 'editor', 'commenter', 'viewer'])
def search_linkable_records(table_id):
    """
    搜索可关联的记录
    
    用于关联字段选择器，搜索目标表中可关联的记录
    
    Args:
        table_id: 目标表 ID
    
    Query Parameters:
        - keyword: 搜索关键词（可选）
        - exclude_ids: 排除的记录 ID 列表（可选，逗号分隔）
        - page: 页码（可选，默认 1）
        - per_page: 每页数量（可选，默认 20）
    
    Returns:
        记录列表
    """
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)
    
    # 获取查询参数
    keyword = request.args.get('keyword', '')
    exclude_ids_str = request.args.get('exclude_ids', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # 限制每页数量
    if per_page > 100:
        per_page = 100
    
    # 解析排除的 ID 列表
    exclude_ids = [id.strip() for id in exclude_ids_str.split(',') if id.strip()]
    
    try:
        # 搜索记录
        if keyword:
            records = RecordService.search_records(table_id, keyword)
            total = len(records)
        else:
            records, total = RecordService.get_table_records(table_id, page=page, per_page=per_page)
        
        # 过滤排除的记录
        if exclude_ids:
            records = [r for r in records if str(r.id) not in exclude_ids]
            # 更新总数（排除后）
            if keyword:
                total = len(records)
        
        # 手动分页（如果是搜索模式）
        if keyword:
            start = (page - 1) * per_page
            end = start + per_page
            records = records[start:end]
        
        # 序列化记录数据
        items = []
        for record in records:
            item = record.to_dict()
            # 只返回基本信息，减少数据量
            items.append({
                'id': item['id'],
                'values': item.get('values', {}),
                'created_at': item.get('created_at')
            })
        
        return paginated_response(items, total, page, per_page)
    
    except Exception as e:
        return error_response(f'搜索记录失败: {str(e)}', 500)
