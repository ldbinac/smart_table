# Auto-split from plugins.py

"""子蓝图模块"""

from app.routes.plugin import plugins_bp
from app.services.plugin_service import PluginValidationError, PluginNotFoundError


def _sign(payload: str) -> str:
    from flask import current_app
    key = current_app.config.get('SECRET_KEY', '') or ''
    return hmac.new(key.encode('utf-8'), payload.encode('utf-8'),
                    hashlib.sha256).hexdigest()

def _verify_any_token(token: str, plugin_id: str, version: str) -> bool:
    """文件静态服务令牌：沙箱令牌或文件令牌任一有效即可"""
    return verify_sandbox_token(token, plugin_id, version) or verify_file_token(token, plugin_id, version)

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

def generate_file_token(plugin_id: str, version: str) -> str:
    """生成包内静态资源文件令牌（较长 TTL，供 loader 内 CSS/图片/额外 JS 引用）"""
    exp = int(time.time()) + FILE_TOKEN_TTL
    payload = f'{plugin_id}|{version}|file|{exp}'
    return f'{exp}.{_sign(payload)}'

def verify_file_token(token: str, plugin_id: str, version: str) -> bool:
    try:
        exp_str, sig = token.split('.', 1)
        exp = int(exp_str)
    except (ValueError, AttributeError):
        return False
    if exp < int(time.time()):
        return False
    return hmac.compare_digest(_sign(f'{plugin_id}|{version}|file|{exp}'), sig)

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
        return _plugin_validation_error(e)
    except Exception:
        log.exception('[plugins] 安装包处理失败')
        return error_response('plugin_install_failed', 500)

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
        return _plugin_validation_error(e)

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
        return _plugin_validation_error(e)

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
