"""
FieldPermissionService 字段权限服务测试

采用 mock 数据库查询的方式编写纯逻辑测试，
避免依赖 JWT/数据库 fixture 环境。
覆盖服务所有公开方法的权限判定与过滤逻辑。
"""
import pytest
from unittest.mock import MagicMock

from app.services.field_permission_service import FieldPermissionService
from app.models.field import (
    Field,
    FieldType,
    FIELD_PERMISSION_READ,
    FIELD_PERMISSION_WRITE,
    FIELD_PERMISSION_NONE,
    DEFAULT_FIELD_PERMISSIONS,
    UNRESTRICTABLE_ROLES,
)
from app.models.base import MemberRole


# ---------------------------------------------------------------------------
# 辅助工厂：构造不依赖数据库的领域对象
# ---------------------------------------------------------------------------

def _make_field(field_id='field-1', table_id='table-1', config=None):
    """构造一个真实 Field 实例（不持久化），复用其 get_effective_permission 逻辑"""
    return Field(
        name='测试字段',
        type=FieldType.SINGLE_LINE_TEXT.value,
        table_id=table_id,
        config=config,
        id=field_id,
    )


def _make_table(table_id='table-1', base_id='base-1'):
    """构造一个模拟 Table 对象"""
    table = MagicMock()
    table.id = table_id
    table.base_id = base_id
    return table


def _make_base(base_id='base-1', owner_id='owner-user'):
    """构造一个模拟 Base 对象"""
    base = MagicMock()
    base.id = base_id
    base.owner_id = owner_id
    return base


def _make_member(role: MemberRole):
    """构造一个模拟 BaseMember 对象"""
    member = MagicMock()
    member.role = role
    return member


def _setup_query_mocks(monkeypatch, *, field=None, table=None, base=None,
                       member=None, field_list=None):
    """统一 mock 掉服务模块中引用的 Field/Table/Base/BaseMember。

    通过替换 field_permission_service 模块中的模型引用来避免触发
    Flask-SQLAlchemy 的 _QueryProperty 描述符（该描述符需要应用上下文）。

    Args:
        monkeypatch: pytest monkeypatch fixture
        field: Field.query.get 返回值（None 表示字段不存在）
        table: Table.query.get 返回值
        base: Base.query.get 返回值
        member: BaseMember.query.filter_by().first() 返回值
        field_list: Field.query.filter_by().all() 返回值
    """
    import app.services.field_permission_service as fps_module

    # Field 类 mock
    field_query = MagicMock()
    field_query.get.return_value = field
    field_query.filter_by.return_value.all.return_value = field_list or []
    mock_field_cls = MagicMock()
    mock_field_cls.query = field_query
    monkeypatch.setattr(fps_module, 'Field', mock_field_cls)

    # Table 类 mock
    table_query = MagicMock()
    table_query.get.return_value = table
    mock_table_cls = MagicMock()
    mock_table_cls.query = table_query
    monkeypatch.setattr(fps_module, 'Table', mock_table_cls)

    # Base 类 mock
    base_query = MagicMock()
    base_query.get.return_value = base
    mock_base_cls = MagicMock()
    mock_base_cls.query = base_query
    monkeypatch.setattr(fps_module, 'Base', mock_base_cls)

    # BaseMember 类 mock
    member_query = MagicMock()
    member_query.filter_by.return_value.first.return_value = member
    mock_member_cls = MagicMock()
    mock_member_cls.query = member_query
    monkeypatch.setattr(fps_module, 'BaseMember', mock_member_cls)


# 导入需要 mock 的模型（仅用于类型引用，测试中通过服务模块引用替换）
from app.models.base import Base, BaseMember
from app.models.table import Table


# ---------------------------------------------------------------------------
# get_field_permission 测试
# ---------------------------------------------------------------------------

