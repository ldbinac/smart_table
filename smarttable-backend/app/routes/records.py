"""
记录管理路由模块
"""
import uuid
import traceback
from typing import Dict, List
from datetime import datetime, timezone
from flask import Blueprint, request, g, current_app

from sqlalchemy import insert

from app.services.record_service import RecordService, _format_date_value, SYSTEM_FIELD_TYPES
from app.services.table_service import TableService
from app.services.formula_service import FormulaService
from app.services.link_service import LinkService
from app.services.field_service import FieldService
from app.services.permission_service import PermissionService
from app.services.field_permission_service import FieldPermissionService
from app.schemas.record_schema import (
    record_create_schema,
    record_update_schema,
    batch_create_schema,
    batch_update_schema
)
from app.utils.response import success_response, error_response, paginated_response
from app.utils.decorators import jwt_required, role_required, query_rate_limit, write_rate_limit
from app.extensions import db
from app.models.record import Record
from app.models.record_history import RecordHistory, HistoryAction
from app.models.field import Field, FieldType
from app.models.base import MemberRole

records_bp = Blueprint('records', __name__)
# 禁用严格斜杠，允许带或不带斜杠的URL
records_bp.strict_slashes = False


def _to_uuid(value: str) -> uuid.UUID:
    """将字符串转为 UUID 对象"""
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


@records_bp.route('/tables/<table_id>/records', methods=['GET'])
@jwt_required
@query_rate_limit(max_queries=200, window=60)
def get_records(table_id) -> tuple:
    """
    获取表格记录列表
    ---
    tags:
      - Records
    security:
      - Bearer: []
    parameters:
      - name: table_id
        in: path
        type: string
        required: true
        description: 表格 ID
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
      - name: search
        in: query
        type: string
        description: 搜索关键词
    responses:
      200:
        description: 记录列表（分页）
    """
    # 检查表格是否存在
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)
    
    # 资源级权限检查
    if not PermissionService.check_permission(
        str(table.base_id), g.current_user_id, MemberRole.VIEWER
    ):
        return error_response('无权访问该表格', 403)
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    
    # 限制每页数量
    if per_page > 500:
        per_page = 500
    
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
        
        # 批量加载关联数据（仅需 2 条 SQL，替代逐条调用的 N+1 查询）
        record_links_map: Dict[str, Dict[str, List[str]]] = {}
        if link_fields and records:
            record_ids_str = [str(r.id) for r in records]
            record_links_map = LinkService.batch_get_record_link_ids(record_ids_str)
        
        # 预查询公式字段，避免每条记录重复查询数据库
        formula_fields = Field.query.filter_by(table_id=table_id, type='formula').all()

        # 批量获取当前用户的字段权限（用于字段值过滤，无用户上下文时跳过保持向后兼容）
        user_id = g.current_user_id
        field_permissions = None
        if user_id:
            field_permissions = FieldPermissionService.get_table_field_permissions(
                str(table_id), str(user_id)
            )

        # 序列化记录数据
        items = []
        for record in records:
            item = record.to_dict(field_permissions=field_permissions)
            
            # 填充关联字段数据（使用批量加载的缓存结果）
            if link_fields:
                record_links = record_links_map.get(str(record.id), {})
                for field in link_fields:
                    field_id = str(field.id)
                    if field_id in record_links:
                        # batch_get_record_link_ids 已返回去重后的 ID 列表
                        item['values'][field_id] = record_links[field_id]
            
            # 计算公式值（传入预查询的 formula_fields，避免重复 DB 查询）
            if formula_fields:
                item['computed_values'] = FormulaService.compute_record_formulas(
                    table_id, record.values, formula_fields=formula_fields
                )
            else:
                item['computed_values'] = {}
            items.append(item)
        
        return paginated_response(items, total, page, per_page)
    
    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 获取记录列表失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response('获取记录列表失败，请稍后重试', 500, error='internal_server_error', request_id=request_id)


