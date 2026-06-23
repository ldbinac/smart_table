"""
字段级权限配置测试

覆盖 Field 模型的 get_permissions / set_permissions / get_effective_permission
方法以及 to_dict() 中 permissions 字段的序列化行为。
"""
import pytest
from app.models.field import (
    Field,
    FieldType,
    FIELD_PERMISSION_READ,
    FIELD_PERMISSION_WRITE,
    FIELD_PERMISSION_NONE,
    DEFAULT_FIELD_PERMISSIONS,
    UNRESTRICTABLE_ROLES,
)


def _make_field(config=None):
    """构造一个用于单元测试的 Field 实例（不依赖数据库）"""
    return Field(
        name='测试字段',
        type=FieldType.SINGLE_LINE_TEXT.value,
        table_id='test-table-id',
        config=config,
    )


class TestGetPermissions:
    """get_permissions 方法测试"""

    def test_returns_empty_dict_when_config_is_none(self):
        """未配置权限时（config 为 None）返回空字典"""
        field = _make_field(config=None)
        assert field.get_permissions() == {}

    def test_returns_empty_dict_when_permissions_not_set(self):
        """config 存在但未配置 permissions 时返回空字典"""
        field = _make_field(config={'defaultValue': 'foo'})
        assert field.get_permissions() == {}

    def test_returns_permissions_when_configured(self):
        """已配置 permissions 时返回该配置"""
        field = _make_field(config={
            'permissions': {'editor': 'read', 'viewer': 'none'}
        })
        result = field.get_permissions()
        assert result == {'editor': 'read', 'viewer': 'none'}


class TestSetPermissions:
    """set_permissions 方法测试"""

    def test_stores_valid_permissions(self):
        """set_permissions 正确存储有效权限配置"""
        field = _make_field(config={})
        field.set_permissions({'editor': 'read', 'commenter': 'none', 'viewer': 'read'})
        assert field.config['permissions'] == {
            'editor': 'read',
            'commenter': 'none',
            'viewer': 'read',
        }

    def test_filters_unrestrictable_roles(self):
        """set_permissions 自动过滤 owner/admin 配置项"""
        field = _make_field(config={})
        field.set_permissions({
            'owner': 'read',     # 应被过滤
            'admin': 'none',     # 应被过滤
            'editor': 'read',    # 应保留
            'viewer': 'none',    # 应保留
        })
        permissions = field.config['permissions']
        assert 'owner' not in permissions
        assert 'admin' not in permissions
        assert permissions == {'editor': 'read', 'viewer': 'none'}

    def test_filters_invalid_permission_values(self):
        """set_permissions 自动过滤无效权限值"""
        field = _make_field(config={})
        field.set_permissions({
            'editor': 'read',       # 有效
            'commenter': 'delete',  # 无效，应被过滤
            'viewer': '',           # 无效，应被过滤
            'editor2': 'write',     # 有效
        })
        permissions = field.config['permissions']
        assert permissions == {'editor': 'read', 'editor2': 'write'}

    def test_only_invalid_values_yields_empty_dict(self):
        """全部为无效值时存储空字典"""
        field = _make_field(config={})
        field.set_permissions({'editor': 'delete', 'viewer': 'execute'})
        assert field.config['permissions'] == {}

    def test_ignores_non_dict_input(self):
        """非字典输入时直接返回，不修改 config"""
        field = _make_field(config={'existing': 'value'})
        field.set_permissions(['editor', 'read'])  # 列表，非字典
        # config 不应被修改，也不应新增 permissions 键
        assert 'permissions' not in field.config
        assert field.config == {'existing': 'value'}

    def test_ignores_none_input(self):
        """None 输入时直接返回，不修改 config"""
        field = _make_field(config={'existing': 'value'})
        field.set_permissions(None)
        assert 'permissions' not in field.config

    def test_initializes_config_when_none(self):
        """config 为 None 时自动初始化为字典"""
        field = _make_field(config=None)
        field.set_permissions({'editor': 'read'})
        assert isinstance(field.config, dict)
        assert field.config['permissions'] == {'editor': 'read'}

    def test_updates_updated_at_timestamp_when_present(self):
        """config 中已存在 updatedAt 时，设置权限会刷新时间戳"""
        field = _make_field(config={'updatedAt': '2020-01-01T00:00:00+00:00'})
        field.set_permissions({'editor': 'read'})
        assert field.config['updatedAt'] != '2020-01-01T00:00:00+00:00'
        # 应为有效的 ISO 格式时间字符串
        from datetime import datetime
        datetime.fromisoformat(field.config['updatedAt'])

    def test_does_not_create_updated_at_when_absent(self):
        """config 中不存在 updatedAt 时，不会主动创建该字段"""
        field = _make_field(config={})
        field.set_permissions({'editor': 'read'})
        assert 'updatedAt' not in field.config

    def test_overwrites_existing_permissions(self):
        """重复调用 set_permissions 会覆盖原有配置"""
        field = _make_field(config={})
        field.set_permissions({'editor': 'read', 'viewer': 'none'})
        field.set_permissions({'commenter': 'write'})
        # 应完全替换，而非合并
        assert field.config['permissions'] == {'commenter': 'write'}


