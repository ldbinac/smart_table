"""
字段权限配置 API 测试

使用 mock 方式测试路由处理器，避免依赖 JWT 和数据库。
覆盖 PUT /fields/<field_id>/permissions 和 GET /tables/<table_id>/field-permissions。
"""
import uuid
from unittest.mock import MagicMock

import pytest
from flask import g

from app import create_app
from app.extensions import db
from app.routes.fields import (
    update_field_permissions,
    get_table_field_permissions,
)


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
    """获取去掉 jwt_required 装饰器的原始处理函数"""
    return handler.__wrapped__


def _make_field(permissions=None):
    """构造一个 mock Field 对象"""
    field = MagicMock()
    field.config = {}
    field.get_permissions.return_value = permissions or {}
    return field


def _make_table():
    """构造一个 mock Table 对象"""
    table = MagicMock()
    table.id = str(uuid.uuid4())
    table.base_id = str(uuid.uuid4())
    return table


def _setup_field_mocks(monkeypatch, *, field=None, check_permission=True):
    """统一 mock Field.query.get、FieldService.check_permission、db.session

    Args:
        monkeypatch: pytest monkeypatch fixture
        field: Field.query.get 返回值（None 表示字段不存在）
        check_permission: FieldService.check_permission 返回值

    Returns:
        mock_db: 替换后的 db 对象，用于断言 session.commit 调用
    """
    import app.routes.fields as fields_module

    mock_field_cls = MagicMock()
    mock_field_cls.query.get.return_value = field
    monkeypatch.setattr(fields_module, 'Field', mock_field_cls)

    monkeypatch.setattr(
        fields_module.FieldService, 'check_permission',
        lambda *a, **kw: check_permission
    )

    mock_db = MagicMock()
    monkeypatch.setattr(fields_module, 'db', mock_db)
    return mock_db


# ---------------------------------------------------------------------------
# PUT /fields/<field_id>/permissions 测试
# ---------------------------------------------------------------------------

class TestUpdateFieldPermissions:
    """PUT /fields/<field_id>/permissions 测试"""

    def test_admin_updates_permissions_successfully(self, app, monkeypatch):
        """admin 用户成功更新字段权限"""
        permissions = {'editor': 'read', 'viewer': 'none'}
        mock_field = _make_field(permissions=permissions)
        mock_db = _setup_field_mocks(
            monkeypatch, field=mock_field, check_permission=True
        )

        with app.test_request_context(json={'permissions': permissions}):
            g.current_user_id = 'admin-user-id'
            response, status_code = _undecorated(update_field_permissions)(uuid.uuid4())

            assert status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['data']['permissions'] == permissions
            mock_field.set_permissions.assert_called_once_with(permissions)
            mock_db.session.commit.assert_called_once()

    def test_non_admin_returns_403(self, app, monkeypatch):
        """非 admin 用户返回 403"""
        mock_field = _make_field()
        mock_db = _setup_field_mocks(
            monkeypatch, field=mock_field, check_permission=False
        )

        with app.test_request_context(json={'permissions': {'editor': 'read'}}):
            g.current_user_id = 'editor-user-id'
            response, status_code = _undecorated(update_field_permissions)(uuid.uuid4())

            assert status_code == 403
            data = response.get_json()
            assert data['success'] is False
            mock_field.set_permissions.assert_not_called()
            mock_db.session.commit.assert_not_called()

    def test_field_not_found_returns_404(self, app, monkeypatch):
        """字段不存在返回 404"""
        _setup_field_mocks(monkeypatch, field=None, check_permission=True)

        with app.test_request_context(json={'permissions': {'editor': 'read'}}):
            g.current_user_id = 'user-id'
            response, status_code = _undecorated(update_field_permissions)(uuid.uuid4())

            assert status_code == 404
            data = response.get_json()
            assert data['success'] is False

    def test_missing_permissions_returns_400(self, app, monkeypatch):
        """请求体缺少 permissions 字段返回 400"""
        mock_field = _make_field()
        _setup_field_mocks(monkeypatch, field=mock_field, check_permission=True)

        with app.test_request_context(json={'name': 'foo'}):
            g.current_user_id = 'user-id'
            response, status_code = _undecorated(update_field_permissions)(uuid.uuid4())

            assert status_code == 400
            data = response.get_json()
            assert data['success'] is False

    def test_permissions_not_dict_returns_400(self, app, monkeypatch):
        """permissions 不是字典返回 400"""
        mock_field = _make_field()
        _setup_field_mocks(monkeypatch, field=mock_field, check_permission=True)

        with app.test_request_context(json={'permissions': ['editor', 'read']}):
            g.current_user_id = 'user-id'
            response, status_code = _undecorated(update_field_permissions)(uuid.uuid4())

            assert status_code == 400
            data = response.get_json()
            assert data['success'] is False

    def test_invalid_role_returns_400(self, app, monkeypatch):
        """无效的角色返回 400（owner/admin 不允许在路由层配置）"""
        mock_field = _make_field()
        _setup_field_mocks(monkeypatch, field=mock_field, check_permission=True)

        with app.test_request_context(json={'permissions': {'owner': 'read'}}):
            g.current_user_id = 'user-id'
            response, status_code = _undecorated(update_field_permissions)(uuid.uuid4())

            assert status_code == 400
            data = response.get_json()
            assert '无效的角色' in data['message']

    def test_invalid_permission_value_returns_400(self, app, monkeypatch):
        """无效的权限值返回 400"""
        mock_field = _make_field()
        _setup_field_mocks(monkeypatch, field=mock_field, check_permission=True)

        with app.test_request_context(json={'permissions': {'editor': 'delete'}}):
            g.current_user_id = 'user-id'
            response, status_code = _undecorated(update_field_permissions)(uuid.uuid4())

            assert status_code == 400
            data = response.get_json()
            assert '无效的权限值' in data['message']


