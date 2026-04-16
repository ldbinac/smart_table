import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope='session')
def app():
    app = create_app('testing', enable_realtime=True)
    yield app


@pytest.fixture(scope='session')
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    client.post('/api/auth/register', json={
        'username': 'realtime_tester',
        'email': 'realtime@test.com',
        'password': 'Test123456'
    })
    response = client.post('/api/auth/login', json={
        'login': 'realtime@test.com',
        'password': 'Test123456'
    })
    data = response.get_json()
    token = data.get('data', {}).get('access_token', '')
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def test_base_id(client, auth_headers):
    response = client.post('/api/bases/', headers=auth_headers, json={
        'name': 'Realtime Test Base'
    })
    return response.get_json()['data']['id']


class TestRealtimeEnabled:

    def test_realtime_status_enabled(self, client):
        response = client.get('/api/realtime/status')
        data = response.get_json()
        assert response.status_code == 200
        assert data['data']['enabled'] is True
        assert data['data']['socket_url'] is not None

    def test_config_realtime_enabled(self, app):
        assert app.config.get('REALTIME_ENABLED') is True


class TestSocketIOConnection:

    def test_socketio_connect_with_valid_token(self, app, auth_headers):
        token = auth_headers['Authorization'].replace('Bearer ', '')
        socketio_client = app.extensions.get('socketio')
        if socketio_client and socketio_client.server:
            sio_client = socketio_client.test_client(app, query_string=f'token={token}')
            assert sio_client.is_connected()

    def test_socketio_connect_without_token(self, app):
        socketio_client = app.extensions.get('socketio')
        if socketio_client and socketio_client.server:
            sio_client = socketio_client.test_client(app)
            received = sio_client.get_received()
            assert not sio_client.is_connected()


class TestCollaborationService:

    def test_broadcast_if_enabled(self, app):
        with app.app_context():
            from app.services.collaboration_service import CollaborationService
            result = CollaborationService.broadcast_if_enabled(
                'data:record_created', 'test-base-id', {'test': 'data'}
            )
            assert result is not None

    def test_join_room(self, app):
        with app.app_context():
            from app.services.collaboration_service import CollaborationService
            result = CollaborationService.join_room('test-base-id', 'test-user-id', 'test-sid')
            assert result is not None

    def test_leave_room(self, app):
        with app.app_context():
            from app.services.collaboration_service import CollaborationService
            CollaborationService.join_room('test-base-id', 'test-user-id', 'test-sid')
            CollaborationService.leave_room('test-base-id', 'test-user-id')

    def test_get_online_users(self, app):
        with app.app_context():
            from app.services.collaboration_service import CollaborationService
            users = CollaborationService.get_online_users('test-base-id')
            assert isinstance(users, list)

    def test_acquire_and_release_lock(self, app):
        with app.app_context():
            from app.services.collaboration_service import CollaborationService
            success, locked_by = CollaborationService.acquire_lock(
                'test-base-id', 'user-1', 'table-1', 'record-1', 'field-1'
            )
            assert success is True
            assert locked_by is None

            success2, locked_by2 = CollaborationService.acquire_lock(
                'test-base-id', 'user-2', 'table-1', 'record-1', 'field-1'
            )
            assert success2 is False
            assert locked_by2 is not None

            CollaborationService.release_lock(
                'test-base-id', 'user-1', 'table-1', 'record-1', 'field-1'
            )

            success3, locked_by3 = CollaborationService.acquire_lock(
                'test-base-id', 'user-2', 'table-1', 'record-1', 'field-1'
            )
            assert success3 is True

    def test_update_user_view(self, app):
        with app.app_context():
            from app.services.collaboration_service import CollaborationService
            CollaborationService.update_user_view(
                'test-base-id', 'test-user', 'table-1', 'view-1', 'table'
            )

    def test_update_user_cell(self, app):
        with app.app_context():
            from app.services.collaboration_service import CollaborationService
            CollaborationService.update_user_cell(
                'test-base-id', 'test-user', 'table-1', 'record-1', 'field-1'
            )


class TestOptimisticLock:

    def test_update_record_conflict(self, app, client, auth_headers):
        with app.app_context():
            from app.services.record_service import RecordService
            from app.services.table_service import TableService
            from app.errors.handlers import ConflictError

            response = client.post('/api/bases/', headers=auth_headers, json={
                'name': 'Optimistic Lock Test Base'
            })
            base_id = response.get_json()['data']['id']

            response = client.post(f'/api/bases/{base_id}/tables', headers=auth_headers, json={
                'name': 'Lock Test Table'
            })
            table_id = response.get_json()['data']['id']

            response = client.post(f'/api/tables/{table_id}/records', headers=auth_headers, json={
                'values': {}
            })
            record_id = response.get_json()['data']['id']

            record = RecordService.get_record_by_id(record_id)
            with pytest.raises(ConflictError):
                RecordService.update_record(
                    record,
                    values={'field1': 'new_value'},
                    updated_by=None,
                    expected_updated_at='2000-01-01T00:00:00+00:00'
                )

    def test_update_record_success_with_matching_timestamp(self, app, client, auth_headers):
        with app.app_context():
            from app.services.record_service import RecordService

            response = client.post('/api/bases/', headers=auth_headers, json={
                'name': 'Optimistic Lock Success Base'
            })
            base_id = response.get_json()['data']['id']

            response = client.post(f'/api/bases/{base_id}/tables', headers=auth_headers, json={
                'name': 'Lock Success Table'
            })
            table_id = response.get_json()['data']['id']

            response = client.post(f'/api/tables/{table_id}/records', headers=auth_headers, json={
                'values': {}
            })
            record_id = response.get_json()['data']['id']

            record = RecordService.get_record_by_id(record_id)
            current_ts = record.updated_at.isoformat() if record.updated_at else None
            updated = RecordService.update_record(
                record,
                values={'field1': 'value1'},
                updated_by=None,
                expected_updated_at=current_ts
            )
            assert updated is not None
