"""
公式字段权限单元测试

验证 FormulaService 在计算公式时正确处理字段权限：
- 公式引用 none 权限字段时返回 None
- 公式引用 read 权限字段时正常计算
- 公式引用 write 权限字段时正常计算
- 无用户上下文时正常计算（向后兼容）

采用 mock 数据库查询的方式编写纯逻辑测试，避免依赖完整 fixture 环境。
"""
import pytest
from unittest.mock import MagicMock, patch

from app.services.formula_service import FormulaService
from app.models.field import (
    FIELD_PERMISSION_READ,
    FIELD_PERMISSION_WRITE,
    FIELD_PERMISSION_NONE,
)


# ---------------------------------------------------------------------------
# 辅助工厂：构造不依赖数据库的领域对象
# ---------------------------------------------------------------------------

def _make_field(field_id='field-1', name='price', table_id='table-1'):
    """构造一个模拟 Field 对象"""
    field = MagicMock()
    field.id = field_id
    field.name = name
    field.table_id = table_id
    return field


def _setup_field_query_mock(monkeypatch, field_list):
    """mock 掉 formula_service 模块中引用的 Field.query

    通过替换 formula_service 模块中的 Field 引用，
    避免 Flask-SQLAlchemy 的 _QueryProperty 需要应用上下文。

    Args:
        monkeypatch: pytest monkeypatch fixture
        field_list: Field.query.filter_by().all() 返回值
    """
    import app.services.formula_service as fs_module

    field_query = MagicMock()
    field_query.filter_by.return_value.all.return_value = field_list
    mock_field_cls = MagicMock()
    mock_field_cls.query = field_query
    monkeypatch.setattr(fs_module, 'Field', mock_field_cls)


def _setup_permission_service_mock(monkeypatch, permissions):
    """mock 掉 FieldPermissionService.get_table_field_permissions

    Args:
        monkeypatch: pytest monkeypatch fixture
        permissions: get_table_field_permissions 返回值 {field_id: 'read'/'write'/'none'}
    """
    import app.services.formula_service as fs_module

    mock_service = MagicMock()
    mock_service.get_table_field_permissions.return_value = permissions
    # 由于 _check_formula_permissions 内部使用函数内导入，需要 patch 源模块
    monkeypatch.setattr(
        'app.services.field_permission_service.FieldPermissionService.get_table_field_permissions',
        MagicMock(return_value=permissions)
    )


# ---------------------------------------------------------------------------
# evaluate_formula 字段权限测试
# ---------------------------------------------------------------------------

