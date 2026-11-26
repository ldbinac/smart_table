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

API_DOCUMENTATION = {
    "name": "SmartTable API",
    "version": "1.0.0",
    "description": "SmartTable 数据管理系统 RESTful API 文档",
    "base_url": "/api",
    "authentication": {
        "type": "JWT",
        "header": "Authorization: Bearer <token>",
        "description": "大部分 API 需要在请求头中携带 JWT Token 进行身份验证"
    },
    "endpoints": {
        "认证模块 (Auth)": {
            "prefix": "/api/auth",
            "routes": [
                {"method": "POST", "path": "/register", "description": "用户注册"},
                {"method": "POST", "path": "/login", "description": "用户登录"},
                {"method": "POST", "path": "/refresh", "description": "刷新访问令牌"},
                {"method": "POST", "path": "/logout", "description": "用户登出"},
                {"method": "POST", "path": "/logout-all", "description": "在所有设备上登出"},
                {"method": "GET", "path": "/me", "description": "获取当前用户信息"},
                {"method": "PUT", "path": "/me", "description": "更新当前用户信息"},
                {"method": "PUT", "path": "/password", "description": "修改密码"},
                {"method": "GET", "path": "/check-email", "description": "检查邮箱是否可用"},
                {"method": "GET", "path": "/verify-token", "description": "验证令牌有效性"},
                {"method": "GET", "path": "/verify-email", "description": "验证邮箱"},
                {"method": "POST", "path": "/resend-verification", "description": "重新发送验证邮件"},
                {"method": "POST", "path": "/forgot-password", "description": "忘记密码"},
                {"method": "POST", "path": "/reset-password", "description": "重置密码"}
            ]
        },
        "验证码模块 (Auth Captcha)": {
            "prefix": "/api",
            "routes": [
                {"method": "GET", "path": "/auth/captcha", "description": "获取验证码"}
            ]
        },
        "数据基础模块 (Bases)": {
            "prefix": "/api/bases",
            "routes": [
                {"method": "GET", "path": "/", "description": "获取所有数据基础"},
                {"method": "POST", "path": "/", "description": "创建数据基础"},
                {"method": "GET", "path": "/<base_id>", "description": "获取数据基础详情"},
                {"method": "PUT", "path": "/<base_id>", "description": "更新数据基础"},
                {"method": "DELETE", "path": "/<base_id>", "description": "删除数据基础"},
                {"method": "POST", "path": "/<base_id>/star", "description": "收藏/取消收藏数据基础"},
                {"method": "GET", "path": "/<base_id>/members", "description": "获取成员列表"},
                {"method": "POST", "path": "/<base_id>/members", "description": "添加成员"},
                {"method": "POST", "path": "/<base_id>/members/batch", "description": "批量添加成员"},
                {"method": "PUT", "path": "/<base_id>/members/<user_id>", "description": "更新成员权限"},
                {"method": "DELETE", "path": "/<base_id>/members/<user_id>", "description": "移除成员"},
                {"method": "POST", "path": "/<base_id>/copy", "description": "复制数据基础"}
            ]
        },
        "表格模块 (Tables)": {
            "prefix": "/api",
            "routes": [
                {"method": "GET", "path": "/bases/<base_id>/tables", "description": "获取表格列表"},
                {"method": "POST", "path": "/bases/<base_id>/tables", "description": "创建表格"},
                {"method": "GET", "path": "/tables/<table_id>", "description": "获取表格详情"},
                {"method": "PUT", "path": "/tables/<table_id>", "description": "更新表格"},
                {"method": "DELETE", "path": "/tables/<table_id>", "description": "删除表格"},
                {"method": "POST", "path": "/bases/<base_id>/tables/reorder", "description": "重新排序表格"},
                {"method": "POST", "path": "/tables/<table_id>/duplicate", "description": "复制表格"}
            ]
        },
        "字段模块 (Fields)": {
            "prefix": "/api",
            "routes": [
                {"method": "GET", "path": "/tables/<table_id>/fields", "description": "获取字段列表"},
                {"method": "POST", "path": "/tables/<table_id>/fields", "description": "创建字段"},
                {"method": "GET", "path": "/fields/<field_id>", "description": "获取字段详情"},
                {"method": "PUT", "path": "/fields/<field_id>", "description": "更新字段"},
                {"method": "DELETE", "path": "/fields/<field_id>", "description": "删除字段"},
                {"method": "POST", "path": "/fields/reorder", "description": "重新排序字段"},
                {"method": "POST", "path": "/fields/<field_id>/duplicate", "description": "复制字段"},
                {"method": "GET", "path": "/fields/types", "description": "获取所有字段类型"},
                {"method": "GET", "path": "/fields/types/<field_type>", "description": "获取字段类型详情"},
                {"method": "POST", "path": "/fields/<field_id>/validate", "description": "验证字段值"},
                {"method": "POST", "path": "/fields/link", "description": "创建关联字段"},
                {"method": "PUT", "path": "/fields/<field_id>/link", "description": "更新关联字段"},
                {"method": "DELETE", "path": "/fields/<field_id>/link", "description": "删除关联字段"},
                {"method": "GET", "path": "/tables/<table_id>/links", "description": "获取表格关联字段"}
            ]
        },
        "地理位置模块 (Geo)": {
            "prefix": "/api",
            "routes": [
                {"method": "GET", "path": "/geo/config", "description": "获取地图服务配置（天地图 Key）"},
                {"method": "GET", "path": "/geo/china-locations", "description": "获取中国省/市/区数据"},
                {"method": "GET", "path": "/geo/regions", "description": "获取国家和地区数据（支持中英文）"}
            ]
        },
        "记录模块 (Records)": {
            "prefix": "/api",
            "routes": [
                {"method": "GET", "path": "/tables/<table_id>/records", "description": "获取记录列表"},
                {"method": "POST", "path": "/tables/<table_id>/records", "description": "创建记录"},
                {"method": "POST", "path": "/tables/<table_id>/records/batch", "description": "批量创建记录"},
                {"method": "GET", "path": "/records/<record_id>", "description": "获取记录详情"},
                {"method": "PUT", "path": "/records/<record_id>", "description": "更新记录"},
                {"method": "PUT", "path": "/records/batch", "description": "批量更新记录"},
                {"method": "DELETE", "path": "/records/<record_id>", "description": "删除记录"},
                {"method": "DELETE", "path": "/records/batch", "description": "批量删除记录"},
                {"method": "POST", "path": "/records/<record_id>/compute", "description": "计算记录字段值"},
                {"method": "GET", "path": "/records/<record_id>/history", "description": "获取记录历史"},
                {"method": "GET", "path": "/records/<record_id>/links", "description": "获取记录关联数据"},
                {"method": "PUT", "path": "/records/<record_id>/links/<field_id>", "description": "更新记录关联"},
                {"method": "GET", "path": "/tables/<table_id>/records/search", "description": "搜索记录"}
            ]
        },
        "视图模块 (Views)": {
            "prefix": "/api",
            "routes": [
                {"method": "GET", "path": "/tables/<table_id>/views", "description": "获取视图列表"},
                {"method": "POST", "path": "/tables/<table_id>/views", "description": "创建视图"},
                {"method": "GET", "path": "/views/<view_id>", "description": "获取视图详情"},
                {"method": "PUT", "path": "/views/<view_id>", "description": "更新视图"},
                {"method": "DELETE", "path": "/views/<view_id>", "description": "删除视图"},
                {"method": "POST", "path": "/views/<view_id>/duplicate", "description": "复制视图"},
                {"method": "PUT", "path": "/tables/<table_id>/views/reorder", "description": "重新排序视图"},
                {"method": "PUT", "path": "/tables/<table_id>/views/<view_id>/set-default", "description": "设置默认视图"},
                {"method": "GET", "path": "/views/types", "description": "获取视图类型"}
            ]
        },
        "仪表盘模块 (Dashboards)": {
            "prefix": "/api",
            "routes": [
                {"method": "GET", "path": "/bases/<base_id>/dashboards", "description": "获取仪表盘列表"},
                {"method": "POST", "path": "/bases/<base_id>/dashboards", "description": "创建仪表盘"},
                {"method": "GET", "path": "/dashboards/<dashboard_id>", "description": "获取仪表盘详情"},
                {"method": "PUT", "path": "/dashboards/<dashboard_id>", "description": "更新仪表盘"},
                {"method": "DELETE", "path": "/dashboards/<dashboard_id>", "description": "删除仪表盘"},
                {"method": "POST", "path": "/dashboards/<dashboard_id>/widgets", "description": "添加组件"},
                {"method": "PUT", "path": "/dashboards/<dashboard_id>/widgets", "description": "批量更新组件"},
                {"method": "PUT", "path": "/dashboards/<dashboard_id>/widgets/<widget_id>", "description": "更新组件"},
                {"method": "DELETE", "path": "/dashboards/<dashboard_id>/widgets/<widget_id>", "description": "删除组件"},
                {"method": "PUT", "path": "/dashboards/<dashboard_id>/layout", "description": "更新布局"},
                {"method": "POST", "path": "/dashboards/<dashboard_id>/duplicate", "description": "复制仪表盘"},
                {"method": "POST", "path": "/dashboards/<dashboard_id>/set-default", "description": "设置默认仪表盘"}
            ]
        },
        "仪表盘分享模块 (Dashboards Share)": {
            "prefix": "/api",
            "routes": [
                {"method": "GET", "path": "/dashboards/<dashboard_id>/shares", "description": "获取分享列表"},
                {"method": "POST", "path": "/dashboards/<dashboard_id>/shares", "description": "创建分享"},
                {"method": "DELETE", "path": "/shares/<share_id>", "description": "删除分享"},
                {"method": "POST", "path": "/shares/<share_id>/deactivate", "description": "停用分享"},
                {"method": "POST", "path": "/shares/<token>/validate", "description": "验证分享令牌"},
                {"method": "GET", "path": "/shares/<token>/dashboard", "description": "获取分享的仪表盘"}
            ]
        },
        "附件模块 (Attachments)": {
            "prefix": "/api/attachments",
            "routes": [
                {"method": "POST", "path": "/upload", "description": "上传附件"},
                {"method": "GET", "path": "/<attachment_id>", "description": "获取附件信息"},
                {"method": "GET", "path": "/<attachment_id>/download", "description": "下载附件"},
                {"method": "GET", "path": "/<attachment_id>/preview", "description": "预览附件"},
                {"method": "DELETE", "path": "/<attachment_id>", "description": "删除附件"},
                {"method": "GET", "path": "/bases/<base_id>", "description": "获取基础附件列表"},
                {"method": "GET", "path": "/<attachment_id>/thumbnail", "description": "获取缩略图"},
                {"method": "GET", "path": "/uploads/<filename>", "description": "访问上传的文件"}
            ]
        },
        "导入导出模块 (Import/Export)": {
            "prefix": "/api",
            "routes": [
                {"method": "POST", "path": "/import/preview", "description": "预览导入数据"},
                {"method": "POST", "path": "/import", "description": "导入数据"},
                {"method": "POST", "path": "/import/json", "description": "导入JSON数据"},
                {"method": "POST", "path": "/import/analyze", "description": "分析导入文件"},
                {"method": "POST", "path": "/export", "description": "导出数据"},
                {"method": "POST", "path": "/export/excel", "description": "导出Excel"},
                {"method": "POST", "path": "/export/csv", "description": "导出CSV"},
                {"method": "POST", "path": "/export/json", "description": "导出JSON"},
                {"method": "GET", "path": "/import/<task_id>", "description": "获取导入任务状态"}
            ]
        },
        "分享模块 (Shares)": {
            "prefix": "/api",
            "routes": [
                {"method": "POST", "path": "/bases/<base_id>/shares", "description": "创建分享"},
                {"method": "GET", "path": "/bases/<base_id>/shares", "description": "获取分享列表"},
                {"method": "PUT", "path": "/shares/<share_id>", "description": "更新分享"},
                {"method": "DELETE", "path": "/shares/<share_id>", "description": "删除分享"},
                {"method": "GET", "path": "/share/<share_token>", "description": "访问分享"},
                {"method": "GET", "path": "/bases/shared-with-me", "description": "获取分享给我的基础"},
                {"method": "GET", "path": "/bases/shared-by-me", "description": "获取我分享的基础"}
            ]
        },
        "表单分享模块 (Form Shares)": {
            "prefix": "/api",
            "routes": [
                {"method": "POST", "path": "/tables/<table_id>/form-shares", "description": "创建表单分享"},
                {"method": "GET", "path": "/tables/<table_id>/form-shares", "description": "获取表单分享列表"},
                {"method": "GET", "path": "/form-shares/<share_id>", "description": "获取表单分享详情"},
                {"method": "PUT", "path": "/form-shares/<share_id>", "description": "更新表单分享"},
                {"method": "DELETE", "path": "/form-shares/<share_id>", "description": "删除表单分享"},
                {"method": "GET", "path": "/form-shares/<share_id>/submissions", "description": "获取表单提交记录"},
                {"method": "GET", "path": "/form-shares/<token>/schema", "description": "获取表单结构"},
                {"method": "POST", "path": "/form-shares/<token>/submit", "description": "提交表单"},
                {"method": "GET", "path": "/form-shares/<token>/validate", "description": "验证表单令牌"},
                {"method": "GET", "path": "/form-shares/<token>/captcha", "description": "获取表单验证码"}
            ]
        },
        "管理员模块 (Admin)": {
            "prefix": "/api/admin",
            "routes": [
                {"method": "GET", "path": "/users", "description": "获取用户列表"},
                {"method": "POST", "path": "/users", "description": "创建用户"},
                {"method": "GET", "path": "/users/<user_id>", "description": "获取用户详情"},
                {"method": "PUT", "path": "/users/<user_id>", "description": "更新用户"},
                {"method": "DELETE", "path": "/users/<user_id>", "description": "删除用户"},
                {"method": "PUT", "path": "/users/<user_id>/status", "description": "更新用户状态"},
                {"method": "POST", "path": "/users/<user_id>/reset-password", "description": "重置用户密码"},
                {"method": "GET", "path": "/settings", "description": "获取系统设置"},
                {"method": "PUT", "path": "/settings", "description": "更新系统设置"},
                {"method": "GET", "path": "/operation-logs", "description": "获取操作日志"},
                {"method": "GET", "path": "/operation-logs/export", "description": "导出操作日志"},
                {"method": "GET", "path": "/roles", "description": "获取角色列表"},
                {"method": "POST", "path": "/email/verify-config", "description": "验证邮件配置"},
                {"method": "POST", "path": "/email/test", "description": "发送测试邮件"}
            ]
        },
        "邮件模块 (Email)": {
            "prefix": "/api/admin/email",
            "routes": [
                {"method": "GET", "path": "/templates", "description": "获取邮件模板列表"},
                {"method": "GET", "path": "/templates/<template_key>", "description": "获取邮件模板"},
                {"method": "PUT", "path": "/templates/<template_key>", "description": "更新邮件模板"},
                {"method": "POST", "path": "/templates/<template_key>/reset", "description": "重置邮件模板"},
                {"method": "GET", "path": "/logs", "description": "获取邮件日志"},
                {"method": "GET", "path": "/stats", "description": "获取邮件统计"},
                {"method": "GET", "path": "/queue/stats", "description": "获取队列统计"},
                {"method": "POST", "path": "/queue/clear", "description": "清空邮件队列"}
            ]
        },
        "站内信通知模块 (Notifications)": {
            "prefix": "/api",
            "routes": [
                {"method": "GET", "path": "/notifications", "description": "获取当前用户的站内信列表"},
                {"method": "GET", "path": "/notifications/unread-count", "description": "获取未读站内信数量"},
                {"method": "GET", "path": "/notifications/<notification_id>", "description": "获取站内信详情"},
                {"method": "POST", "path": "/notifications/<notification_id>/read", "description": "标记站内信为已读"},
                {"method": "POST", "path": "/notifications/read-all", "description": "标记所有站内信为已读"},
                {"method": "DELETE", "path": "/notifications/<notification_id>", "description": "删除站内信"},
                {"method": "GET", "path": "/admin/notifications/logs", "description": "获取站内信日志"},
                {"method": "GET", "path": "/admin/notifications/stats", "description": "获取站内信统计"},
                {"method": "POST", "path": "/admin/notifications/<notification_id>/retry", "description": "重试发送失败的站内信"}
            ]
        },
        "实时协作模块 (Realtime)": {
            "prefix": "/api",
            "routes": [
                {"method": "GET", "path": "/realtime/status", "description": "获取实时协作状态"}
            ]
        },
        "审批模块 (Approvals)": {
            "prefix": "/api",
            "routes": [
                {"method": "GET", "path": "/bases/<base_id>/approvals", "description": "获取我的待审批/已审批列表"},
                {"method": "GET", "path": "/approvals/<task_id>", "description": "获取审批任务详情"},
                {"method": "POST", "path": "/approvals/<task_id>/approve", "description": "同意审批"},
                {"method": "POST", "path": "/approvals/<task_id>/reject", "description": "驳回审批"},
                {"method": "POST", "path": "/approvals/<task_id>/transfer", "description": "转办审批"},
                {"method": "GET", "path": "/records/<record_id>/approval-history", "description": "获取记录审批历史"}
            ]
        },
        "审批流模块 (ApprovalFlows)": {
            "prefix": "/api",
            "routes": [
                {"method": "GET", "path": "/bases/<base_id>/approval-flows", "description": "获取审批流列表"},
                {"method": "POST", "path": "/bases/<base_id>/approval-flows", "description": "创建审批流"},
                {"method": "GET", "path": "/approval-flows/<flow_id>", "description": "获取审批流详情"},
                {"method": "PUT", "path": "/approval-flows/<flow_id>", "description": "更新审批流名称/描述"},
                {"method": "PUT", "path": "/approval-flows/<flow_id>/config", "description": "保存画布与表单配置"},
                {"method": "POST", "path": "/approval-flows/<flow_id>/publish", "description": "发布审批流"},
                {"method": "POST", "path": "/approval-flows/<flow_id>/pause", "description": "停用审批流"},
                {"method": "POST", "path": "/approval-flows/<flow_id>/clone", "description": "复制审批流"},
                {"method": "DELETE", "path": "/approval-flows/<flow_id>", "description": "删除审批流"},
                {"method": "GET", "path": "/approval-flows/<flow_id>/versions", "description": "获取版本列表"},
                {"method": "POST", "path": "/approval-flows/<flow_id>/submit", "description": "提交审批表单"},
                {"method": "GET", "path": "/bases/<base_id>/approval-flow-instances", "description": "获取实例列表"},
                {"method": "GET", "path": "/approval-flow-instances/<instance_id>", "description": "获取实例详情"},
                {"method": "GET", "path": "/bases/<base_id>/approval-flow-tasks", "description": "获取我的待办任务"},
                {"method": "POST", "path": "/approval-flow-tasks/<task_id>/approve", "description": "同意审批任务"},
                {"method": "POST", "path": "/approval-flow-tasks/<task_id>/reject", "description": "驳回审批任务"},
                {"method": "POST", "path": "/approval-flow-tasks/<task_id>/transfer", "description": "转办审批任务"},
                {"method": "POST", "path": "/approval-flow-instances/<instance_id>/comments", "description": "添加评论"},
                {"method": "GET", "path": "/approval-flow-instances/<instance_id>/comments", "description": "获取评论列表"}
            ]
        },
        "Webhook 模块 (Webhooks)": {
            "prefix": "/api",
            "routes": [
                {"method": "GET", "path": "/bases/<base_id>/webhooks", "description": "获取 Webhook 配置列表"},
                {"method": "POST", "path": "/bases/<base_id>/webhooks", "description": "创建 Webhook 配置"},
                {"method": "GET", "path": "/webhooks/<webhook_id>", "description": "获取 Webhook 配置详情"},
                {"method": "PUT", "path": "/webhooks/<webhook_id>", "description": "更新 Webhook 配置"},
                {"method": "DELETE", "path": "/webhooks/<webhook_id>", "description": "删除 Webhook 配置"},
                {"method": "POST", "path": "/webhooks/<webhook_id>/test", "description": "测试发送 Webhook"},
                {"method": "GET", "path": "/webhooks/<webhook_id>/deliveries", "description": "获取 Webhook 投递日志"}
            ]
        },
        "工作流模板模块 (Workflow Templates)": {
            "prefix": "/api/workflow-templates",
            "routes": [
                {"method": "GET", "path": "/", "description": "获取工作流模板列表"},
                {"method": "POST", "path": "/", "description": "将工作流保存为模板"},
                {"method": "POST", "path": "/<template_id>/instantiate", "description": "从模板创建工作流"}
            ]
        },
        "工作流模块 (Workflows)": {
            "prefix": "/api",
            "routes": [
                {"method": "GET", "path": "/bases/<base_id>/workflows", "description": "获取基础数据下工作流列表"},
                {"method": "POST", "path": "/bases/<base_id>/workflows", "description": "创建工作流"},
                {"method": "GET", "path": "/workflows/<workflow_id>", "description": "获取工作流详情"},
                {"method": "PUT", "path": "/workflows/<workflow_id>", "description": "更新工作流"},
                {"method": "DELETE", "path": "/workflows/<workflow_id>", "description": "删除工作流"},
                {"method": "POST", "path": "/workflows/<workflow_id>/publish", "description": "发布工作流"},
                {"method": "POST", "path": "/workflows/<workflow_id>/pause", "description": "暂停工作流"},
                {"method": "POST", "path": "/workflows/<workflow_id>/resume", "description": "恢复工作流"},
                {"method": "GET", "path": "/workflows/<workflow_id>/instances", "description": "获取工作流实例列表"},
                {"method": "GET", "path": "/workflows/<workflow_id>/instances/<instance_id>", "description": "获取工作流实例详情"},
                {"method": "POST", "path": "/tables/<table_id>/records/<record_id>/trigger", "description": "手动触发工作流"}
            ]
        },
        "插件模块 (Plugins)": {
            "prefix": "/api/plugins",
            "routes": [
                {"method": "POST", "path": "/upload", "description": "上传安装/升级插件包（系统管理员）"},
                {"method": "GET", "path": "/", "description": "获取插件列表（可选 base_id 附带 Base 级状态）"},
                {"method": "GET", "path": "/<plugin_id>", "description": "获取插件详情（含版本历史）"},
                {"method": "PUT", "path": "/<plugin_id>/status", "description": "全局启用/禁用/恢复（系统管理员）"},
                {"method": "POST", "path": "/<plugin_id>/rollback", "description": "回滚到历史版本（系统管理员）"},
                {"method": "DELETE", "path": "/<plugin_id>", "description": "卸载插件（系统管理员）"},
                {"method": "GET", "path": "/<plugin_id>/config", "description": "读取生效配置（base 合并 global）"},
                {"method": "PUT", "path": "/<plugin_id>/config", "description": "写入配置（configSchema 校验）"},
                {"method": "GET", "path": "/<plugin_id>/installations", "description": "获取 Base 级安装状态"},
                {"method": "POST", "path": "/<plugin_id>/installations", "description": "在 Base 内安装并启用（Base 管理员）"},
                {"method": "PUT", "path": "/<plugin_id>/installations", "description": "启停 Base 级插件（Base 管理员）"},
                {"method": "DELETE", "path": "/<plugin_id>/installations", "description": "从 Base 移除插件（Base 管理员）"},
                {"method": "POST", "path": "/<plugin_id>/run", "description": "手动运行脚本插件（触发者身份）"},
                {"method": "GET", "path": "/<plugin_id>/run-logs", "description": "查询运行日志（Base 管理员）"},
                {"method": "POST", "path": "/<plugin_id>/sandbox-url", "description": "获取 UI 插件沙箱签名 URL"},
                {"method": "GET", "path": "/<plugin_id>/versions/<version>/loader.html", "description": "UI 插件沙箱 loader（签名鉴权）"},
                {"method": "GET", "path": "/<plugin_id>/versions/<version>/files/<filename>", "description": "插件包静态文件（签名鉴权）"}
            ]
        },
        "打印模板模块 (Print Templates)": {
            "prefix": "/api",
            "routes": [
                {"method": "GET", "path": "/bases/<base_id>/print-templates", "description": "获取打印模板列表（按用户可见性过滤）"},
                {"method": "POST", "path": "/bases/<base_id>/print-templates", "description": "创建打印模板（含导入）"},
                {"method": "GET", "path": "/print-templates/<template_id>", "description": "获取打印模板详情（含模板 JSON）"},
                {"method": "PUT", "path": "/print-templates/<template_id>", "description": "更新打印模板（创建者或 Base 管理员）"},
                {"method": "DELETE", "path": "/print-templates/<template_id>", "description": "删除打印模板（创建者或 Base 管理员）"}
            ]
        }
    },
    "field_types": [
        {"type": "SINGLE_LINE_TEXT", "name": "单行文本", "description": "单行文本输入"},
        {"type": "LONG_TEXT", "name": "多行文本", "description": "多行文本输入"},
        {"type": "RICH_TEXT", "name": "富文本", "description": "富文本编辑器"},
        {"type": "NUMBER", "name": "数字", "description": "数值输入"},
        {"type": "CURRENCY", "name": "货币", "description": "货币金额"},
        {"type": "PERCENT", "name": "百分比", "description": "百分比数值"},
        {"type": "DATE", "name": "日期", "description": "日期选择"},
        {"type": "DATE_TIME", "name": "日期时间", "description": "日期时间选择"},
        {"type": "SINGLE_SELECT", "name": "单选", "description": "单选下拉框"},
        {"type": "MULTI_SELECT", "name": "多选", "description": "多选下拉框"},
        {"type": "CHECKBOX", "name": "复选框", "description": "布尔值选择"},
        {"type": "ATTACHMENT", "name": "附件", "description": "文件上传"},
        {"type": "LINK", "name": "关联", "description": "关联到其他表"},
        {"type": "LOOKUP", "name": "查找", "description": "查找关联表字段"},
        {"type": "FORMULA", "name": "公式", "description": "计算公式字段"},
        {"type": "ROLLUP", "name": "汇总", "description": "汇总关联数据"},
        {"type": "PHONE", "name": "电话", "description": "电话号码"},
        {"type": "EMAIL", "name": "邮箱", "description": "邮箱地址"},
        {"type": "URL", "name": "链接", "description": "URL链接"},
        {"type": "AUTO_NUMBER", "name": "自动编号", "description": "自动生成唯一编号"},
        {"type": "GEOLOCATION", "name": "地理位置", "description": "省份/城市/区县/国家和地区/经纬度/地图选点"},
        {"type": "CREATED_TIME", "name": "创建时间", "description": "记录创建时间"},
        {"type": "CREATED_BY", "name": "创建人", "description": "记录创建人"},
        {"type": "LAST_MODIFIED_TIME", "name": "最后修改时间", "description": "记录最后修改时间"},
        {"type": "LAST_MODIFIED_BY", "name": "最后修改人", "description": "记录最后修改人"}
    ],
    "response_codes": {
        "200": "请求成功",
        "201": "创建成功",
        "400": "请求参数错误",
        "401": "未授权，需要登录",
        "403": "禁止访问，权限不足",
        "404": "资源不存在",
        "422": "请求格式正确但语义错误",
        "500": "服务器内部错误"
    }
}