@records_bp.route('/tables/<table_id>/records', methods=['POST'])
@jwt_required
@write_rate_limit(max_writes=100, window=60)
def create_record(table_id) -> tuple:
    """
    创建记录
    ---
    tags:
      - Records
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
          required:
            - values
          properties:
            values:
              type: object
              description: 记录字段值
    responses:
      201:
        description: 记录创建成功
    """
    # 检查表格是否存在
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)
    
    # 资源级权限检查
    if not PermissionService.check_permission(
        str(table.base_id), g.current_user_id, MemberRole.EDITOR
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
            created_by=g.current_user_id
        )

        # 批量获取当前用户的字段权限（用于响应字段值过滤，无用户上下文时跳过）
        user_id = g.current_user_id
        field_permissions = None
        if user_id:
            field_permissions = FieldPermissionService.get_table_field_permissions(
                str(table_id), str(user_id)
            )

        result = record.to_dict(field_permissions=field_permissions)
        # 计算公式值
        result['computed_values'] = FormulaService.compute_record_formulas(
            table_id, record.values
        )

        return success_response(result, '记录创建成功', 201)
    
    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 创建记录失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response('创建记录失败，请稍后重试', 500, error='internal_server_error', request_id=request_id)


@records_bp.route('/tables/<table_id>/records/batch', methods=['POST'])
@jwt_required
@write_rate_limit(max_writes=200, window=60)
def batch_create_records(table_id) -> tuple:
    """
    批量创建记录
    ---
    tags:
      - Records
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
        required: true
        schema:
          type: object
          required:
            - records
          properties:
            records:
              type: array
              description: 记录列表
              items:
                type: object
                properties:
                  values:
                    type: object
                    description: 记录字段值
    responses:
      200:
        description: 批量创建结果
      400:
        description: 参数错误
      403:
        description: 无权限
      404:
        description: 表格不存在
    """
    # 检查表格是否存在
    table = TableService.get_table_by_id(table_id)
    if not table:
        return error_response('表格不存在', 404)

    # 资源级权限检查
    if not PermissionService.check_permission(
        str(table.base_id), g.current_user_id, MemberRole.EDITOR
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
        # ---------- 批量预加载（只需一次） ----------
        fields = FieldService.get_all_fields(table_id)
        field_map = {str(f.id): f for f in fields}
        auto_number_fields = [f for f in fields if f.type == FieldType.AUTO_NUMBER.value]
        now = datetime.now(timezone.utc)
        changer_id = _to_uuid(g.current_user_id) if g.current_user_id else None
        tbl_id = _to_uuid(table_id)

        # 批量获取当前用户的字段权限（用于写权限过滤，无用户上下文时跳过保持向后兼容）
        user_id = g.current_user_id
        field_permissions = None
        if user_id:
            field_permissions = FieldPermissionService.get_table_field_permissions(
                str(table_id), str(user_id)
            )

        # 系统字段 ID 集合（AUTO_NUMBER/CREATED_BY/LAST_MODIFIED_BY 不参与权限过滤）
        system_field_ids = {
            str(f.id) for f in fields if f.type in SYSTEM_FIELD_TYPES
        }

        # ---------- 组装批量数据 ----------
        records_dicts = []
        history_dicts = []
        created_record_ids = []

        for record_data in records_data:
            raw_values = record_data.get('values', {})
            final_values = dict(raw_values) if raw_values else {}

            # 字段写权限过滤：过滤掉用户无写权限的字段值（系统字段豁免）
            if field_permissions:
                # 分离系统字段值和普通字段值
                system_values = {k: v for k, v in final_values.items() if k in system_field_ids}
                user_values = {k: v for k, v in final_values.items() if k not in system_field_ids}
                # 过滤用户字段值（仅保留 write 权限字段）
                filtered_user_values = FieldPermissionService.filter_writable_values(
                    user_values, field_permissions
                )
                # 记录被过滤的字段
                filtered_keys = set(user_values.keys()) - set(filtered_user_values.keys())
                if filtered_keys:
                    current_app.logger.warning(
                        f'[batch_create_records] 字段无写权限已过滤. '
                        f'Table: {table_id}, User: {user_id}, Fields: {filtered_keys}'
                    )
                final_values = {**system_values, **filtered_user_values}

            # 格式化日期字段值
            for field_id, value in list(final_values.items()):
                field = field_map.get(field_id)
                if field and field.type in (FieldType.DATE.value, FieldType.DATE_TIME.value):
                    final_values[field_id] = _format_date_value(value, field)

            # 应用字段默认值
            for field in fields:
                field_id = str(field.id)
                if field_id not in final_values:
                    default_value = field.get_default_value()
                    if default_value is not None:
                        if default_value == 'now':
                            if field.type == FieldType.DATE_TIME.value:
                                final_values[field_id] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                            else:
                                final_values[field_id] = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                        else:
                            final_values[field_id] = default_value

            # 处理自动编号字段
            record_created_at = datetime.now()
            for field in auto_number_fields:
                field_id = str(field.id)
                if field_id not in final_values or not final_values[field_id]:
                    sequence = RecordService._get_next_auto_number_sequence(
                        table_id, field_id, field
                    )
                    final_values[field_id] = field.generate_auto_number(sequence, record_created_at)

            record_id = uuid.uuid4()
            created_record_ids.append(record_id)

            records_dicts.append({
                'id': record_id,
                'table_id': tbl_id,
                'values': final_values,
                'is_deleted': False,
                'created_by': changer_id,
                'updated_by': changer_id,
                'created_at': now,
                'updated_at': now,
            })

            history_dicts.append({
                'id': uuid.uuid4(),
                'record_id': record_id,
                'table_id': tbl_id,
                'action': HistoryAction.CREATE.value,
                'changed_by': changer_id,
                'changed_at': now,
                'changes': None,
                'snapshot': final_values,
            })

        # ---------- 批量 SQL 插入（仅 2 条 SQL） ----------
        stmt_records = insert(Record.__table__)
        db.session.execute(stmt_records, records_dicts)

        stmt_history = insert(RecordHistory.__table__)
        db.session.execute(stmt_history, history_dicts)

        db.session.commit()

        # ---------- 广播协作事件（不影响主流程） ----------
        try:
            from app.services.collaboration_service import CollaborationService
            if table:
                for record_id_uuid in created_record_ids:
                    CollaborationService.broadcast_if_enabled(
                        'data:record_created',
                        str(table.base_id),
                        {
                            'table_id': table_id,
                            'record': {
                                'id': str(record_id_uuid),
                                'table_id': table_id,
                                'values': {},
                                'created_at': now.isoformat(),
                                'updated_at': now.isoformat(),
                            },
                            'changed_by': str(g.current_user_id) if g.current_user_id else None,
                            'timestamp': now.isoformat(),
                        }
                    )
        except Exception as e:
            current_app.logger.error(f'[batch_create_records] broadcast error: {e}')

        return success_response({
            'created_count': len(records_dicts),
            'record_ids': [str(rid) for rid in created_record_ids],
        }, f'成功创建 {len(records_dicts)} 条记录')

    except Exception as e:
        db.session.rollback()
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 批量创建记录失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response('批量创建记录失败，请稍后重试', 500, error='internal_server_error', request_id=request_id)


@records_bp.route('/records/<record_id>', methods=['GET'])
@jwt_required
def get_record(record_id) -> tuple:
    """
    获取记录详情
    ---
    tags:
      - Records
    security:
      - Bearer: []
    parameters:
      - name: record_id
        in: path
        type: string
        required: true
        description: 记录 ID
    responses:
      200:
        description: 记录详情
      403:
        description: 无权限
      404:
        description: 记录不存在
    """
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)
    
    # 资源级权限检查
    table = TableService.get_table_by_id(record.table_id)
    if table and not PermissionService.check_permission(
        str(table.base_id), g.current_user_id, MemberRole.VIEWER
    ):
        return error_response('无权访问该记录', 403)
    
    try:
        # 批量获取当前用户的字段权限（用于字段值过滤，无用户上下文时跳过保持向后兼容）
        user_id = g.current_user_id
        field_permissions = None
        if user_id:
            field_permissions = FieldPermissionService.get_table_field_permissions(
                str(record.table_id), str(user_id)
            )

        result = record.to_dict(field_permissions=field_permissions)
        # 计算公式值
        result['computed_values'] = FormulaService.compute_record_formulas(
            record.table_id, record.values
        )

        return success_response(result)
    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 获取记录详情失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response('获取记录详情失败，请稍后重试', 500, error='internal_server_error', request_id=request_id)


