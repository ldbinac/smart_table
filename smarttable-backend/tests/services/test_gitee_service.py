import pytest
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


def test_check_starred_returns_true_on_204():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app, \
         patch('app.services.gitee_service.requests.get') as mock_get:
        mock_app.config = {
            'GITEE_REPO_OWNER': 'binac',
            'GITEE_REPO_NAME': 'smart_table',
            'GITEE_STAR_CHECK_STRICT_MODE': False
        }
        mock_get.return_value = MagicMock(status_code=204)
        starred, error = GiteeService.check_starred('fake_token')
        assert starred is True
        assert error is None


def test_check_starred_returns_false_on_404():
    with patch('app.services.gitee_service.current_app', new=MagicMock()) as mock_app, \
         patch('app.services.gitee_service.requests.get') as mock_get:
        mock_app.config = {
            'GITEE_REPO_OWNER': 'binac',
            'GITEE_REPO_NAME': 'smart_table',
            'GITEE_STAR_CHECK_STRICT_MODE': False
        }
        mock_get.return_value = MagicMock(status_code=404)
        starred, error = GiteeService.check_starred('fake_token')
        assert starred is False
        assert error == 'gitee_repo_not_starred'
