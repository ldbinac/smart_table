"""
开放 API 路由（第三方应用以应用身份访问数据）

前缀：/api/open/v1

鉴权：所有端点需携带 Bearer 令牌（OAuth2 客户端凭证签发），并通过该应用授权的
Base 范围（allowed_bases）与 scope 权限校验。

端点：
- GET  /bases                                  列出授权 Base
- GET  /bases/<base_id>                        Base 详情
- GET  /bases/<base_id>/tables                 表列表
- GET  /bases/<base_id>/tables/<table_id>      表详情
- GET  /bases/<base_id>/tables/<table_id>/fields   字段结构
- GET  /bases/<base_id>/tables/<table_id>/records   记录列表（分页）
- GET  /bases/<base_id>/tables/<table_id>/records/search?q=  记录搜索
- GET  /bases/<base_id>/tables/<table_id>/records/<record_id>  记录详情
- POST /bases/<base_id>/tables/<table_id>/records   创建记录
- PUT  /bases/<base_id>/tables/<table_id>/records/<record_id>  更新记录
- DELETE /bases/<base_id>/tables/<table_id>/records/<record_id> 删除记录
"""
from flask import Blueprint, request, g

from app.utils.decorators import (
    open_api_auth_required,
    require_open_scope,
    open_api_rate_limit,
)
from app.utils.response import (
    success_response,
    created_response,
    paginated_response,
    error_response,
)
from app.services.open_api_service import OpenAPIService, OpenAPIError
from app.services.oauth_app_service import OAuthAppService

open_api_bp = Blueprint('open_api', __name__, url_prefix='/api/open/v1')


def _handle_error(e: OpenAPIError):
    """将 OpenAPIError 转换为统一错误响应"""
    return error_response(
        message=e.message_key,
        code=e.status,
        error=e.error
    )


def _audit_write(action: str, detail: str):
    """记录开放 API 写操作审计（应用身份）"""
    try:
        OAuthAppService.write_audit(
            app_id=getattr(g, 'oauth_app_id', None),
            action=action,
            detail=detail,
            ip=request.remote_addr
        )
    except Exception:
        pass


def _audit_read(detail: str):
    """记录开放 API 读操作审计（应用身份）"""
    try:
        OAuthAppService.write_audit(
            app_id=getattr(g, 'oauth_app_id', None),
            action='api_read',
            detail=detail,
            ip=request.remote_addr
        )
    except Exception:
        pass


def _parse_pagination():
    try:
        page = int(request.args.get('page', 1))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(request.args.get('per_page', 20))
    except (TypeError, ValueError):
        per_page = 20
    page = max(page, 1)
    per_page = max(min(per_page, 200), 1)
    return page, per_page


def _parse_values():
    data = request.get_json(silent=True) or {}
    if isinstance(data, dict) and 'values' in data and isinstance(data['values'], dict):
        return data['values']
    return data


# =========================================================================
# Base
# =========================================================================
@open_api_bp.route('/bases', methods=['GET'])
@open_api_auth_required
@require_open_scope('base:read')
@open_api_rate_limit(max_requests=600, window=60)
def list_bases():
    try:
        bases = OpenAPIService.list_bases(g.oauth_app)
    except OpenAPIError as e:
        return _handle_error(e)
    _audit_read('GET bases')
    return success_response(data=bases, message='fetch_success')


@open_api_bp.route('/bases/<base_id>', methods=['GET'])
@open_api_auth_required
@require_open_scope('base:read')
@open_api_rate_limit(max_requests=600, window=60)
def get_base(base_id):
    try:
        base = OpenAPIService.get_base(g.oauth_app, base_id)
    except OpenAPIError as e:
        return _handle_error(e)
    _audit_read(f'GET base {base_id}')
    return success_response(data=base, message='fetch_success')


# =========================================================================
# 表 / 字段
# =========================================================================
@open_api_bp.route('/bases/<base_id>/tables', methods=['GET'])
@open_api_auth_required
@require_open_scope('table:read')
@open_api_rate_limit(max_requests=600, window=60)
def list_tables(base_id):
    try:
        tables = OpenAPIService.list_tables(g.oauth_app, base_id)
    except OpenAPIError as e:
        return _handle_error(e)
    _audit_read(f'GET tables base={base_id}')
    return success_response(data=tables, message='fetch_success')