@records_bp.route('/records/<record_id>', methods=['PUT'])
@jwt_required
@write_rate_limit(max_writes=100, window=60)
def update_record(record_id) -> tuple:
    """
    更新记录
    ---
    tags:
      - Records
    security:
      - Bearer: []
    parameters:
      - name: record_id
        in: path
        type: string
        required: true
        description: 记录 ID
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
              description: 记录字段值
    responses:
      200:
        description: 更新后的记录详情
      400:
        description: 参数错误
      403:
        description: 无权限
      404:
        description: 记录不存在
    """
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)
    
    # 资源级权限检查
    table = TableService.get_table_by_id(record.table_id)
    if table and not PermissionService.check_permission(
        str(table.base_id), g.current_user_id, MemberRole.EDITOR
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
            updated_by=g.current_user_id
        )

        # 批量获取当前用户的字段权限（用于响应字段值过滤，无用户上下文时跳过）
        user_id = g.current_user_id
        field_permissions = None
        if user_id:
            field_permissions = FieldPermissionService.get_table_field_permissions(
                str(record.table_id), str(user_id)
            )

        result = record.to_dict(field_permissions=field_permissions)
        # 计算公式值
        result['computed_values'] = FormulaService.compute_record_formulas(
            record.table_id, record.values
        )

        return success_response(result, '记录更新成功')
    
    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 更新记录失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response('更新记录失败，请稍后重试', 500, error='internal_server_error', request_id=request_id)


