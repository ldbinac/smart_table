# Auto-split from plugins.py

"""子蓝图模块"""

from flask import Response
from app.routes.plugin import plugins_bp
from app.services.plugin_service import PluginValidationError, PluginNotFoundError


def _plugin_validation_error(e: PluginValidationError) -> Response:
    """插件校验失败统一响应

    PluginValidationError.detail 为 i18n key（含 {占位符}），此处按当前请求
    语言渲染并插值；未命中词条时 translate 原样返回，兼容硬编码文案。
    """
    detail = translate(e.detail, **(e.params or {})) if e.detail else e.error_code
    return error_response(
        message=detail,
        code=400,
        error=e.error_code,
        details=([{'error_code': e.error_code, 'detail': detail}]
                 if detail else None),
    )

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
    base_id = data.get('base_id') or None

    # base_id 可选：缺省时按全局作用域处理（如首页菜单插件，无 Base 上下文）
    if base_id:
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
    # Base 级有效启用检查（全局作用域插件无需 Base 安装）
    if base_id:
        from app.models.plugin import PluginInstallation
        inst = PluginInstallation.query.filter_by(
            plugin_id=plugin_id, base_id=base_id, enabled=True).first()
        if inst is None:
            return forbidden_response('plugin_not_enabled_in_base')

    version = plugin.current_version
    st = generate_sandbox_token(plugin_id, version)
    fst = generate_file_token(plugin_id, version)
    url = f'/api/plugins/{plugin_id}/versions/{version}/loader.html?st={st}&fst={fst}'
    return success_response({'url': url, 'version': version, 'fst': fst})

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
        manifest = plugin.manifest or {}
        entry = manifest.get('entry', '')

        # 包内静态资源令牌（较长 TTL），供 loader 内 CSS/图片/额外 JS 引用
        fst = generate_file_token(plugin_id, version)

        # 按 manifest.assets 声明注入 <link>/<script>（在入口前加载）
        assets = manifest.get('assets') or {}
        asset_parts = []
        for css in (assets.get('styles') or []):
            asset_parts.append(
                f'<link rel="stylesheet" href="files/{css}?fst={fst}">')
        for js in (assets.get('scripts') or []):
            asset_parts.append(
                f'<script src="files/{js}?fst={fst}"></script>')
        assets_html = '\n'.join(asset_parts)

        # 动态 CSP：依据 network 白名单放行声明的第三方 CDN 域；
        # 宿主资源用 request 来源显式声明（沙箱 opaque origin 下 'self' 无法匹配）
        origin = request.host_url.rstrip('/')
        cdn = (manifest.get('permissions') or {}).get('network') or []
        sources = [origin] + [str(d) for d in cdn if d]
        csp = (
            "default-src 'none'; "
            # 内联 SDK（握手/client）需 'unsafe-inline'；
            # 由同源签名 URL 鉴权 + sandbox="allow-scripts" 隔离，风险可控
            f"script-src 'unsafe-inline' 'unsafe-eval' {' '.join(sources)}; "
            f"style-src 'unsafe-inline' {' '.join(sources)}; "
            f"img-src {origin} data: blob: {' '.join(sources)}; "
            f"font-src {origin} data:; "
            f"connect-src {' '.join(sources)}; "
            "frame-src 'self';"
        )

        html = _LOADER_TEMPLATE.format(
            plugin_id_json=json.dumps(plugin_id),
            version_json=json.dumps(version),
            fst=fst,
            st=st,
            entry=entry,
            assets_html=assets_html,
        )
        resp = Response(html, mimetype='text/html; charset=utf-8')
        resp.headers['Content-Security-Policy'] = csp
        return resp
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')
    except Exception:
        log.exception('[plugins] loader 生成失败 %s@%s', plugin_id, version)
        return error_response('plugin_loader_error', 500)