class TestEvaluateFormulaPermissions:
    """evaluate_formula 方法字段权限测试"""

    def test_formula_returns_none_when_referenced_field_is_none_permission(self, monkeypatch):
        """公式引用 none 权限字段时返回 None"""
        fields = [
            _make_field(field_id='f1', name='price'),
            _make_field(field_id='f2', name='quantity'),
        ]
        _setup_field_query_mock(monkeypatch, fields)
        _setup_permission_service_mock(monkeypatch, {
            'f1': FIELD_PERMISSION_NONE,  # price 不可读
            'f2': FIELD_PERMISSION_READ,
        })

        result = FormulaService.evaluate_formula(
            '{price} * {quantity}',
            {'price': 100, 'quantity': 5},
            use_cache=False,
            table_id='table-1',
            user_id='user-1'
        )

        assert result is None

    def test_formula_returns_none_when_any_referenced_field_is_none(self, monkeypatch):
        """公式引用多个字段，其中任一为 none 权限时返回 None"""
        fields = [
            _make_field(field_id='f1', name='price'),
            _make_field(field_id='f2', name='quantity'),
            _make_field(field_id='f3', name='tax_rate'),
        ]
        _setup_field_query_mock(monkeypatch, fields)
        _setup_permission_service_mock(monkeypatch, {
            'f1': FIELD_PERMISSION_READ,
            'f2': FIELD_PERMISSION_NONE,  # quantity 不可读
            'f3': FIELD_PERMISSION_WRITE,
        })

        result = FormulaService.evaluate_formula(
            '{price} * {quantity} * (1 + {tax_rate})',
            {'price': 100, 'quantity': 5, 'tax_rate': 0.13},
            use_cache=False,
            table_id='table-1',
            user_id='user-1'
        )

        assert result is None

    def test_formula_calculates_when_all_fields_are_read_permission(self, monkeypatch):
        """公式引用 read 权限字段时正常计算"""
        fields = [
            _make_field(field_id='f1', name='price'),
            _make_field(field_id='f2', name='quantity'),
        ]
        _setup_field_query_mock(monkeypatch, fields)
        _setup_permission_service_mock(monkeypatch, {
            'f1': FIELD_PERMISSION_READ,
            'f2': FIELD_PERMISSION_READ,
        })

        result = FormulaService.evaluate_formula(
            '{price} * {quantity}',
            {'price': 100, 'quantity': 5},
            use_cache=False,
            table_id='table-1',
            user_id='user-1'
        )

        assert result == 500

    def test_formula_calculates_when_all_fields_are_write_permission(self, monkeypatch):
        """公式引用 write 权限字段时正常计算"""
        fields = [
            _make_field(field_id='f1', name='price'),
            _make_field(field_id='f2', name='quantity'),
        ]
        _setup_field_query_mock(monkeypatch, fields)
        _setup_permission_service_mock(monkeypatch, {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_WRITE,
        })

        result = FormulaService.evaluate_formula(
            '{price} * {quantity}',
            {'price': 100, 'quantity': 5},
            use_cache=False,
            table_id='table-1',
            user_id='user-1'
        )

        assert result == 500

    def test_formula_calculates_with_mixed_read_write_permissions(self, monkeypatch):
        """公式引用 read 和 write 混合权限字段时正常计算"""
        fields = [
            _make_field(field_id='f1', name='price'),
            _make_field(field_id='f2', name='quantity'),
        ]
        _setup_field_query_mock(monkeypatch, fields)
        _setup_permission_service_mock(monkeypatch, {
            'f1': FIELD_PERMISSION_WRITE,
            'f2': FIELD_PERMISSION_READ,
        })

        result = FormulaService.evaluate_formula(
            '{price} * {quantity}',
            {'price': 100, 'quantity': 5},
            use_cache=False,
            table_id='table-1',
            user_id='user-1'
        )

        assert result == 500

    def test_formula_calculates_when_no_user_context(self, monkeypatch):
        """无用户上下文时正常计算（向后兼容）"""
        # 不需要 mock 权限服务，因为无用户上下文不会调用
        result = FormulaService.evaluate_formula(
            '{price} * {quantity}',
            {'price': 100, 'quantity': 5},
            use_cache=False,
            table_id='table-1'
            # 不传 user_id
        )

        assert result == 500

    def test_formula_calculates_when_no_table_id(self, monkeypatch):
        """无 table_id 时正常计算（向后兼容）"""
        result = FormulaService.evaluate_formula(
            '{price} * {quantity}',
            {'price': 100, 'quantity': 5},
            use_cache=False,
            user_id='user-1'
            # 不传 table_id
        )

        assert result == 500

    def test_formula_calculates_when_no_user_and_no_table(self):
        """无 user_id 且无 table_id 时正常计算（最简调用，向后兼容）"""
        result = FormulaService.evaluate_formula(
            '{price} * {quantity}',
            {'price': 100, 'quantity': 5},
            use_cache=False
        )

        assert result == 500

    def test_formula_with_field_id_reference(self, monkeypatch):
        """公式使用字段 ID 引用时也能正确检查权限"""
        fields = [
            _make_field(field_id='f1', name='price'),
            _make_field(field_id='f2', name='quantity'),
        ]
        _setup_field_query_mock(monkeypatch, fields)
        _setup_permission_service_mock(monkeypatch, {
            'f1': FIELD_PERMISSION_NONE,
            'f2': FIELD_PERMISSION_READ,
        })

        # 公式使用 {f1} 而非 {price}
        result = FormulaService.evaluate_formula(
            '{f1} * {f2}',
            {'f1': 100, 'f2': 5},
            use_cache=False,
            table_id='table-1',
            user_id='user-1'
        )

        assert result is None

    def test_formula_with_field_id_reference_readable(self, monkeypatch):
        """公式使用字段 ID 引用且字段可读时正常计算"""
        fields = [
            _make_field(field_id='f1', name='price'),
            _make_field(field_id='f2', name='quantity'),
        ]
        _setup_field_query_mock(monkeypatch, fields)
        _setup_permission_service_mock(monkeypatch, {
            'f1': FIELD_PERMISSION_READ,
            'f2': FIELD_PERMISSION_READ,
        })

        result = FormulaService.evaluate_formula(
            '{f1} * {f2}',
            {'f1': 100, 'f2': 5},
            use_cache=False,
            table_id='table-1',
            user_id='user-1'
        )

        assert result == 500

    def test_formula_without_field_references_calculates_normally(self, monkeypatch):
        """公式不引用任何字段时正常计算（不受权限影响）"""
        _setup_field_query_mock(monkeypatch, [])
        _setup_permission_service_mock(monkeypatch, {})

        result = FormulaService.evaluate_formula(
            'SUM(1, 2, 3)',
            {},
            use_cache=False,
            table_id='table-1',
            user_id='user-1'
        )

        assert result == 6

    def test_formula_returns_none_when_all_fields_none(self, monkeypatch):
        """所有引用字段都不可读时返回 None"""
        fields = [
            _make_field(field_id='f1', name='price'),
            _make_field(field_id='f2', name='quantity'),
        ]
        _setup_field_query_mock(monkeypatch, fields)
        _setup_permission_service_mock(monkeypatch, {
            'f1': FIELD_PERMISSION_NONE,
            'f2': FIELD_PERMISSION_NONE,
        })

        result = FormulaService.evaluate_formula(
            '{price} * {quantity}',
            {'price': 100, 'quantity': 5},
            use_cache=False,
            table_id='table-1',
            user_id='user-1'
        )

        assert result is None

    def test_permission_check_exception_does_not_block_calculation(self, monkeypatch):
        """权限检查抛出异常时不阻断计算（向后兼容）"""
        fields = [
            _make_field(field_id='f1', name='price'),
        ]
        _setup_field_query_mock(monkeypatch, fields)

        # 让 get_table_field_permissions 抛出异常
        monkeypatch.setattr(
            'app.services.field_permission_service.FieldPermissionService.get_table_field_permissions',
            MagicMock(side_effect=Exception("DB error"))
        )

        result = FormulaService.evaluate_formula(
            '{price} * 2',
            {'price': 100},
            use_cache=False,
            table_id='table-1',
            user_id='user-1'
        )

        # 异常被吞掉，正常计算
        assert result == 200


