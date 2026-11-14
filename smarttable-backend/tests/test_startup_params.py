import os
import sys
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
            with patch.object(sys, 'argv', ['run.py']):
                args = parse_args()
                assert args.enable_realtime is True

    def test_env_var_disable_realtime(self):
        with patch.dict(os.environ, {'ENABLE_REALTIME': 'false'}):
            from run import parse_args
            with patch.object(sys, 'argv', ['run.py']):
                args = parse_args()
                assert args.enable_realtime is False

    def test_env_var_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            if 'ENABLE_REALTIME' in os.environ:
                del os.environ['ENABLE_REALTIME']
            from run import parse_args
            with patch.object(sys, 'argv', ['run.py']):
                args = parse_args()
                assert args.enable_realtime is False

    def test_cli_flag_enable_realtime(self):
        from run import parse_args
        with patch.object(sys, 'argv', ['run.py', '--enable-realtime']):
            args = parse_args()
            assert args.enable_realtime is True

    def test_cli_short_flag_r(self):
        from run import parse_args
        with patch.object(sys, 'argv', ['run.py', '-r']):
            args = parse_args()
            assert args.enable_realtime is True

    def test_cli_flag_overrides_env(self):
        with patch.dict(os.environ, {'ENABLE_REALTIME': 'false'}):
            from run import parse_args
            with patch.object(sys, 'argv', ['run.py', '--enable-realtime']):
                args = parse_args()
                assert args.enable_realtime is True

    def test_realtime_status_endpoint_disabled(self, app, client):
        resp = client.get('/api/realtime/status')
        data = resp.get_json()
        assert data['data']['enabled'] is False

    def test_realtime_status_endpoint_enabled(self):
        app = create_app('testing', enable_realtime=True)
        app.config['DEV_SKIP_CAPTCHA'] = True
        from app.extensions import db
        with app.app_context():
            db.create_all()
            with app.test_client() as client:
                resp = client.get('/api/realtime/status')
                data = resp.get_json()
                assert data['data']['enabled'] is True
