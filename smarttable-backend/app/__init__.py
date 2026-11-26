# Auto-split skeleton

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

from app.init_app import register_blueprints, register_api_docs, init_swagger, register_health_check, register_lifecycle_hooks, register_error_handlers, register_shell_context, register_socketio_handlers

def create_app(config_name='default', enable_realtime=False):
    """
    应用工厂函数

    Args:
        config_name: 配置名称，可选值：development, testing, production, default
        enable_realtime: 是否启用实时协作功能

    Returns:
        Flask 应用实例
    """
    app = Flask(__name__)

    # 禁用严格斜杠，避免 308 重定向
    app.url_map.strict_slashes = False

    # 加载配置
    app.config.from_object(config[config_name])

    # 调用配置类的 init_app 方法（初始化日志、校验等）
    config_class = config.get(config_name)
    if hasattr(config_class, 'init_app') and callable(config_class.init_app):
        config_class.init_app(app)

    # 设置实时协作配置
    app.config['REALTIME_ENABLED'] = enable_realtime
    
    # 初始化扩展
    init_extensions(app)

    # 初始化工作流执行引擎，确保后台事件处理在 Flask 应用上下文中运行
    init_workflow_execution_engine(app)

    # RAG 增量索引订阅工作流事件总线（P2-3，E1：记录变更 → 记录级重建块）
    try:
        from app.services.ai.rag_index_service import init_rag_index
    except ImportError:
        init_rag_index = None
    if init_rag_index:
        init_rag_index(app)

    # AI 字段自动刷新订阅工作流事件总线（B8：记录变更 → auto 字段防抖重生成）
    try:
        from app.services.ai.ai_field_service import init_ai_field_auto_refresh
    except ImportError:
        init_ai_field_auto_refresh = None
    if init_ai_field_auto_refresh:
        init_ai_field_auto_refresh(app)

    # 条件初始化 SocketIO 事件处理器
    if app.config.get('REALTIME_ENABLED', False):
        register_socketio_handlers(app)
    
    # 注册蓝图
    register_blueprints(app)

    # 注册可选集成（泛微 E10 OAuth2 单点登录）
    register_e10_integration(app)

    # 注册 API 文档路由
    register_api_docs(app)

    # 初始化 Flasgger Swagger
    init_swagger(app)

    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册 Shell 上下文
    register_shell_context(app)
    
    # 邮件模板 / 工作流模板初始化
    # 不在此处调 db.create_all()——那会先于 run_migrations 建表，
    # 导致 Alembic upgrade 过程中 batch_alter_table(recreate) 操作
    # 因 SQLite WAL 模式 + 空中间表而清空核心业务表数据（tables/records/fields/views）。
    # 表结构初始化和升级统一由 run.py 的 run_migrations() 负责。
    with app.app_context():
        try:
            init_default_email_templates()
            init_default_workflow_templates()
        except Exception as e:
            # 表可能尚未由 run_migrations 创建，忽略"no such table"等启动期错误
            # run_migrations 之后的下一次启动会正常执行
            print(f"[{config_name}] 邮件/工作流模板初始化跳过（数据库可能尚未就绪）: {e}")

    # 注册健康检查端点
    register_health_check(app)

    # 注册应用生命周期钩子
    register_lifecycle_hooks(app)

    # 打包模式：配置前端静态文件托管（如果尚未配置）
    # 注意：在 run.py 中也会调用 configure_static_serving，这里作为备用
    if not hasattr(app, '_static_serving_configured'):
        try:
            if configure_static_serving(app):
                app._static_serving_configured = True
        except Exception as e:
            print(f"[Warning] Failed to configure static serving: {e}")

    return app

