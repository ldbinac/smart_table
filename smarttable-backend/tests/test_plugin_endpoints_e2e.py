"""
插件自定义后端接口（endpoint）与第三方代理（proxy）端到端集成测试

覆盖设计 plan.md 中：
- §3 自定义 backend 接口：鉴权（Editor+ RBAC + 全局启用 + UI 需 Base 生效）、
  沙箱执行、manifest.endpoints 声明校验、RunLog 落库；
- §4 第三方网络代理：network 白名单 + SSRF 防护、鉴权（Editor+）；
- 完整链路：上传安装包 → 全局启用 → Base 安装启用 → 调用接口。
"""
import io
import json
import zipfile

import pytest

from app.extensions import db
from app.models.base import BaseMember, MemberRole
from app.models.plugin import (
    Plugin,
    PluginInstallation,
    PluginRunLog,
    PluginType,
    PluginVersion,
    PluginStatus,
)
from app.services import plugin_proxy_service


PLUGIN_ID = "com.example.echo"
NET_PLUGIN_ID = "com.example.net"


def _login(client, email, password="Test1234!"):
    resp = client.post("/api/auth/login", json={
        "email": email,
        "password": password,
        "captcha": "TEST",
    })
    if resp.status_code != 200:
        return {}
    data = resp.get_json().get("data", {})
    token = data.get("tokens", {}).get("access_token") or data.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


@pytest.fixture
def echo_package_dir(tmp_path):
    """在临时目录写入插件包文件（入口 + endpoint 源码）"""
    (tmp_path / "main.py").write_text("# script entry\n")
    ep = tmp_path / "endpoints"
    ep.mkdir(exist_ok=True)
    (ep / "echo.py").write_text(
        "result = {'ok': True, 'echo': (request or {}).get('payload')}\n")
    return tmp_path


@pytest.fixture
def seeded_echo(app, db_session, test_user, test_base, echo_package_dir):
    """直接落库一个已启用、Base 已安装的脚本插件（含 endpoint + network 声明）"""
    plugin = Plugin(
        id=PLUGIN_ID,
        name="Echo",
        type=PluginType.SCRIPT,
        status=PluginStatus.ENABLED,
        current_version="1.0.0",
        manifest={
            "id": PLUGIN_ID,
            "name": "Echo",
            "version": "1.0.0",
            "type": "script",
            "apiVersion": "1",
            "engines": {"smarttable": ">=1.0.0"},
            "entry": "main.py",
            "permissions": {"network": ["api.example.com", "https://api.example.com"]},
            "endpoints": [{"name": "echo", "entry": "endpoints/echo.py", "timeout": 30}],
        },
    )
    db.session.add(plugin)
    db.session.add(PluginVersion(
        plugin_id=PLUGIN_ID, version="1.0.0",
        package_path=str(echo_package_dir), checksum="abc"))
    db.session.add(PluginInstallation(
        plugin_id=PLUGIN_ID, base_id=test_base.id, enabled=True))
    db.session.commit()
    return plugin


@pytest.fixture
def seeded_net_only(app, db_session, test_user, test_base, echo_package_dir):
    """仅声明 endpoint、不声明 network 的脚本插件（用于 proxy 未声明白名单用例）"""
    plugin = Plugin(
        id=NET_PLUGIN_ID,
        name="NetOnly",
        type=PluginType.SCRIPT,
        status=PluginStatus.ENABLED,
        current_version="1.0.0",
        manifest={
            "id": NET_PLUGIN_ID,
            "name": "NetOnly",
            "version": "1.0.0",
            "type": "script",
            "apiVersion": "1",
            "engines": {"smarttable": ">=1.0.0"},
            "entry": "main.py",
            "permissions": {},
            "endpoints": [{"name": "echo", "entry": "endpoints/echo.py", "timeout": 30}],
        },
    )
    db.session.add(plugin)
    db.session.add(PluginVersion(
        plugin_id=NET_PLUGIN_ID, version="1.0.0",
        package_path=str(echo_package_dir), checksum="abc"))
    db.session.add(PluginInstallation(
        plugin_id=NET_PLUGIN_ID, base_id=test_base.id, enabled=True))
    db.session.commit()
    return plugin


# ==================== endpoint 调用 ====================

def test_call_endpoint_success(client, auth_headers, seeded_echo, test_base):
    resp = client.post(
        f"/api/plugins/{PLUGIN_ID}/call/echo",
        headers=auth_headers,
        json={"base_id": str(test_base.id), "payload": {"hello": "world"}})
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["status"] == "success"
    assert data["result"] == {"ok": True, "echo": {"hello": "world"}}
    # RunLog 落库（result 以 {endpoint, data} 包裹，便于审计区分）
    rec = PluginRunLog.query.filter_by(
        plugin_id=PLUGIN_ID, base_id=test_base.id).first()
    assert rec is not None
    assert rec.result == {"endpoint": "echo", "data": {"ok": True, "echo": {"hello": "world"}}}


def test_call_endpoint_missing_base_id(client, auth_headers, seeded_echo):
    resp = client.post(
        f"/api/plugins/{PLUGIN_ID}/call/echo",
        headers=auth_headers, json={"payload": {}})
    assert resp.status_code == 400


