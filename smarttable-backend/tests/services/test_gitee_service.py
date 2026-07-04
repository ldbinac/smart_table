import json

import pytest
import requests
from unittest.mock import patch, MagicMock
from app.services.gitee_service import GiteeService


def test_is_demo_enabled_default():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app:
        mock_app.config = {'IS_DEMO_ENVIRONMENT': False}
        assert GiteeService.is_demo_enabled() is False


def test_get_repo_url():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app:
        mock_app.config = {'GITEE_REPO_OWNER': 'binac', 'GITEE_REPO_NAME': 'smart_table'}
        assert GiteeService.get_repo_url() == 'https://gitee.com/binac/smart_table'


def test_generate_authorize_url_creates_state_and_url():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app, \
         patch('app.services.gitee_service.secrets.token_urlsafe', return_value='fixed_state_123'), \
         patch('app.extensions.redis_client') as mock_redis:
        mock_app.config = {
            'GITEE_CLIENT_ID': 'client_id_abc',
            'GITEE_REDIRECT_URI': 'http://localhost/callback',
        }
        url = GiteeService.generate_authorize_url('user_1', 'user@example.com')

        mock_redis.setex.assert_called_once()
        cache_key, ttl, raw_payload = mock_redis.setex.call_args[0]
        assert cache_key == 'demo:gitee_star_state:fixed_state_123'
        assert ttl == 600
        assert json.loads(raw_payload) == {'user_id': 'user_1', 'email': 'user@example.com'}

        assert url.startswith('https://gitee.com/oauth/authorize?')
        assert 'response_type=code' in url
        assert 'client_id=client_id_abc' in url
        assert 'redirect_uri=http%3A%2F%2Flocalhost%2Fcallback' in url
        assert 'state=fixed_state_123' in url


def test_generate_authorize_url_raises_when_redis_unavailable():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app, \
         patch('app.extensions.redis_client', None):
        mock_app.config = {}
        with pytest.raises(RuntimeError, match='Redis 不可用'):
            GiteeService.generate_authorize_url('user_1', 'user@example.com')


def test_get_state_data_returns_payload_when_hit():
    with patch('app.extensions.redis_client') as mock_redis:
        mock_redis.get.return_value = json.dumps({'user_id': 'user_1', 'email': 'a@b.com'})
        result = GiteeService.get_state_data('state_123')
        assert result == {'user_id': 'user_1', 'email': 'a@b.com'}


def test_get_state_data_returns_none_when_miss():
    with patch('app.extensions.redis_client') as mock_redis:
        mock_redis.get.return_value = None
        result = GiteeService.get_state_data('state_123')
        assert result is None


def test_get_state_data_returns_none_on_exception():
    with patch('app.extensions.redis_client') as mock_redis:
        mock_redis.get.side_effect = Exception('redis error')
        result = GiteeService.get_state_data('state_123')
        assert result is None


def test_clear_state_deletes_key():
    with patch('app.extensions.redis_client') as mock_redis:
        GiteeService.clear_state('state_123')
        mock_redis.delete.assert_called_once_with('demo:gitee_star_state:state_123')


def test_exchange_access_token_success():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app, \
         patch('app.services.gitee_service.requests.post') as mock_post:
        mock_app.config = {
            'GITEE_CLIENT_ID': 'cid',
            'GITEE_CLIENT_SECRET': 'secret',
            'GITEE_REDIRECT_URI': 'http://localhost/callback',
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'token_123'}
        mock_post.return_value = mock_response
        token, error = GiteeService.exchange_access_token('code_123')
        assert token == 'token_123'
        assert error is None


def test_exchange_access_token_failure_on_non_200():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app, \
         patch('app.services.gitee_service.requests.post') as mock_post:
        mock_app.config = {}
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'bad request'
        mock_post.return_value = mock_response
        token, error = GiteeService.exchange_access_token('code_123')
        assert token is None
        assert error == 'gitee_oauth_failed'


