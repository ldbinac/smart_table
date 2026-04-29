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
from flask_wtf.csrf import CSRFProtect
from flask import request
import redis


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

# CSRF 保护扩展
csrf = CSRFProtect()

# WebSocket 扩展（async_mode 在 init_app 中根据配置动态设置）
socketio = SocketIO()

# Redis 客户端（全局连接池）
redis_client = None


def init_extensions(app):
    """
    初始化所有 Flask 扩展
    
    Args:
        app: Flask 应用实例
    """
    global redis_client
    
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
    
    # 初始化 Redis 客户端（使用连接池）
    redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
        app.logger.info('[Extensions] Redis client initialized successfully')
    except Exception as e:
        app.logger.warning(f'[Extensions] Redis connection failed: {e}. Redis features will be unavailable.')
        redis_client = None
    
    # 初始化 CSRF 保护
    # 项目使用 JWT Bearer Token 认证，不受 CSRF 攻击影响，禁用 CSRF 保护
    app.config['WTF_CSRF_ENABLED'] = False
    csrf.init_app(app)
    
    # 初始化 CORS（使用配置中的允许来源列表，不再默认允许所有来源）
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', ['http://localhost:3000']),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Authorization", "Content-Type", "*"],
            "expose_headers": ["Authorization"],
            "supports_credentials": True
        }
    })
    
    if app.config.get('REALTIME_ENABLED', False):
        socketio_kwargs = {
            'async_mode': 'threading',
            'cors_allowed_origins': app.config.get('CORS_ORIGINS', ['http://localhost:3000']),
            'ping_timeout': app.config.get('SOCKETIO_PING_TIMEOUT', 60),
            'ping_interval': app.config.get('SOCKETIO_PING_INTERVAL', 25),
        }
        message_queue = app.config.get('SOCKETIO_MESSAGE_QUEUE')
        if message_queue:
            socketio_kwargs['message_queue'] = message_queue
        socketio.init_app(app, **socketio_kwargs)
    
    # 初始化安全响应头中间件
    from app.middleware import init_security_headers
    init_security_headers(app)
    
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
        from flask import current_app
        
        jti = jwt_payload["jti"]
        user_id = jwt_payload.get("sub")
        
        try:
            # 先检查是否在黑名单中
            token = TokenBlocklist.query.filter_by(jti=jti).first()
            if token is not None:
                return True
        except Exception as e:
            # 如果表不存在，记录错误但不阻止验证（允许登录）
            current_app.logger.error(f'[JWT] 查询 TokenBlocklist 失败：{str(e)}')
            # 表不存在时，假设令牌未被撤销，允许继续验证
            pass
        
        # 检查令牌版本号（用于退出所有设备功能）
        try:
            cache_key = f"user_token_version:{user_id}"
            current_version = cache.get(cache_key) or 0
            token_version = jwt_payload.get('token_version', 0)
            
            # 如果令牌版本号小于当前版本号，说明令牌已失效
            if token_version < current_version:
                return True
        except Exception as e:
            current_app.logger.error(f'[JWT] 检查令牌版本失败：{str(e)}')
        
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