def test_call_endpoint_undeclared_404(client, auth_headers, seeded_echo, test_base):
    resp = client.post(
        f"/api/plugins/{PLUGIN_ID}/call/nonexistent",
        headers=auth_headers, json={"base_id": str(test_base.id), "payload": {}})
    assert resp.status_code == 404


def test_call_endpoint_not_enabled(client, auth_headers, seeded_echo, test_base):
    seeded_echo.status = PluginStatus.DISABLED
    db.session.commit()
    resp = client.post(
        f"/api/plugins/{PLUGIN_ID}/call/echo",
        headers=auth_headers, json={"base_id": str(test_base.id), "payload": {}})
    assert resp.status_code == 403


def test_call_endpoint_requires_editor_role(client, auth_headers, seeded_echo,
                                            test_base, test_viewer_user):
    # 浏览者（Viewer）加入 Base，endpoint 调用要求 Editor+，应被拒
    db.session.add(BaseMember(
        base_id=test_base.id, user_id=test_viewer_user.id, role=MemberRole.VIEWER))
    db.session.commit()
    viewer_headers = _login(client, "viewer@example.com")
    resp = client.post(
        f"/api/plugins/{PLUGIN_ID}/call/echo",
        headers=viewer_headers, json={"base_id": str(test_base.id), "payload": {}})
    assert resp.status_code == 403


def test_call_endpoint_non_member_denied(client, seeded_echo, test_base,
                                         db_session):
    # 非 Base 成员用户（仅登录，未加入 Base）应被拒
    from app.models.user import User
    outsider = User(email="outsider@example.com", name="外部")
    outsider.set_password("Test1234!")
    db.session.add(outsider)
    db.session.commit()
    headers = _login(client, "outsider@example.com")
    resp = client.post(
        f"/api/plugins/{PLUGIN_ID}/call/echo",
        headers=headers, json={"base_id": str(test_base.id), "payload": {}})
    assert resp.status_code == 403


# ==================== proxy 第三方代理 ====================

class _FakeResp:
    def __init__(self, status_code, headers, content):
        self.status_code = status_code
        self.headers = headers
        self._content = content

    def iter_content(self, chunk_size=8192):
        for i in range(0, len(self._content), chunk_size):
            yield self._content[i:i + chunk_size]

    def close(self):
        pass


@pytest.fixture
def patched_http(monkeypatch):
    captured = {}

    def fake_request(method, url, headers=None, data=None, timeout=None,
                     stream=True, allow_redirects=False):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = headers
        captured["data"] = data
        return _FakeResp(200, {"content-type": "application/json"},
                         b'{"ok":true}')

    monkeypatch.setattr(plugin_proxy_service.requests, "request", fake_request)
    # 旁路真实 DNS 解析（离线/无网络环境下 api.example.com 解析失败会被误判为受限），
    # 使代理转发「放行路径」可在集成测试中确定性验证
    monkeypatch.setattr(plugin_proxy_service, "_is_restricted_addr",
                        lambda host: False)
    return captured


def test_proxy_whitelist_pass(client, auth_headers, seeded_echo, test_base,
                              patched_http):
    resp = client.post(
        f"/api/plugins/{PLUGIN_ID}/proxy",
        headers=auth_headers,
        json={"base_id": str(test_base.id),
              "url": "https://api.example.com/v1/x", "method": "GET"})
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["status"] == 200
    assert data["body"] == '{"ok":true}'
    assert data["body_encoding"] == "text"
    # 受控头（如 Authorization）不得透传给上游
    assert "authorization" not in (patched_http["headers"] or {})


def test_proxy_unlisted_host_blocked(client, auth_headers, seeded_echo, test_base,
                                      patched_http):
    # 目标域名不在 manifest.network 白名单 → 拦截，请求不真正发出
    resp = client.post(
        f"/api/plugins/{PLUGIN_ID}/proxy",
        headers=auth_headers,
        json={"base_id": str(test_base.id),
              "url": "http://127.0.0.1:8080/secret"})
    assert resp.status_code in (400, 403)
    assert patched_http.get("url") is None


def test_proxy_ssrf_resolver_blocks_internal(client, auth_headers, seeded_echo,
                                              test_base, patched_http, monkeypatch):
    # 即使域名命中白名单，SSRF 解析判定为受限地址（如内网 IP）仍拦截
    monkeypatch.setattr(plugin_proxy_service, "_is_restricted_addr",
                        lambda host: True)
    resp = client.post(
        f"/api/plugins/{PLUGIN_ID}/proxy",
        headers=auth_headers,
        json={"base_id": str(test_base.id),
              "url": "https://api.example.com/internal"})
    assert resp.status_code == 400
    assert patched_http.get("url") is None


def test_proxy_requires_network_declared(client, auth_headers, seeded_net_only,
                                         test_base):
    resp = client.post(
        f"/api/plugins/{NET_PLUGIN_ID}/proxy",
        headers=auth_headers,
        json={"base_id": str(test_base.id),
              "url": "https://api.example.com/x"})
    assert resp.status_code == 403