@records_bp.route('/records/batch', methods=['PUT'])
@jwt_required
@write_rate_limit(max_writes=50, window=60)
def batch_update_records() -> tuple:
    """
    批量更新记录
    ---
    tags:
      - Records
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - record_ids
            - values
          properties:
            record_ids:
              type: array
              description: 记录 ID 列表
              items:
                type: string
            values:
              type: object
              description: 要更新的字段值
    responses:
      200:
        description: 批量更新结果
      400:
        description: 参数错误
      403:
        description: 无权限
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
                    str(table.base_id), g.current_user_id, MemberRole.EDITOR
                ):
                    return error_response(f'无权修改表格 {table.base_id} 中的记录', 403)
                base_ids_checked.add(str(table.base_id))
    
    try:
        # 批量获取当前用户的字段权限（用于写权限过滤，无用户上下文时跳过保持向后兼容）
        # 从第一条有效记录获取 table_id，批量获取字段权限
        user_id = g.current_user_id
        field_permissions = None
        sample_table_id = None
        if user_id and record_ids:
            for rid in record_ids:
                sample_record = RecordService.get_record_by_id(rid)
                if sample_record:
                    sample_table_id = str(sample_record.table_id)
                    break
        if sample_table_id and user_id:
            field_permissions = FieldPermissionService.get_table_field_permissions(
                sample_table_id, str(user_id)
            )

        # 字段写权限过滤：过滤掉用户无写权限的字段值（仅在有权限数据时生效）
        filtered_values = values
        if field_permissions:
            original_keys = set(values.keys())
            filtered_values = FieldPermissionService.filter_writable_values(
                values, field_permissions
            )
            filtered_keys = original_keys - set(filtered_values.keys())
            if filtered_keys:
                current_app.logger.warning(
                    f'[batch_update_records] 字段无写权限已过滤. '
                    f'User: {user_id}, Fields: {filtered_keys}'
                )

        updated_count = 0
        failed_ids = []

        for record_id in record_ids:
            record = RecordService.get_record_by_id(record_id)
            if record:
                RecordService.update_record(
                    record=record,
                    values=filtered_values,
                    updated_by=g.current_user_id
                )
                updated_count += 1
            else:
                failed_ids.append(record_id)
        
        return success_response({
            'updated_count': updated_count,
            'failed_ids': failed_ids
        }, f'成功更新 {updated_count} 条记录')
    
    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 批量更新记录失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response('批量更新记录失败，请稍后重试', 500, error='internal_server_error', request_id=request_id)


@records_bp.route('/records/<record_id>', methods=['DELETE'])
@jwt_required
@write_rate_limit(max_writes=100, window=60)
def delete_record(record_id) -> tuple:
    """
    删除记录
    ---
    tags:
      - Records
    security:
      - Bearer: []
    parameters:
      - name: record_id
        in: path
        type: string
        required: true
        description: 记录 ID
    responses:
      200:
        description: 删除成功
      403:
        description: 无权限
      404:
        description: 记录不存在
      500:
        description: 删除失败
    """
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)
    
    # 资源级权限检查
    table = TableService.get_table_by_id(record.table_id)
    if table and not PermissionService.check_permission(
        str(table.base_id), g.current_user_id, MemberRole.EDITOR
    ):
        return error_response('无权删除该记录', 403)
    
    try:
        success = RecordService.delete_record(record)
        if success:
            return success_response(None, '记录删除成功')
        else:
            return error_response('删除记录失败', 500)
    
    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 删除记录失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response('删除记录失败，请稍后重试', 500, error='internal_server_error', request_id=request_id)


@records_bp.route('/records/batch', methods=['DELETE'])
@jwt_required
@write_rate_limit(max_writes=50, window=60)
def batch_delete_records() -> tuple:
    """
    批量删除记录
    ---
    tags:
      - Records
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - record_ids
          properties:
            record_ids:
              type: array
              description: 记录 ID 列表
              items:
                type: string
    responses:
      200:
        description: 批量删除结果
      400:
        description: 参数错误
      403:
        description: 无权限
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
                    str(table.base_id), g.current_user_id, MemberRole.EDITOR
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
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 批量删除记录失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response('批量删除记录失败，请稍后重试', 500, error='internal_server_error', request_id=request_id)


