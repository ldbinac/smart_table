"""
泛微 E10 OAuth2 单点登录单元测试。

运行：
    cd smarttable-backend
    pytest tests/test_e10_sso.py -q
"""
from __future__ import annotations

from urllib.parse import parse_qs, quote, urlsplit

import pytest

from app.extensions import db
from app.integrations.e10 import register_e10_integration
from app.integrations.e10.client import (
    E10AccessToken,
    E10Client,
    E10OAuthError,
    E10Profile,
)
from app.integrations.e10.config import E10Config
from app.integrations.e10.models import E10Identity
from app.integrations.e10.service import (
    E10UserService,
    create_state,
    sanitize_redirect,
    verify_state,
)
from app.models.user import User


@pytest.fixture()
def e10_app(app):
    """启用 E10 SSO 的测试应用。"""
    app.config.update(
        E10_SSO_ENABLED=True,
        E10_BASE_URL='https://e10.example.com',
        E10_CLIENT_ID='test-client-id',
        E10_CLIENT_SECRET='test-client-secret',
        E10_REDIRECT_URI='https://smart.example.com/api/integrations/e10/callback',
        E10_FRONTEND_BASE_URL='https://smart.example.com',
        E10_EMAIL_DOMAIN='corp.example.com',
        E10_AUTO_CREATE_USERS=True,
        E10_DEFAULT_ROLE='editor',
        E10_PASSWORD_LOGIN_ENABLED=True,
        E10_LOGOUT_WITH_E10=True,
    )
    register_e10_integration(app)
    return app


@pytest.fixture()
def e10_client(e10_app):
    return e10_app.test_client()


# ----------------------------------------------------------------------
# 纯函数
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    'value,expected',
    [
        ('/base/123', '/base/123'),
        ('/base/123?view=1', '/base/123?view=1'),
        ('', '/'),
        (None, '/'),
        ('https://evil.example.com', '/'),
        ('//evil.example.com', '/'),
        ('/\\evil.example.com', '/'),
        ('/#/base/1', '/'),
        ('/base/1\nSet-Cookie: x=y', '/'),
    ],
)
def test_sanitize_redirect(value, expected):
    assert sanitize_redirect(value) == expected


def test_state_roundtrip(e10_app):
    with e10_app.app_context():
        cfg = E10Config.from_app(e10_app)
        token = create_state('/base/1', cfg.state_ttl)
        payload, error = verify_state(token, cfg.state_ttl)
        assert error is None
        assert payload['r'] == '/base/1'


# ----------------------------------------------------------------------
# 配置 / 跳转
# ----------------------------------------------------------------------
def test_config_disabled(app):
    app.config['E10_SSO_ENABLED'] = False
    register_e10_integration(app)
    response = app.test_client().get('/api/integrations/e10/config')
    assert response.status_code == 200
    data = response.get_json()['data']
    assert data['enabled'] is False
    assert data['login_url'] is None


def test_config_enabled(e10_client):
    response = e10_client.get('/api/integrations/e10/config')
    assert response.status_code == 200
    data = response.get_json()['data']
    assert data['enabled'] is True
    assert data['login_url'] == '/api/integrations/e10/login'
    assert data['password_login_enabled'] is True


def test_config_hides_button_when_misconfigured(e10_app):
    e10_app.config['E10_BASE_URL'] = ''
    register_e10_integration(e10_app)
    response = e10_app.test_client().get('/api/integrations/e10/config')
    assert response.status_code == 200
    data = response.get_json()['data']
    assert data['enabled'] is False
    assert data['ready'] is False


def test_login_redirects_to_e10(e10_client):
    response = e10_client.get('/api/integrations/e10/login?redirect=/base/1')
    assert response.status_code == 302

    location = response.headers['Location']
    assert location.startswith('https://e10.example.com/papi/sso/oauth2.0/authorize?')
    query = parse_qs(urlsplit(location).query)
    assert query['client_id'] == ['test-client-id']
    assert query['response_type'] == ['code']
    assert query['redirect_uri'] == [
        'https://smart.example.com/api/integrations/e10/callback'
    ]
    assert query['state']

    cookie = e10_client.get_cookie('e10_oauth_state', path='/api/integrations/e10')
    assert cookie is not None
    assert cookie.value == query['state'][0]