def test_proxy_requires_editor_role(client, seeded_echo, test_base,
                                     test_viewer_user, db_session):
    db.session.add(BaseMember(
        base_id=test_base.id, user_id=test_viewer_user.id, role=MemberRole.VIEWER))
    db.session.commit()
    viewer_headers = _login(client, "viewer@example.com")
    resp = client.post(
        f"/api/plugins/{PLUGIN_ID}/proxy",
        headers=viewer_headers,
        json={"base_id": str(test_base.id),
              "url": "https://api.example.com/x"})
    assert resp.status_code == 403


# ==================== 完整链路：上传 → 启用 → 安装 → 调用 ====================

def _build_package() -> bytes:
    # 用 UI 插件走完整链路（脚本插件不依赖 Base 安装，见开发者指南 §5）
    manifest = {
        "id": PLUGIN_ID,
        "name": "Echo",
        "version": "1.0.0",
        "type": "ui",
        "apiVersion": "1",
        "engines": {"smarttable": ">=1.0.0"},
        "entry": "main.js",
        "permissions": {"network": ["api.example.com"]},
        "extensionPoints": [{"type": "toolbar-button", "title": "Echo"}],
        "endpoints": [{"name": "echo", "entry": "endpoints/echo.py", "timeout": 30}],
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        zf.writestr("main.js", "// entry\n")
        zf.writestr("endpoints/echo.py",
                    "result = {'ok': True, 'echo': (request or {}).get('payload')}\n")
    return buf.getvalue()


def _admin_user(app, db_session, client):
    from app.models.user import User, UserRole
    admin = User(email="admin@example.com", name="系统管理员", role=UserRole.ADMIN)
    admin.set_password("Test1234!")
    db.session.add(admin)
    db.session.commit()
    return _login(client, "admin@example.com")


def test_full_lifecycle_upload_enable_install_call(client, app, db_session,
                                                   test_base, tmp_path):
    # 隔离上传目录，避免污染仓库
    app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")

    admin_headers = _admin_user(app, db_session, client)

    # 1) 上传安装包（系统管理员）
    zip_bytes = _build_package()
    resp = client.post(
        "/api/plugins/upload",
        headers=admin_headers,
        data={"package": (io.BytesIO(zip_bytes), "echo.stplugin.zip")})
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["data"]["plugin"]["id"] == PLUGIN_ID

    # 2) 全局启用（setPluginStatus 使用 PUT）
    resp = client.put(
        f"/api/plugins/{PLUGIN_ID}/status",
        headers=admin_headers, json={"status": "enabled"})
    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == "enabled"

    # 3) Base 内安装并启用（Base Owner）
    owner_headers = _login(client, "test@example.com")
    resp = client.post(
        f"/api/plugins/{PLUGIN_ID}/installations",
        headers=owner_headers, json={"base_id": str(test_base.id)})
    assert resp.status_code == 200
    assert resp.get_json()["data"]["enabled"] is True

    # 4) 调用自定义接口（真实解包 + 受限沙箱子进程执行）
    resp = client.post(
        f"/api/plugins/{PLUGIN_ID}/call/echo",
        headers=owner_headers,
        json={"base_id": str(test_base.id), "payload": {"k": 1}})
    assert resp.status_code == 200
    assert resp.get_json()["data"]["result"] == {"ok": True, "echo": {"k": 1}}


def test_plugin_error_messages_follow_accept_language(client, app, db_session,
                                                      tmp_path):
    """插件接口错误消息按 Accept-Language 返回对应语言

    覆盖两层：
    - 路由层静态 key（如 plugin_not_found）
    - PluginValidationError.detail（i18n key + 参数插值）
    """
    app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
    admin_headers = _admin_user(app, db_session, client)
    en_headers = dict(admin_headers, **{"Accept-Language": "en-US"})

    # 缺失资源：默认中文
    resp = client.get("/api/plugins/not-exist", headers=admin_headers)
    assert resp.status_code == 404
    assert resp.get_json()["message"] == "插件不存在"

    resp = client.get("/api/plugins/not-exist", headers=en_headers)
    assert resp.status_code == 404
    assert resp.get_json()["message"] == "Plugin not found"

    # 重复上传同版本：触发校验错误（detail 为 i18n key 且带插值参数）
    zip_bytes = _build_package()
    assert client.post(
        "/api/plugins/upload", headers=admin_headers,
        data={"package": (io.BytesIO(zip_bytes), "echo.stplugin.zip")}
    ).status_code == 200

    resp = client.post(
        "/api/plugins/upload", headers=admin_headers,
        data={"package": (io.BytesIO(zip_bytes), "echo.stplugin.zip")})
    assert resp.status_code == 400
    assert PLUGIN_ID in resp.get_json()["message"]
    assert "已安装" in resp.get_json()["message"]

    resp = client.post(
        "/api/plugins/upload", headers=en_headers,
        data={"package": (io.BytesIO(zip_bytes), "echo.stplugin.zip")})
    assert resp.status_code == 400
    assert PLUGIN_ID in resp.get_json()["message"]
    assert "already installed" in resp.get_json()["message"]
