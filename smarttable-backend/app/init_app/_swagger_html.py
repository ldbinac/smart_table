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

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ name }} - API 文档</title>
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        line-height: 1.6;
        color: #333;
        background: #f5f5f5;
    }
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }
    .header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 40px;
        border-radius: 10px;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .header h1 {
        font-size: 2.5em;
        margin-bottom: 10px;
    }
    .header .version {
        display: inline-block;
        background: rgba(255,255,255,0.2);
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.9em;
        margin-left: 10px;
    }
    .header p {
        margin-top: 15px;
        opacity: 0.9;
        font-size: 1.1em;
    }
    .section {
        background: white;
        padding: 25px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .section h2 {
        color: #667eea;
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 2px solid #f0f0f0;
    }
    .auth-box {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    .auth-box h3 {
        margin-bottom: 10px;
        color: #333;
    }
    .endpoint-group {
        margin-bottom: 30px;
    }
    .endpoint-group h3 {
        color: #333;
        margin-bottom: 15px;
        font-size: 1.2em;
    }
    .endpoint-group .prefix {
        color: #666;
        font-size: 0.9em;
        margin-bottom: 10px;
    }
    .route {
        display: flex;
        align-items: center;
        padding: 12px 15px;
        margin-bottom: 8px;
        background: #f8f9fa;
        border-radius: 6px;
        transition: background 0.2s;
    }
    .route:hover {
        background: #e9ecef;
    }
    .method {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.75em;
        font-weight: bold;
        margin-right: 15px;
        min-width: 60px;
        text-align: center;
    }
    .method.GET { background: #61affe; color: white; }
    .method.POST { background: #49cc90; color: white; }
    .method.PUT { background: #fca130; color: white; }
    .method.DELETE { background: #f93e3e; color: white; }
    .method.PATCH { background: #50e3c2; color: white; }
    .path {
        font-family: "Consolas", "Monaco", monospace;
        color: #333;
        margin-right: 15px;
        font-size: 0.95em;
    }
    .description {
        color: #666;
        font-size: 0.9em;
    }
    .field-types {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 15px;
    }
    .field-type {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 3px solid #667eea;
    }
    .field-type .type-name {
        font-weight: bold;
        color: #333;
        margin-bottom: 5px;
    }
    .field-type .type-code {
        font-family: monospace;
        color: #667eea;
        font-size: 0.85em;
        margin-bottom: 5px;
    }
    .field-type .type-desc {
        color: #666;
        font-size: 0.9em;
    }
    .response-codes {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 10px;
    }
    .response-code {
        display: flex;
        align-items: center;
        padding: 10px 15px;
        background: #f8f9fa;
        border-radius: 6px;
    }
    .response-code .code {
        font-weight: bold;
        margin-right: 10px;
        min-width: 40px;
    }
    .response-code .code.success { color: #49cc90; }
    .response-code .code.error { color: #f93e3e; }
    .response-code .code.warning { color: #fca130; }
    .footer {
        text-align: center;
        padding: 30px;
        color: #666;
        font-size: 0.9em;
    }
    .json-link {
        display: inline-block;
        margin-top: 10px;
        padding: 10px 20px;
        background: #667eea;
        color: white;
        text-decoration: none;
        border-radius: 5px;
        transition: background 0.2s;
    }
    .json-link:hover {
        background: #5568d3;
    }
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>{{ name }} <span class="version">v{{ version }}</span></h1>
        <p>{{ description }}</p>
        <a href="/api/docs.json" class="json-link">查看 JSON 格式</a>
    </div>

    <div class="section">
        <h2>🔐 认证方式</h2>
        <div class="auth-box">
            <h3>JWT Token 认证</h3>
            <p><strong>Header:</strong> <code>Authorization: Bearer &lt;token&gt;</code></p>
            <p style="margin-top: 10px;">{{ authentication.description }}</p>
        </div>
    </div>

    <div class="section">
        <h2>📚 API 端点</h2>
        {% for group_name, group in endpoints.items() %}
        <div class="endpoint-group">
            <h3>{{ group_name }}</h3>
            <div class="prefix">前缀: {{ group.prefix }}</div>
            {% for route in group.routes %}
            <div class="route">
                <span class="method {{ route.method }}">{{ route.method }}</span>
                <span class="path">{{ route.path }}</span>
                <span class="description">{{ route.description }}</span>
            </div>
            {% endfor %}
        </div>
        {% endfor %}
    </div>

    <div class="section">
        <h2>📝 字段类型</h2>
        <div class="field-types">
            {% for ft in field_types %}
            <div class="field-type">
                <div class="type-name">{{ ft.name }}</div>
                <div class="type-code">{{ ft.type }}</div>
                <div class="type-desc">{{ ft.description }}</div>
            </div>
            {% endfor %}
        </div>
    </div>

    <div class="section">
        <h2>📊 响应状态码</h2>
        <div class="response-codes">
            {% for code, desc in response_codes.items() %}
            <div class="response-code">
                <span class="code {% if code|int < 300 %}success{% elif code|int < 400 %}warning{% else %}error{% endif %}">{{ code }}</span>
                <span>{{ desc }}</span>
            </div>
            {% endfor %}
        </div>
    </div>

    <div class="footer">
        <p>SmartTable API Documentation &copy; 2024</p>
    </div>
</div>
</body>
</html>
'''