@records_bp.route('/records/<record_id>/compute', methods=['POST'])
@jwt_required
@role_required(['owner', 'admin', 'editor', 'commenter', 'viewer'])
def compute_formulas(record_id) -> tuple:
    """
    计算记录的公式值
    ---
    tags:
      - Records
    security:
      - Bearer: []
    description: 用于实时预览公式计算结果
    parameters:
      - name: record_id
        in: path
        type: string
        required: true
        description: 记录 ID
      - name: body
        in: body
        schema:
          type: object
          properties:
            preview_values:
              type: object
              description: 预览值（可能包含未保存的修改）
    responses:
      200:
        description: 公式计算结果
      404:
        description: 记录不存在
      500:
        description: 计算失败
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
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 公式计算失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response('公式计算失败，请稍后重试', 500, error='internal_server_error', request_id=request_id)


@records_bp.route('/records/<record_id>/history', methods=['GET'])
@jwt_required
@role_required(['owner', 'admin', 'editor', 'commenter', 'viewer'])
def get_record_history(record_id) -> tuple:
    """
    获取记录变更历史
    ---
    tags:
      - Records
    security:
      - Bearer: []
    description: 支持分页查询，按时间倒序排列
    parameters:
      - name: record_id
        in: path
        type: string
        required: true
        description: 记录 ID
      - name: page
        in: query
        type: integer
        default: 1
        description: 页码
      - name: size
        in: query
        type: integer
        default: 20
        description: 每页数量
    responses:
      200:
        description: 变更历史列表（分页）
      404:
        description: 记录不存在
      500:
        description: 获取失败
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
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 获取变更历史失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response('获取变更历史失败，请稍后重试', 500, error='internal_server_error', request_id=request_id)


# ==================== 关联记录 API ====================

@records_bp.route('/records/<record_id>/links', methods=['GET'])
@jwt_required
@role_required(['owner', 'admin', 'editor', 'commenter', 'viewer'])
def get_record_links(record_id) -> tuple:
    """
    获取记录的关联数据
    ---
    tags:
      - Records
    security:
      - Bearer: []
    description: 返回该记录所有关联字段的关联数据
    parameters:
      - name: record_id
        in: path
        type: string
        required: true
        description: 记录 ID
    responses:
      200:
        description: 关联数据，按 outbound 和 inbound 分组
      404:
        description: 记录不存在
      500:
        description: 获取失败
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
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 获取关联数据失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response('获取关联数据失败，请稍后重试', 500, error='internal_server_error', request_id=request_id)


@records_bp.route('/records/<record_id>/links/<field_id>', methods=['PUT'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def update_record_link(record_id, field_id) -> tuple:
    """
    更新记录的关联值
    ---
    tags:
      - Records
    security:
      - Bearer: []
    parameters:
      - name: record_id
        in: path
        type: string
        required: true
        description: 记录 ID
      - name: field_id
        in: path
        type: string
        required: true
        description: 关联字段 ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - target_record_ids
          properties:
            target_record_ids:
              type: array
              description: 目标记录 ID 列表
              items:
                type: string
    responses:
      200:
        description: 关联值更新成功
      400:
        description: 参数错误或不是关联字段
      404:
        description: 记录或字段不存在
      500:
        description: 更新失败
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
            updated_by=g.current_user_id
        )
        
        if not result[0]:
            return error_response(result[1], 400)
        
        return success_response(
            data={'updated_count': result[0]},
            message='关联值更新成功'
        )
    
    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 更新关联值失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response('更新关联值失败，请稍后重试', 500, error='internal_server_error', request_id=request_id)


