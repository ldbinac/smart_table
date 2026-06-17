"""
应用配置模块
包含开发、测试、生产环境的配置
"""
import os
import sys
import logging
from datetime import timedelta
from logging.handlers import RotatingFileHandler

# 修复 Windows 终端 GBK 编码无法打印 Unicode 字符的问题
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


class SafeRotatingFileHandler(RotatingFileHandler):
    """
    安全的日志文件处理器，解决 Windows 上文件占用问题
    """
    def doRollover(self):
        """
        重写日志轮转方法，处理 Windows 文件占用问题
        """
        try:
            super().doRollover()
        except PermissionError:
            # Windows 上文件被占用时，跳过此次轮转
            pass
        except Exception:
            # 其他错误也静默处理，避免影响应用运行
            pass


class Config:
    """基础配置类"""
    
    # Flask 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # ===== 打包模式检测与配置 =====
    PACKAGING_MODE = getattr(sys, 'frozen', False)

    # 数据目录配置
    DATA_DIR = os.environ.get('DATA_DIR', 'data')

    # ✅ 关键修复：使用绝对路径确保数据库位置确定
    # 打包模式下，基于 EXE 所在目录（而非当前工作目录 cwd）
    if PACKAGING_MODE:
        _exe_dir = os.path.dirname(sys.executable)
        _abs_data_dir = os.path.join(_exe_dir, DATA_DIR)
    else:
        _abs_data_dir = os.path.abspath(DATA_DIR)
    
    # 确保数据目录存在
    if not os.path.exists(_abs_data_dir):
        try:
            os.makedirs(_abs_data_dir, exist_ok=True)
            print(f'[Config] ✓ 自动创建数据目录: {_abs_data_dir}')
        except OSError as e:
            print(f'[Config] ⚠️ 无法创建数据目录 {_abs_data_dir}: {e}')
    
    # 数据库路径（绝对路径）
    DATABASE_PATH = os.path.join(_abs_data_dir, 'smarttable.db')

    # 数据库配置 (默认使用 SQLite 进行开发/打包)
    _env_database_url = os.environ.get('DATABASE_URL', '').strip()

    if not _env_database_url:
        # 未设置环境变量 → 使用绝对路径 ✅
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
        print(f'[Config] ✓ 数据库路径 (自动): {DATABASE_PATH}')
    else:
        # 检查是否为 SQLite 相对路径（需要转换为绝对路径）
        if _env_database_url.startswith('sqlite:///') and not os.path.isabs(_env_database_url[10:]):
            # 提取相对路径部分
            relative_db_path = _env_database_url[10:]  # 去掉 "sqlite:///" 前缀

            # ===== 关键修复：避免路径重复拼接 =====
            # 问题场景：_abs_data_dir 已经是 ".../data/"
            #           但 .env 中配置的是 "data/smarttable.db"
            #           直接 join 会变成 ".../data/data/smarttable.db"
            #
            # 解决方案：检测并去除重复的 "data/" 前缀
            _data_dir_name = os.path.basename(_abs_data_dir)  # "data"
            if relative_db_path.startswith(f'{_data_dir_name}{os.sep}') or \
               relative_db_path.startswith(f'{_data_dir_name}/'):
                # 去掉重复的 "data/" 前缀，只保留后面的部分
                relative_db_path = relative_db_path[len(_data_dir_name) + 1:]

            abs_db_path = os.path.join(_abs_data_dir, relative_db_path)
            abs_db_path = os.path.normpath(abs_db_path)  # 规范化路径（处理 .. 和多余分隔符）
            SQLALCHEMY_DATABASE_URI = f'sqlite:///{abs_db_path}'
            print(f'[Config] ✓ 数据库路径 (转换): {abs_db_path}')
            print(f'   原始配置: {_env_database_url}')
        else:
            # 绝对路径或其他数据库（PostgreSQL 等）→ 直接使用
            SQLALCHEMY_DATABASE_URI = _env_database_url
            print(f'[Config] ✓ 数据库路径 (外部): {_env_database_url}')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # JWT 配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 86400))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # Redis 配置
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # 缓存配置
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 300
    
    # MinIO 对象存储配置（打包模式下禁用，使用本地文件系统）
    MINIO_ENABLED = os.environ.get('MINIO_ENABLED', 'false').lower() == 'true'
    MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT', '') if MINIO_ENABLED else ''
    MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY', '') if MINIO_ENABLED else ''
    MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY', '') if MINIO_ENABLED else ''
    MINIO_BUCKET_NAME = os.environ.get('MINIO_BUCKET_NAME', 'smarttable') if MINIO_ENABLED else ''
    MINIO_SECURE = False
    
    # 分页配置
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # CORS 配置
    CORS_ORIGINS = [
        'http://localhost', 'http://127.0.0.1',
        'http://localhost:80', 'http://127.0.0.1:80',
        'http://localhost:3000', 'http://127.0.0.1:3000',
        'http://localhost:5000', 'http://127.0.0.1:5000',
        'http://localhost:8080', 'http://127.0.0.1:8080',
    ]
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # 文件上传配置
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 最大文件大小 50MB
    ALLOWED_EXTENSIONS = {
        'image': ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'],
        'document': ['doc', 'docx', 'pdf', 'txt', 'md'],
        'video': ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv'],
        'audio': ['mp3', 'wav', 'ogg', 'flac', 'aac']
    }

    # 实时协作配置
    REALTIME_ENABLED = os.environ.get('ENABLE_REALTIME', '').lower() == 'true'

    # SocketIO 配置
    SOCKETIO_MESSAGE_QUEUE = os.environ.get('SOCKETIO_MESSAGE_QUEUE') or 'redis://localhost:6379/2'
    SOCKETIO_PING_TIMEOUT = int(os.environ.get('SOCKETIO_PING_TIMEOUT', 60))
    SOCKETIO_PING_INTERVAL = int(os.environ.get('SOCKETIO_PING_INTERVAL', 25))

    # 错误处理配置
    ERROR_SHOW_DETAILS = os.environ.get('ERROR_SHOW_DETAILS', 'false').lower() == 'true'
    ERROR_LOG_STACK_TRACE = True
    ERROR_REQUEST_ID_HEADER = 'X-Request-ID'


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-not-for-production'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-jwt-secret-not-for-production'

    @classmethod
    def init_app(cls, app):
        """开发环境初始化 - 检查并警告未配置的敏感凭据，配置日志"""
        logger = logging.getLogger(__name__)

        if not os.environ.get('MINIO_ACCESS_KEY') or not os.environ.get('MINIO_SECRET_KEY'):
            logger.warning(
                '⚠️  MINIO_ACCESS_KEY 或 MINIO_SECRET_KEY 未设置！'
                'MinIO 文件存储功能将不可用。'
                '请在 .env 文件中配置这些环境变量。'
            )
            app.config['MINIO_ACCESS_KEY'] = None
            app.config['MINIO_SECRET_KEY'] = None

        if cls.SECRET_KEY == 'dev-secret-key-not-for-production':
            logger.warning(
                '⚠️  使用默认开发密钥！请勿在生产环境中使用。'
            )
        if cls.JWT_SECRET_KEY == 'dev-jwt-secret-not-for-production':
            logger.warning(
                '⚠️  使用默认 JWT 密钥！请勿在生产环境中使用。'
            )

        # ===== 配置开发环境日志（与生产环境保持一致）=====
        _data_dir = app.config.get('DATA_DIR', 'data')
        if getattr(sys, 'frozen', False):
            _exe_dir = os.path.dirname(sys.executable)
            _abs_data_dir = os.path.join(_exe_dir, _data_dir)
            logs_dir = os.path.join(_exe_dir, 'logs')
        else:
            _abs_data_dir = os.path.abspath(_data_dir)
            logs_dir = 'logs'

        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, 'smarttable.log')

        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        )

        file_handler = SafeRotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)  # 开发模式使用 DEBUG 级别

        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.DEBUG)  # 开发模式记录更详细的日志
        app.logger.info(f'[Dev] SmartTable startup (log file: {log_file})')
        print(f'[Config] ✓ 日志文件已配置: {log_file}')


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 0


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    
    # 生产环境 CORS 必须通过环境变量明确指定允许的来源
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',') if os.environ.get('CORS_ORIGINS') else []
    
    @classmethod
    def init_app(cls, app):
        """生产环境初始化"""

        # 强制校验关键安全变量（但允许打包模式使用默认值）
        if not app.config.get('SECRET_KEY') or app.config.get('SECRET_KEY') == 'your-secret-key-here':
            if getattr(sys, 'frozen', False):
                print('[Config] ⚠️ SECRET_KEY 使用默认值（打包模式）')
            else:
                raise RuntimeError("生产环境必须设置 SECRET_KEY 环境变量")
        if not app.config.get('JWT_SECRET_KEY') or app.config.get('JWT_SECRET_KEY') == 'your-jwt-secret-key-here':
            if getattr(sys, 'frozen', False):
                print('[Config] ⚠️ JWT_SECRET_KEY 使用默认值（打包模式）')
            else:
                raise RuntimeError("生产环境必须设置 JWT_SECRET_KEY 环境变量")

        # CORS 配置：缺失时使用默认值（允许本地访问）
        cors_origins = app.config.get('CORS_ORIGINS', [])
        if not cors_origins or (isinstance(cors_origins, list) and len(cors_origins) == 1 and not cors_origins[0]):
            default_cors = ['http://localhost', 'http://127.0.0.1', 'http://localhost:80', 'http://127.0.0.1:80']
            app.config['CORS_ORIGINS'] = default_cors
            print(f'[Config] ℹ️ CORS_ORIGINS 未设置，使用默认值: {default_cors}')
        
        # 配置日志

        # ===== 使用绝对路径确保日志写入正确位置 =====
        _data_dir = app.config.get('DATA_DIR', 'data')
        if getattr(sys, 'frozen', False):
            _exe_dir = os.path.dirname(sys.executable)
            _abs_data_dir = os.path.join(_exe_dir, _data_dir)
        else:
            _abs_data_dir = os.path.abspath(_data_dir)

        logs_dir = os.path.join(_exe_dir, 'logs') if cls.PACKAGING_MODE else 'logs'
        os.makedirs(logs_dir, exist_ok=True)

        log_file = os.path.join(logs_dir, 'smarttable.log')

        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        )

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB (原值 10KB 太小)
            backupCount=10,
            encoding='utf-8'  # 确保中文日志正确编码
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)

        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info(f'SmartTable startup (log file: {log_file})')


# 配置映射字典
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
