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
from flask import request, g, current_app
import redis
import sys
import os


# 数据库扩展
db = SQLAlchemy()

# 数据库迁移扩展
migrate = Migrate()

# 分层迁移目录（各产品版本层级独立维护迁移，互不干扰）：
# - versions/      基础层（feat-plugin）
# - versions_fa/   打印/移动端/高级权限层（feat/field-auth-base）
# - versions_am/   应用模式层（feat/app-base-mode）
# - versions_ap/   审批流层（feat/approval-flows）
# 低版本分支只存在部分目录，不存在的目录会被 Alembic 自动忽略。
_MIGRATION_LAYER_DIRS = ('versions', 'versions_fa', 'versions_am', 'versions_ap')


@migrate.configure
def _configure_migration_version_locations(config):
    """
    将各层迁移目录聚合进 Alembic 的 version_locations。

    flask_migrate 构建的 Config 会读取迁移目录下的 alembic.ini，
    本回调在其后执行并以「基于 script_location 的路径」覆盖配置，
    避免相对路径受进程工作目录（开发/Docker/PyInstaller）影响。
    所有 flask_migrate 调用（run.py 迁移、flask db 命令）均经过此处。
    """
    script_dir = config.get_main_option('script_location')
    if not script_dir:
        return config
    locations = [
        os.path.join(script_dir, layer_dir)
        for layer_dir in _MIGRATION_LAYER_DIRS
        if os.path.isdir(os.path.join(script_dir, layer_dir))
    ]
    if locations:
        config.set_main_option('version_path_separator', 'os')
        config.set_main_option('version_locations', os.pathsep.join(locations))
    return config

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

