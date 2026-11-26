"""
SmartTable Flask 应用工厂模块 — Swagger 部分

API_DOCUMENTATION 和 HTML_TEMPLATE 已移至子文件以绕过 PyArmor 32KB 限制。
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

from ._swagger_spec import API_DOCUMENTATION
from ._swagger_html import HTML_TEMPLATE


def register_api_docs(app):
    """
    注册 API 文档路由

    Args:
        app: Flask 应用实例
    """

    @app.route('/api/', methods=['GET'])
    def api_docs():
        """API 文档 HTML 页面"""
        return render_template_string(HTML_TEMPLATE, **API_DOCUMENTATION)

    @app.route('/api/docs.json', methods=['GET'])
    def api_docs_json():
        """API 文档 JSON 格式"""
        return jsonify(API_DOCUMENTATION)


def init_swagger(app):
    """
    初始化 Flasgger Swagger
    
    Args:
        app: Flask 应用实例
    """
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec_1",
                "route": "/apispec_1.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/apidocs/",
    }

    # 定义标签分组顺序和描述
    swagger_tags = [
        {"name": "Auth", "description": "用户认证相关接口（登录、注册、密码重置等）"},
        {"name": "Auth Captcha", "description": "验证码相关接口"},
        {"name": "Bases", "description": "数据基础（Base）管理接口"},
        {"name": "Tables", "description": "表格管理接口"},
        {"name": "Fields", "description": "字段管理接口"},
        {"name": "Geo", "description": "地理位置数据接口（行政区划、国家和地区、地图配置）"},
        {"name": "Records", "description": "记录（数据行）管理接口"},
        {"name": "Views", "description": "视图管理接口"},
        {"name": "Dashboards", "description": "仪表盘管理接口"},
        {"name": "Dashboards Share", "description": "仪表盘分享接口"},
        {"name": "Workflows", "description": "工作流管理接口"},
        {"name": "Workflow Templates", "description": "工作流模板接口"},
        {"name": "Approvals", "description": "工作流审批任务接口"},
        {"name": "ApprovalFlows", "description": "审批流配置与执行接口"},
        {"name": "Attachments", "description": "附件上传下载接口"},
        {"name": "Import/Export", "description": "数据导入导出接口"},
        {"name": "Shares", "description": "基础数据分享接口"},
        {"name": "Form Shares", "description": "表单分享接口"},
        {"name": "Admin", "description": "管理员接口（用户管理、系统设置等）"},
        {"name": "Email", "description": "邮件服务管理接口"},
        {"name": "Notifications", "description": "站内信通知管理接口"},
        {"name": "Realtime", "description": "实时协作状态接口"},
        {"name": "Plugins", "description": "插件管理接口（安装/升级/回滚/生命周期/配置/运行）"},
        {"name": "Print Templates", "description": "打印模板接口（CRUD/可见性过滤/共享权限）"},
    ]
    
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "SmartTable API",
            "description": "SmartTable 数据管理系统 RESTful API 文档",
            "version": "1.0.0",
            "contact": {
                "name": "SmartTable Team",
            },
        },
        "basePath": "/api",
        "schemes": ["http", "https"],
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Token 认证，格式：Bearer <token>",
            }
        },
        "tags": swagger_tags,
    }

    # 设置 Flasgger UI 配置
    app.config['SWAGGER'] = {
        'title': 'SmartTable API',
        'uiversion': 3,
        'specs_route': '/apidocs/',
        'doc_expansion': 'none',  # 默认收起所有分组
        'auth': {},  # 避免 None 错误
        'ui_params': {
            'showCommonExtensions': True,
            'showExtensions': True,
        },
        # 在页面顶部显示联系信息
        'top_text': '<div style="position: absolute;right:0; margin-top: 60px;padding: 10px 20px; background: #f5f5f5; border-bottom: 1px solid #ddd; font-size: 14px; color: #666;"><strong>Contact：</strong> &nbsp;GitHub <a href="https://github.com/ldbinac/smart_table.git" target="_blank" rel="noopener noreferrer" title="GitHub" style="padding-left: 0px; "><svg style="with:24px;height:24px;" viewBox="0 0 24 24" fill="currentColor" data-v-fa254d35=""><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" data-v-fa254d35=""></path></svg></a></div>',
    }

    Swagger(app, config=swagger_config, template=swagger_template)
