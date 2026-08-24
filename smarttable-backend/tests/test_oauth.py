"""
OAuth2 第三方应用接入 & 开放 API 单元测试
"""
import pytest
from uuid import uuid4

from app import create_app
from app.extensions import db, jwt
from app.models.user import User, UserRole
from app.models.base import Base
from app.models.oauth_app import OAuthApp, ApiAppToken, ApiAppAuditLog
from app.services.oauth_app_service import OAuthAppService
from flask_jwt_extended import create_access_token


@pytest.fixture(scope='function')
def app_ctx(app):
    with app.app_context():
        yield app


@pytest.fixture(scope='function')
def admin_user(app, db_session):
    user = User(email='admin@example.com', name='管理员')
    user.set_password('Test1234!')
    user.role = UserRole.ADMIN
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user


@pytest.fixture(scope='function')
def normal_user(app, db_session):
    user = User(email='normal@example.com', name='普通用户')
    user.set_password('Test1234!')
    user.role = UserRole.EDITOR
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user


@pytest.fixture(scope='function')
def owned_base(app, db_session, admin_user):
    base = Base(name='测试多维表格', owner_id=admin_user.id, icon='table', color='#6366f1')
    db.session.add(base)
    db.session.commit()
    db.session.refresh(base)
    return base


@pytest.fixture(scope='function')
def other_base(app, db_session, admin_user):
    base = Base(name='另一个多维表格', owner_id=admin_user.id, icon='table', color='#22c55e')
    db.session.add(base)
    db.session.commit()
    db.session.refresh(base)
    return base


@pytest.fixture(scope='function')
def app_table(app, db_session, owned_base):
    """属于授权 Base 的测试表"""
    from app.models.table import Table
    table = Table(base_id=owned_base.id, name='开放表', order=0)
    db.session.add(table)
    db.session.commit()
    db.session.refresh(table)
    return table


@pytest.fixture(scope='function')
def app_field(app, db_session, app_table):
    """属于授权表的测试字段"""
    from app.models.field import Field, FieldType
    field = Field(
        table_id=app_table.id,
        name='名称',
        type=FieldType.SINGLE_LINE_TEXT.value,
        order=0,
        is_required=False,
    )
    db.session.add(field)
    db.session.commit()
    db.session.refresh(field)
    return field


def _admin_token(app, admin_user):
    with app.app_context():
        return create_access_token(identity=str(admin_user.id))


def _normal_token(app, normal_user):
    with app.app_context():
        return create_access_token(identity=str(normal_user.id))


def _create_app(app, admin_user, base, scopes='base:read table:read record:read record:write'):
    with app.app_context():
        app_obj, secret = OAuthAppService.create_app(
            app_name='测试应用',
            owner_id=admin_user.id,
            allowed_bases=[str(base.id)],
            scopes=scopes,
            callback_url='https://example.com/cb',
        )
        # 返回快照，避免跨 app_context 访问已分离实例触发 DetachedInstanceError
        snap = type('AppInfo', (), {})()
        snap.id = app_obj.id
        snap.client_id = app_obj.client_id
        snap.app_name = app_obj.app_name
        return snap, secret


def _app_token(app, app_obj):
    with app.app_context():
        access_token, _ = OAuthAppService.issue_token(OAuthApp.query.get(app_obj.id))
        return access_token