# WebSocket 扩展（延迟配置 async_mode，避免与 init_app 双重指定导致 PyInstaller 环境初始化失败）
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

    # ========== SQLite PRAGMA 配置 ==========
    # SQLite 默认 journal_mode=DELETE + busy_timeout=0 → 遇锁立刻抛 OperationalError
    # 大表流式加载（3 并发 × 50 页）时多个请求同时 SELECT + COUNT + formulas 计算
    # 很容易互相锁 → "数据库锁死" 偶发 500
    # WAL mode：允许读写并发，读不阻塞写，写不阻塞读（但写写仍串行）
    # busy_timeout=5000：遇锁等 5 秒再抛错，吸收瞬时锁冲突
    # foreign_keys=ON：SQLite 默认不强制外键
    # synchronous=NORMAL：WAL 模式下安全性能折中
    with app.app_context():
        engine = db.engine
        from sqlalchemy import event
        from sqlalchemy.engine import Engine

        @event.listens_for(Engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            """每个新 SQLite 连接都设置 PRAGMA"""
            try:
                cursor = dbapi_connection.cursor()
                # WAL：Write-Ahead Logging，允许读写并发
                cursor.execute("PRAGMA journal_mode=WAL")
                # 遇锁等 5 秒再抛错（默认 0 = 立刻失败）
                cursor.execute("PRAGMA busy_timeout=5000")
                # 强制外键（SQLite 默认 OFF）
                cursor.execute("PRAGMA foreign_keys=ON")
                # WAL 模式下的同步级别（NORMAL：OS 崩溃安全，断电可能丢最后几个事务）
                cursor.execute("PRAGMA synchronous=NORMAL")
                # 临时内存存储模式（WAL + 内存 temp_store）
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.close()
            except Exception as _e:
                # 非 SQLite 引擎（PostgreSQL 等）不执行这些 PRAGMA
                pass

        # 如果是 SQLite 数据库，立即在当前 engine 上执行一次 PRAGMA
        # 上面的 listener 只对后续新建连接生效，已存在的连接需要手动执行
        if 'sqlite' in str(engine.url).lower():
            try:
                with engine.connect() as conn:
                    conn.execute(db.text("PRAGMA journal_mode=WAL"))
                    conn.execute(db.text("PRAGMA busy_timeout=5000"))
                    conn.execute(db.text("PRAGMA foreign_keys=ON"))
                    conn.execute(db.text("PRAGMA synchronous=NORMAL"))
                    conn.execute(db.text("PRAGMA temp_store=MEMORY"))
                app.logger.info('[Extensions] ✓ SQLite WAL mode + busy_timeout=5000 configured')
            except Exception as e:
                app.logger.warning(f'[Extensions] SQLite PRAGMA setup failed: {e}')
    
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
        app.logger.error(f'[Extensions] Redis connection failed: {e}. Redis features will be unavailable.')
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
        is_packaged = getattr(sys, 'frozen', False)
        is_docker = os.environ.get('DOCKER_ENV', 'false').lower() == 'true'

        # Docker 生产环境：使用 eventlet（需要在启动前调用 eventlet.monkey_patch()）
        # PyInstaller 打包模式：使用 threading（不需要 monkey_patch）
        # 开发环境：使用 threading（更稳定，不影响 Redis 连接）
        if is_docker:
            async_mode = 'eventlet'
            try:
                import engineio.async_drivers.eventlet  # noqa: F401
                app.logger.info('[Extensions] Using eventlet async mode for Docker environment')
            except ImportError:
                app.logger.warning('[Extensions] engineio.async_drivers.eventlet not importable, falling back to threading')
                async_mode = 'threading'
        else:
            # 开发环境和打包环境统一使用 threading 模式
            async_mode = 'threading'
            try:
                import engineio.async_drivers.threading  # noqa: F401
                app.logger.info('[Extensions] Using threading async mode for development/packaged environment')
            except ImportError:
                app.logger.warning('[Extensions] engineio.async_drivers.threading not importable, SocketIO may fail')

        socketio_kwargs = {
            'async_mode': async_mode,
            'cors_allowed_origins': '*',  # WebSocket 通过 JWT Token 认证，不需要 CORS 限制来源
            'ping_timeout': app.config.get('SOCKETIO_PING_TIMEOUT', 60),
            'ping_interval': app.config.get('SOCKETIO_PING_INTERVAL', 25),
        }

        # 在打包环境和开发环境中，避免使用 message_queue（可能导致初始化失败）
        # 单进程模式下不需要消息队列，只有 Docker 多进程部署才需要
        if is_docker:
            message_queue = app.config.get('SOCKETIO_MESSAGE_QUEUE')
            if message_queue:
                socketio_kwargs['message_queue'] = message_queue

        try:
            socketio.init_app(app, **socketio_kwargs)
            app.logger.info(f'[Extensions] ✓ SocketIO initialized successfully (async_mode: {async_mode})')
        except Exception as e:
            app.logger.error(f'[Extensions] ⚠️ SocketIO initialization failed: {e}')
            app.logger.error(f'[Extensions]   Error type: {type(e).__name__}')
            # 诊断：检测具体哪个驱动模块不可用
            for driver in ['threading', 'eventlet']:
                try:
                    __import__(f'engineio.async_drivers.{driver}')
                    app.logger.info(f'[Extensions]   engineio.async_drivers.{driver}: OK')
                except ImportError as ie:
                    app.logger.error(f'[Extensions]   engineio.async_drivers.{driver}: IMPORT FAILED - {ie}')
            app.logger.error('[Extensions]   Real-time collaboration will be disabled')
            app.config['REALTIME_ENABLED'] = False
    
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
        
        jti = jwt_payload["jti"]
        user_id = jwt_payload.get("sub")

        # 第三方应用令牌（OAuth2 客户端凭证）撤销检查：Redis jti 黑名单，O(1) 查询
        try:
            from app.extensions import redis_client
            if redis_client is not None:
                if redis_client.sismember('oauth:revoked_jti', jti):
                    return True
        except Exception:
            # Redis 不可用时不影响用户令牌校验路径
            pass

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
        request_id = getattr(g, 'request_id', None)
        return {
            'success': False,
            'message': 'token_expired_log_again',
            'error': 'token_expired',
            'request_id': request_id
        }, 401
    
    @jwt_manager.invalid_token_loader
    def invalid_token_callback(error):
        """无效令牌回调"""
        request_id = getattr(g, 'request_id', None)
        return {
            'success': False,
            'message': 'invalid_token',
            'error': 'invalid_token',
            'request_id': request_id
        }, 401
    
    @jwt_manager.unauthorized_loader
    def missing_token_callback(error):
        """缺少令牌回调"""
        request_id = getattr(g, 'request_id', None)
        return {
            'success': False,
            'message': 'request_missing_authentication_token',
            'error': 'authorization_required',
            'request_id': request_id
        }, 401
    
    @jwt_manager.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        """被撤销的令牌回调"""
        request_id = getattr(g, 'request_id', None)
        return {
            'success': False,
            'message': 'token_been_revoked_log_again',
            'error': 'token_revoked',
            'request_id': request_id
        }, 401