class TestGetEffectivePermission:
    """get_effective_permission 方法测试"""

    def test_owner_always_returns_write(self):
        """owner 始终返回 write，即使显式配置了更低权限"""
        field = _make_field(config={'permissions': {'owner': 'none'}})
        assert field.get_effective_permission('owner') == FIELD_PERMISSION_WRITE

    def test_admin_always_returns_write(self):
        """admin 始终返回 write，即使显式配置了更低权限"""
        field = _make_field(config={'permissions': {'admin': 'read'}})
        assert field.get_effective_permission('admin') == FIELD_PERMISSION_WRITE

    def test_owner_admin_write_without_config(self):
        """无任何配置时 owner/admin 仍返回 write"""
        field = _make_field(config=None)
        assert field.get_effective_permission('owner') == FIELD_PERMISSION_WRITE
        assert field.get_effective_permission('admin') == FIELD_PERMISSION_WRITE

    def test_returns_default_when_role_not_configured(self):
        """未配置角色返回默认值（editor->write, commenter->read, viewer->read）"""
        field = _make_field(config={})
        assert field.get_effective_permission('editor') == FIELD_PERMISSION_WRITE
        assert field.get_effective_permission('commenter') == FIELD_PERMISSION_READ
        assert field.get_effective_permission('viewer') == FIELD_PERMISSION_READ

    def test_returns_configured_value_when_role_configured(self):
        """已配置角色返回配置值"""
        field = _make_field(config={
            'permissions': {
                'editor': 'read',
                'commenter': 'none',
                'viewer': 'none',
            }
        })
        assert field.get_effective_permission('editor') == FIELD_PERMISSION_READ
        assert field.get_effective_permission('commenter') == FIELD_PERMISSION_NONE
        assert field.get_effective_permission('viewer') == FIELD_PERMISSION_NONE

    def test_unknown_role_defaults_to_read(self):
        """未知角色（不在默认映射中）默认返回 read"""
        field = _make_field(config={})
        assert field.get_effective_permission('guest') == FIELD_PERMISSION_READ

    def test_explicit_config_overrides_default(self):
        """显式配置优先于默认值"""
        field = _make_field(config={'permissions': {'editor': 'none'}})
        # editor 默认是 write，但显式配置为 none
        assert field.get_effective_permission('editor') == FIELD_PERMISSION_NONE

    def test_default_field_permissions_constants_consistent(self):
        """DEFAULT_FIELD_PERMISSIONS 与 UNRESTRICTABLE_ROLES 保持一致：
        owner/admin 在默认映射中均为 write，且属于不可限制角色"""
        for role in UNRESTRICTABLE_ROLES:
            assert DEFAULT_FIELD_PERMISSIONS[role] == FIELD_PERMISSION_WRITE


class TestToDictSerialization:
    """to_dict() 中 permissions 字段序列化测试"""

    def test_to_dict_includes_permissions_when_configured(self):
        """to_dict 包含 permissions 字段（已配置时）"""
        field = _make_field(config={
            'permissions': {'editor': 'read', 'viewer': 'none'}
        })
        # to_dict 需要 id/table_id 等属性，直接调用会因未持久化报错
        # 这里通过手动设置必要属性来绕过
        import uuid
        from datetime import datetime, timezone
        field.id = uuid.uuid4()
        field.table_id = uuid.uuid4()
        field.created_at = datetime.now(timezone.utc)
        field.updated_at = datetime.now(timezone.utc)

        result = field.to_dict()
        assert 'permissions' in result
        assert result['permissions'] == {'editor': 'read', 'viewer': 'none'}
        # config 中也应仍然包含 permissions
        assert result['config']['permissions'] == {'editor': 'read', 'viewer': 'none'}

    def test_to_dict_omits_permissions_when_not_configured(self):
        """未配置 permissions 时 to_dict 不包含 permissions 顶层字段"""
        field = _make_field(config={'defaultValue': 'foo'})
        import uuid
        from datetime import datetime, timezone
        field.id = uuid.uuid4()
        field.table_id = uuid.uuid4()
        field.created_at = datetime.now(timezone.utc)
        field.updated_at = datetime.now(timezone.utc)

        result = field.to_dict()
        assert 'permissions' not in result

    def test_to_dict_omits_permissions_when_config_none(self):
        """config 为 None 时 to_dict 不包含 permissions 顶层字段"""
        field = _make_field(config=None)
        import uuid
        from datetime import datetime, timezone
        field.id = uuid.uuid4()
        field.table_id = uuid.uuid4()
        field.created_at = datetime.now(timezone.utc)
        field.updated_at = datetime.now(timezone.utc)

        result = field.to_dict()
        assert 'permissions' not in result

    def test_to_dict_permissions_reflects_set_permissions(self):
        """通过 set_permissions 设置后，to_dict 反映最新权限配置"""
        field = _make_field(config={})
        import uuid
        from datetime import datetime, timezone
        field.id = uuid.uuid4()
        field.table_id = uuid.uuid4()
        field.created_at = datetime.now(timezone.utc)
        field.updated_at = datetime.now(timezone.utc)

        field.set_permissions({'editor': 'read', 'commenter': 'none'})
        result = field.to_dict()
        assert result['permissions'] == {'editor': 'read', 'commenter': 'none'}