# ---------------------------------------------------------------------------
# _get_current_user_id 测试
# ---------------------------------------------------------------------------

class TestGetCurrentUserId:
    """_get_current_user_id 方法测试"""

    def test_returns_explicit_user_id(self):
        """显式传入 user_id 时返回该值"""
        assert FormulaService._get_current_user_id('user-123') == 'user-123'

    def test_returns_none_without_flask_context(self):
        """无 Flask 上下文时返回 None"""
        assert FormulaService._get_current_user_id(None) is None

    def test_returns_user_id_from_g_object(self):
        """从 Flask g 对象获取 user_id"""
        from flask import Flask, g

        app = Flask(__name__)
        with app.app_context():
            g.current_user_id = 'user-from-g'
            assert FormulaService._get_current_user_id(None) == 'user-from-g'

    def test_returns_none_when_g_has_no_current_user_id(self):
        """g 对象无 current_user_id 属性时返回 None"""
        from flask import Flask, g

        app = Flask(__name__)
        with app.app_context():
            # 不设置 g.current_user_id
            assert FormulaService._get_current_user_id(None) is None


# ---------------------------------------------------------------------------
# _get_referenced_field_ids 测试
# ---------------------------------------------------------------------------

class TestGetReferencedFieldIds:
    """_get_referenced_field_ids 方法测试"""

    def test_returns_field_ids_by_name(self, monkeypatch):
        """通过字段名引用时返回对应字段 ID"""
        fields = [
            _make_field(field_id='f1', name='price'),
            _make_field(field_id='f2', name='quantity'),
        ]
        _setup_field_query_mock(monkeypatch, fields)

        result = FormulaService._get_referenced_field_ids(
            '{price} * {quantity}',
            'table-1'
        )

        assert set(result) == {'f1', 'f2'}

    def test_returns_field_ids_by_id(self, monkeypatch):
        """通过字段 ID 引用时返回对应字段 ID"""
        fields = [
            _make_field(field_id='f1', name='price'),
            _make_field(field_id='f2', name='quantity'),
        ]
        _setup_field_query_mock(monkeypatch, fields)

        result = FormulaService._get_referenced_field_ids(
            '{f1} * {f2}',
            'table-1'
        )

        assert set(result) == {'f1', 'f2'}

    def test_returns_empty_for_no_references(self, monkeypatch):
        """公式无字段引用时返回空列表"""
        _setup_field_query_mock(monkeypatch, [])

        result = FormulaService._get_referenced_field_ids(
            'SUM(1, 2, 3)',
            'table-1'
        )

        assert result == []

    def test_returns_empty_for_empty_formula(self, monkeypatch):
        """空公式返回空列表"""
        _setup_field_query_mock(monkeypatch, [])

        result = FormulaService._get_referenced_field_ids('', 'table-1')
        assert result == []

        result = FormulaService._get_referenced_field_ids(None, 'table-1')
        assert result == []

    def test_deduplicates_field_ids(self, monkeypatch):
        """重复引用同一字段时去重"""
        fields = [
            _make_field(field_id='f1', name='price'),
        ]
        _setup_field_query_mock(monkeypatch, fields)

        result = FormulaService._get_referenced_field_ids(
            '{price} + {price} + {price}',
            'table-1'
        )

        assert result == ['f1']

    def test_handles_mixed_name_and_id_references(self, monkeypatch):
        """混合使用字段名和字段 ID 引用"""
        fields = [
            _make_field(field_id='f1', name='price'),
            _make_field(field_id='f2', name='quantity'),
        ]
        _setup_field_query_mock(monkeypatch, fields)

        result = FormulaService._get_referenced_field_ids(
            '{price} * {f2}',
            'table-1'
        )

        assert set(result) == {'f1', 'f2'}


