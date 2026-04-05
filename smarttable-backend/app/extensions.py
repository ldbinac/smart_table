"""
Flask 扩展初始化模块
集中管理所有 Flask 扩展的初始化
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_cors import CORS
from flask_socketio import SocketIO


# 数据库扩展
db = SQLAlchemy()

# 数据库迁移扩展
migrate = Migrate()

# JWT 认证扩展
jwt = JWTManager()

# 密码哈希扩展
bcrypt = Bcrypt()

# 缓存扩展
cache = Cache()

# CORS 扩展
cors = CORS()

# WebSocket 扩展
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')


def init_extensions(app):
    """
    初始化所有 Flask 扩展
    
    Args:
        app: Flask 应用实例
    """
    # 初始化数据库
    db.init_app(app)
    
    # 初始化迁移工具
    migrate.init_app(app, db)
    
    # 初始化 JWT
    jwt.init_app(app)
    
    # 初始化密码哈希
    bcrypt.init_app(app)
    
    # 初始化缓存
    cache.init_app(app)
    
    # 初始化 CORS
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', ['*']),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Authorization", "Content-Type", "*"],
            "expose_headers": ["Authorization"],
            "supports_credentials": True
        }
    })
    
    # 初始化 WebSocket
    socketio.init_app(app)
    
    # 注册 JWT 回调函数
    register_jwt_callbacks(jwt)


def register_jwt_callbacks(jwt_manager):
    """
    注册 JWT 相关的回调函数
    
    Args:
        jwt_manager: JWTManager 实例
    """
    
    @jwt_manager.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """检查令牌是否被撤销"""
        from app.models.user import TokenBlocklist
        from app.extensions import cache
        
        jti = jwt_payload["jti"]
        user_id = jwt_payload.get("sub")
        
        # 先检查是否在黑名单中
        token = TokenBlocklist.query.filter_by(jti=jti).first()
        if token is not None:
            return True
        
        # 检查令牌版本号（用于退出所有设备功能）
        cache_key = f"user_token_version:{user_id}"
        current_version = cache.get(cache_key) or 0
        token_version = jwt_payload.get('token_version', 0)
        
        # 如果令牌版本号小于当前版本号，说明令牌已失效
        if token_version < current_version:
            return True
        
        return False
    
    @jwt_manager.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        """令牌过期回调"""
        return {
            'success': False,
            'message': '令牌已过期，请重新登录',
            'error': 'token_expired'
        }, 401
    
    @jwt_manager.invalid_token_loader
    def invalid_token_callback(error):
        """无效令牌回调"""
        return {
            'success': False,
            'message': '无效的令牌',
            'error': 'invalid_token'
        }, 401
    
    @jwt_manager.unauthorized_loader
    def missing_token_callback(error):
        """缺少令牌回调"""
        return {
            'success': False,
            'message': '请求缺少认证令牌',
            'error': 'authorization_required'
        }, 401