class TestGetFieldPermission:
    """get_field_permission 方法测试"""

    def test_owner_returns_write(self, monkeypatch):
        """owner 用户对字段返回 write"""
        field = _make_field(config={'permissions': {'editor': 'none'}})
        table = _make_table()
        base = _make_base(owner_id='owner-user')
        _setup_query_mocks(monkeypatch, field=field, table=table, base=base,
                           member=None)
        # owner-user 匹配 base.owner_id，应返回 'owner' 角色
        perm = FieldPermissionService.get_field_permission('field-1', 'owner-user')
        assert perm == FIELD_PERMISSION_WRITE

    def test_admin_returns_write(self, monkeypatch):
        """admin 用户对字段返回 write（即使字段配置了更低权限）"""
        field = _make_field(config={'permissions': {'admin': 'none'}})
        table = _make_table()
        base = _make_base(owner_id='someone-else')
        member = _make_member(MemberRole.ADMIN)
        _setup_query_mocks(monkeypatch, field=field, table=table, base=base,
                           member=member)
        perm = FieldPermissionService.get_field_permission('field-1', 'admin-user')
        assert perm == FIELD_PERMISSION_WRITE

    def test_editor_default_returns_write(self, monkeypatch):
        """editor 用户在未配置权限时默认返回 write"""
        field = _make_field(config={})
        table = _make_table()
        base = _make_base(owner_id='someone-else')
        member = _make_member(MemberRole.EDITOR)
        _setup_query_mocks(monkeypatch, field=field, table=table, base=base,
                           member=member)
        perm = FieldPermissionService.get_field_permission('field-1', 'editor-user')
        assert perm == FIELD_PERMISSION_WRITE

    def test_viewer_default_returns_read(self, monkeypatch):
        """viewer 用户在未配置权限时默认返回 read"""
        field = _make_field(config={})
        table = _make_table()
        base = _make_base(owner_id='someone-else')
        member = _make_member(MemberRole.VIEWER)
        _setup_query_mocks(monkeypatch, field=field, table=table, base=base,
                           member=member)
        perm = FieldPermissionService.get_field_permission('field-1', 'viewer-user')
        assert perm == FIELD_PERMISSION_READ

    def test_no_base_permission_returns_none(self, monkeypatch):
        """无 Base 权限的用户返回 none"""
        field = _make_field()
        table = _make_table()
        base = _make_base(owner_id='someone-else')
        _setup_query_mocks(monkeypatch, field=field, table=table, base=base,
                           member=None)
        perm = FieldPermissionService.get_field_permission('field-1', 'stranger')
        assert perm == FIELD_PERMISSION_NONE

    def test_nonexistent_field_returns_none(self, monkeypatch):
        """不存在的字段返回 none"""
        _setup_query_mocks(monkeypatch, field=None, table=None, base=None,
                           member=None)
        perm = FieldPermissionService.get_field_permission('no-such-field', 'any-user')
        assert perm == FIELD_PERMISSION_NONE

    def test_nonexistent_table_returns_none(self, monkeypatch):
        """字段存在但表不存在时返回 none"""
        field = _make_field()
        _setup_query_mocks(monkeypatch, field=field, table=None, base=None,
                           member=None)
        perm = FieldPermissionService.get_field_permission('field-1', 'any-user')
        assert perm == FIELD_PERMISSION_NONE

    def test_editor_with_explicit_read_config_returns_read(self, monkeypatch):
        """editor 用户在字段显式配置为 read 时返回 read"""
        field = _make_field(config={'permissions': {'editor': 'read'}})
        table = _make_table()
        base = _make_base(owner_id='someone-else')
        member = _make_member(MemberRole.EDITOR)
        _setup_query_mocks(monkeypatch, field=field, table=table, base=base,
                           member=member)
        perm = FieldPermissionService.get_field_permission('field-1', 'editor-user')
        assert perm == FIELD_PERMISSION_READ

    def test_viewer_with_explicit_none_config_returns_none(self, monkeypatch):
        """viewer 用户在字段显式配置为 none 时返回 none"""
        field = _make_field(config={'permissions': {'viewer': 'none'}})
        table = _make_table()
        base = _make_base(owner_id='someone-else')
        member = _make_member(MemberRole.VIEWER)
        _setup_query_mocks(monkeypatch, field=field, table=table, base=base,
                           member=member)
        perm = FieldPermissionService.get_field_permission('field-1', 'viewer-user')
        assert perm == FIELD_PERMISSION_NONE

    def test_commenter_default_returns_read(self, monkeypatch):
        """commenter 用户在未配置权限时默认返回 read"""
        field = _make_field(config={})
        table = _make_table()
        base = _make_base(owner_id='someone-else')
        member = _make_member(MemberRole.COMMENTER)
        _setup_query_mocks(monkeypatch, field=field, table=table, base=base,
                           member=member)
        perm = FieldPermissionService.get_field_permission('field-1', 'commenter-user')
        assert perm == FIELD_PERMISSION_READ


# ---------------------------------------------------------------------------
# get_table_field_permissions 测试
# ---------------------------------------------------------------------------

