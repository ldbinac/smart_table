"""
字段权限 API 集成测试

使用 mock 方式测试路由处理器，验证字段权限过滤在以下端点中正确应用：
- GET /tables/<table_id>/fields：响应包含 field_permission
- GET /tables/<table_id>/records：应用字段读权限过滤
- GET /records/<record_id>：应用字段读权限过滤
- POST /tables/<table_id>/records/batch：应用字段写权限过滤
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from flask import g

from app import create_app
from app.extensions import db
from app.routes.fields import get_fields, get_field
from app.routes.records import (
    get_records,
    get_record,
    batch_create_records,
)
from app.models.field import (
    FIELD_PERMISSION_READ,
    FIELD_PERMISSION_WRITE,
    FIELD_PERMISSION_NONE,
)


# 测试用的有效 UUID 字符串
TEST_TABLE_ID = '12345678-1234-5678-1234-567812345678'
TEST_FIELD_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
TEST_FIELD_ID_2 = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
TEST_FIELD_ID_3 = 'cccccccc-cccc-cccc-cccc-cccccccccccc'
TEST_RECORD_ID = '11111111-1111-1111-1111-111111111111'
TEST_USER_ID = '87654321-4321-8765-4321-876543218765'
TEST_BASE_ID = '99999999-9999-9999-9999-999999999999'


@pytest.fixture(scope='module')
def app():
    """创建测试应用实例（仅用于提供应用/请求上下文）"""
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    app.config['SECRET_KEY'] = 'test-secret-key'
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _undecorated(handler):
    """获取去掉所有装饰器的原始处理函数（支持多层装饰器）"""
    while hasattr(handler, '__wrapped__'):
        handler = handler.__wrapped__
    return handler


def _make_field(field_id=TEST_FIELD_ID, name='字段1', field_type='single_line_text',
                config=None, permissions=None):
    """构造一个 mock Field 对象"""
    field = MagicMock()
    field.id = field_id
    field.name = name
    field.type = field_type
    field.description = None
    field.order = 0
    field.is_primary = False
    field.is_required = False
    field.options = {}
    field.config = config or {}
    field.created_at = datetime.now(timezone.utc)
    field.updated_at = datetime.now(timezone.utc)
    field.get_default_value.return_value = None
    field.get_auto_number_config.return_value = {'startNumber': 1}
    field.generate_auto_number.return_value = 'AUTO-1'

    # to_dict 返回包含基本字段的字典
    field_dict = {
        'id': str(field_id),
        'table_id': TEST_TABLE_ID,
        'name': name,
        'type': field_type,
        'description': None,
        'order': 0,
        'is_primary': False,
        'is_required': False,
        'options': {},
        'config': config or {},
        'created_at': field.created_at.isoformat(),
        'updated_at': field.updated_at.isoformat(),
    }
    field.to_dict.return_value = field_dict
    return field


def _make_record(record_id=TEST_RECORD_ID, values=None):
    """构造一个 mock Record 对象"""
    record = MagicMock()
    record.id = record_id if isinstance(record_id, uuid.UUID) else uuid.UUID(record_id)
    record.table_id = uuid.UUID(TEST_TABLE_ID)
    record.values = values or {}
    record.created_by = None
    record.updated_by = None
    record.created_at = datetime.now(timezone.utc)
    record.updated_at = datetime.now(timezone.utc)

    # to_dict 调用 FieldPermissionService.filter_values_by_permission 进行过滤
    # 这里模拟真实 Record.to_dict 的行为
    def to_dict(include_values=True, include_meta=True, user_id=None, field_permissions=None):
        data = {
            'id': str(record.id),
            'table_id': str(record.table_id)
        }
        if include_values:
            values_dict = dict(record.values) if record.values else {}
            # 模拟字段权限过滤
            if field_permissions is not None:
                from app.services.field_permission_service import FieldPermissionService
                values_dict = FieldPermissionService.filter_values_by_permission(
                    values_dict, field_permissions
                )
            data['values'] = values_dict
        if include_meta:
            data['created_by'] = None
            data['updated_by'] = None
            data['created_at'] = record.created_at.isoformat()
            data['updated_at'] = record.updated_at.isoformat()
        return data

    record.to_dict.side_effect = to_dict
    return record


def _make_table(table_id=TEST_TABLE_ID, base_id=TEST_BASE_ID):
    """构造一个 mock Table 对象"""
    table = MagicMock()
    table.id = table_id
    table.base_id = base_id
    return table


# ---------------------------------------------------------------------------
# GET /tables/<table_id>/fields 测试
# ---------------------------------------------------------------------------

class TestGetFieldsWithPermissions:
    """GET /tables/<table_id>/fields 字段权限标识测试"""

    def test_response_includes_field_permission(self, app, monkeypatch):
        """响应中每个字段包含 field_permission 字段"""
        import app.routes.fields as fields_module

        # 构造 mock 字段
        field1 = _make_field(field_id=TEST_FIELD_ID, name='字段1')
        field2 = _make_field(field_id=TEST_FIELD_ID_2, name='字段2')

        monkeypatch.setattr(
            fields_module.TableService, 'check_permission',
            lambda *a, **kw: True
        )
        monkeypatch.setattr(
            fields_module.FieldService, 'get_all_fields',
            lambda *a, **kw: [field1, field2]
        )

        # mock 字段权限：field1=write, field2=none
        permissions = {
            TEST_FIELD_ID: FIELD_PERMISSION_WRITE,
            TEST_FIELD_ID_2: FIELD_PERMISSION_NONE,
        }
        monkeypatch.setattr(
            fields_module.FieldPermissionService, 'get_table_field_permissions',
            lambda *a, **kw: permissions
        )

        with app.test_request_context():
            g.current_user_id = TEST_USER_ID
            response, status_code = _undecorated(get_fields)(uuid.UUID(TEST_TABLE_ID))

            assert status_code == 200
            data = response.get_json()
            assert data['success'] is True
            fields_list = data['data']
            assert len(fields_list) == 2
            # 每个字段应包含 field_permission
            assert fields_list[0]['field_permission'] == FIELD_PERMISSION_WRITE
            assert fields_list[1]['field_permission'] == FIELD_PERMISSION_NONE

    def test_no_user_id_skips_permission_query(self, app, monkeypatch):
        """无 user_id 时不查询字段权限，field_permission 默认为 'read'"""
        import app.routes.fields as fields_module

        field1 = _make_field(field_id=TEST_FIELD_ID, name='字段1')

        monkeypatch.setattr(
            fields_module.TableService, 'check_permission',
            lambda *a, **kw: True
        )
        monkeypatch.setattr(
            fields_module.FieldService, 'get_all_fields',
            lambda *a, **kw: [field1]
        )

        # 即使 mock 了 get_table_field_permissions，无 user_id 时不应被调用
        call_count = {'count': 0}

        def mock_get_perms(*a, **kw):
            call_count['count'] += 1
            return {}

        monkeypatch.setattr(
            fields_module.FieldPermissionService, 'get_table_field_permissions',
            mock_get_perms
        )

        with app.test_request_context():
            g.current_user_id = None
            response, status_code = _undecorated(get_fields)(uuid.UUID(TEST_TABLE_ID))

            assert status_code == 200
            data = response.get_json()
            assert data['success'] is True
            # 无 user_id 时不调用权限查询
            assert call_count['count'] == 0
            # field_permission 默认为 'read'
            assert data['data'][0]['field_permission'] == FIELD_PERMISSION_READ


# ---------------------------------------------------------------------------
# GET /fields/<field_id> 测试
# ---------------------------------------------------------------------------

class TestGetFieldWithPermissions:
    """GET /fields/<field_id> 字段权限标识测试"""

    def test_response_includes_field_permission(self, app, monkeypatch):
        """响应中包含 field_permission 字段"""
        import app.routes.fields as fields_module

        field = _make_field(field_id=TEST_FIELD_ID, name='字段1')

        monkeypatch.setattr(
            fields_module.FieldService, 'check_permission',
            lambda *a, **kw: True
        )
        monkeypatch.setattr(
            fields_module.FieldService, 'get_field',
            lambda *a, **kw: field
        )
        monkeypatch.setattr(
            fields_module.FieldPermissionService, 'get_field_permission',
            lambda *a, **kw: FIELD_PERMISSION_WRITE
        )

        with app.test_request_context():
            g.current_user_id = TEST_USER_ID
            response, status_code = _undecorated(get_field)(uuid.UUID(TEST_FIELD_ID))

            assert status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['data']['field_permission'] == FIELD_PERMISSION_WRITE

    def test_no_user_id_skips_permission(self, app, monkeypatch):
        """无 user_id 时不附加 field_permission"""
        import app.routes.fields as fields_module

        field = _make_field(field_id=TEST_FIELD_ID, name='字段1')

        monkeypatch.setattr(
            fields_module.FieldService, 'check_permission',
            lambda *a, **kw: True
        )
        monkeypatch.setattr(
            fields_module.FieldService, 'get_field',
            lambda *a, **kw: field
        )

        call_count = {'count': 0}

        def mock_get_perm(*a, **kw):
            call_count['count'] += 1
            return FIELD_PERMISSION_READ

        monkeypatch.setattr(
            fields_module.FieldPermissionService, 'get_field_permission',
            mock_get_perm
        )

        with app.test_request_context():
            g.current_user_id = None
            response, status_code = _undecorated(get_field)(uuid.UUID(TEST_FIELD_ID))

            assert status_code == 200
            data = response.get_json()
            assert data['success'] is True
            # 无 user_id 时不调用权限查询
            assert call_count['count'] == 0
            # 不附加 field_permission 字段
            assert 'field_permission' not in data['data']


# ---------------------------------------------------------------------------
# GET /tables/<table_id>/records 测试
# ---------------------------------------------------------------------------

class TestGetRecordsWithPermissions:
    """GET /tables/<table_id>/records 字段权限过滤测试"""

    def test_records_values_filtered_by_permission(self, app, monkeypatch):
        """记录值按字段权限过滤：none 权限字段被移除"""
        import app.routes.records as records_module

        # 构造 mock 记录（包含 3 个字段值）
        record_values = {
            TEST_FIELD_ID: 'value1',      # write 权限，保留
            TEST_FIELD_ID_2: 'value2',    # read 权限，保留
            TEST_FIELD_ID_3: 'value3',    # none 权限，移除
        }
        record = _make_record(values=record_values)
        table = _make_table()

        monkeypatch.setattr(
            records_module.TableService, 'get_table_by_id',
            lambda *a, **kw: table
        )
        monkeypatch.setattr(
            records_module.PermissionService, 'check_permission',
            lambda *a, **kw: True
        )
        monkeypatch.setattr(
            records_module.RecordService, 'get_table_records',
            lambda *a, **kw: ([record], 1)
        )
        monkeypatch.setattr(
            records_module.FieldService, 'get_fields_by_type',
            lambda *a, **kw: []
        )
        # mock Field.query.filter_by 链式调用
        mock_field_query = MagicMock()
        mock_field_query.filter_by.return_value.all.return_value = []
        monkeypatch.setattr(
            records_module, 'Field', mock_field_query
        )
        monkeypatch.setattr(
            records_module.LinkService, 'batch_get_record_link_ids',
            lambda *a, **kw: {}
        )
        monkeypatch.setattr(
            records_module.FormulaService, 'compute_record_formulas',
            lambda *a, **kw: {}
        )

        # mock 字段权限
        permissions = {
            TEST_FIELD_ID: FIELD_PERMISSION_WRITE,
            TEST_FIELD_ID_2: FIELD_PERMISSION_READ,
            TEST_FIELD_ID_3: FIELD_PERMISSION_NONE,
        }
        monkeypatch.setattr(
            records_module.FieldPermissionService, 'get_table_field_permissions',
            lambda *a, **kw: permissions
        )

        with app.test_request_context():
            g.current_user_id = TEST_USER_ID
            response, status_code = _undecorated(get_records)(TEST_TABLE_ID)

            assert status_code == 200
            data = response.get_json()
            items = data['data']
            assert len(items) == 1
            values = items[0]['values']
            # write/read 字段保留，none 字段移除
            assert TEST_FIELD_ID in values
            assert TEST_FIELD_ID_2 in values
            assert TEST_FIELD_ID_3 not in values

    def test_no_user_id_keeps_all_values(self, app, monkeypatch):
        """无 user_id 时不进行字段过滤，保留所有字段值（向后兼容）"""
        import app.routes.records as records_module

        record_values = {
            TEST_FIELD_ID: 'value1',
            TEST_FIELD_ID_2: 'value2',
        }
        record = _make_record(values=record_values)
        table = _make_table()

        monkeypatch.setattr(
            records_module.TableService, 'get_table_by_id',
            lambda *a, **kw: table
        )
        monkeypatch.setattr(
            records_module.PermissionService, 'check_permission',
            lambda *a, **kw: True
        )
        monkeypatch.setattr(
            records_module.RecordService, 'get_table_records',
            lambda *a, **kw: ([record], 1)
        )
        monkeypatch.setattr(
            records_module.FieldService, 'get_fields_by_type',
            lambda *a, **kw: []
        )
        mock_field_query = MagicMock()
        mock_field_query.filter_by.return_value.all.return_value = []
        monkeypatch.setattr(
            records_module, 'Field', mock_field_query
        )
        monkeypatch.setattr(
            records_module.LinkService, 'batch_get_record_link_ids',
            lambda *a, **kw: {}
        )
        monkeypatch.setattr(
            records_module.FormulaService, 'compute_record_formulas',
            lambda *a, **kw: {}
        )

        call_count = {'count': 0}

        def mock_get_perms(*a, **kw):
            call_count['count'] += 1
            return {}

        monkeypatch.setattr(
            records_module.FieldPermissionService, 'get_table_field_permissions',
            mock_get_perms
        )

        with app.test_request_context():
            g.current_user_id = None
            response, status_code = _undecorated(get_records)(TEST_TABLE_ID)

            assert status_code == 200
            data = response.get_json()
            items = data['data']
            # 无 user_id 时不调用权限查询
            assert call_count['count'] == 0
            # 所有字段值保留
            values = items[0]['values']
            assert TEST_FIELD_ID in values
            assert TEST_FIELD_ID_2 in values


# ---------------------------------------------------------------------------
# GET /records/<record_id> 测试
# ---------------------------------------------------------------------------

class TestGetRecordWithPermissions:
    """GET /records/<record_id> 字段权限过滤测试"""

    def test_record_values_filtered_by_permission(self, app, monkeypatch):
        """单条记录值按字段权限过滤：none 权限字段被移除"""
        import app.routes.records as records_module

        record_values = {
            TEST_FIELD_ID: 'value1',      # write 权限，保留
            TEST_FIELD_ID_2: 'value2',    # read 权限，保留
            TEST_FIELD_ID_3: 'value3',    # none 权限，移除
        }
        record = _make_record(values=record_values)
        table = _make_table()

        monkeypatch.setattr(
            records_module.RecordService, 'get_record_by_id',
            lambda *a, **kw: record
        )
        monkeypatch.setattr(
            records_module.TableService, 'get_table_by_id',
            lambda *a, **kw: table
        )
        monkeypatch.setattr(
            records_module.PermissionService, 'check_permission',
            lambda *a, **kw: True
        )
        monkeypatch.setattr(
            records_module.FormulaService, 'compute_record_formulas',
            lambda *a, **kw: {}
        )

        permissions = {
            TEST_FIELD_ID: FIELD_PERMISSION_WRITE,
            TEST_FIELD_ID_2: FIELD_PERMISSION_READ,
            TEST_FIELD_ID_3: FIELD_PERMISSION_NONE,
        }
        monkeypatch.setattr(
            records_module.FieldPermissionService, 'get_table_field_permissions',
            lambda *a, **kw: permissions
        )

        with app.test_request_context():
            g.current_user_id = TEST_USER_ID
            response, status_code = _undecorated(get_record)(TEST_RECORD_ID)

            assert status_code == 200
            data = response.get_json()
            values = data['data']['values']
            assert TEST_FIELD_ID in values
            assert TEST_FIELD_ID_2 in values
            assert TEST_FIELD_ID_3 not in values

    def test_no_user_id_keeps_all_values(self, app, monkeypatch):
        """无 user_id 时不进行字段过滤（向后兼容）"""
        import app.routes.records as records_module

        record_values = {
            TEST_FIELD_ID: 'value1',
            TEST_FIELD_ID_2: 'value2',
        }
        record = _make_record(values=record_values)
        table = _make_table()

        monkeypatch.setattr(
            records_module.RecordService, 'get_record_by_id',
            lambda *a, **kw: record
        )
        monkeypatch.setattr(
            records_module.TableService, 'get_table_by_id',
            lambda *a, **kw: table
        )
        monkeypatch.setattr(
            records_module.PermissionService, 'check_permission',
            lambda *a, **kw: True
        )
        monkeypatch.setattr(
            records_module.FormulaService, 'compute_record_formulas',
            lambda *a, **kw: {}
        )

        call_count = {'count': 0}

        def mock_get_perms(*a, **kw):
            call_count['count'] += 1
            return {}

        monkeypatch.setattr(
            records_module.FieldPermissionService, 'get_table_field_permissions',
            mock_get_perms
        )

        with app.test_request_context():
            g.current_user_id = None
            response, status_code = _undecorated(get_record)(TEST_RECORD_ID)

            assert status_code == 200
            data = response.get_json()
            # 无 user_id 时不调用权限查询
            assert call_count['count'] == 0
            values = data['data']['values']
            assert TEST_FIELD_ID in values
            assert TEST_FIELD_ID_2 in values


# ---------------------------------------------------------------------------
# POST /tables/<table_id>/records/batch 测试
# ---------------------------------------------------------------------------

class TestBatchCreateRecordsWithPermissions:
    """POST /tables/<table_id>/records/batch 字段写权限过滤测试"""

    def test_writable_values_filtered_by_permission(self, app, monkeypatch):
        """批量创建时过滤掉用户无写权限的字段值（保留 write，移除 read/none）"""
        import app.routes.records as records_module

        # 构造 mock 字段（普通字段，非系统字段）
        field1 = _make_field(field_id=TEST_FIELD_ID, name='字段1', field_type='single_line_text')
        field2 = _make_field(field_id=TEST_FIELD_ID_2, name='字段2', field_type='single_line_text')
        field3 = _make_field(field_id=TEST_FIELD_ID_3, name='字段3', field_type='single_line_text')

        table = _make_table()

        monkeypatch.setattr(
            records_module.TableService, 'get_table_by_id',
            lambda *a, **kw: table
        )
        monkeypatch.setattr(
            records_module.PermissionService, 'check_permission',
            lambda *a, **kw: True
        )
        monkeypatch.setattr(
            records_module.FieldService, 'get_all_fields',
            lambda *a, **kw: [field1, field2, field3]
        )

        # mock 字段权限：field1=write, field2=read, field3=none
        permissions = {
            TEST_FIELD_ID: FIELD_PERMISSION_WRITE,
            TEST_FIELD_ID_2: FIELD_PERMISSION_READ,
            TEST_FIELD_ID_3: FIELD_PERMISSION_NONE,
        }
        monkeypatch.setattr(
            records_module.FieldPermissionService, 'get_table_field_permissions',
            lambda *a, **kw: permissions
        )

        # mock db.session
        mock_db = MagicMock()
        monkeypatch.setattr(records_module, 'db', mock_db)

        # mock 批量创建 schema 验证（无错误）
        monkeypatch.setattr(
            records_module.batch_create_schema, 'validate',
            lambda *a, **kw: {}
        )

        # mock 协作服务广播（避免副作用）
        monkeypatch.setattr(
            'app.services.collaboration_service.CollaborationService.broadcast_if_enabled',
            lambda *a, **kw: None
        )

        # 请求数据：3 个字段都有值
        request_data = {
            'records': [
                {'values': {
                    TEST_FIELD_ID: 'v1',
                    TEST_FIELD_ID_2: 'v2',
                    TEST_FIELD_ID_3: 'v3',
                }}
            ]
        }

        with app.test_request_context(json=request_data):
            g.current_user_id = TEST_USER_ID
            response, status_code = _undecorated(batch_create_records)(TEST_TABLE_ID)

            assert status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['data']['created_count'] == 1

            # 验证 db.session.execute 被调用，并检查传入的记录数据
            assert mock_db.session.execute.call_count >= 1
            # 第一次 execute 是插入 records，参数是 (stmt, records_dicts)
            call_args = mock_db.session.execute.call_args_list[0]
            records_dicts = call_args[0][1]
            assert len(records_dicts) == 1
            final_values = records_dicts[0]['values']
            # write 权限字段保留
            assert TEST_FIELD_ID in final_values
            assert final_values[TEST_FIELD_ID] == 'v1'
            # read 权限字段被过滤（写权限不足）
            assert TEST_FIELD_ID_2 not in final_values
            # none 权限字段被过滤
            assert TEST_FIELD_ID_3 not in final_values

    def test_system_fields_not_filtered(self, app, monkeypatch):
        """系统字段（AUTO_NUMBER/CREATED_BY/LAST_MODIFIED_BY）不参与权限过滤"""
        import app.routes.records as records_module
        from app.models.field import FieldType

        # 构造一个普通字段和一个系统字段（AUTO_NUMBER）
        normal_field = _make_field(field_id=TEST_FIELD_ID, name='普通字段', field_type='single_line_text')
        auto_number_field = _make_field(
            field_id=TEST_FIELD_ID_2, name='自动编号', field_type=FieldType.AUTO_NUMBER.value
        )

        table = _make_table()

        monkeypatch.setattr(
            records_module.TableService, 'get_table_by_id',
            lambda *a, **kw: table
        )
        monkeypatch.setattr(
            records_module.PermissionService, 'check_permission',
            lambda *a, **kw: True
        )
        monkeypatch.setattr(
            records_module.FieldService, 'get_all_fields',
            lambda *a, **kw: [normal_field, auto_number_field]
        )

        # mock 字段权限：普通字段=none（应被过滤），系统字段不在权限字典中
        permissions = {
            TEST_FIELD_ID: FIELD_PERMISSION_NONE,
        }
        monkeypatch.setattr(
            records_module.FieldPermissionService, 'get_table_field_permissions',
            lambda *a, **kw: permissions
        )

        # mock db.session
        mock_db = MagicMock()
        monkeypatch.setattr(records_module, 'db', mock_db)

        monkeypatch.setattr(
            records_module.batch_create_schema, 'validate',
            lambda *a, **kw: {}
        )

        monkeypatch.setattr(
            'app.services.collaboration_service.CollaborationService.broadcast_if_enabled',
            lambda *a, **kw: None
        )

        # mock 自动编号序列生成
        monkeypatch.setattr(
            records_module.RecordService, '_get_next_auto_number_sequence',
            lambda *a, **kw: 1
        )

        # 请求数据：普通字段和系统字段都有值
        request_data = {
            'records': [
                {'values': {
                    TEST_FIELD_ID: 'normal_value',
                    TEST_FIELD_ID_2: 'AUTO-001',
                }}
            ]
        }

        with app.test_request_context(json=request_data):
            g.current_user_id = TEST_USER_ID
            response, status_code = _undecorated(batch_create_records)(TEST_TABLE_ID)

            assert status_code == 200
            data = response.get_json()
            assert data['success'] is True

            # 验证系统字段值被保留，普通字段被过滤
            call_args = mock_db.session.execute.call_args_list[0]
            records_dicts = call_args[0][1]
            final_values = records_dicts[0]['values']
            # 普通字段（none 权限）被过滤
            assert TEST_FIELD_ID not in final_values
            # 系统字段（AUTO_NUMBER）保留
            assert TEST_FIELD_ID_2 in final_values

    def test_no_user_id_skips_write_filtering(self, app, monkeypatch):
        """无 user_id 时不进行写权限过滤（向后兼容）"""
        import app.routes.records as records_module

        field1 = _make_field(field_id=TEST_FIELD_ID, name='字段1', field_type='single_line_text')
        field2 = _make_field(field_id=TEST_FIELD_ID_2, name='字段2', field_type='single_line_text')

        table = _make_table()

        monkeypatch.setattr(
            records_module.TableService, 'get_table_by_id',
            lambda *a, **kw: table
        )
        monkeypatch.setattr(
            records_module.PermissionService, 'check_permission',
            lambda *a, **kw: True
        )
        monkeypatch.setattr(
            records_module.FieldService, 'get_all_fields',
            lambda *a, **kw: [field1, field2]
        )

        call_count = {'count': 0}

        def mock_get_perms(*a, **kw):
            call_count['count'] += 1
            return {}

        monkeypatch.setattr(
            records_module.FieldPermissionService, 'get_table_field_permissions',
            mock_get_perms
        )

        mock_db = MagicMock()
        monkeypatch.setattr(records_module, 'db', mock_db)

        monkeypatch.setattr(
            records_module.batch_create_schema, 'validate',
            lambda *a, **kw: {}
        )

        monkeypatch.setattr(
            'app.services.collaboration_service.CollaborationService.broadcast_if_enabled',
            lambda *a, **kw: None
        )

        request_data = {
            'records': [
                {'values': {
                    TEST_FIELD_ID: 'v1',
                    TEST_FIELD_ID_2: 'v2',
                }}
            ]
        }

        with app.test_request_context(json=request_data):
            g.current_user_id = None
            response, status_code = _undecorated(batch_create_records)(TEST_TABLE_ID)

            assert status_code == 200
            data = response.get_json()
            assert data['success'] is True
            # 无 user_id 时不调用权限查询
            assert call_count['count'] == 0
            # 所有字段值保留
            call_args = mock_db.session.execute.call_args_list[0]
            records_dicts = call_args[0][1]
            final_values = records_dicts[0]['values']
            assert TEST_FIELD_ID in final_values
            assert TEST_FIELD_ID_2 in final_values