def test_logout_redirects_to_e10(e10_client):
    response = e10_client.get('/api/integrations/e10/logout?redirect=/login')
    assert response.status_code == 302
    location = response.headers['Location']
    assert location.startswith('https://e10.example.com/sp/integration/oauth2.0/logout?')
    service = parse_qs(urlsplit(location).query)['service'][0]
    assert service == 'https://smart.example.com/#/login'


# ----------------------------------------------------------------------
# 回调 / 一次性票据
# ----------------------------------------------------------------------
def _parse_hash_query(url: str):
    """解析 https://host/#/path?x=y 中 # 之后的 query。"""
    fragment = urlsplit(url).fragment
    if '?' not in fragment:
        return {}
    return parse_qs(fragment.split('?', 1)[1])


def test_callback_creates_user_and_exchange(e10_client, monkeypatch):
    login_response = e10_client.get('/api/integrations/e10/login?redirect=/base/1')
    assert login_response.status_code == 302
    state = e10_client.get_cookie('e10_oauth_state', path='/api/integrations/e10').value

    monkeypatch.setattr(
        E10Client,
        'exchange_code',
        lambda self, code, redirect_uri=None: E10AccessToken(
            access_token='e10-access-token', expires_in=7200
        ),
    )
    monkeypatch.setattr(
        E10Client,
        'fetch_profile',
        lambda self, token: E10Profile(
            id='zhangsan',
            attributes={'name': '张三'},
        ),
    )

    callback = e10_client.get(
        f'/api/integrations/e10/callback?code=one-time-code&state={quote(state)}'
    )
    assert callback.status_code == 302
    location = callback.headers['Location']
    assert location.startswith('https://smart.example.com/#/e10-callback?ticket=')
    ticket = _parse_hash_query(location)['ticket'][0]

    exchange = e10_client.post('/api/integrations/e10/exchange', json={'ticket': ticket})
    assert exchange.status_code == 200
    data = exchange.get_json()['data']
    assert data['user']['email'] == 'zhangsan@corp.example.com'
    assert data['user']['name'] == '张三'
    assert data['tokens']['access_token']
    assert data['tokens']['refresh_token']
    assert data['redirect'] == '/base/1'

    # 票据只能使用一次
    second = e10_client.post('/api/integrations/e10/exchange', json={'ticket': ticket})
    assert second.status_code == 401
    assert second.get_json()['error'] == 'e10_ticket_used'


def test_ticket_is_bound_to_the_original_browser(e10_app, monkeypatch):
    """攻击者把 ticket 链接发给受害者时，受害者浏览器没有绑定 Cookie，不能兑换。"""
    browser_a = e10_app.test_client()
    browser_b = e10_app.test_client()

    login_response = browser_a.get('/api/integrations/e10/login')
    assert login_response.status_code == 302
    state = browser_a.get_cookie(
        'e10_oauth_state', path='/api/integrations/e10'
    ).value

    monkeypatch.setattr(
        E10Client,
        'exchange_code',
        lambda self, code, redirect_uri=None: E10AccessToken(
            access_token='e10-access-token'
        ),
    )
    monkeypatch.setattr(
        E10Client,
        'fetch_profile',
        lambda self, token: E10Profile(id='bound-user', attributes={}),
    )

    callback = browser_a.get(
        f'/api/integrations/e10/callback?code=code&state={quote(state)}'
    )
    ticket = _parse_hash_query(callback.headers['Location'])['ticket'][0]

    stolen = browser_b.post(
        '/api/integrations/e10/exchange', json={'ticket': ticket}
    )
    assert stolen.status_code == 401
    assert stolen.get_json()['error'] == 'e10_ticket_invalid'

    # 错误浏览器不能把合法票据消费掉，原浏览器仍可正常兑换
    legitimate = browser_a.post(
        '/api/integrations/e10/exchange', json={'ticket': ticket}
    )
    assert legitimate.status_code == 200
    assert legitimate.get_json()['data']['tokens']['access_token']


