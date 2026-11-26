"""
SmartTable Flask 应用工厂模块
"""

import uuid

from flask import Flask, jsonify, render_template_string, g, request

from flasgger import Swagger

from app.extensions import init_extensions, db

from app.config import config

from app.routes.auth import auth_bp

from app.routes.bases import bases_bp

from app.routes.tables import tables_bp

from app.routes.fields import fields_bp

from app.routes.records import records_bp

from app.routes.views import views_bp

from app.routes.dashboards import dashboards_bp

from app.routes.dashboards_share import dashboards_share_bp

from app.routes.attachments import attachments_bp

from app.routes.import_export import import_export_bp

from app.routes.admin import admin_bp

try:
    from app.routes.ai_models import ai_admin_bp
except ImportError:
    ai_admin_bp = None

try:
    from app.routes.ai_field import ai_field_bp
except ImportError:
    ai_field_bp = None

try:
    from app.routes.ai_chat import ai_chat_bp
except ImportError:
    ai_chat_bp = None

try:
    from app.routes.ai_rag import ai_rag_bp
except ImportError:
    ai_rag_bp = None

try:
    from app.routes.ai_insight import ai_insight_bp
except ImportError:
    ai_insight_bp = None

try:
    from app.routes.ai_doc import ai_doc_bp
except ImportError:
    ai_doc_bp = None

try:
    from app.routes.ai_poc import ai_poc_bp
except ImportError:
    ai_poc_bp = None

from app.routes.shares import shares_bp

from app.routes.table_shares import table_shares_bp

from app.routes.form_shares import form_shares_bp

from app.routes.auth_captcha import auth_captcha_bp

from app.routes.email import email_bp

from app.routes.notifications import notifications_bp

from app.routes.realtime import realtime_bp

from app.routes.users import users_bp

from app.routes.documents import documents_bp

from app.routes.document_versions import document_versions_bp

from app.routes.approvals import approvals_bp

try:
    from app.routes.approval_flows import approval_flows_bp
except ImportError:
    approval_flows_bp = None

from app.routes.webhooks import webhooks_bp

from app.routes.workflow_templates import workflow_templates_bp

from app.routes.workflows import workflows_bp

from app.routes.config import config_bp

from app.routes.lookup import lookup_bp

from app.routes import register_application_blueprints

from app.routes.geo import geo_bp

try:
    from app.routes.roles import roles_bp
except ImportError:
    roles_bp = None

try:
    from app.routes.permission_groups import permission_groups_bp
except ImportError:
    permission_groups_bp = None

try:
    from app.routes.permission_assignments import permission_assignments_bp
except ImportError:
    permission_assignments_bp = None

try:
    from app.routes.data_conditions import data_conditions_bp
except ImportError:
    data_conditions_bp = None

from app.routes.oauth import oauth_bp

from app.routes.open_api import open_api_bp

from app.routes.plugins import plugins_bp

try:
    from app.routes.print_templates import print_templates_bp
except ImportError:
    print_templates_bp = None

from app.integrations.e10 import register_e10_integration

from app.integrations.e10 import register_e10_integration

from app.integrations.e10 import register_e10_integration

from app.services.email_queue_service import init_email_queue

from app.services.webhook_service import WebhookService

from app.utils.init_email_templates import init_default_email_templates

from app.services.workflow_template_service import init_default_templates as init_default_workflow_templates

from app.services.workflow_execution_engine import init_workflow_execution_engine

from app.static_serving import configure_static_serving

from app.errors.handlers import register_handlers

from app.i18n.utils import parse_accept_language, set_current_language

from app.models import (
    User, Base, BaseMember, Table, Field,
    Record, View, Dashboard, Attachment
)

from app.extensions import socketio

from app.routes.socketio_events import register_socketio_handlers as _register_socketio

