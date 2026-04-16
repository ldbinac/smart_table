"""
SmartTable Flask 应用工厂模块
"""
from flask import Flask
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