def plugin_vendor_asset(filename: str, plugin_id: str = '', version: str = ''):
    """沙箱内可用的前端运行时资源（宿主自带，非插件包内容）

    与 `/files/<path>`（插件包静态文件，需签名）不同，vendor 资源：
    - 同源提供，不依赖外网/CDN，离线环境可用；
    - 文件名白名单 + send_from_directory 双重防路径穿越。
    """
    name = Path(filename).name
    if name not in _VENDOR_ALLOWED or not (_VENDOR_DIR / name).is_file():
        return not_found_response('plugin_vendor_not_found')
    resp = send_from_directory(str(_VENDOR_DIR), name)
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp

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
    st = request.args.get('st', '') or request.args.get('fst', '')
    if not _verify_any_token(st, plugin_id, version):
        return forbidden_response('plugin_sandbox_token_invalid')

    try:
        package_dir = PluginService.get_package_dir(plugin_id, version)
    except PluginNotFoundError:
        return not_found_response('plugin_not_found')

    # send_from_directory 自带路径穿越防护
    return send_from_directory(str(package_dir), filename)

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

def call_plugin_endpoint(plugin_id: str, endpoint: str):
    """调用插件自定义后端接口（endpoint 模式，经受限沙箱执行）

    鉴权：触发者对 base_id 的 RBAC（Editor+，与 run 一致）+ 插件全局启用；
    UI 插件还需该 Base 已安装并启用（与前端 UI 可见性一致）。
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
    if plugin.status != PluginStatus.ENABLED:
        return forbidden_response('plugin_not_enabled')

    # UI 插件要求该 Base 已安装并启用（与前端 UI 入口可见性一致）
    if plugin.type == PluginType.UI:
        inst = PluginInstallation.query.filter_by(
            plugin_id=plugin_id, base_id=base_id, enabled=True).first()
        if inst is None:
            return forbidden_response('plugin_not_enabled_in_base')

    # 接口必须已在 manifest.endpoints 声明
    endpoints = (plugin.manifest or {}).get('endpoints') or []
    if not any((e.get('name') == endpoint) for e in endpoints):
        return not_found_response('plugin_endpoint_not_found')

    from app.services.plugin_script_service import PluginScriptService
    payload = data.get('payload')
    result = PluginScriptService.call_endpoint(
        plugin, endpoint, payload, str(base_id), str(g.current_user_id))
    return success_response(result)

def proxy_plugin_request(plugin_id: str):
    """插件第三方后端代理（宿主转发，按 manifest network 白名单 + SSRF 防护）

    鉴权：Base 成员（Editor+，与 endpoints/run 一致）+ 插件全局启用；
    UI 插件还需该 Base 已安装并启用。目标域名必须落在插件
    permissions.network 白名单内。
    """
    data = request.get_json(silent=True) or {}
    base_id = data.get('base_id')
    target_url = data.get('url')
    if not base_id:
        return error_response('base_id_required', 400)
    if not target_url:
        return error_response('proxy_url_required', 400)

    if not PermissionService.check_permission(
            str(base_id), str(g.current_user_id), MemberRole.EDITOR):
        return forbidden_response('no_permission_run_plugin')

    plugin = Plugin.query.filter_by(id=plugin_id).first()
    if plugin is None:
        return not_found_response('plugin_not_found')
    if plugin.status != PluginStatus.ENABLED:
        return forbidden_response('plugin_not_enabled')

    if plugin.type == PluginType.UI:
        inst = PluginInstallation.query.filter_by(
            plugin_id=plugin_id, base_id=base_id, enabled=True).first()
        if inst is None:
            return forbidden_response('plugin_not_enabled_in_base')

    if not ((plugin.manifest or {}).get('permissions') or {}).get('network'):
        return forbidden_response('plugin_network_not_declared')

    from app.services import plugin_proxy_service
    try:
        result = plugin_proxy_service.proxy(
            plugin_id=str(plugin_id),
            manifest=plugin.manifest or {},
            url=str(target_url),
            method=data.get('method', 'GET'),
            headers=data.get('headers') or {},
            body=data.get('body'),
        )
    except plugin_proxy_service.ProxyError as e:
        # e.message 为 i18n key，按当前语言渲染（含参数插值）
        return error_response(
            translate(e.message, **(e.params or {})), e.http_status, e.error_code)
    return success_response(result)

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
