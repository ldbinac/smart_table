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

def register_health_check(app):
    """
    注册健康检查端点

    Args:
        app: Flask 应用实例
    """
    @app.route('/api/health')
    def health_check():
        """健康检查接口，返回服务状态和当前时间"""
        from datetime import datetime
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'smarttable'
        })

def register_lifecycle_hooks(app):
    """
    注册应用生命周期钩子

    Args:
        app: Flask 应用实例
    """
    # 使用 before_request 配合标志位实现 before_first_request 功能
    # 因为 Flask 2.3+ 已移除 before_first_request
    _first_request_initialized = False

    @app.before_request
    def generate_request_id():
        """为每个请求生成唯一 ID"""
        g.request_id = str(uuid.uuid4())

    @app.before_request
    def parse_language():
        """解析 Accept-Language header，设置当前请求语言到 g.language"""
        accept_lang = request.headers.get('Accept-Language', '')
        lang = parse_accept_language(accept_lang)
        set_current_language(lang)

    @app.before_request
    def init_services():
        """应用首次请求时初始化服务"""
        nonlocal _first_request_initialized
        if not _first_request_initialized:
            _first_request_initialized = True
            init_email_queue(app)
            WebhookService.start_retry_scheduler(app)
            # 应用退出时才停止重试调度线程，避免每次请求 teardown 误停
            import atexit
            atexit.register(WebhookService.stop_retry_scheduler)

            # 启动工作流定时调度器并加载所有 active 的指定时间任务
            from app.services.workflow_scheduler_service import start_scheduler, stop_scheduler, reschedule_all
            start_scheduler(app)
            reschedule_all(app)
            atexit.register(stop_scheduler)

            # 启动工作流记录时间扫描器
            from app.services.workflow_record_time_scanner import start_scanner, stop_scanner as stop_record_time_scanner
            start_scanner(app)
            atexit.register(stop_record_time_scanner)

def register_error_handlers(app):
    """
    注册错误处理器

    Args:
        app: Flask 应用实例
    """
    register_handlers(app)

def register_shell_context(app):
    """
    注册 Flask Shell 上下文
    
    Args:
        app: Flask 应用实例
    """
    @app.shell_context_processor
    def make_shell_context():
        """为 Flask Shell 提供上下文"""
        return {
            'db': db,
            'User': User,
            'Base': Base,
            'BaseMember': BaseMember,
            'Table': Table,
            'Field': Field,
            'Record': Record,
            'View': View,
            'Dashboard': Dashboard,
            'Attachment': Attachment
        }

def register_socketio_handlers(app):
    _register_socketio(socketio, app)