# ---------------------------------------------------------------------------
# GET /tables/<table_id>/field-permissions 测试
# ---------------------------------------------------------------------------

class TestGetTableFieldPermissions:
    """GET /tables/<table_id>/field-permissions 测试"""

    def test_returns_permissions_dict(self, app, monkeypatch):
        """成功返回当前用户在表中所有字段的权限字典"""
        import app.routes.fields as fields_module

        expected = {'field-1': 'read', 'field-2': 'none'}

        mock_table_cls = MagicMock()
        mock_table_cls.query.get.return_value = _make_table()
        monkeypatch.setattr(fields_module, 'Table', mock_table_cls)

        monkeypatch.setattr(
            fields_module.BaseService, 'check_permission',
            lambda *a, **kw: True
        )

        monkeypatch.setattr(
            fields_module.FieldPermissionService,
            'get_table_field_permissions',
            lambda *a, **kw: expected
        )

        with app.test_request_context():
            g.current_user_id = 'viewer-user-id'
            response, status_code = _undecorated(get_table_field_permissions)(uuid.uuid4())

            assert status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['data'] == expected

    def test_table_not_found_returns_404(self, app, monkeypatch):
        """表不存在返回 404"""
        import app.routes.fields as fields_module

        mock_table_cls = MagicMock()
        mock_table_cls.query.get.return_value = None
        monkeypatch.setattr(fields_module, 'Table', mock_table_cls)

        with app.test_request_context():
            g.current_user_id = 'user-id'
            response, status_code = _undecorated(get_table_field_permissions)(uuid.uuid4())

            assert status_code == 404
            data = response.get_json()
            assert data['success'] is False

    def test_no_base_permission_returns_403(self, app, monkeypatch):
        """无 Base VIEWER 权限返回 403"""
        import app.routes.fields as fields_module

        mock_table_cls = MagicMock()
        mock_table_cls.query.get.return_value = _make_table()
        monkeypatch.setattr(fields_module, 'Table', mock_table_cls)

        monkeypatch.setattr(
            fields_module.BaseService, 'check_permission',
            lambda *a, **kw: False
        )

        with app.test_request_context():
            g.current_user_id = 'user-id'
            response, status_code = _undecorated(get_table_field_permissions)(uuid.uuid4())

            assert status_code == 403
            data = response.get_json()
            assert data['success'] is False