class TestGetTableFieldPermissions:
    """get_table_field_permissions 批量查询测试"""

    def test_batch_returns_correct_permissions(self, monkeypatch):
        """批量返回各字段权限（混合配置）"""
        field1 = _make_field(field_id='f1', config={})  # editor -> write
        field2 = _make_field(field_id='f2',
                             config={'permissions': {'editor': 'read'}})
        field3 = _make_field(field_id='f3',
                             config={'permissions': {'editor': 'none'}})
        table = _make_table()
        base = _make_base(owner_id='someone-else')
        member = _make_member(MemberRole.EDITOR)
        _setup_query_mocks(monkeypatch, field=None, table=table, base=base,
                           member=member, field_list=[field1, field2, field3])

        result = FieldPermissionService.get_table_field_permissions('table-1', 'editor-user')

        assert result == {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_READ,
            'f3': FIELD_PERMISSION_NONE,
        }

    def test_batch_owner_all_write(self, monkeypatch):
        """owner 用户对所有字段返回 write"""
        field1 = _make_field(field_id='f1',
                             config={'permissions': {'owner': 'none'}})
        field2 = _make_field(field_id='f2',
                             config={'permissions': {'editor': 'none'}})
        table = _make_table()
        base = _make_base(owner_id='owner-user')
        _setup_query_mocks(monkeypatch, field=None, table=table, base=base,
                           member=None, field_list=[field1, field2])

        result = FieldPermissionService.get_table_field_permissions('table-1', 'owner-user')

        assert result == {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_WRITE,
        }

    def test_batch_no_permission_all_none(self, monkeypatch):
        """无 Base 权限用户对所有字段返回 none"""
        field1 = _make_field(field_id='f1')
        field2 = _make_field(field_id='f2')
        table = _make_table()
        base = _make_base(owner_id='someone-else')
        _setup_query_mocks(monkeypatch, field=None, table=table, base=base,
                           member=None, field_list=[field1, field2])

        result = FieldPermissionService.get_table_field_permissions('table-1', 'stranger')

        assert result == {
            'f1': FIELD_PERMISSION_NONE,
            'f2': FIELD_PERMISSION_NONE,
        }

    def test_batch_nonexistent_table_returns_empty(self, monkeypatch):
        """不存在的表返回空字典"""
        _setup_query_mocks(monkeypatch, field=None, table=None, base=None,
                           member=None, field_list=[])
        result = FieldPermissionService.get_table_field_permissions('no-table', 'any-user')
        assert result == {}

    def test_batch_empty_table_returns_empty(self, monkeypatch):
        """存在但无字段的表返回空字典"""
        table = _make_table()
        base = _make_base(owner_id='owner-user')
        _setup_query_mocks(monkeypatch, field=None, table=table, base=base,
                           member=None, field_list=[])
        result = FieldPermissionService.get_table_field_permissions('table-1', 'owner-user')
        assert result == {}


# ---------------------------------------------------------------------------
# check_field_read_permission / check_field_write_permission 测试
# ---------------------------------------------------------------------------

