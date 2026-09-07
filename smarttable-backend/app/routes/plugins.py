"""
插件路由模块
插件管理 REST API（上传/升级/回滚/生命周期/配置/运行/日志）与
UI 插件沙箱静态服务（loader.html + 包文件，签名 URL 鉴权）。

权限模型（两层 RBAC）：
- 上传/升级/回滚/卸载/全局启停：系统 Admin
- Base 级安装/启停/配置：Base Owner/Admin
- 脚本手动运行：Base Editor 及以上
- 沙箱静态服务：短时签名 URL（iframe 无法携带 JWT 头）
"""
import hashlib
import hmac
import json
import logging
import time
from pathlib import Path

from flask import Blueprint, request, g, send_from_directory, Response

from app.i18n import translate
from app.models.base import MemberRole
from app.models.plugin import (
    Plugin, PluginRunLog, PluginType, PluginStatus, RunStatus,
)
from app.services.permission_service import PermissionService
from app.services.plugin_service import (
    PluginService, PluginValidationError, PluginNotFoundError,
)
from app.utils.decorators import jwt_required, admin_required
from app.utils.response import (
    success_response, error_response, not_found_response,
    forbidden_response, paginated_response
)

log = logging.getLogger(__name__)

plugins_bp = Blueprint('plugins', __name__)
plugins_bp.strict_slashes = False

# 沙箱签名 URL 有效期（秒）
SANDBOX_TOKEN_TTL = 600