def test_callback_state_mismatch(e10_client):
    e10_client.get('/api/integrations/e10/login')
    response = e10_client.get(
        '/api/integrations/e10/callback?code=abc&state=not-the-cookie-state'
    )
    assert response.status_code == 302
    location = response.headers['Location']
    assert 'error=e10_state_mismatch' in location


def test_callback_missing_state_cookie(e10_client):
    response = e10_client.get('/api/integrations/e10/callback?code=abc')
    assert response.status_code == 302
    assert 'error=e10_state_missing' in response.headers['Location']


def test_enforce_sso_blocks_local_auth(e10_app):
    e10_app.config['E10_ENFORCE_SSO'] = True
    register_e10_integration(e10_app)
    client = e10_app.test_client()

    response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'Test1234!',
        'captcha': 'TEST',
    })
    assert response.status_code == 403
    assert response.get_json()['error'] == 'e10_sso_only'

    register_response = client.post('/api/auth/register', json={
        'email': 'new@example.com',
        'password': 'Test1234!',
        'captcha': 'TEST',
    })
    assert register_response.status_code == 403


def test_exchange_invalid_ticket(e10_client):
    response = e10_client.post(
        '/api/integrations/e10/exchange', json={'ticket': 'not-a-valid-ticket'}
    )
    assert response.status_code == 401
    assert response.get_json()['error'] == 'e10_ticket_invalid'


# ----------------------------------------------------------------------
# E10 HTTP 客户端（参数位置 / 错误码映射）
# ----------------------------------------------------------------------
class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = str(payload)

    def json(self):
        return self._payload


def test_client_exchange_code_uses_documented_query_params(e10_app, monkeypatch):
    with e10_app.app_context():
        cfg = E10Config.from_app(e10_app)
        client = E10Client(cfg)
        calls = []

        def fake_post(url, **kwargs):
            calls.append((url, kwargs))
            return _FakeResponse({
                'msg': 'SUCCESS',
                'code': '0',
                'status': 200,
                'access_token': 'e10-token',
                'expire': 7200,
            })

        monkeypatch.setattr(client.session, 'post', fake_post)
        token = client.exchange_code('one-time-code')

        assert token.access_token == 'e10-token'
        assert token.expires_in == 7200
        assert len(calls) == 1
        url, kwargs = calls[0]
        assert url == 'https://e10.example.com/papi/sso/oauth2.0/accessToken'
        assert kwargs['params']['grant_type'] == 'authorization_code'
        assert kwargs['params']['client_secret'] == 'test-client-secret'
        assert kwargs['params']['redirect_uri'] == (
            'https://smart.example.com/api/integrations/e10/callback'
        )


def test_client_auto_retries_with_form_on_missing_param(e10_app, monkeypatch):
    with e10_app.app_context():
        cfg = E10Config.from_app(e10_app)
        client = E10Client(cfg)
        calls = []

        def fake_post(url, **kwargs):
            calls.append((url, kwargs))
            if len(calls) == 1:
                return _FakeResponse({
                    'msg': '参数client_id不能为空',
                    'code': '1002',
                    'status': 400,
                })
            return _FakeResponse({
                'msg': 'SUCCESS',
                'code': '0',
                'status': 200,
                'access_token': 'e10-token',
            })

        monkeypatch.setattr(client.session, 'post', fake_post)
        token = client.exchange_code('one-time-code')

        assert token.access_token == 'e10-token'
        assert len(calls) == 2
        assert 'params' in calls[0][1]
        assert calls[1][1]['data']['code'] == 'one-time-code'


def test_client_maps_e10_error_code(e10_app, monkeypatch):
    with e10_app.app_context():
        cfg = E10Config.from_app(e10_app)
        client = E10Client(cfg)

        monkeypatch.setattr(
            client.session,
            'post',
            lambda url, **kwargs: _FakeResponse({
                'msg': '回调地址与认证应用注册的业务系统URL地址不一致',
                'code': '80013',
                'status': 400,
            }, status=400),
        )
        with pytest.raises(E10OAuthError) as exc_info:
            client.exchange_code('one-time-code')
        assert exc_info.value.reason == 'redirect_mismatch'
        assert exc_info.value.public_reason == 'e10_redirect_mismatch'
        assert exc_info.value.upstream_code == '80013'