class TestCheckFieldPermissions:
    """check_field_read_permission / check_field_write_permission 测试"""

    def test_check_read_permission_true_for_write(self, monkeypatch):
        """write 权限通过读检查"""
        field = _make_field(config={})
        table = _make_table()
        base = _make_base(owner_id='owner-user')
        _setup_query_mocks(monkeypatch, field=field, table=table, base=base,
                           member=None)
        assert FieldPermissionService.check_field_read_permission('field-1', 'owner-user') is True

    def test_check_read_permission_true_for_read(self, monkeypatch):
        """read 权限通过读检查"""
        field = _make_field(config={'permissions': {'viewer': 'read'}})
        table = _make_table()
        base = _make_base(owner_id='someone-else')
        member = _make_member(MemberRole.VIEWER)
        _setup_query_mocks(monkeypatch, field=field, table=table, base=base,
                           member=member)
        assert FieldPermissionService.check_field_read_permission('field-1', 'viewer-user') is True

    def test_check_read_permission_false_for_none(self, monkeypatch):
        """none 权限不通过读检查"""
        field = _make_field(config={'permissions': {'viewer': 'none'}})
        table = _make_table()
        base = _make_base(owner_id='someone-else')
        member = _make_member(MemberRole.VIEWER)
        _setup_query_mocks(monkeypatch, field=field, table=table, base=base,
                           member=member)
        assert FieldPermissionService.check_field_read_permission('field-1', 'viewer-user') is False

    def test_check_read_permission_false_for_nonexistent_field(self, monkeypatch):
        """不存在的字段不通过读检查"""
        _setup_query_mocks(monkeypatch, field=None, table=None, base=None,
                           member=None)
        assert FieldPermissionService.check_field_read_permission('no-field', 'any-user') is False

    def test_check_write_permission_true_for_write(self, monkeypatch):
        """write 权限通过写检查"""
        field = _make_field(config={})
        table = _make_table()
        base = _make_base(owner_id='owner-user')
        _setup_query_mocks(monkeypatch, field=field, table=table, base=base,
                           member=None)
        assert FieldPermissionService.check_field_write_permission('field-1', 'owner-user') is True

    def test_check_write_permission_false_for_read(self, monkeypatch):
        """read 权限不通过写检查"""
        field = _make_field(config={'permissions': {'viewer': 'read'}})
        table = _make_table()
        base = _make_base(owner_id='someone-else')
        member = _make_member(MemberRole.VIEWER)
        _setup_query_mocks(monkeypatch, field=field, table=table, base=base,
                           member=member)
        assert FieldPermissionService.check_field_write_permission('field-1', 'viewer-user') is False

    def test_check_write_permission_false_for_none(self, monkeypatch):
        """none 权限不通过写检查"""
        field = _make_field(config={'permissions': {'viewer': 'none'}})
        table = _make_table()
        base = _make_base(owner_id='someone-else')
        member = _make_member(MemberRole.VIEWER)
        _setup_query_mocks(monkeypatch, field=field, table=table, base=base,
                           member=member)
        assert FieldPermissionService.check_field_write_permission('field-1', 'viewer-user') is False

    def test_check_write_permission_false_for_nonexistent_field(self, monkeypatch):
        """不存在的字段不通过写检查"""
        _setup_query_mocks(monkeypatch, field=None, table=None, base=None,
                           member=None)
        assert FieldPermissionService.check_field_write_permission('no-field', 'any-user') is False


# ---------------------------------------------------------------------------
# filter_values_by_permission 测试（纯逻辑）
# ---------------------------------------------------------------------------

class TestFilterValuesByPermission:
    """filter_values_by_permission 纯逻辑测试"""

    def test_keeps_read_and_write_fields(self):
        """read/write 权限的字段值保留"""
        values = {'f1': 'v1', 'f2': 'v2', 'f3': 'v3', 'f4': 'v4'}
        permissions = {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_READ,
            'f3': FIELD_PERMISSION_NONE,
            # f4 未在 permissions 中
        }
        result = FieldPermissionService.filter_values_by_permission(values, permissions)
        # f1 (write)、f2 (read)、f4 (默认 read) 应保留；f3 (none) 应移除
        assert result == {'f1': 'v1', 'f2': 'v2', 'f4': 'v4'}

    def test_removes_none_permission_fields(self):
        """none 权限的字段值被移除"""
        values = {'f1': 'v1', 'f2': 'v2'}
        permissions = {'f1': FIELD_PERMISSION_NONE, 'f2': FIELD_PERMISSION_NONE}
        result = FieldPermissionService.filter_values_by_permission(values, permissions)
        assert result == {}

    def test_empty_values_returns_empty(self):
        """空 values 返回空字典"""
        result = FieldPermissionService.filter_values_by_permission({}, {})
        assert result == {}

    def test_empty_permissions_keeps_all(self):
        """空 permissions 时所有字段默认 read，全部保留"""
        values = {'f1': 'v1', 'f2': 'v2'}
        result = FieldPermissionService.filter_values_by_permission(values, {})
        assert result == values

    def test_preserves_value_types(self):
        """保留各种类型的值（字符串、数字、列表、None）"""
        values = {
            'f1': 'text',
            'f2': 42,
            'f3': [1, 2, 3],
            'f4': None,
            'f5': {'nested': 'dict'},
        }
        permissions = {f: FIELD_PERMISSION_READ for f in values}
        result = FieldPermissionService.filter_values_by_permission(values, permissions)
        assert result == values


# ---------------------------------------------------------------------------
# filter_writable_values 测试（纯逻辑）
# ---------------------------------------------------------------------------

