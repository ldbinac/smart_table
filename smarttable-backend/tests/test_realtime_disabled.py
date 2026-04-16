import pytest
from app import create_app


@pytest.fixture(scope='session')
def app():
    app = create_app('testing', enable_realtime=False)
    yield app


@pytest.fixture(scope='session')
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    client.post('/api/auth/register', json={
        'username': 'testuser_disabled',
        'email': 'disabled@test.com',
        'password': 'Test123456'
    })
    response = client.post('/api/auth/login', json={
        'login': 'disabled@test.com',
        'password': 'Test123456'
    })
    data = response.get_json()
    token = data.get('data', {}).get('access_token', '')
    return {'Authorization': f'Bearer {token}'}


class TestRealtimeDisabled:

    def test_realtime_status_disabled(self, client):
        response = client.get('/api/realtime/status')
        data = response.get_json()
        assert response.status_code == 200
        assert data['data']['enabled'] is False
        assert data['data']['socket_url'] is None

    def test_config_realtime_disabled(self, app):
        assert app.config.get('REALTIME_ENABLED') is False

    def test_socketio_not_initialized(self, app):
        from app.extensions import socketio
        assert socketio.server is None

    def test_bases_api_works(self, client, auth_headers):
        response = client.get('/api/bases/', headers=auth_headers)
        assert response.status_code == 200

    def test_tables_api_works(self, client, auth_headers):
        response = client.get('/api/bases/', headers=auth_headers)
        bases = response.get_json().get('data', [])
        if bases:
            base_id = bases[0].get('id')
            response = client.get(f'/api/bases/{base_id}/tables', headers=auth_headers)
            assert response.status_code == 200

    def test_auth_api_works(self, client):
        response = client.post('/api/auth/login', json={
            'login': 'disabled@test.com',
            'password': 'Test123456'
        })
        assert response.status_code == 200

    def test_broadcast_if_enabled_returns_early(self, app):
        with app.app_context():
            from app.services.collaboration_service import CollaborationService
            result = CollaborationService.broadcast_if_enabled(
                'data:record_created', 'test-base-id', {'test': 'data'}
            )
            assert result is None


class TestRealtimeDisabledCRUD:

    def test_create_base(self, client, auth_headers):
        response = client.post('/api/bases/', headers=auth_headers, json={
            'name': 'Test Base Disabled'
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['name'] == 'Test Base Disabled'

    def test_create_table(self, client, auth_headers):
        response = client.post('/api/bases/', headers=auth_headers, json={
            'name': 'Base For Table Test'
        })
        base_id = response.get_json()['data']['id']
        response = client.post(f'/api/bases/{base_id}/tables', headers=auth_headers, json={
            'name': 'Test Table'
        })
        assert response.status_code == 201

    def test_create_record(self, client, auth_headers):
        response = client.post('/api/bases/', headers=auth_headers, json={
            'name': 'Base For Record Test'
        })
        base_id = response.get_json()['data']['id']
        response = client.post(f'/api/bases/{base_id}/tables', headers=auth_headers, json={
            'name': 'Table For Record'
        })
        table_id = response.get_json()['data']['id']
        response = client.post(f'/api/tables/{table_id}/records', headers=auth_headers, json={
            'values': {}
        })
        assert response.status_code == 201