@records_bp.route('/records/<record_id>/links/<field_id>', methods=['DELETE'])
@jwt_required
@role_required(['owner', 'admin', 'editor'])
def delete_record_link(record_id, field_id) -> tuple:
    """
    删除单个关联值（解除记录之间的关联关系）

    仅解除关联关系，不删除关联数据本身。
    如果是双向关联，同步删除反向关联关系。

    ---
    tags:
      - Records
    security:
      - Bearer: []
    parameters:
      - name: record_id
        in: path
        type: string
        required: true
        description: 源记录 ID
      - name: field_id
        in: path
        type: string
        required: true
        description: 关联字段 ID
      - name: target_record_id
        in: query
        type: string
        required: true
        description: 目标记录 ID
    responses:
      200:
        description: 关联解除成功
      400:
        description: 参数错误
      403:
        description: 无权限
      404:
        description: 记录或关联关系不存在
      500:
        description: 操作失败
    """
    record = RecordService.get_record_by_id(record_id)
    if not record:
        return error_response('记录不存在', 404)

    field = FieldService.get_field(field_id)
    if not field:
        return error_response('字段不存在', 404)

    if field.type not in [FieldType.LINK_TO_RECORD.value, 'link']:
        return error_response('该字段不是关联字段', 400)

    target_record_id = request.args.get('target_record_id')
    if not target_record_id:
        return error_response('缺少 target_record_id 参数', 400)

    try:
        # 获取字段配置中的目标表ID
        field_config = field.config or {}
        target_table_id = field_config.get('linkedTableId')
        if not target_table_id:
            return error_response('字段配置缺少关联表ID', 400)

        # 获取关联关系
        link_relation = LinkService.get_link_relation_by_field(field_id, target_table_id)
        if not link_relation:
            return error_response('关联关系不存在', 404)

        # 执行删除
        result = LinkService.delete_link_value_by_target(
            link_relation_id=str(link_relation.id),
            source_record_id=record_id,
            target_record_id=target_record_id,
            updated_by=g.current_user_id
        )

        if not result[0]:
            return error_response(result[1], 400)

        return success_response(
            data={'link_relation_id': str(link_relation.id)},
            message='关联已解除'
        )

    except Exception as e:
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 删除关联值失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response('删除关联值失败，请稍后重试', 500, error='internal_server_error', request_id=request_id)


@records_bp.route('/tables/<table_id>/records/search', methods=['GET'])
@jwt_required
@role_required(['owner', 'admin', 'editor', 'commenter', 'viewer'])
def search_linkable_records(table_id) -> tuple:
    """
    搜索可关联的记录
    ---
    tags:
      - Records
    security:
      - Bearer: []
    description: 用于关联字段选择器，搜索目标表中可关联的记录
    parameters:
      - name: table_id
        in: path
        type: string
        required: true
        description: 目标表 ID
      - name: keyword
        in: query
        type: string
        description: 搜索关键词
      - name: exclude_ids
        in: query
        type: string
        description: 排除的记录 ID 列表（逗号分隔）
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
        description: 记录列表（分页）
      404:
        description: 表格不存在
      500:
        description: 搜索失败
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
    if per_page > 500:
        per_page = 500
    
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
        request_id = getattr(g, 'request_id', None)
        current_app.logger.error(f'[{request_id}] 搜索记录失败: {str(e)}')
        current_app.logger.error(f'[{request_id}] 堆栈跟踪: {traceback.format_exc()}')
        return error_response('搜索记录失败，请稍后重试', 500, error='internal_server_error', request_id=request_id)