class TestFilterWritableValues:
    """filter_writable_values 纯逻辑测试"""

    def test_keeps_only_write_fields(self):
        """仅保留 write 权限的字段值"""
        values = {'f1': 'v1', 'f2': 'v2', 'f3': 'v3', 'f4': 'v4'}
        permissions = {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_READ,
            'f3': FIELD_PERMISSION_NONE,
            # f4 未在 permissions 中
        }
        result = FieldPermissionService.filter_writable_values(values, permissions)
        # 仅 f1 (write) 保留；f2 (read)、f3 (none)、f4 (默认 write 但未配置) 
        # 注意：f4 未配置时默认为 FIELD_PERMISSION_WRITE，因此也会保留
        assert result == {'f1': 'v1', 'f4': 'v4'}

    def test_removes_read_and_none_fields(self):
        """read/none 权限的字段值被移除"""
        values = {'f1': 'v1', 'f2': 'v2'}
        permissions = {
            'f1': FIELD_PERMISSION_READ,
            'f2': FIELD_PERMISSION_NONE,
        }
        result = FieldPermissionService.filter_writable_values(values, permissions)
        assert result == {}

    def test_empty_values_returns_empty(self):
        """空 values 返回空字典"""
        result = FieldPermissionService.filter_writable_values({}, {})
        assert result == {}

    def test_empty_permissions_keeps_all(self):
        """空 permissions 时所有字段默认 write，全部保留"""
        values = {'f1': 'v1', 'f2': 'v2'}
        result = FieldPermissionService.filter_writable_values(values, {})
        assert result == values

    def test_only_write_fields_kept(self):
        """全部为 write 时全部保留"""
        values = {'f1': 'v1', 'f2': 'v2', 'f3': 'v3'}
        permissions = {f: FIELD_PERMISSION_WRITE for f in values}
        result = FieldPermissionService.filter_writable_values(values, permissions)
        assert result == values

    def test_preserves_value_types(self):
        """保留各种类型的值"""
        values = {
            'f1': 'text',
            'f2': 42,
            'f3': [1, 2, 3],
            'f4': None,
        }
        permissions = {f: FIELD_PERMISSION_WRITE for f in values}
        result = FieldPermissionService.filter_writable_values(values, permissions)
        assert result == values


# ---------------------------------------------------------------------------
# get_user_role_in_base 测试
# ---------------------------------------------------------------------------

class TestGetUserRoleInBase:
    """get_user_role_in_base 方法测试"""

    def test_owner_id_match_returns_owner(self, monkeypatch):
        """base.owner_id 匹配时返回 'owner'"""
        base = _make_base(owner_id='owner-user')
        _setup_query_mocks(monkeypatch, base=base, member=None)
        role = FieldPermissionService.get_user_role_in_base('base-1', 'owner-user')
        assert role == 'owner'

    def test_member_role_returned(self, monkeypatch):
        """成员角色返回对应的 role.value 字符串"""
        base = _make_base(owner_id='someone-else')
        member = _make_member(MemberRole.EDITOR)
        _setup_query_mocks(monkeypatch, base=base, member=member)
        role = FieldPermissionService.get_user_role_in_base('base-1', 'editor-user')
        assert role == 'editor'

    def test_admin_member_role_returned(self, monkeypatch):
        """admin 成员返回 'admin'"""
        base = _make_base(owner_id='someone-else')
        member = _make_member(MemberRole.ADMIN)
        _setup_query_mocks(monkeypatch, base=base, member=member)
        role = FieldPermissionService.get_user_role_in_base('base-1', 'admin-user')
        assert role == 'admin'

    def test_nonexistent_base_returns_none(self, monkeypatch):
        """不存在的 base 返回 None"""
        _setup_query_mocks(monkeypatch, base=None, member=None)
        role = FieldPermissionService.get_user_role_in_base('no-base', 'any-user')
        assert role is None

    def test_non_member_returns_none(self, monkeypatch):
        """非成员且非 owner 返回 None"""
        base = _make_base(owner_id='someone-else')
        _setup_query_mocks(monkeypatch, base=base, member=None)
        role = FieldPermissionService.get_user_role_in_base('base-1', 'stranger')
        assert role is None

    def test_all_member_roles_return_correct_strings(self, monkeypatch):
        """所有 MemberRole 枚举值都返回正确的字符串"""
        base = _make_base(owner_id='someone-else')
        for role_enum, expected in [
            (MemberRole.OWNER, 'owner'),
            (MemberRole.ADMIN, 'admin'),
            (MemberRole.EDITOR, 'editor'),
            (MemberRole.COMMENTER, 'commenter'),
            (MemberRole.VIEWER, 'viewer'),
        ]:
            member = _make_member(role_enum)
            _setup_query_mocks(monkeypatch, base=base, member=member)
            role = FieldPermissionService.get_user_role_in_base('base-1', 'user')
            assert role == expected
