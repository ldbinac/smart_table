import os
import pytest
from unittest.mock import patch
from app import create_app


class TestStartupParams:

    def test_default_realtime_disabled(self):
        app = create_app('testing', enable_realtime=False)
        assert app.config.get('REALTIME_ENABLED') is False

    def test_enable_realtime_flag(self):
        app = create_app('testing', enable_realtime=True)
        assert app.config.get('REALTIME_ENABLED') is True

    def test_env_var_enable_realtime(self):
        with patch.dict(os.environ, {'ENABLE_REALTIME': 'true'}):
            from run import parse_args
            args = parse_args([])
            assert args.enable_realtime is True

    def test_env_var_disable_realtime(self):
        with patch.dict(os.environ, {'ENABLE_REALTIME': 'false'}):
            from run import parse_args
            args = parse_args([])
            assert args.enable_realtime is False

    def test_env_var_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            if 'ENABLE_REALTIME' in os.environ:
                del os.environ['ENABLE_REALTIME']
            from run import parse_args
            args = parse_args([])
            assert args.enable_realtime is False

    def test_cli_flag_enable_realtime(self):
        from run import parse_args
        args = parse_args(['--enable-realtime'])
        assert args.enable_realtime is True

    def test_cli_short_flag_r(self):
        from run import parse_args
        args = parse_args(['-r'])
        assert args.enable_realtime is True

    def test_cli_flag_overrides_env(self):
        with patch.dict(os.environ, {'ENABLE_REALTIME': 'false'}):
            from run import parse_args
            args = parse_args(['--enable-realtime'])
            assert args.enable_realtime is True

    def test_gunicorn_worker_class_realtime_enabled(self):
        with patch.dict(os.environ, {'ENABLE_REALTIME': 'true'}):
            import importlib
            import gunicorn.conf
            importlib.reload(gunicorn.conf)
            from gunicorn.conf import worker_class
            assert worker_class == 'eventlet'

    def test_gunicorn_worker_class_realtime_disabled(self):
        with patch.dict(os.environ, {'ENABLE_REALTIME': 'false'}):
            import importlib
            import gunicorn.conf
            importlib.reload(gunicorn.conf)
            from gunicorn.conf import worker_class
            assert worker_class == 'gthread'

    def test_gunicorn_workers_realtime_enabled(self):
        with patch.dict(os.environ, {'ENABLE_REALTIME': 'true'}):
            import importlib
            import gunicorn.conf
            importlib.reload(gunicorn.conf)
            from gunicorn.conf import workers
            assert workers == 1

    def test_realtime_status_endpoint_disabled(self):
        app = create_app('testing', enable_realtime=False)
        with app.test_client() as client:
            response = client.get('/api/realtime/status')
            data = response.get_json()
            assert data['data']['enabled'] is False

    def test_realtime_status_endpoint_enabled(self):
        app = create_app('testing', enable_realtime=True)
        with app.test_client() as client:
            response = client.get('/api/realtime/status')
            data = response.get_json()
            assert data['data']['enabled'] is True