@open_api_bp.route('/bases/<base_id>/tables/<table_id>', methods=['GET'])
@open_api_auth_required
@require_open_scope('table:read')
@open_api_rate_limit(max_requests=600, window=60)
def get_table(base_id, table_id):
    try:
        table = OpenAPIService.get_table(g.oauth_app, base_id, table_id)
    except OpenAPIError as e:
        return _handle_error(e)
    return success_response(data=table, message='fetch_success')


@open_api_bp.route('/bases/<base_id>/tables/<table_id>/fields', methods=['GET'])
@open_api_auth_required
@require_open_scope('field:read')
@open_api_rate_limit(max_requests=600, window=60)
def list_fields(base_id, table_id):
    try:
        fields = OpenAPIService.list_fields(g.oauth_app, base_id, table_id)
    except OpenAPIError as e:
        return _handle_error(e)
    _audit_read(f'GET fields table={table_id}')
    return success_response(data=fields, message='fetch_success')


# =========================================================================
# 记录
# =========================================================================
@open_api_bp.route('/bases/<base_id>/tables/<table_id>/records', methods=['GET'])
@open_api_auth_required
@require_open_scope('record:read')
@open_api_rate_limit(max_requests=600, window=60)
def list_records(base_id, table_id):
    page, per_page = _parse_pagination()
    try:
        records, total = OpenAPIService.list_records(
            g.oauth_app, base_id, table_id, page=page, per_page=per_page
        )
    except OpenAPIError as e:
        return _handle_error(e)
    _audit_read(f'GET records table={table_id} page={page}')
    return paginated_response(items=records, total=total, page=page, per_page=per_page)


@open_api_bp.route('/bases/<base_id>/tables/<table_id>/records/search', methods=['GET'])
@open_api_auth_required
@require_open_scope('record:read')
@open_api_rate_limit(max_requests=600, window=60)
def search_records(base_id, table_id):
    query = (request.args.get('q') or '').strip()
    if not query:
        return error_response(message='param_error', code=400, error='bad_request')
    try:
        records = OpenAPIService.search_records(g.oauth_app, base_id, table_id, query)
    except OpenAPIError as e:
        return _handle_error(e)
    _audit_read(f'SEARCH records table={table_id} q={query}')
    return success_response(data=records, message='fetch_success')


@open_api_bp.route('/bases/<base_id>/tables/<table_id>/records/<record_id>', methods=['GET'])
@open_api_auth_required
@require_open_scope('record:read')
@open_api_rate_limit(max_requests=600, window=60)
def get_record(base_id, table_id, record_id):
    try:
        record = OpenAPIService.get_record(g.oauth_app, base_id, table_id, record_id)
    except OpenAPIError as e:
        return _handle_error(e)
    _audit_read(f'GET record {record_id}')
    return success_response(data=record, message='fetch_success')


@open_api_bp.route('/bases/<base_id>/tables/<table_id>/records', methods=['POST'])
@open_api_auth_required
@require_open_scope('record:write')
@open_api_rate_limit(max_requests=300, window=60)
def create_record(base_id, table_id):
    values = _parse_values()
    try:
        record = OpenAPIService.create_record(g.oauth_app, base_id, table_id, values)
    except OpenAPIError as e:
        return _handle_error(e)
    _audit_write('api_write', f'POST records {base_id}/{table_id}')
    return created_response(data=record, message='resource_created')


@open_api_bp.route('/bases/<base_id>/tables/<table_id>/records/<record_id>', methods=['PUT'])
@open_api_auth_required
@require_open_scope('record:write')
@open_api_rate_limit(max_requests=300, window=60)
def update_record(base_id, table_id, record_id):
    values = _parse_values()
    try:
        record = OpenAPIService.update_record(
            g.oauth_app, base_id, table_id, record_id, values
        )
    except OpenAPIError as e:
        return _handle_error(e)
    _audit_write('api_write', f'PUT record {base_id}/{table_id}/{record_id}')
    return success_response(data=record, message='operation_success')


@open_api_bp.route('/bases/<base_id>/tables/<table_id>/records/<record_id>', methods=['DELETE'])
@open_api_auth_required
@require_open_scope('record:write')
@open_api_rate_limit(max_requests=300, window=60)
def delete_record(base_id, table_id, record_id):
    try:
        ok = OpenAPIService.delete_record(g.oauth_app, base_id, table_id, record_id)
    except OpenAPIError as e:
        return _handle_error(e)
    if not ok:
        return error_response(message='operation_failed', code=500, error='server_error')
    _audit_write('api_write', f'DELETE record {base_id}/{table_id}/{record_id}')
    return success_response(message='operation_success')