def register_blueprints(app):
    """
    注册 Flask 蓝图

    Args:
        app: Flask 应用实例
    """
    # 注册认证蓝图
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    # 注册认证验证码蓝图
    app.register_blueprint(auth_captcha_bp, url_prefix='/api')

    # 注册基础数据蓝图
    app.register_blueprint(bases_bp, url_prefix='/api/bases')

    # 注册表格蓝图 (路由中已包含完整路径)
    app.register_blueprint(tables_bp, url_prefix='/api')

    # 注册字段蓝图 (路由中已包含完整路径)
    app.register_blueprint(fields_bp, url_prefix='/api')

    # 注册记录蓝图 (路由中已包含完整路径)
    app.register_blueprint(records_bp, url_prefix='/api')

    # 注册视图蓝图 (路由中已包含完整路径)
    app.register_blueprint(views_bp, url_prefix='/api')

    # 注册仪表盘蓝图 (路由中已包含完整路径)
    app.register_blueprint(dashboards_bp, url_prefix='/api')

    # 注册仪表盘分享蓝图 (路由中已包含完整路径)
    app.register_blueprint(dashboards_share_bp, url_prefix='/api')

    # 注册附件蓝图
    app.register_blueprint(attachments_bp, url_prefix='/api/attachments')

    # 注册导入导出蓝图
    app.register_blueprint(import_export_bp, url_prefix='/api')

    # 注册管理员蓝图
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    # 注册 AI 模型配置管理蓝图（A 域：A1-A5）
    if ai_admin_bp:
        app.register_blueprint(ai_admin_bp, url_prefix='/api/admin/ai')
    if ai_field_bp:
        app.register_blueprint(ai_field_bp, url_prefix='/api')
    if ai_chat_bp:
        app.register_blueprint(ai_chat_bp, url_prefix='/api')
    # AI 用量/调用日志/任务列表（A6/A9/B9）
    try:
        from app.routes.ai_usage import ai_usage_bp
    except ImportError:
        ai_usage_bp = None
    if ai_usage_bp:
        app.register_blueprint(ai_usage_bp, url_prefix='/api')
    # TinyRobot PoC mock 端点（P0-7 验证用，无模型/DB 副作用）
    # P1 修复：生产环境默认不注册（无功能开关/RBAC，仅限 PoC 验证场景）；
    # 需要时显式设置环境变量 ENABLE_AI_POC=1 开启
    import os as _os
    if _os.environ.get('ENABLE_AI_POC') == '1' or app.config.get('ENABLE_AI_POC'):
        app.register_blueprint(ai_poc_bp, url_prefix='/api')
    # RAG 索引管理（P2-5，E1 管理面板）
    if ai_rag_bp:
        app.register_blueprint(ai_rag_bp, url_prefix='/api')
    # 仪表盘智能洞察（P2-6，F1-F3）
    if ai_insight_bp:
        app.register_blueprint(ai_insight_bp, url_prefix='/api')
    # 文档 AI（P2-7，G1-G2）
    if ai_doc_bp:
        app.register_blueprint(ai_doc_bp, url_prefix='/api')

    # 注册邮件服务蓝图
    app.register_blueprint(email_bp, url_prefix='/api/admin/email')

    # 注册站内信通知蓝图
    app.register_blueprint(notifications_bp, url_prefix='/api')

    # 注册分享蓝图
    app.register_blueprint(shares_bp, url_prefix='/api')

    # 注册数据表分享蓝图 (路由中已包含完整路径)
    app.register_blueprint(table_shares_bp, url_prefix='/api')

    # 注册表单分享蓝图 (路由中已包含完整路径)
    app.register_blueprint(form_shares_bp, url_prefix='/api')

    # 注册实时协作蓝图
    app.register_blueprint(realtime_bp, url_prefix='/api')

    # 注册用户管理蓝图
    app.register_blueprint(users_bp, url_prefix='/api')

    # 注册文档蓝图 (路由中已包含完整路径)
    app.register_blueprint(documents_bp, url_prefix='/api')

    # 注册文档版本历史蓝图
    app.register_blueprint(document_versions_bp, url_prefix='/api')

    # 注册审批蓝图 (路由中已包含完整路径)
    app.register_blueprint(approvals_bp, url_prefix='/api')

    # 注册审批流蓝图 (路由中已包含完整路径)
    if approval_flows_bp:
        app.register_blueprint(approval_flows_bp, url_prefix='/api')

    # 注册 Webhook 蓝图
    app.register_blueprint(webhooks_bp, url_prefix='/api')

    # 注册工作流模板蓝图
    app.register_blueprint(workflow_templates_bp, url_prefix='/api/workflow-templates')

    # 注册工作流蓝图（路由中已包含完整路径）
    app.register_blueprint(workflows_bp, url_prefix='/api')

    # 注册公开配置蓝图
    app.register_blueprint(config_bp, url_prefix='/api/config')

    # 注册查找字段蓝图
    app.register_blueprint(lookup_bp, url_prefix='/api')

    # 注册地理位置数据蓝图（行政区划 / 国家和地区 / 地图配置）
    app.register_blueprint(geo_bp, url_prefix='/api')

    # 注册自定义角色蓝图
    if roles_bp:
        app.register_blueprint(roles_bp, url_prefix='/api')

    # 注册权限规则组蓝图 (路由中已包含完整路径)
    if permission_groups_bp:
        app.register_blueprint(permission_groups_bp, url_prefix='/api')

    # 注册权限分配蓝图 (路由中已包含完整路径)
    if permission_assignments_bp:
        app.register_blueprint(permission_assignments_bp, url_prefix='/api')

    # 注册数据权限条件蓝图 (路由中已包含完整路径)
    if data_conditions_bp:
        app.register_blueprint(data_conditions_bp, url_prefix='/api')

    # 注册 OAuth2 第三方应用接入蓝图（url_prefix 已在 oauth.py 中定义为 /api/oauth）
    app.register_blueprint(oauth_bp)

    # 注册开放 API 蓝图（第三方应用以应用身份访问数据）
    app.register_blueprint(open_api_bp)

    # 注册插件蓝图（插件管理 API + 沙箱静态服务）
    app.register_blueprint(plugins_bp, url_prefix='/api')

    # 注册打印模板蓝图 (路由中已包含完整路径)
    if print_templates_bp:
        app.register_blueprint(print_templates_bp, url_prefix='/api')

    # 注册应用模式蓝图（应用管理 + 应用独立认证）
    register_application_blueprints(app)