# ----------------------------------------------------------------------
# 用户映射
# ----------------------------------------------------------------------
def test_resolve_user_creates_user(e10_app):
    with e10_app.app_context():
        cfg = E10Config.from_app(e10_app)
        user, error = E10UserService.resolve_user(
            E10Profile(id='lisi', attributes={'name': '李四'}),
            cfg,
        )
        assert error is None
        assert user is not None
        assert user.email == 'lisi@corp.example.com'
        assert user.name == '李四'
        assert user.email_verified is True

        identity = E10Identity.query.filter_by(e10_user_id='lisi').first()
        assert identity is not None
        assert identity.user_id == user.id


def test_resolve_user_matches_existing_email(e10_app):
    with e10_app.app_context():
        existing = User(email='wangwu@corp.example.com', name='王五')
        existing.set_password('Test1234!')
        db.session.add(existing)
        db.session.commit()

        cfg = E10Config.from_app(e10_app)
        user, error = E10UserService.resolve_user(
            E10Profile(id='wangwu', attributes={'name': '王五（E10）'}),
            cfg,
        )
        assert error is None
        assert user.id == existing.id
        assert user.name == '王五（E10）'


def test_resolve_user_does_not_overwrite_existing_name(e10_app):
    with e10_app.app_context():
        existing = User(email='zhaoliu@corp.example.com', name='赵六')
        existing.set_password('Test1234!')
        db.session.add(existing)
        db.session.commit()

        cfg = E10Config.from_app(e10_app)
        user, error = E10UserService.resolve_user(
            E10Profile(id='zhaoliu', attributes={}),
            cfg,
        )
        assert error is None
        assert user.id == existing.id
        # E10 未返回姓名时，不应拿登录名覆盖已有显示名
        assert user.name == '赵六'


def test_weaver_person_id_mapping_uses_job_num_and_username(e10_app):
    """人员 id 映射：id=人员id，姓名=username，邮箱由 job_num 派生。"""
    with e10_app.app_context():
        e10_app.config.update(
            E10_ID_FIELD='id',
            E10_EMAIL_TEMPLATE='{job_num}@e10.local',
            E10_EMAIL_FALLBACK_TEMPLATE='{id}@e10.local',
            E10_EMAIL_DOMAIN='',
        )
        register_e10_integration(e10_app)
        cfg = E10Config.from_app(e10_app)

        user, error = E10UserService.resolve_user(
            E10Profile(
                id='18229708888',
                attributes={
                    'username': '张三',
                    'job_num': 'A1001',
                    'mobile': '13800138000',
                },
            ),
            cfg,
        )
        assert error is None
        assert user.email == 'a1001@e10.local'
        assert user.name == '张三'

        identity = E10Identity.query.filter_by(e10_user_id='18229708888').first()
        assert identity is not None
        assert identity.user_id == user.id


def test_weaver_email_attribute_takes_priority(e10_app):
    """E10 返回自定义属性 email 时，优先使用真实邮箱，不再用工号派生。"""
    with e10_app.app_context():
        e10_app.config.update(
            E10_ID_FIELD='id',
            E10_EMAIL_TEMPLATE='{job_num}@e10.local',
            E10_EMAIL_FALLBACK_TEMPLATE='{id}@e10.local',
            E10_EMAIL_DOMAIN='',
        )
        register_e10_integration(e10_app)
        cfg = E10Config.from_app(e10_app)

        user, error = E10UserService.resolve_user(
            E10Profile(
                id='18229708893',
                attributes={
                    'username': '张三',
                    'job_num': 'A1001',
                    'mobile': '13800138000',
                    'email': 'zhangsan@weaver.com.cn',
                },
            ),
            cfg,
        )
        assert error is None
        assert user.email == 'zhangsan@weaver.com.cn'
        assert user.name == '张三'