def test_exchange_access_token_failure_when_no_access_token():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app, \
         patch('app.services.gitee_service.requests.post') as mock_post:
        mock_app.config = {}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'scope': 'user'}
        mock_post.return_value = mock_response
        token, error = GiteeService.exchange_access_token('code_123')
        assert token is None
        assert error == 'gitee_oauth_failed'


def test_exchange_access_token_failure_on_json_decode_error():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app, \
         patch('app.services.gitee_service.requests.post') as mock_post:
        mock_app.config = {}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError('msg', 'doc', 0)
        mock_post.return_value = mock_response
        token, error = GiteeService.exchange_access_token('code_123')
        assert token is None
        assert error == 'gitee_oauth_failed'


def test_exchange_access_token_failure_on_request_exception():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app, \
         patch('app.services.gitee_service.requests.post', side_effect=requests.RequestException('timeout')):
        mock_app.config = {}
        token, error = GiteeService.exchange_access_token('code_123')
        assert token is None
        assert error == 'gitee_oauth_failed'


def test_check_watched_returns_true_on_204():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app, \
         patch('app.services.gitee_service.requests.get') as mock_get:
        mock_app.config = {
            'GITEE_REPO_OWNER': 'binac',
            'GITEE_REPO_NAME': 'smart_table',
            'GITEE_STAR_CHECK_STRICT_MODE': False
        }
        mock_get.return_value = MagicMock(status_code=204)
        watched, error = GiteeService.check_watched('fake_token')
        assert watched is True
        assert error is None


def test_check_watched_returns_false_on_404():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app, \
         patch('app.services.gitee_service.requests.get') as mock_get:
        mock_app.config = {
            'GITEE_REPO_OWNER': 'binac',
            'GITEE_REPO_NAME': 'smart_table',
            'GITEE_STAR_CHECK_STRICT_MODE': False
        }
        mock_get.return_value = MagicMock(status_code=404)
        watched, error = GiteeService.check_watched('fake_token')
        assert watched is False
        assert error == 'gitee_repo_not_watched'


def test_check_watched_strict_mode_500_returns_failure():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app, \
         patch('app.services.gitee_service.requests.get') as mock_get:
        mock_app.config = {
            'GITEE_REPO_OWNER': 'binac',
            'GITEE_REPO_NAME': 'smart_table',
            'GITEE_STAR_CHECK_STRICT_MODE': True
        }
        mock_get.return_value = MagicMock(status_code=500)
        watched, error = GiteeService.check_watched('fake_token')
        assert watched is False
        assert error == 'gitee_watch_check_failed'


def test_check_watched_non_strict_mode_500_returns_success():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app, \
         patch('app.services.gitee_service.requests.get') as mock_get:
        mock_app.config = {
            'GITEE_REPO_OWNER': 'binac',
            'GITEE_REPO_NAME': 'smart_table',
            'GITEE_STAR_CHECK_STRICT_MODE': False
        }
        mock_get.return_value = MagicMock(status_code=500)
        watched, error = GiteeService.check_watched('fake_token')
        assert watched is True
        assert error is None


def test_check_watched_request_exception_strict_mode():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app, \
         patch('app.services.gitee_service.requests.get', side_effect=requests.RequestException('timeout')):
        mock_app.config = {
            'GITEE_REPO_OWNER': 'binac',
            'GITEE_REPO_NAME': 'smart_table',
            'GITEE_STAR_CHECK_STRICT_MODE': True
        }
        watched, error = GiteeService.check_watched('fake_token')
        assert watched is False
        assert error == 'gitee_watch_check_failed'


def test_check_watched_request_exception_non_strict_mode():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app, \
         patch('app.services.gitee_service.requests.get', side_effect=requests.RequestException('timeout')):
        mock_app.config = {
            'GITEE_REPO_OWNER': 'binac',
            'GITEE_REPO_NAME': 'smart_table',
            'GITEE_STAR_CHECK_STRICT_MODE': False
        }
        watched, error = GiteeService.check_watched('fake_token')
        assert watched is True
        assert error is None
