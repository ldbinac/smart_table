"""
路由模块初始化
提供应用相关蓝图的统一注册入口
"""
from flask import Flask


def register_application_blueprints(app: Flask) -> None:
    """
    注册应用模式相关蓝图

    包含：
    - applications_bp：应用主路由（CRUD/菜单/页面/组件/权限/发布/模板）
    - application_auth_bp：应用独立认证路由（login/logout/session/guest）

    两个蓝图均挂载在 /api/applications URL 前缀下：
    - 应用管理：/api/applications/...
    - 应用认证：/api/applications/<app_id>/auth/...

    Args:
        app: Flask 应用实例
    """
    try:
        from app.routes.applications import applications_bp
    except ImportError:
        applications_bp = None
    try:
        from app.routes.application_auth import application_auth_bp
    except ImportError:
        application_auth_bp = None

    # 应用主蓝图：处理应用 CRUD 及子资源
    if applications_bp:
        app.register_blueprint(applications_bp, url_prefix='/api/applications')

    # 应用独立认证蓝图：与应用主蓝图共用前缀，但路由路径不冲突
    # （application_auth_bp 的所有路由均以 /<app_id>/auth/ 开头）
    if application_auth_bp:
        app.register_blueprint(application_auth_bp, url_prefix='/api/applications')
