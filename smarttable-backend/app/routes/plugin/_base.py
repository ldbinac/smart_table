# Auto-split from plugins.py

"""子蓝图模块"""

from app.routes.plugin import plugins_bp
from app.services.plugin_service import PluginValidationError, PluginNotFoundError


def _check_base_admin(base_id) -> bool:
    """Base 成员角色鉴权：Admin 及以上（运行日志等管理/审计类读操作）"""
    return PermissionService.check_permission(
        str(base_id), str(g.current_user_id), MemberRole.ADMIN)

def _check_base_owner(base_id) -> bool:
    """Base 级插件管理鉴权：仅多维表格的创建者（所有者）可安装/启停/移除插件

    与调用者在该 Base 的成员角色（admin/editor/...）解耦：系统 Admin 负责
    全局安装并启用插件，Base 创建者自行决定把哪些已启用的插件挂到自己
    创建的 Base 上。

    Args:
        base_id: Base ID（UUID 字符串或 UUID 对象）

    Returns:
        当前登录用户是否为该 Base 的创建者
    """
    try:
        base_uuid = (base_id if isinstance(base_id, uuid.UUID)
                     else uuid.UUID(str(base_id)))
    except (ValueError, AttributeError, TypeError):
        return False
    base = Base.query.filter_by(id=base_uuid).first()
    if base is None:
        return False
    return str(base.owner_id) == str(g.current_user_id)

def _ensure_plugin_globally_enabled(plugin_id: str):
    """校验插件已由系统 Admin 安装并全局启用（Base 级挂载/启用的前置条件）

    Returns:
        (plugin, error_response)：校验通过时 error_response 为 None
    """
    plugin = Plugin.query.filter_by(id=plugin_id).first()
    if plugin is None:
        return None, not_found_response('plugin_not_found')
    if plugin.status != PluginStatus.ENABLED:
        return None, forbidden_response('plugin_not_enabled')
    return plugin, None

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

def install_to_base(plugin_id: str):
    """在 Base 内安装并启用插件（Base 创建者；插件须已由 Admin 全局启用）

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
    if not _check_base_owner(base_id):
        return forbidden_response('no_permission_manage_plugin_in_base')
    # 前置条件：插件须先由系统 Admin 安装并全局启用
    _plugin, err = _ensure_plugin_globally_enabled(plugin_id)
    if err:
        return err
    try:
        result = PluginService.install_to_base(
            plugin_id, base_id, str(g.current_user_id))
        return success_response(result)
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')
    except PluginValidationError as e:
        return _plugin_validation_error(e)

def set_installation_enabled(plugin_id: str):
    """启停插件在 Base 内的启用状态（Base 创建者）

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
    if not _check_base_owner(base_id):
        return forbidden_response('no_permission_manage_plugin_in_base')
    # 重新启用时插件须仍处于全局启用状态（Admin 全局禁用后不允许 Base 内启用）
    if enabled:
        _plugin, err = _ensure_plugin_globally_enabled(plugin_id)
        if err:
            return err
    try:
        result = PluginService.set_base_enabled(plugin_id, base_id, enabled)
        return success_response(result)
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')
    except PluginValidationError as e:
        return _plugin_validation_error(e)

def uninstall_from_base(plugin_id: str):
    """从 Base 移除插件（Base 创建者）

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
    if not _check_base_owner(base_id):
        return forbidden_response('no_permission_manage_plugin_in_base')
    try:
        PluginService.uninstall_from_base(plugin_id, base_id)
        return success_response({'removed': plugin_id})
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')

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

def set_plugin_config(plugin_id: str):
    """写入插件配置（global 级需系统 Admin；base 级需 Base 创建者）

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

    # 权限：global 级需系统 Admin；base 级需 Base 创建者
    is_admin = hasattr(g, 'current_user') and g.current_user is not None \
        and g.current_user.is_admin()
    if scope == 'global':
        if not is_admin:
            return forbidden_response('admin_required_for_global_config')
    else:
        if not _check_base_owner(base_id):
            return forbidden_response('no_permission_manage_plugin_in_base')

    try:
        result = PluginService.set_config(
            plugin_id, scope, base_id, config, str(g.current_user_id))
        return success_response(result)
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')
    except PluginValidationError as e:
        return _plugin_validation_error(e)
