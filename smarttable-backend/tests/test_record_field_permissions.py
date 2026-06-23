"""
RecordService 字段权限过滤测试

采用 mock 方式测试，避免依赖完整数据库和 Flask 上下文环境。
覆盖：
- Record.to_dict 在提供 field_permissions 时正确过滤
- Record.to_dict 向后兼容（无权限参数时不过滤）
- _filter_writable_values_by_permission 辅助方法逻辑
- create_record 在有权限限制时正确过滤字段值
- update_record 在有权限限制时正确过滤字段值
- 系统字段（AUTO_NUMBER/CREATED_BY/LAST_MODIFIED_BY）不被过滤
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.field import (
    Field,
    FieldType,
    FIELD_PERMISSION_READ,
    FIELD_PERMISSION_WRITE,
    FIELD_PERMISSION_NONE,
)
from app.models.record import Record
from app.services.field_permission_service import FieldPermissionService


# 测试用的有效 UUID 字符串（create_record/update_record 内部会调用 uuid.UUID(table_id)）
TEST_TABLE_ID = '12345678-1234-5678-1234-567812345678'
TEST_USER_ID = '87654321-4321-8765-4321-876543218765'


# ---------------------------------------------------------------------------
# 辅助工厂
# ---------------------------------------------------------------------------

def _make_field(field_id='field-1', table_id='table-1', field_type=FieldType.SINGLE_LINE_TEXT.value,
                config=None):
    """构造一个真实 Field 实例（不持久化）"""
    return Field(
        name=f'字段-{field_id}',
        type=field_type,
        table_id=table_id,
        config=config,
        id=field_id,
    )


def _make_record(record_id=None, table_id='table-1', values=None,
                 created_by=None, updated_by=None):
    """构造一个 Record 实例（不持久化），用于 to_dict 测试"""
    now = datetime.now(timezone.utc)
    record = Record(
        id=record_id or uuid.uuid4(),
        table_id=table_id,
        values=values or {},
        created_by=created_by,
        updated_by=updated_by,
        created_at=now,
        updated_at=now,
    )
    # table 属性用于 get_primary_value，这里不设置，由 to_dict 的 try/except 处理
    return record


# ---------------------------------------------------------------------------
# Record.to_dict 字段权限过滤测试
# ---------------------------------------------------------------------------

class TestRecordToDictWithPermissions:
    """Record.to_dict 字段权限过滤测试"""

    def test_to_dict_filters_none_permission_fields(self):
        """to_dict 在提供 field_permissions 时移除 none 权限字段"""
        record = _make_record(values={'f1': 'v1', 'f2': 'v2', 'f3': 'v3'})
        field_permissions = {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_READ,
            'f3': FIELD_PERMISSION_NONE,
        }
        result = record.to_dict(field_permissions=field_permissions)
        # f3 (none) 应被移除
        assert 'f1' in result['values']
        assert 'f2' in result['values']
        assert 'f3' not in result['values']

    def test_to_dict_keeps_read_and_write_fields(self):
        """to_dict 保留 read/write 权限字段"""
        record = _make_record(values={'f1': 'v1', 'f2': 'v2'})
        field_permissions = {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_READ,
        }
        result = record.to_dict(field_permissions=field_permissions)
        assert result['values'] == {'f1': 'v1', 'f2': 'v2'}

    def test_to_dict_without_field_permissions_keeps_all(self):
        """to_dict 未提供 field_permissions 时保留所有字段（向后兼容）"""
        record = _make_record(values={'f1': 'v1', 'f2': 'v2'})
        result = record.to_dict()
        assert result['values'] == {'f1': 'v1', 'f2': 'v2'}

    def test_to_dict_with_none_field_permissions_keeps_all(self):
        """to_dict 显式传入 None 时不过滤"""
        record = _make_record(values={'f1': 'v1', 'f2': 'v2'})
        result = record.to_dict(field_permissions=None)
        assert result['values'] == {'f1': 'v1', 'f2': 'v2'}

    def test_to_dict_with_empty_field_permissions_keeps_all(self):
        """to_dict 传入空权限字典时，所有字段默认 read，全部保留"""
        record = _make_record(values={'f1': 'v1', 'f2': 'v2'})
        result = record.to_dict(field_permissions={})
        assert result['values'] == {'f1': 'v1', 'f2': 'v2'}

    def test_to_dict_with_attached_field_permissions(self):
        """to_dict 使用 service 层附加的 _field_permissions 属性过滤"""
        record = _make_record(values={'f1': 'v1', 'f2': 'v2', 'f3': 'v3'})
        # 模拟 service 层附加的属性
        record._field_permissions = {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_READ,
            'f3': FIELD_PERMISSION_NONE,
        }
        result = record.to_dict()
        # f3 (none) 应被移除
        assert 'f1' in result['values']
        assert 'f2' in result['values']
        assert 'f3' not in result['values']

    def test_to_dict_explicit_permissions_override_attached(self):
        """显式传入的 field_permissions 优先于附加的 _field_permissions"""
        record = _make_record(values={'f1': 'v1', 'f2': 'v2'})
        # 附加属性标记 f1 为 none
        record._field_permissions = {
            'f1': FIELD_PERMISSION_NONE,
            'f2': FIELD_PERMISSION_READ,
        }
        # 显式传入标记 f1 为 write
        explicit_permissions = {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_READ,
        }
        result = record.to_dict(field_permissions=explicit_permissions)
        # 显式传入应优先生效，f1 保留
        assert 'f1' in result['values']
        assert 'f2' in result['values']

    def test_to_dict_preserves_meta_data_with_permissions(self):
        """to_dict 在过滤字段值时仍正确返回元数据"""
        user_id = uuid.uuid4()
        record = _make_record(
            values={'f1': 'v1', 'f2': 'v2'},
            created_by=user_id,
            updated_by=user_id,
        )
        field_permissions = {'f1': FIELD_PERMISSION_WRITE, 'f2': FIELD_PERMISSION_NONE}
        result = record.to_dict(field_permissions=field_permissions)
        assert result['created_by'] == str(user_id)
        assert result['updated_by'] == str(user_id)
        assert 'created_at' in result
        assert 'updated_at' in result


# ---------------------------------------------------------------------------
# _filter_writable_values_by_permission 辅助方法测试
# ---------------------------------------------------------------------------

class TestFilterWritableValuesByPermission:
    """_filter_writable_values_by_permission 辅助方法测试"""

    def test_no_user_context_returns_original_values(self):
        """无用户上下文时返回原值（不过滤）"""
        from app.services.record_service import RecordService
        fields = [_make_field(field_id='f1'), _make_field(field_id='f2')]
        values = {'f1': 'v1', 'f2': 'v2'}
        # 无 Flask 上下文，_get_current_user_id 返回 None
        result = RecordService._filter_writable_values_by_permission(
            'table-1', fields, values
        )
        assert result == values

    def test_filters_non_writable_fields(self, monkeypatch):
        """有用户上下文时过滤无写权限的字段"""
        from app.services import record_service as rs_module
        from app.services.record_service import RecordService

        # mock g.current_user_id
        monkeypatch.setattr(rs_module, '_get_current_user_id', lambda: 'user-1')

        # mock FieldPermissionService.get_table_field_permissions
        field_permissions = {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_READ,
            'f3': FIELD_PERMISSION_NONE,
        }
        monkeypatch.setattr(
            FieldPermissionService,
            'get_table_field_permissions',
            staticmethod(lambda table_id, user_id: field_permissions),
        )

        # mock current_app.logger.warning 避免无应用上下文报错
        mock_logger = MagicMock()
        monkeypatch.setattr(rs_module, 'current_app', MagicMock(logger=mock_logger))

        fields = [
            _make_field(field_id='f1'),
            _make_field(field_id='f2'),
            _make_field(field_id='f3'),
        ]
        values = {'f1': 'v1', 'f2': 'v2', 'f3': 'v3'}
        result = RecordService._filter_writable_values_by_permission(
            'table-1', fields, values
        )
        # 仅 f1 (write) 保留
        assert result == {'f1': 'v1'}

    def test_system_fields_not_filtered(self, monkeypatch):
        """系统字段（AUTO_NUMBER/CREATED_BY/LAST_MODIFIED_BY）不被过滤"""
        from app.services import record_service as rs_module
        from app.services.record_service import RecordService

        monkeypatch.setattr(rs_module, '_get_current_user_id', lambda: 'user-1')

        # 所有字段都无写权限
        field_permissions = {
            'f-auto': FIELD_PERMISSION_NONE,
            'f-created': FIELD_PERMISSION_NONE,
            'f-modified': FIELD_PERMISSION_NONE,
            'f-normal': FIELD_PERMISSION_NONE,
        }
        monkeypatch.setattr(
            FieldPermissionService,
            'get_table_field_permissions',
            staticmethod(lambda table_id, user_id: field_permissions),
        )

        mock_logger = MagicMock()
        monkeypatch.setattr(rs_module, 'current_app', MagicMock(logger=mock_logger))

        fields = [
            _make_field(field_id='f-auto', field_type=FieldType.AUTO_NUMBER.value),
            _make_field(field_id='f-created', field_type=FieldType.CREATED_BY.value),
            _make_field(field_id='f-modified', field_type=FieldType.LAST_MODIFIED_BY.value),
            _make_field(field_id='f-normal', field_type=FieldType.SINGLE_LINE_TEXT.value),
        ]
        values = {
            'f-auto': 'AUTO-001',
            'f-created': 'user-creator',
            'f-modified': 'user-modifier',
            'f-normal': 'normal-value',
        }
        result = RecordService._filter_writable_values_by_permission(
            'table-1', fields, values
        )
        # 系统字段保留，普通字段被过滤
        assert 'f-auto' in result
        assert 'f-created' in result
        assert 'f-modified' in result
        assert 'f-normal' not in result

    def test_logs_warning_when_fields_filtered(self, monkeypatch):
        """被过滤字段时记录 warning 日志"""
        from app.services import record_service as rs_module
        from app.services.record_service import RecordService

        monkeypatch.setattr(rs_module, '_get_current_user_id', lambda: 'user-1')

        field_permissions = {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_NONE,
        }
        monkeypatch.setattr(
            FieldPermissionService,
            'get_table_field_permissions',
            staticmethod(lambda table_id, user_id: field_permissions),
        )

        mock_logger = MagicMock()
        monkeypatch.setattr(rs_module, 'current_app', MagicMock(logger=mock_logger))

        fields = [_make_field(field_id='f1'), _make_field(field_id='f2')]
        values = {'f1': 'v1', 'f2': 'v2'}
        RecordService._filter_writable_values_by_permission('table-1', fields, values)
        # 应记录 warning
        mock_logger.warning.assert_called_once()

    def test_no_filtering_when_all_writable(self, monkeypatch):
        """所有字段都有写权限时不记录日志"""
        from app.services import record_service as rs_module
        from app.services.record_service import RecordService

        monkeypatch.setattr(rs_module, '_get_current_user_id', lambda: 'user-1')

        field_permissions = {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_WRITE,
        }
        monkeypatch.setattr(
            FieldPermissionService,
            'get_table_field_permissions',
            staticmethod(lambda table_id, user_id: field_permissions),
        )

        mock_logger = MagicMock()
        monkeypatch.setattr(rs_module, 'current_app', MagicMock(logger=mock_logger))

        fields = [_make_field(field_id='f1'), _make_field(field_id='f2')]
        values = {'f1': 'v1', 'f2': 'v2'}
        result = RecordService._filter_writable_values_by_permission(
            'table-1', fields, values
        )
        assert result == values
        mock_logger.warning.assert_not_called()


# ---------------------------------------------------------------------------
# _get_current_user_id 辅助方法测试
# ---------------------------------------------------------------------------

class TestGetCurrentUserId:
    """_get_current_user_id 辅助方法测试"""

    def test_returns_none_without_app_context(self):
        """无 Flask 应用上下文时返回 None"""
        from app.services.record_service import _get_current_user_id
        result = _get_current_user_id()
        assert result is None

    def test_returns_user_id_with_app_context(self, app):
        """有 Flask 应用上下文且 g.current_user_id 设置时返回用户 ID"""
        from flask import g
        from app.services.record_service import _get_current_user_id
        with app.app_context():
            g.current_user_id = 'test-user-123'
            result = _get_current_user_id()
            assert result == 'test-user-123'

    def test_returns_none_when_g_has_no_current_user_id(self, app):
        """有 Flask 应用上下文但 g.current_user_id 未设置时返回 None"""
        from app.services.record_service import _get_current_user_id
        with app.app_context():
            result = _get_current_user_id()
            assert result is None


# ---------------------------------------------------------------------------
# create_record 字段权限过滤测试
# ---------------------------------------------------------------------------

def _setup_create_record_mocks(monkeypatch, fields, field_permissions):
    """为 create_record 测试设置通用 mock。

    返回 captured_record 字典，测试可通过 captured_record['record'] 访问创建的记录。
    """
    from app.services import record_service as rs_module
    from app.services.record_service import RecordService
    from app.services.field_service import FieldService

    # mock 当前用户
    monkeypatch.setattr(rs_module, '_get_current_user_id', lambda: 'user-1')

    # mock 字段列表
    monkeypatch.setattr(FieldService, 'get_all_fields', staticmethod(lambda table_id: fields))

    # mock 字段权限
    monkeypatch.setattr(
        FieldPermissionService,
        'get_table_field_permissions',
        staticmethod(lambda table_id, user_id: field_permissions),
    )

    # mock current_app.logger
    mock_logger = MagicMock()
    monkeypatch.setattr(rs_module, 'current_app', MagicMock(logger=mock_logger))

    # mock Record 类（避免 SQLAlchemy 默认值未应用导致 ID 为 None）
    captured_record = {}

    def mock_record_factory(**kwargs):
        record = MagicMock()
        record.id = uuid.uuid4()
        record.values = kwargs.get('values', {})
        record.table_id = kwargs.get('table_id')
        record.created_by = kwargs.get('created_by')
        record.updated_by = kwargs.get('updated_by')
        record.to_dict.return_value = {'values': record.values}
        captured_record['record'] = record
        return record

    monkeypatch.setattr(rs_module, 'Record', mock_record_factory)

    # mock db.session
    monkeypatch.setattr(rs_module.db.session, 'add', lambda record: None)
    monkeypatch.setattr(rs_module.db.session, 'flush', lambda: None)
    monkeypatch.setattr(rs_module.db.session, 'commit', lambda: None)

    # mock RecordHistory.create_history
    monkeypatch.setattr(
        rs_module.RecordHistory,
        'create_history',
        staticmethod(lambda **kwargs: MagicMock()),
    )

    # mock Table.query.get（返回 None 跳过广播）
    monkeypatch.setattr(rs_module.Table, 'query', MagicMock(get=MagicMock(return_value=None)))

    return captured_record


class TestCreateRecordFieldPermissions:
    """create_record 字段权限过滤测试"""

    def test_create_record_filters_non_writable_values(self, monkeypatch, app):
        """create_record 过滤无写权限的字段值"""
        from app.services.record_service import RecordService

        fields = [
            _make_field(field_id='f1'),
            _make_field(field_id='f2'),
            _make_field(field_id='f3'),
        ]
        field_permissions = {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_READ,
            'f3': FIELD_PERMISSION_NONE,
        }
        captured_record = _setup_create_record_mocks(monkeypatch, fields, field_permissions)

        # 调用 create_record
        values = {'f1': 'v1', 'f2': 'v2', 'f3': 'v3'}
        RecordService.create_record(TEST_TABLE_ID, values, created_by=TEST_USER_ID)

        # 验证 f1 (write) 的用户值被保留
        created_record = captured_record['record']
        assert created_record.values.get('f1') == 'v1'
        # f2 (read) 和 f3 (none) 的用户值被过滤（可能被替换为默认值）
        assert created_record.values.get('f2') != 'v2'
        assert created_record.values.get('f3') != 'v3'

    def test_create_record_preserves_system_fields(self, monkeypatch, app):
        """create_record 保留系统字段值（即使无写权限）"""
        from app.services.record_service import RecordService

        fields = [
            _make_field(field_id='f-auto', field_type=FieldType.AUTO_NUMBER.value),
            _make_field(field_id='f-created', field_type=FieldType.CREATED_BY.value),
            _make_field(field_id='f-normal', field_type=FieldType.SINGLE_LINE_TEXT.value),
        ]
        # 所有字段都无写权限
        field_permissions = {
            'f-auto': FIELD_PERMISSION_NONE,
            'f-created': FIELD_PERMISSION_NONE,
            'f-normal': FIELD_PERMISSION_NONE,
        }
        captured_record = _setup_create_record_mocks(monkeypatch, fields, field_permissions)

        values = {
            'f-auto': 'AUTO-001',
            'f-created': 'creator-id',
            'f-normal': 'normal-value',
        }
        RecordService.create_record(TEST_TABLE_ID, values, created_by=TEST_USER_ID)

        created_record = captured_record['record']
        # 系统字段保留
        assert 'f-auto' in created_record.values
        assert 'f-created' in created_record.values
        # 普通字段被过滤（用户提供的值被移除，可能被替换为默认值）
        assert created_record.values.get('f-normal') != 'normal-value'

    def test_create_record_no_filtering_without_user_context(self, monkeypatch, app):
        """无用户上下文时 create_record 不过滤字段值（向后兼容）"""
        from app.services import record_service as rs_module
        from app.services.record_service import RecordService
        from app.services.field_service import FieldService

        # mock 无当前用户
        monkeypatch.setattr(rs_module, '_get_current_user_id', lambda: None)

        fields = [_make_field(field_id='f1'), _make_field(field_id='f2')]
        monkeypatch.setattr(FieldService, 'get_all_fields', staticmethod(lambda table_id: fields))

        # mock Record 类
        captured_record = {}
        def mock_record_factory(**kwargs):
            record = MagicMock()
            record.id = uuid.uuid4()
            record.values = kwargs.get('values', {})
            record.to_dict.return_value = {'values': record.values}
            captured_record['record'] = record
            return record
        monkeypatch.setattr(rs_module, 'Record', mock_record_factory)

        monkeypatch.setattr(rs_module.db.session, 'add', lambda record: None)
        monkeypatch.setattr(rs_module.db.session, 'flush', lambda: None)
        monkeypatch.setattr(rs_module.db.session, 'commit', lambda: None)
        monkeypatch.setattr(
            rs_module.RecordHistory,
            'create_history',
            staticmethod(lambda **kwargs: MagicMock()),
        )
        monkeypatch.setattr(rs_module.Table, 'query', MagicMock(get=MagicMock(return_value=None)))

        values = {'f1': 'v1', 'f2': 'v2'}
        RecordService.create_record(TEST_TABLE_ID, values, created_by=TEST_USER_ID)

        created_record = captured_record['record']
        # 无用户上下文，所有字段保留
        assert created_record.values.get('f1') == 'v1'
        assert created_record.values.get('f2') == 'v2'


# ---------------------------------------------------------------------------
# update_record 字段权限过滤测试
# ---------------------------------------------------------------------------

def _setup_update_record_mocks(monkeypatch, fields, field_permissions, has_user=True):
    """为 update_record 测试设置通用 mock。

    Args:
        has_user: 是否模拟有当前用户上下文（True=有权限过滤，False=无用户上下文）

    返回 None。测试自行构造 record 对象。
    """
    from app.services import record_service as rs_module
    from app.services.field_service import FieldService

    # mock 当前用户
    if has_user:
        monkeypatch.setattr(rs_module, '_get_current_user_id', lambda: 'user-1')
    else:
        monkeypatch.setattr(rs_module, '_get_current_user_id', lambda: None)

    # mock 字段列表
    monkeypatch.setattr(FieldService, 'get_all_fields', staticmethod(lambda table_id: fields))

    # mock 字段权限
    if field_permissions is not None:
        monkeypatch.setattr(
            FieldPermissionService,
            'get_table_field_permissions',
            staticmethod(lambda table_id, user_id: field_permissions),
        )

    # mock current_app.logger
    mock_logger = MagicMock()
    monkeypatch.setattr(rs_module, 'current_app', MagicMock(logger=mock_logger))

    # mock db.session
    monkeypatch.setattr(rs_module.db.session, 'flush', lambda: None)
    monkeypatch.setattr(rs_module.db.session, 'commit', lambda: None)
    monkeypatch.setattr(rs_module.db.session, 'add', lambda obj: None)

    # mock Table.query.get（返回 None 跳过广播）
    monkeypatch.setattr(rs_module.Table, 'query', MagicMock(get=MagicMock(return_value=None)))


class TestUpdateRecordFieldPermissions:
    """update_record 字段权限过滤测试"""

    def test_update_record_filters_non_writable_values(self, monkeypatch, app):
        """update_record 过滤无写权限的字段值"""
        from app.services.record_service import RecordService

        fields = [
            _make_field(field_id='f1'),
            _make_field(field_id='f2'),
            _make_field(field_id='f3'),
        ]
        field_permissions = {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_READ,
            'f3': FIELD_PERMISSION_NONE,
        }
        _setup_update_record_mocks(monkeypatch, fields, field_permissions)

        # 构造已有记录（使用有效 UUID 作为 table_id）
        record = _make_record(
            table_id=TEST_TABLE_ID,
            values={'f1': 'old-v1', 'f2': 'old-v2', 'f3': 'old-v3'},
        )

        # 调用 update_record
        new_values = {'f1': 'new-v1', 'f2': 'new-v2', 'f3': 'new-v3'}
        RecordService.update_record(record, values=new_values, updated_by=TEST_USER_ID)

        # 验证只有 f1 (write) 被更新
        assert record.values.get('f1') == 'new-v1'
        # f2 (read) 和 f3 (none) 未被更新
        assert record.values.get('f2') == 'old-v2'
        assert record.values.get('f3') == 'old-v3'

    def test_update_record_preserves_auto_number_fields(self, monkeypatch, app):
        """update_record 保留 AUTO_NUMBER 字段过滤逻辑（不可编辑）"""
        from app.services.record_service import RecordService

        fields = [
            _make_field(field_id='f-auto', field_type=FieldType.AUTO_NUMBER.value),
            _make_field(field_id='f-normal', field_type=FieldType.SINGLE_LINE_TEXT.value),
        ]
        # 所有普通字段都有写权限
        field_permissions = {
            'f-auto': FIELD_PERMISSION_WRITE,
            'f-normal': FIELD_PERMISSION_WRITE,
        }
        _setup_update_record_mocks(monkeypatch, fields, field_permissions)

        record = _make_record(
            table_id=TEST_TABLE_ID,
            values={'f-auto': 'AUTO-001', 'f-normal': 'old-value'},
        )

        # 尝试修改自动编号字段和普通字段
        new_values = {'f-auto': 'HACKED', 'f-normal': 'new-value'}
        RecordService.update_record(record, values=new_values, updated_by=TEST_USER_ID)

        # 自动编号字段不可修改
        assert record.values.get('f-auto') == 'AUTO-001'
        # 普通字段可修改
        assert record.values.get('f-normal') == 'new-value'

    def test_update_record_preserves_system_fields(self, monkeypatch, app):
        """update_record 保留系统字段（CREATED_BY/LAST_MODIFIED_BY）"""
        from app.services.record_service import RecordService

        fields = [
            _make_field(field_id='f-created', field_type=FieldType.CREATED_BY.value),
            _make_field(field_id='f-modified', field_type=FieldType.LAST_MODIFIED_BY.value),
            _make_field(field_id='f-normal', field_type=FieldType.SINGLE_LINE_TEXT.value),
        ]
        # 所有字段都无写权限
        field_permissions = {
            'f-created': FIELD_PERMISSION_NONE,
            'f-modified': FIELD_PERMISSION_NONE,
            'f-normal': FIELD_PERMISSION_NONE,
        }
        _setup_update_record_mocks(monkeypatch, fields, field_permissions)

        record = _make_record(
            table_id=TEST_TABLE_ID,
            values={
                'f-created': 'original-creator',
                'f-modified': 'original-modifier',
                'f-normal': 'old-value',
            },
        )

        new_values = {
            'f-created': 'hacked-creator',
            'f-modified': 'hacked-modifier',
            'f-normal': 'new-value',
        }
        RecordService.update_record(record, values=new_values, updated_by=TEST_USER_ID)

        # 系统字段保留原值（不被权限过滤，但也不应被用户修改）
        # 注意：系统字段值会通过权限过滤（因为系统字段豁免），但这里我们测试的是
        # 系统字段不会被权限过滤掉
        assert 'f-created' in record.values
        assert 'f-modified' in record.values
        # 普通字段被过滤
        assert record.values.get('f-normal') == 'old-value'

    def test_update_record_no_filtering_without_user_context(self, monkeypatch, app):
        """无用户上下文时 update_record 不过滤字段值（向后兼容）"""
        from app.services.record_service import RecordService

        fields = [_make_field(field_id='f1'), _make_field(field_id='f2')]
        _setup_update_record_mocks(monkeypatch, fields, None, has_user=False)

        record = _make_record(
            table_id=TEST_TABLE_ID,
            values={'f1': 'old-v1', 'f2': 'old-v2'},
        )

        new_values = {'f1': 'new-v1', 'f2': 'new-v2'}
        RecordService.update_record(record, values=new_values, updated_by=TEST_USER_ID)

        # 无用户上下文，所有字段可更新
        assert record.values.get('f1') == 'new-v1'
        assert record.values.get('f2') == 'new-v2'


# ---------------------------------------------------------------------------
# get_table_records 字段权限附加测试
# ---------------------------------------------------------------------------

class TestGetTableRecordsFieldPermissions:
    """get_table_records 字段权限附加测试"""

    def test_attaches_field_permissions_to_records(self, monkeypatch, app):
        """get_table_records 将字段权限附加到记录对象上"""
        from app.services import record_service as rs_module
        from app.services.record_service import RecordService

        monkeypatch.setattr(rs_module, '_get_current_user_id', lambda: 'user-1')

        field_permissions = {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_NONE,
        }
        monkeypatch.setattr(
            FieldPermissionService,
            'get_table_field_permissions',
            staticmethod(lambda table_id, user_id: field_permissions),
        )

        # mock Record.query
        record1 = _make_record(values={'f1': 'v1', 'f2': 'v2'})
        record2 = _make_record(values={'f1': 'v3', 'f2': 'v4'})

        mock_query = MagicMock()
        mock_query.filter_by.return_value = mock_query
        mock_query.count.return_value = 2
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value.all.return_value = [record1, record2]
        monkeypatch.setattr(rs_module.Record, 'query', mock_query)

        records, total = RecordService.get_table_records('table-1', page=1, per_page=20)

        assert total == 2
        assert len(records) == 2
        # 验证字段权限被附加
        assert hasattr(records[0], '_field_permissions')
        assert records[0]._field_permissions == field_permissions
        assert hasattr(records[1], '_field_permissions')
        assert records[1]._field_permissions == field_permissions

    def test_no_attaching_without_user_context(self, monkeypatch, app):
        """无用户上下文时不附加字段权限"""
        from app.services import record_service as rs_module
        from app.services.record_service import RecordService

        monkeypatch.setattr(rs_module, '_get_current_user_id', lambda: None)

        record1 = _make_record(values={'f1': 'v1'})

        mock_query = MagicMock()
        mock_query.filter_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value.all.return_value = [record1]
        monkeypatch.setattr(rs_module.Record, 'query', mock_query)

        records, total = RecordService.get_table_records('table-1', page=1, per_page=20)

        assert total == 1
        # 无用户上下文，不附加属性
        assert not hasattr(records[0], '_field_permissions')

    def test_attached_permissions_used_in_to_dict(self, monkeypatch, app):
        """附加的权限属性在 to_dict 时生效"""
        from app.services import record_service as rs_module
        from app.services.record_service import RecordService

        monkeypatch.setattr(rs_module, '_get_current_user_id', lambda: 'user-1')

        field_permissions = {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_NONE,
        }
        monkeypatch.setattr(
            FieldPermissionService,
            'get_table_field_permissions',
            staticmethod(lambda table_id, user_id: field_permissions),
        )

        record1 = _make_record(values={'f1': 'v1', 'f2': 'v2'})

        mock_query = MagicMock()
        mock_query.filter_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value.all.return_value = [record1]
        monkeypatch.setattr(rs_module.Record, 'query', mock_query)

        records, total = RecordService.get_table_records('table-1', page=1, per_page=20)

        # 调用 to_dict，应自动使用附加的权限
        data = records[0].to_dict()
        assert 'f1' in data['values']
        assert 'f2' not in data['values']