class TestOAuthAppManagement:
    def test_create_app_success(self, client, app, admin_user, owned_base):
        token = _admin_token(app, admin_user)
        resp = client.post(
            '/api/oauth/apps',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'app_name': '测试应用',
                'allowed_bases': [str(owned_base.id)],
                'scopes': 'base:read record:read',
                'callback_url': 'https://example.com/cb',
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert resp.status_code == 201
        assert 'client_id' in data['data']
        assert 'client_secret' in data['data']
        assert data['data']['scopes'] == ['base:read', 'record:read']

    def test_create_app_forbidden_for_non_admin(self, client, app, normal_user, owned_base):
        token = _normal_token(app, normal_user)
        resp = client.post(
            '/api/oauth/apps',
            headers={'Authorization': f'Bearer {token}'},
            json={'app_name': 'x', 'allowed_bases': [str(owned_base.id)], 'scopes': 'base:read'},
        )
        assert resp.status_code == 403

    def test_create_app_without_auth(self, client):
        resp = client.post('/api/oauth/apps', json={'app_name': 'x', 'scopes': 'base:read'})
        assert resp.status_code == 401

    def test_create_app_filters_invalid_scope(self, client, app, admin_user, owned_base):
        token = _admin_token(app, admin_user)
        resp = client.post(
            '/api/oauth/apps',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'app_name': 'x',
                'allowed_bases': [str(owned_base.id)],
                'scopes': 'evil:scope base:read',
            },
        )
        assert resp.status_code == 201
        assert resp.get_json()['data']['scopes'] == ['base:read']

    def test_list_apps(self, client, app, admin_user, owned_base):
        token = _admin_token(app, admin_user)
        _create_app(app, admin_user, owned_base)
        resp = client.get('/api/oauth/apps', headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data['data'], list)
        assert len(data['data']) >= 1
        app_item = data['data'][0]
        # 列表应返回授权 Base 名称（供表格展示）
        assert 'allowed_base_names' in app_item
        assert str(owned_base.name) in app_item['allowed_base_names']

    def test_get_app_includes_secret_once(self, client, app, admin_user, owned_base):
        token = _admin_token(app, admin_user)
        app_obj, secret = _create_app(app, admin_user, owned_base)
        resp = client.get(
            f'/api/oauth/apps/{app_obj.id}', headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        # 列表/详情默认不返回明文 secret
        assert 'client_secret' not in resp.get_json()['data']

    def test_update_app(self, client, app, admin_user, owned_base, other_base):
        token = _admin_token(app, admin_user)
        app_obj, _ = _create_app(app, admin_user, owned_base)
        resp = client.put(
            f'/api/oauth/apps/{app_obj.id}',
            headers={'Authorization': f'Bearer {token}'},
            json={'app_name': '改名应用', 'is_active': False},
        )
        assert resp.status_code == 200
        with app.app_context():
            updated = OAuthApp.query.get(app_obj.id)
            assert updated.app_name == '改名应用'
            assert updated.is_active is False

    def test_reset_secret_changes_secret(self, client, app, admin_user, owned_base):
        token = _admin_token(app, admin_user)
        app_obj, old_secret = _create_app(app, admin_user, owned_base)
        resp = client.post(
            f'/api/oauth/apps/{app_obj.id}/reset-secret',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        new_secret = resp.get_json()['data']['client_secret']
        assert new_secret != old_secret
        # 旧 secret 立即失效：哈希已变化
        with app.app_context():
            reloaded = OAuthApp.query.get(app_obj.id)
            assert OAuthAppService.verify_secret(reloaded.client_id, old_secret) is None
            assert OAuthAppService.verify_secret(reloaded.client_id, new_secret) is not None

    def test_delete_app(self, client, app, admin_user, owned_base):
        token = _admin_token(app, admin_user)
        app_obj, _ = _create_app(app, admin_user, owned_base)
        resp = client.delete(
            f'/api/oauth/apps/{app_obj.id}', headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        with app.app_context():
            assert OAuthApp.query.get(app_obj.id) is None


class TestTokenEndpoint:
    def test_token_success(self, client, app, admin_user, owned_base):
        app_obj, secret = _create_app(app, admin_user, owned_base)
        resp = client.post(
            '/api/oauth/token',
            json={
                'grant_type': 'client_credentials',
                'client_id': app_obj.client_id,
                'client_secret': secret,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'access_token' in data
        assert data['token_type'] == 'Bearer'

    def test_token_basic_auth(self, client, app, admin_user, owned_base):
        app_obj, secret = _create_app(app, admin_user, owned_base)
        cred = f'{app_obj.client_id}:{secret}'
        import base64
        basic = base64.b64encode(cred.encode()).decode()
        resp = client.post(
            '/api/oauth/token',
            headers={'Authorization': f'Basic {basic}'},
            json={'grant_type': 'client_credentials'},
        )
        assert resp.status_code == 200
        assert 'access_token' in resp.get_json()

    def test_token_wrong_secret(self, client, app, admin_user, owned_base):
        app_obj, _ = _create_app(app, admin_user, owned_base)
        resp = client.post(
            '/api/oauth/token',
            json={
                'grant_type': 'client_credentials',
                'client_id': app_obj.client_id,
                'client_secret': 'wrong-secret',
            },
        )
        assert resp.status_code == 401

    def test_token_unknown_client(self, client):
        resp = client.post(
            '/api/oauth/token',
            json={
                'grant_type': 'client_credentials',
                'client_id': 'not-exist',
                'client_secret': 'x',
            },
        )
        assert resp.status_code == 401

    def test_token_bad_grant(self, client, app, admin_user, owned_base):
        app_obj, secret = _create_app(app, admin_user, owned_base)
        resp = client.post(
            '/api/oauth/token',
            json={
                'grant_type': 'authorization_code',
                'client_id': app_obj.client_id,
                'client_secret': secret,
            },
        )
        assert resp.status_code == 400

    def test_token_inactive_app(self, client, app, admin_user, owned_base):
        app_obj, secret = _create_app(app, admin_user, owned_base)
        with app.app_context():
            a = OAuthApp.query.get(app_obj.id)
            a.is_active = False
            db.session.commit()
        resp = client.post(
            '/api/oauth/token',
            json={
                'grant_type': 'client_credentials',
                'client_id': app_obj.client_id,
                'client_secret': secret,
            },
        )
        assert resp.status_code == 401


class TestOpenAPI:
    def _token(self, app, admin_user, base, scopes):
        app_obj, _ = _create_app(app, admin_user, base, scopes=scopes)
        return _app_token(app, app_obj)

    def test_list_bases(self, client, app, admin_user, owned_base):
        token = self._token(app, admin_user, owned_base, 'base:read')
        resp = client.get(
            '/api/open/v1/bases', headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        ids = [b['id'] for b in data['data']]
        assert str(owned_base.id) in ids

    def test_get_base_detail(self, client, app, admin_user, owned_base):
        token = self._token(app, admin_user, owned_base, 'base:read')
        resp = client.get(
            f'/api/open/v1/bases/{owned_base.id}',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        assert resp.get_json()['data']['id'] == str(owned_base.id)

    def test_base_not_authorized(self, client, app, admin_user, owned_base, other_base):
        token = self._token(app, admin_user, owned_base, 'base:read')
        resp = client.get(
            f'/api/open/v1/bases/{other_base.id}',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 403

    def test_missing_scope(self, client, app, admin_user, owned_base):
        token = self._token(app, admin_user, owned_base, 'base:read')
        resp = client.get(
            f'/api/open/v1/bases/{owned_base.id}/tables',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 403

    def test_no_token(self, client, app, admin_user, owned_base):
        resp = client.get('/api/open/v1/bases')
        assert resp.status_code == 401

    def test_user_token_rejected(self, client, app, admin_user, owned_base):
        token = _admin_token(app, admin_user)
        resp = client.get(
            '/api/open/v1/bases', headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 403

    def test_get_tables_and_fields(self, client, app, admin_user, owned_base, app_table, app_field):
        token = self._token(app, admin_user, owned_base, 'base:read table:read field:read')
        resp = client.get(
            f'/api/open/v1/bases/{owned_base.id}/tables',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        assert any(t['id'] == str(app_table.id) for t in resp.get_json()['data'])

        resp = client.get(
            f'/api/open/v1/bases/{owned_base.id}/tables/{app_table.id}/fields',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        assert any(f['id'] == str(app_field.id) for f in resp.get_json()['data'])

    def test_record_crud_flow(self, client, app, admin_user, owned_base, app_table, app_field):
        token = self._token(
            app, admin_user, owned_base,
            'base:read table:read record:read record:write field:read',
        )
        # create
        resp = client.post(
            f'/api/open/v1/bases/{owned_base.id}/tables/{app_table.id}/records',
            headers={'Authorization': f'Bearer {token}'},
            json={'values': {str(app_field.id): '开放API写入'}},
        )
        assert resp.status_code == 201
        record_id = resp.get_json()['data']['id']
        # get
        resp = client.get(
            f'/api/open/v1/bases/{owned_base.id}/tables/{app_table.id}/records/{record_id}',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        # update
        resp = client.put(
            f'/api/open/v1/bases/{owned_base.id}/tables/{app_table.id}/records/{record_id}',
            headers={'Authorization': f'Bearer {token}'},
            json={'values': {str(app_field.id): '已更新'}},
        )
        assert resp.status_code == 200
        # delete
        resp = client.delete(
            f'/api/open/v1/bases/{owned_base.id}/tables/{app_table.id}/records/{record_id}',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200

    def test_record_list_pagination(self, client, app, admin_user, owned_base, app_table):
        token = self._token(app, admin_user, owned_base, 'base:read table:read record:read')
        resp = client.get(
            f'/api/open/v1/bases/{owned_base.id}/tables/{app_table.id}/records?page=1&page_size=10',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data['data'], list)
        assert data['meta']['pagination']['total'] >= 0


class TestTokenRevocation:
    def test_revoke_token_then_rejected(self, client, app, admin_user, owned_base):
        app_obj, secret = _create_app(app, admin_user, owned_base)
        with app.app_context():
            real_app = OAuthApp.query.get(app_obj.id)
            token, _ = OAuthAppService.issue_token(real_app)
            # 找到刚签发的 ApiAppToken 并撤销
            issued = ApiAppToken.query.filter_by(app_id=real_app.id).order_by(
                ApiAppToken.created_at.desc()
            ).first()
            OAuthAppService.revoke_token_by_jti(issued.jti)
        resp = client.get(
            '/api/open/v1/bases', headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 401

    def test_revoke_all_app_tokens(self, client, app, admin_user, owned_base):
        token = _admin_token(app, admin_user)
        app_obj, secret = _create_app(app, admin_user, owned_base)
        with app.app_context():
            real_app = OAuthApp.query.get(app_obj.id)
            t1, _ = OAuthAppService.issue_token(real_app)
            OAuthAppService.revoke_all_app_tokens(real_app.id)
        resp = client.get(
            '/api/open/v1/bases', headers={'Authorization': f'Bearer {t1}'}
        )
        assert resp.status_code == 401
        # 管理端撤销返回成功
        resp = client.post(
            f'/api/oauth/apps/{app_obj.id}/tokens/revoke',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200


class TestServiceLayer:
    def test_generate_access_token_claims(self, app, admin_user, owned_base):
        app_obj, _ = _create_app(app, admin_user, owned_base)
        with app.app_context():
            real_app = OAuthApp.query.get(app_obj.id)
            access_token, _ = OAuthAppService.issue_token(real_app)
            assert access_token
            # 解析 claim
            from flask_jwt_extended import decode_token
            decoded = decode_token(access_token)
            assert decoded.get('app_id') == str(real_app.id)
            assert decoded.get('token_type') == 'app'
            assert decoded.get('sub') == str(real_app.id)

    def test_audit_log_written(self, app, admin_user, owned_base):
        app_obj, _ = _create_app(app, admin_user, owned_base)
        with app.app_context():
            real_app = OAuthApp.query.get(app_obj.id)
            OAuthAppService.issue_token(real_app)
            assert ApiAppAuditLog.query.filter_by(app_id=real_app.id).count() >= 1
            assert ApiAppAuditLog.query.filter_by(app_id=app_obj.id).count() >= 1


class TestOpenAPIExtended:
    def _token(self, app, admin_user, base, scopes):
        app_obj, _ = _create_app(app, admin_user, base, scopes=scopes)
        return _app_token(app, app_obj)

    def test_search_records(self, client, app, admin_user, owned_base, app_table, app_field):
        token = self._token(
            app, admin_user, owned_base,
            'base:read table:read record:read record:write field:read',
        )
        c = client.post(
            f'/api/open/v1/bases/{owned_base.id}/tables/{app_table.id}/records',
            headers={'Authorization': f'Bearer {token}'},
            json={'values': {str(app_field.id): '待搜索关键字'}},
        )
        assert c.status_code == 201
        resp = client.get(
            f'/api/open/v1/bases/{owned_base.id}/tables/{app_table.id}/records/search?q=关键字',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        records = resp.get_json()['data']
        # 搜索按 values JSON 全文匹配，应至少命中刚创建的记录
        assert len(records) >= 1
        assert any('关键字' in str(r['values']) for r in records)

    def test_search_records_requires_query(self, client, app, admin_user, owned_base, app_table):
        token = self._token(app, admin_user, owned_base, 'base:read table:read record:read')
        resp = client.get(
            f'/api/open/v1/bases/{owned_base.id}/tables/{app_table.id}/records/search',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 400

    def test_write_without_write_scope(self, client, app, admin_user, owned_base, app_table, app_field):
        # 仅授予 record:read，写入应被拒绝
        token = self._token(app, admin_user, owned_base, 'base:read table:read record:read')
        resp = client.post(
            f'/api/open/v1/bases/{owned_base.id}/tables/{app_table.id}/records',
            headers={'Authorization': f'Bearer {token}'},
            json={'values': {str(app_field.id): 'x'}},
        )
        assert resp.status_code == 403

    def test_record_on_unrelated_base(self, client, app, admin_user, owned_base, other_base, app_table):
        token = self._token(app, admin_user, owned_base, 'base:read table:read record:read')
        resp = client.get(
            f'/api/open/v1/bases/{other_base.id}/tables/{app_table.id}/records',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 403

    def test_admin_base_candidates(self, client, app, admin_user, owned_base):
        token = _admin_token(app, admin_user)
        resp = client.get('/api/oauth/bases', headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        ids = [b['id'] for b in resp.get_json()['data']]
        assert str(owned_base.id) in ids

    def test_admin_list_tokens(self, client, app, admin_user, owned_base):
        token = _admin_token(app, admin_user)
        app_obj, secret = _create_app(app, admin_user, owned_base)
        with app.app_context():
            real_app = OAuthApp.query.get(app_obj.id)
            OAuthAppService.issue_token(real_app)
        resp = client.get(
            f'/api/oauth/apps/{app_obj.id}/tokens',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        assert len(resp.get_json()['data']) >= 1

    def test_admin_audit_log(self, client, app, admin_user, owned_base):
        token = _admin_token(app, admin_user)
        app_obj, secret = _create_app(app, admin_user, owned_base)
        with app.app_context():
            real_app = OAuthApp.query.get(app_obj.id)
            OAuthAppService.issue_token(real_app)
        resp = client.get(
            f'/api/oauth/apps/{app_obj.id}/audit',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        assert len(resp.get_json()['data']) >= 1


class TestAuditCoverage:
    """审计日志覆盖测试：读操作 / 单令牌撤销 / token 失败 / 用户操作日志"""

    def _audit_actions(self, app, app_id):
        with app.app_context():
            return [
                log.action
                for log in ApiAppAuditLog.query.filter_by(app_id=app_id).all()
            ]

    def test_read_operations_audited(self, client, app, admin_user, owned_base, app_table, app_field):
        from app.models.log import OperationLog
        token = _app_token(app, _create_app(app, admin_user, owned_base)[0])
        client.get('/api/open/v1/bases', headers={'Authorization': f'Bearer {token}'})
        client.get(
            f'/api/open/v1/bases/{owned_base.id}/tables/{app_table.id}/records',
            headers={'Authorization': f'Bearer {token}'},
        )
        with app.app_context():
            from app.models.oauth_app import OAuthApp as OA
            app_id = OA.query.filter_by(app_name='测试应用').first().id
            actions = self._audit_actions(app, app_id)
            assert 'api_read' in actions
            assert 'token_issue' in actions

    def test_token_fail_audited(self, client, app, admin_user, owned_base):
        app_obj, secret = _create_app(app, admin_user, owned_base)
        client.post(
            '/api/oauth/token',
            json={'grant_type': 'client_credentials', 'client_id': app_obj.client_id, 'client_secret': 'bad'},
        )
        with app.app_context():
            actions = self._audit_actions(app, app_obj.id)
            assert 'token_fail' in actions

    def test_single_token_revoke_audited(self, client, app, admin_user, owned_base):
        app_obj, secret = _create_app(app, admin_user, owned_base)
        admin_token = _admin_token(app, admin_user)
        with app.app_context():
            real_app = OAuthApp.query.get(app_obj.id)
            access_token, record = OAuthAppService.issue_token(real_app)
            issued_jti = record.jti
        resp = client.post(
            f'/api/oauth/apps/{app_obj.id}/tokens/revoke',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'jti': issued_jti},
        )
        assert resp.status_code == 200
        with app.app_context():
            actions = self._audit_actions(app, app_obj.id)
            assert 'token_revoke' in actions

    def test_admin_create_writes_operation_log(self, client, app, admin_user, owned_base):
        from app.models.log import OperationLog
        token = _admin_token(app, admin_user)
        resp = client.post(
            '/api/oauth/apps',
            headers={'Authorization': f'Bearer {token}'},
            json={'app_name': '日志应用', 'allowed_bases': [str(owned_base.id)], 'scopes': 'base:read'},
        )
        assert resp.status_code == 201
        with app.app_context():
            logs = OperationLog.query.filter_by(
                action='create', entity_type='oauth_app'
            ).all()
            assert len(logs) >= 1
            assert str(logs[-1].user_id) == str(admin_user.id)

    def test_admin_reset_secret_writes_operation_log(self, client, app, admin_user, owned_base):
        from app.models.log import OperationLog
        token = _admin_token(app, admin_user)
        app_obj, _ = _create_app(app, admin_user, owned_base)
        resp = client.post(
            f'/api/oauth/apps/{app_obj.id}/reset-secret',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        with app.app_context():
            logs = OperationLog.query.filter_by(
                action='reset_secret', entity_type='oauth_app'
            ).all()
            assert len(logs) >= 1
            # 不捕获明文密钥进操作日志
            assert logs[-1].new_value is None
