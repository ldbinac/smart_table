"""
应用配置模块
包含开发、测试、生产环境的配置类
"""
import os
from datetime import timedelta


class Config:
    """基础配置类"""
    
    # Flask 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # 数据库配置 (默认使用 SQLite 进行开发)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///smarttable.db'
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
    
    # MinIO 配置
    MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT', 'localhost:9000')
    MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY')
    MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY')
    MINIO_BUCKET_NAME = os.environ.get('MINIO_BUCKET_NAME', 'smarttable')
    MINIO_SECURE = os.environ.get('MINIO_SECURE', 'False').lower() == 'true'
    
    # 分页配置
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # CORS 配置
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-not-for-production'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-jwt-secret-not-for-production'
    MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY') or 'minioadmin'
    MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY') or 'minioadmin'


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
        # 强制校验关键环境变量
        if not app.config.get('SECRET_KEY'):
            raise RuntimeError("生产环境必须设置 SECRET_KEY 环境变量")
        if not app.config.get('JWT_SECRET_KEY'):
            raise RuntimeError("生产环境必须设置 JWT_SECRET_KEY 环境变量")
        if not app.config.get('CORS_ORIGINS'):
            raise RuntimeError("生产环境必须设置 CORS_ORIGINS 环境变量（逗号分隔的允许来源列表）")
        
        # 配置日志
        import logging
        from logging.handlers import RotatingFileHandler
        
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        )
        
        file_handler = RotatingFileHandler(
            'logs/smarttable.log',
            maxBytes=10240,
            backupCount=10
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('SmartTable startup')


# 配置映射字典
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