# loader.html 中注入的 SDK 源码（握手 + postMessage JSON-RPC 客户端）
# 保持与前端宿主 rpc.ts 协议一致：init/initAck/rpc.request/rpc.response
_LOADER_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  html,body {{ margin:0; padding:0; height:100%;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif;
    font-size: 14px; color: #303133; background: #fff; }}
</style>
</head>
<body>
<div id="app"></div>
<script>
(function () {{
  var PLUGIN_ID = {plugin_id_json};
  var VERSION = {version_json};
  var HANDSHAKE_TIMEOUT = 10000;

  // ---- 握手：从 URL fragment 读取一次性 token，向宿主发起 init ----
  var handshakeToken = null;
  try {{
    var m = window.location.hash.match(/[#&]token=([^&]+)/);
    if (m) handshakeToken = decodeURIComponent(m[1]);
  }} catch (e) {{ /* ignore */ }}

  var pendingCalls = Object.create(null);
  var readyCallbacks = [];
  var ready = false;
  var nextId = 1;

  function post(msg) {{ window.parent.postMessage(msg, '*'); }}

  function fail(reason) {{
    document.getElementById('app').innerHTML =
      '<div style="padding:24px;color:#F56C6C">' + reason + '</div>';
  }}

  var initTimer = setTimeout(function () {{
    if (!ready) fail('Plugin handshake timeout: host did not respond.');
  }}, HANDSHAKE_TIMEOUT);

  function handleInitAck(msg) {{
    ready = true;
    clearTimeout(initTimer);
    SDK.permissions = msg.permissions || {{}};
    SDK.sdkInfo = msg.sdk || {{}};
    readyCallbacks.splice(0).forEach(function (cb) {{ cb(SDK); }});
  }}

  window.addEventListener('message', function (event) {{
    var msg = event.data;
    if (!msg || typeof msg !== 'object') return;
    if (msg.type === 'initAck' && !ready) {{
      handleInitAck(msg);
      return;
    }}
    if (msg.type === 'rpc.response' && msg.id && pendingCalls[msg.id]) {{
      var p = pendingCalls[msg.id];
      delete pendingCalls[msg.id];
      if (msg.error) p.reject(msg.error);
      else p.resolve(msg.result);
    }}
  }});

  // ---- SDK：暴露给插件代码的全局对象 ----
  var SDK = {{
    pluginId: PLUGIN_ID,
    version: VERSION,
    permissions: {{}},
    sdkInfo: {{}},
    ready: function (cb) {{
      return new Promise(function (resolve) {{
        if (ready) {{ cb && cb(SDK); resolve(SDK); return; }}
        readyCallbacks.push(function (s) {{ cb && cb(s); resolve(s); }});
      }});
    }},
    request: function (method, params) {{
      if (!ready) return Promise.reject({{ code: 'NOT_READY',
        message: 'SDK not ready; use SmartTableSDK.ready()' }});
      return new Promise(function (resolve, reject) {{
        var id = 'req-' + (nextId++) + '-' + Math.random().toString(36).slice(2, 8);
        pendingCalls[id] = {{ resolve: resolve, reject: reject }};
        post({{ type: 'rpc.request', id: id, method: method, params: params || {{}} }});
        setTimeout(function () {{
          if (pendingCalls[id]) {{
            delete pendingCalls[id];
            reject({{ code: 'TIMEOUT', message: 'RPC call timed out: ' + method }});
          }}
        }}, 30000);
      }});
    }},
    onUnloaded: function (cb) {{ window.addEventListener('unload', cb); }}
  }};
  window.SmartTableSDK = SDK;

  // ---- 发起握手 ----
  if (handshakeToken) {{
    post({{ type: 'init', token: handshakeToken }});
  }} else {{
    fail('Plugin initialization failed: missing handshake token.');
  }}
}})();
</script>
<script src="files/{entry}?st={st}"></script>
</body>
</html>
"""


# ==================== 沙箱签名 URL ====================

def _sign(payload: str) -> str:
    from flask import current_app
    key = current_app.config.get('SECRET_KEY', '') or ''
    return hmac.new(key.encode('utf-8'), payload.encode('utf-8'),
                    hashlib.sha256).hexdigest()


def generate_sandbox_token(plugin_id: str, version: str) -> str:
    """生成短时签名 token（plugin_id + version + 过期时间）"""
    exp = int(time.time()) + SANDBOX_TOKEN_TTL
    payload = f'{plugin_id}|{version}|{exp}'
    return f'{exp}.{_sign(payload)}'


def verify_sandbox_token(token: str, plugin_id: str, version: str) -> bool:
    try:
        exp_str, sig = token.split('.', 1)
        exp = int(exp_str)
    except (ValueError, AttributeError):
        return False
    if exp < int(time.time()):
        return False
    return hmac.compare_digest(_sign(f'{plugin_id}|{version}|{exp}'), sig)


# ==================== 沙箱静态服务 ====================

@plugins_bp.route(
    '/plugins/<string:plugin_id>/versions/<string:version>/loader.html',
    methods=['GET'])
def plugin_loader(plugin_id: str, version: str):
    """UI 插件沙箱 loader（签名 URL 鉴权，iframe 无法携带 JWT 头）

    ---
    tags:
      - Plugins
    parameters:
      - name: plugin_id
        in: path
        type: string
        required: true
      - name: version
        in: path
        type: string
        required: true
      - name: st
        in: query
        type: string
        required: true
        description: 短时签名 token（POST /sandbox-url 获取）
    responses:
      200:
        description: loader HTML
      403:
        description: 签名校验失败或过期
    """
    st = request.args.get('st', '')
    if not verify_sandbox_token(st, plugin_id, version):
        return forbidden_response('plugin_sandbox_token_invalid')

    try:
        plugin = Plugin.query.filter_by(id=plugin_id).first()
        if plugin is None or plugin.status != PluginStatus.ENABLED:
            return forbidden_response('plugin_not_enabled')
        entry = (plugin.manifest or {}).get('entry', '')
        html = _LOADER_TEMPLATE.format(
            plugin_id_json=json.dumps(plugin_id),
            version_json=json.dumps(version),
            entry=entry,
            st=st,
        )
        return Response(html, mimetype='text/html; charset=utf-8')
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')
    except Exception:
        log.exception('[plugins] loader 生成失败 %s@%s', plugin_id, version)
        return error_response('plugin_loader_error', 500)


@plugins_bp.route(
    '/plugins/<string:plugin_id>/versions/<string:version>/files/<path:filename>',
    methods=['GET'])
def plugin_file(plugin_id: str, version: str, filename: str):
    """插件包内静态文件（send_from_directory 防路径穿越，签名 URL 鉴权）

    ---
    tags:
      - Plugins
    parameters:
      - name: plugin_id
        in: path
        type: string
        required: true
      - name: version
        in: path
        type: string
        required: true
      - name: filename
        in: path
        type: string
        required: true
      - name: st
        in: query
        type: string
        required: true
    responses:
      200:
        description: 文件内容
      403:
        description: 签名校验失败
      404:
        description: 文件不存在
    """
    st = request.args.get('st', '')
    if not verify_sandbox_token(st, plugin_id, version):
        return forbidden_response('plugin_sandbox_token_invalid')

    try:
        package_dir = PluginService.get_package_dir(plugin_id, version)
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')

    # send_from_directory 自带路径穿越防护
    return send_from_directory(str(package_dir), filename)


@plugins_bp.route('/plugins/<string:plugin_id>/sandbox-url', methods=['POST'])
@jwt_required
def get_sandbox_url(plugin_id: str):
    """获取 UI 插件沙箱的短时签名 URL（前端创建 iframe 时调用）

    ---
    tags:
      - Plugins
    security:
      - Bearer: []
    parameters:
      - name: plugin_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        schema:
          type: object
          required: [base_id]
          properties:
            base_id:
              type: string
    responses:
      200:
        description: 签名 URL
    """
    data = request.get_json(silent=True) or {}
    base_id = data.get('base_id')
    if not base_id:
        return error_response('base_id_required', 400)

    # 用户须为 Base 成员（viewer 即可查看插件 UI）
    if not PermissionService.check_permission(
            str(base_id), str(g.current_user_id), MemberRole.VIEWER):
        return forbidden_response('no_permission_access_base')

    plugin = Plugin.query.filter_by(id=plugin_id).first()
    if plugin is None:
        return not_found_response('plugin_not_found')
    if plugin.type != PluginType.UI:
        return error_response('plugin_not_ui_type', 400)
    if plugin.status != PluginStatus.ENABLED:
        return forbidden_response('plugin_not_enabled')
    # Base 级有效启用检查
    from app.models.plugin import PluginInstallation
    inst = PluginInstallation.query.filter_by(
        plugin_id=plugin_id, base_id=base_id, enabled=True).first()
    if inst is None:
        return forbidden_response('plugin_not_enabled_in_base')

    version = plugin.current_version
    st = generate_sandbox_token(plugin_id, version)
    url = f'/api/plugins/{plugin_id}/versions/{version}/loader.html?st={st}'
    return success_response({'url': url, 'version': version})


# ==================== 管理接口：上传/升级/回滚/启停/卸载 ====================

@plugins_bp.route('/plugins/upload', methods=['POST'])
@jwt_required
@admin_required
def upload_plugin():
    """上传安装/升级 .stplugin.zip 安装包（系统 Admin）

    ---
    tags:
      - Plugins
    security:
      - Bearer: []
    consumes:
      - multipart/form-data
    parameters:
      - name: package
        in: formData
        type: file
        required: true
        description: .stplugin.zip 安装包（内含 manifest.json + 入口文件）
    responses:
      200:
        description: 安装/升级成功
      400:
        description: 安装包校验失败
    """
    if 'package' not in request.files:
        return error_response('package_file_required', 400)
    file = request.files['package']
    zip_bytes = file.read()
    if not zip_bytes:
        return error_response('package_file_required', 400)
    if len(zip_bytes) > 50 * 1024 * 1024:
        return error_response('package_too_large', 400, error='INVALID_PACKAGE')

    try:
        result = PluginService.install_or_upgrade(
            zip_bytes, str(g.current_user_id))
        return success_response(result)
    except PluginValidationError as e:
        return error_response(
            message=e.detail or e.error_code,
            code=400,
            error=e.error_code,
            details=([{'error_code': e.error_code, 'detail': e.detail}]
                     if e.detail else None),
        )
    except Exception:
        log.exception('[plugins] 安装包处理失败')
        return error_response('plugin_install_failed', 500)


@plugins_bp.route('/plugins', methods=['GET'])
@jwt_required
def list_plugins():
    """获取插件列表（可选 base_id 过滤，附带 Base 级安装/生效状态）

    ---
    tags:
      - Plugins
    security:
      - Bearer: []
    parameters:
      - name: base_id
        in: query
        type: string
        required: false
    responses:
      200:
        description: 插件列表
    """
    base_id = request.args.get('base_id')
    if base_id:
        if not PermissionService.check_permission(
                base_id, str(g.current_user_id), MemberRole.VIEWER):
            return forbidden_response('no_permission_access_base')
    return success_response(PluginService.list_plugins(base_id))


@plugins_bp.route('/plugins/<string:plugin_id>', methods=['GET'])
@jwt_required
def get_plugin(plugin_id: str):
    """获取插件详情（含版本历史）

    ---
    tags:
      - Plugins
    security:
      - Bearer: []
    parameters:
      - name: plugin_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: 插件详情
      404:
        description: 插件不存在
    """
    try:
        return success_response(PluginService.get_plugin(plugin_id))
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')


@plugins_bp.route('/plugins/<string:plugin_id>/status', methods=['PUT'])
@jwt_required
@admin_required
def set_plugin_status(plugin_id: str):
    """全局启用/禁用/恢复插件（系统 Admin）

    ---
    tags:
      - Plugins
    security:
      - Bearer: []
    parameters:
      - name: plugin_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        schema:
          type: object
          required: [status]
          properties:
            status:
              type: string
              enum: [enabled, disabled, installed]
    responses:
      200:
        description: 更新成功
    """
    data = request.get_json(silent=True) or {}
    status = data.get('status')
    if status not in ('enabled', 'disabled', 'installed'):
        return error_response('invalid_status', 400)
    try:
        return success_response(PluginService.set_status(plugin_id, status))
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')
    except PluginValidationError as e:
        return error_response(
            message=e.detail or e.error_code,
            code=400,
            error=e.error_code,
            details=([{'error_code': e.error_code, 'detail': e.detail}]
                     if e.detail else None),
        )


@plugins_bp.route('/plugins/<string:plugin_id>/rollback', methods=['POST'])
@jwt_required
@admin_required
def rollback_plugin(plugin_id: str):
    """回滚到已保留的历史版本（系统 Admin，保留配置与 Base 级安装关系）

    ---
    tags:
      - Plugins
    security:
      - Bearer: []
    parameters:
      - name: plugin_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        schema:
          type: object
          required: [version]
          properties:
            version:
              type: string
    responses:
      200:
        description: 回滚成功
    """
    data = request.get_json(silent=True) or {}
    target = data.get('version')
    if not target:
        return error_response('version_required', 400)
    try:
        return success_response(PluginService.rollback(plugin_id, target))
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')
    except PluginValidationError as e:
        return error_response(
            message=e.detail or e.error_code,
            code=400,
            error=e.error_code,
            details=([{'error_code': e.error_code, 'detail': e.detail}]
                     if e.detail else None),
        )


@plugins_bp.route('/plugins/<string:plugin_id>', methods=['DELETE'])
@jwt_required
@admin_required
def uninstall_plugin(plugin_id: str):
    """卸载插件（系统 Admin，删除全部配置/安装关系/运行日志/包文件）

    ---
    tags:
      - Plugins
    security:
      - Bearer: []
    parameters:
      - name: plugin_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: 卸载成功
    """
    try:
        PluginService.uninstall(plugin_id)
        return success_response({'uninstalled': plugin_id})
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')


# ==================== Base 级安装/启停 ====================

def _check_base_admin(base_id) -> bool:
    return PermissionService.check_permission(
        str(base_id), str(g.current_user_id), MemberRole.ADMIN)


@plugins_bp.route('/plugins/<string:plugin_id>/installations', methods=['GET'])
@jwt_required
def get_installations(plugin_id: str):
    """获取插件在某 Base 的安装状态

    ---
    tags:
      - Plugins
    security:
      - Bearer: []
    parameters:
      - name: plugin_id
        in: path
        type: string
        required: true
      - name: base_id
        in: query
        type: string
        required: true
    responses:
      200:
        description: 安装状态
    """
    base_id = request.args.get('base_id')
    if not base_id:
        return error_response('base_id_required', 400)
    if not PermissionService.check_permission(
            base_id, str(g.current_user_id), MemberRole.VIEWER):
        return forbidden_response('no_permission_access_base')

    from app.models.plugin import PluginInstallation
    inst = PluginInstallation.query.filter_by(
        plugin_id=plugin_id, base_id=base_id).first()
    return success_response(inst.to_dict() if inst else None)


@plugins_bp.route('/plugins/<string:plugin_id>/installations', methods=['POST'])
@jwt_required
def install_to_base(plugin_id: str):
    """在 Base 内安装并启用插件（Base Owner/Admin）

    ---
    tags:
      - Plugins
    security:
      - Bearer: []
    parameters:
      - name: plugin_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        schema:
          type: object
          required: [base_id]
          properties:
            base_id:
              type: string
    responses:
      200:
        description: 安装成功
    """
    data = request.get_json(silent=True) or {}
    base_id = data.get('base_id')
    if not base_id:
        return error_response('base_id_required', 400)
    if not _check_base_admin(base_id):
        return forbidden_response('no_permission_manage_plugin_in_base')
    try:
        result = PluginService.install_to_base(
            plugin_id, base_id, str(g.current_user_id))
        return success_response(result)
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')
    except PluginValidationError as e:
        return error_response(
            message=e.detail or e.error_code,
            code=400,
            error=e.error_code,
            details=([{'error_code': e.error_code, 'detail': e.detail}]
                     if e.detail else None),
        )


@plugins_bp.route('/plugins/<string:plugin_id>/installations', methods=['PUT'])
@jwt_required
def set_installation_enabled(plugin_id: str):
    """启停插件在 Base 内的启用状态（Base Owner/Admin）

    ---
    tags:
      - Plugins
    security:
      - Bearer: []
    parameters:
      - name: plugin_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        schema:
          type: object
          required: [base_id, enabled]
          properties:
            base_id:
              type: string
            enabled:
              type: boolean
    responses:
      200:
        description: 更新成功
    """
    data = request.get_json(silent=True) or {}
    base_id = data.get('base_id')
    enabled = data.get('enabled')
    if not base_id or not isinstance(enabled, bool):
        return error_response('base_id_and_enabled_required', 400)
    if not _check_base_admin(base_id):
        return forbidden_response('no_permission_manage_plugin_in_base')
    try:
        result = PluginService.set_base_enabled(plugin_id, base_id, enabled)
        return success_response(result)
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')
    except PluginValidationError as e:
        return error_response(
            message=e.detail or e.error_code,
            code=400,
            error=e.error_code,
            details=([{'error_code': e.error_code, 'detail': e.detail}]
                     if e.detail else None),
        )


@plugins_bp.route('/plugins/<string:plugin_id>/installations', methods=['DELETE'])
@jwt_required
def uninstall_from_base(plugin_id: str):
    """从 Base 移除插件（Base Owner/Admin）

    ---
    tags:
      - Plugins
    security:
      - Bearer: []
    parameters:
      - name: plugin_id
        in: path
        type: string
        required: true
      - name: base_id
        in: query
        type: string
        required: true
    responses:
      200:
        description: 移除成功
    """
    base_id = request.args.get('base_id')
    if not base_id:
        return error_response('base_id_required', 400)
    if not _check_base_admin(base_id):
        return forbidden_response('no_permission_manage_plugin_in_base')
    try:
        PluginService.uninstall_from_base(plugin_id, base_id)
        return success_response({'removed': plugin_id})
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')


# ==================== 配置 ====================

@plugins_bp.route('/plugins/<string:plugin_id>/config', methods=['GET'])
@jwt_required
def get_plugin_config(plugin_id: str):
    """读取插件生效配置（base 级深合并于 global 之上）

    ---
    tags:
      - Plugins
    security:
      - Bearer: []
    parameters:
      - name: plugin_id
        in: path
        type: string
        required: true
      - name: base_id
        in: query
        type: string
        required: false
    responses:
      200:
        description: 生效配置
    """
    base_id = request.args.get('base_id')
    scope = request.args.get('scope')  # 可选：global/base，按作用域返回存储值；缺省返回生效合并视图
    if scope:
        if scope not in ('global', 'base'):
            return error_response('scope_and_config_required', 400)
        if scope == 'base':
            if not base_id:
                return error_response('base_id_required', 400)
            if not PermissionService.check_permission(
                    base_id, str(g.current_user_id), MemberRole.VIEWER):
                return forbidden_response('no_permission_access_base')
        try:
            return success_response(PluginService.get_scope_config(
                plugin_id, scope, base_id if scope == 'base' else None))
        except PluginNotFoundError:
            return not_found_response('plugin_not_found')
        except PluginValidationError:
            return error_response('scope_and_config_required', 400)
    if base_id and not PermissionService.check_permission(
            base_id, str(g.current_user_id), MemberRole.VIEWER):
        return forbidden_response('no_permission_access_base')
    try:
        return success_response(PluginService.get_effective_config(plugin_id, base_id))
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')


@plugins_bp.route('/plugins/<string:plugin_id>/config', methods=['PUT'])
@jwt_required
def set_plugin_config(plugin_id: str):
    """写入插件配置（global 级需系统 Admin；base 级需 Base Owner/Admin）

    ---
    tags:
      - Plugins
    security:
      - Bearer: []
    parameters:
      - name: plugin_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        schema:
          type: object
          required: [scope, config]
          properties:
            scope:
              type: string
              enum: [global, base]
            base_id:
              type: string
            config:
              type: object
    responses:
      200:
        description: 写入成功
      400:
        description: configSchema 校验失败
    """
    data = request.get_json(silent=True) or {}
    scope = data.get('scope', 'base')
    base_id = data.get('base_id')
    config = data.get('config')
    if scope not in ('global', 'base') or not isinstance(config, dict):
        return error_response('scope_and_config_required', 400)
    if scope == 'base' and not base_id:
        return error_response('base_id_required', 400)

    # 权限：global 级需系统 Admin；base 级需 Base Owner/Admin
    is_admin = hasattr(g, 'current_user') and g.current_user is not None \
        and g.current_user.is_admin()
    if scope == 'global':
        if not is_admin:
            return forbidden_response('admin_required_for_global_config')
    else:
        if not _check_base_admin(base_id):
            return forbidden_response('no_permission_manage_plugin_in_base')

    try:
        result = PluginService.set_config(
            plugin_id, scope, base_id, config, str(g.current_user_id))
        return success_response(result)
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')
    except PluginValidationError as e:
        return error_response(
            message=e.detail or e.error_code,
            code=400,
            error=e.error_code,
            details=([{'error_code': e.error_code, 'detail': e.detail}]
                     if e.detail else None),
        )


# ==================== 脚本插件运行 ====================

@plugins_bp.route('/plugins/<string:plugin_id>/run', methods=['POST'])
@jwt_required
def run_plugin(plugin_id: str):
    """手动运行脚本插件（Base Editor 及以上，以触发者身份代理执行）

    ---
    tags:
      - Plugins
    security:
      - Bearer: []
    parameters:
      - name: plugin_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        schema:
          type: object
          required: [base_id]
          properties:
            base_id:
              type: string
    responses:
      200:
        description: 运行结果
    """
    data = request.get_json(silent=True) or {}
    base_id = data.get('base_id')
    if not base_id:
        return error_response('base_id_required', 400)
    if not PermissionService.check_permission(
            str(base_id), str(g.current_user_id), MemberRole.EDITOR):
        return forbidden_response('no_permission_run_plugin')

    plugin = Plugin.query.filter_by(id=plugin_id).first()
    if plugin is None:
        return not_found_response('plugin_not_found')
    if plugin.type != PluginType.SCRIPT:
        return error_response('plugin_not_script_type', 400)
    if plugin.status != PluginStatus.ENABLED:
        return forbidden_response('plugin_not_enabled')

    from app.services.plugin_script_service import PluginScriptService
    result = PluginScriptService.run(plugin, base_id, str(g.current_user_id))
    return success_response(result)


@plugins_bp.route('/plugins/<string:plugin_id>/run-logs', methods=['GET'])
@jwt_required
def get_run_logs(plugin_id: str):
    """查询脚本插件运行日志（Base Owner/Admin）

    ---
    tags:
      - Plugins
    security:
      - Bearer: []
    parameters:
      - name: plugin_id
        in: path
        type: string
        required: true
      - name: base_id
        in: query
        type: string
        required: true
      - name: page
        in: query
        type: integer
        required: false
      - name: per_page
        in: query
        type: integer
        required: false
    responses:
      200:
        description: 运行日志列表
    """
    base_id = request.args.get('base_id')
    if not base_id:
        return error_response('base_id_required', 400)
    if not _check_base_admin(base_id):
        return forbidden_response('no_permission_access_base')

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    query = PluginRunLog.query.filter_by(
        plugin_id=plugin_id, base_id=base_id).order_by(
        PluginRunLog.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return paginated_response(
        [r.to_dict() for r in pagination.items],
        pagination.total, page, per_page)
