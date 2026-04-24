"""
SmartTable Flask 应用工厂模块
"""
from flask import Flask
from flasgger import Swagger
from app.extensions import init_extensions, db
from app.config import config


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

    # 设置实时协作配置
    app.config['REALTIME_ENABLED'] = enable_realtime
    
    # 初始化扩展
    init_extensions(app)

    # 条件初始化 SocketIO 事件处理器
    if app.config.get('REALTIME_ENABLED', False):
        register_socketio_handlers(app)
    
    # 注册蓝图
    register_blueprints(app)

    # 注册 API 文档路由
    register_api_docs(app)

    # 初始化 Flasgger Swagger
    init_swagger(app)

    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册 Shell 上下文
    register_shell_context(app)
    
    # 开发环境下自动创建数据库表
    if config_name == 'development':
        with app.app_context():
            try:
                # 先删除所有表，再重新创建（确保表结构最新）
               # db.drop_all()
                db.create_all()
                print("数据库表创建成功")

                # 初始化默认邮件模板
                from app.utils.init_email_templates import init_default_email_templates
                init_default_email_templates()
            except Exception as e:
                print(f"创建数据库表失败：{e}")
    else:
        # 生产环境也初始化邮件模板
        with app.app_context():
            try:
                from app.utils.init_email_templates import init_default_email_templates
                init_default_email_templates()
            except Exception as e:
                print(f"初始化邮件模板失败：{e}")

    # 注册应用生命周期钩子
    register_lifecycle_hooks(app)

    return app


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
    def init_services():
        """应用首次请求时初始化服务"""
        nonlocal _first_request_initialized
        if not _first_request_initialized:
            _first_request_initialized = True
            from app.services.email_queue_service import init_email_queue
            init_email_queue(app)

    @app.teardown_appcontext
    def shutdown_services(exception=None):
        """应用上下文销毁时关闭服务"""
        pass  # 邮件队列服务在应用退出时统一关闭


def register_blueprints(app):
    """
    注册 Flask 蓝图
    
    Args:
        app: Flask 应用实例
    """
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
    from app.routes.shares import shares_bp
    from app.routes.form_shares import form_shares_bp
    from app.routes.auth_captcha import auth_captcha_bp
    from app.routes.email import email_bp
    from app.routes.realtime import realtime_bp
    
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

    # 注册邮件服务蓝图
    app.register_blueprint(email_bp, url_prefix='/api/admin/email')

    # 注册分享蓝图
    app.register_blueprint(shares_bp, url_prefix='/api')
    
    # 注册表单分享蓝图 (路由中已包含完整路径)
    app.register_blueprint(form_shares_bp, url_prefix='/api')

    # 注册实时协作蓝图
    app.register_blueprint(realtime_bp, url_prefix='/api')


def register_error_handlers(app):
    """
    注册错误处理器
    
    Args:
        app: Flask 应用实例
    """
    from app.errors.handlers import register_handlers
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
        from app.models import (
            User, Base, BaseMember, Table, Field, 
            Record, View, Dashboard, Attachment
        )
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
    from app.extensions import socketio
    from app.routes.socketio_events import register_socketio_handlers as _register
    _register(socketio, app)


def register_api_docs(app):
    """
    注册 API 文档路由

    Args:
        app: Flask 应用实例
    """
    from flask import jsonify, render_template_string

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
            "实时协作模块 (Realtime)": {
                "prefix": "/api",
                "routes": [
                    {"method": "GET", "path": "/realtime/status", "description": "获取实时协作状态"}
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
        {"name": "Records", "description": "记录（数据行）管理接口"},
        {"name": "Views", "description": "视图管理接口"},
        {"name": "Dashboards", "description": "仪表盘管理接口"},
        {"name": "Dashboards Share", "description": "仪表盘分享接口"},
        {"name": "Attachments", "description": "附件上传下载接口"},
        {"name": "Import/Export", "description": "数据导入导出接口"},
        {"name": "Shares", "description": "基础数据分享接口"},
        {"name": "Form Shares", "description": "表单分享接口"},
        {"name": "Admin", "description": "管理员接口（用户管理、系统设置等）"},
        {"name": "Email", "description": "邮件服务管理接口"},
        {"name": "Realtime", "description": "实时协作状态接口"},
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