# ---------------------------------------------------------------------------
# _check_formula_permissions 测试
# ---------------------------------------------------------------------------

class TestCheckFormulaPermissions:
    """_check_formula_permissions 方法测试"""

    def test_returns_true_when_all_fields_readable(self, monkeypatch):
        """所有引用字段可读时返回 True"""
        fields = [
            _make_field(field_id='f1', name='price'),
            _make_field(field_id='f2', name='quantity'),
        ]
        _setup_field_query_mock(monkeypatch, fields)
        _setup_permission_service_mock(monkeypatch, {
            'f1': FIELD_PERMISSION_READ,
            'f2': FIELD_PERMISSION_WRITE,
        })

        result = FormulaService._check_formula_permissions(
            '{price} * {quantity}',
            'table-1',
            'user-1'
        )

        assert result is True

    def test_returns_false_when_any_field_none(self, monkeypatch):
        """任一引用字段不可读时返回 False"""
        fields = [
            _make_field(field_id='f1', name='price'),
            _make_field(field_id='f2', name='quantity'),
        ]
        _setup_field_query_mock(monkeypatch, fields)
        _setup_permission_service_mock(monkeypatch, {
            'f1': FIELD_PERMISSION_READ,
            'f2': FIELD_PERMISSION_NONE,
        })

        result = FormulaService._check_formula_permissions(
            '{price} * {quantity}',
            'table-1',
            'user-1'
        )

        assert result is False

    def test_returns_true_when_no_references(self, monkeypatch):
        """无字段引用时返回 True"""
        _setup_field_query_mock(monkeypatch, [])
        _setup_permission_service_mock(monkeypatch, {})

        result = FormulaService._check_formula_permissions(
            'SUM(1, 2, 3)',
            'table-1',
            'user-1'
        )

        assert result is True

    def test_returns_true_when_field_not_in_permissions(self, monkeypatch):
        """引用字段不在权限字典中时默认可读（返回 True）"""
        fields = [
            _make_field(field_id='f1', name='price'),
        ]
        _setup_field_query_mock(monkeypatch, fields)
        # 权限字典中不包含 f1
        _setup_permission_service_mock(monkeypatch, {})

        result = FormulaService._check_formula_permissions(
            '{price}',
            'table-1',
            'user-1'
        )

        assert result is True

    def test_uses_batch_permission_query(self, monkeypatch):
        """验证使用批量权限查询（而非逐字段查询）"""
        fields = [
            _make_field(field_id='f1', name='price'),
            _make_field(field_id='f2', name='quantity'),
            _make_field(field_id='f3', name='tax'),
        ]
        _setup_field_query_mock(monkeypatch, fields)

        mock_perm_fn = MagicMock(return_value={
            'f1': FIELD_PERMISSION_READ,
            'f2': FIELD_PERMISSION_READ,
            'f3': FIELD_PERMISSION_READ,
        })
        monkeypatch.setattr(
            'app.services.field_permission_service.FieldPermissionService.get_table_field_permissions',
            mock_perm_fn
        )

        FormulaService._check_formula_permissions(
            '{price} * {quantity} + {tax}',
            'table-1',
            'user-1'
        )

        # 应该只调用一次批量查询
        assert mock_perm_fn.call_count == 1
        mock_perm_fn.assert_called_once_with('table-1', 'user-1')