def test_weaver_mapping_falls_back_to_person_id(e10_app):
    """工号缺失时回退到 {id}@e10.local，避免无法开通。"""
    with e10_app.app_context():
        e10_app.config.update(
            E10_EMAIL_TEMPLATE='{job_num}@e10.local',
            E10_EMAIL_FALLBACK_TEMPLATE='{id}@e10.local',
            E10_EMAIL_DOMAIN='',
        )
        register_e10_integration(e10_app)
        cfg = E10Config.from_app(e10_app)

        user, error = E10UserService.resolve_user(
            E10Profile(
                id='18229708889',
                attributes={'username': '李四', 'mobile': '13900139000'},
            ),
            cfg,
        )
        assert error is None
        assert user.email == '18229708889@e10.local'
        assert user.name == '李四'


def test_client_normalizes_attribute_list(e10_app, monkeypatch):
    """兼容 attributes 为 [{name, value}] 列表的 E10 版本。"""
    with e10_app.app_context():
        cfg = E10Config.from_app(e10_app)
        client = E10Client(cfg)

        monkeypatch.setattr(
            client.session,
            'post',
            lambda url, **kwargs: _FakeResponse({
                'msg': 'SUCCESS',
                'code': '0',
                'status': 200,
                'id': '18229708890',
                'attributes': [
                    {'name': 'username', 'value': '王五'},
                    {'name': 'job_num', 'value': 'B2002'},
                    {'name': 'mobile', 'value': '13700137000'},
                ],
            }),
        )
        profile = client.fetch_profile('token')
        assert profile.id == '18229708890'
        assert profile.attributes['username'] == '王五'
        assert profile.attributes['job_num'] == 'B2002'
        assert profile.attributes['mobile'] == '13700137000'


def test_client_merges_top_level_custom_attributes(e10_app, monkeypatch):
    """兼容自定义属性平铺在 /profile 顶层的 E10 版本。"""
    with e10_app.app_context():
        cfg = E10Config.from_app(e10_app)
        client = E10Client(cfg)

        monkeypatch.setattr(
            client.session,
            'post',
            lambda url, **kwargs: _FakeResponse({
                'msg': 'SUCCESS',
                'code': '0',
                'status': 200,
                'id': '18229708891',
                'username': '赵六',
                'job_num': 'C3003',
                'mobile': '13600136000',
            }),
        )
        profile = client.fetch_profile('token')
        assert profile.attributes['username'] == '赵六'
        assert profile.attributes['job_num'] == 'C3003'
        assert profile.attributes['mobile'] == '13600136000'


def test_admin_ids_can_match_job_num(e10_app):
    with e10_app.app_context():
        e10_app.config.update(
            E10_ADMIN_IDS='A1001',
            E10_EMAIL_TEMPLATE='{job_num}@e10.local',
            E10_EMAIL_FALLBACK_TEMPLATE='{id}@e10.local',
            E10_EMAIL_DOMAIN='',
        )
        register_e10_integration(e10_app)
        cfg = E10Config.from_app(e10_app)

        user, error = E10UserService.resolve_user(
            E10Profile(
                id='18229708892',
                attributes={'username': '管理员', 'job_num': 'A1001'},
            ),
            cfg,
        )
        assert error is None
        assert user.role.value == 'admin'


def test_resolve_user_disabled_auto_create(e10_app):
    with e10_app.app_context():
        e10_app.config['E10_AUTO_CREATE_USERS'] = False
        register_e10_integration(e10_app)
        cfg = E10Config.from_app(e10_app)
        user, error = E10UserService.resolve_user(
            E10Profile(id='nobody', attributes={}),
            cfg,
        )
        assert user is None
        assert error == 'e10_user_not_provisioned'


def test_resolve_user_requires_email_mapping(e10_app):
    with e10_app.app_context():
        e10_app.config['E10_EMAIL_DOMAIN'] = ''
        e10_app.config['E10_EMAIL_TEMPLATE'] = ''
        register_e10_integration(e10_app)
        cfg = E10Config.from_app(e10_app)
        user, error = E10UserService.resolve_user(
            E10Profile(id='login-only', attributes={}),
            cfg,
        )
        assert user is None
        assert error == 'e10_email_not_configured'
