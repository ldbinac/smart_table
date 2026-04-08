"""
SmartTable Flask 应用工厂模块
"""
from flask import Flask
from app.extensions import init_extensions, db
from app.config import config


def create_app(config_name='default'):
    """
    应用工厂函数

    Args:
        config_name: 配置名称，可选值：development, testing, production, default

    Returns:
        Flask 应用实例
    """
    app = Flask(__name__)

    # 禁用严格斜杠，避免 308 重定向
    app.url_map.strict_slashes = False

    # 加载配置
    app.config.from_object(config[config_name])
    
    # 初始化扩展
    init_extensions(app)
    
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
                db.create_all()
                print("数据库表创建成功")
            except Exception as e:
                print(f"创建数据库表失败：{e}")
    
    return app


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
    
    # 注册认证蓝图
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
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
    
    # 注册分享蓝图
    app.register_blueprint(shares_bp, url_prefix='/api')


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
