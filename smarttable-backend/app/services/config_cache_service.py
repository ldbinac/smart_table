"""
系统配置缓存服务
使用 Redis 缓存系统配置，提升性能
"""
import json
import logging
from typing import Optional, Dict, Any
from functools import wraps

from app.extensions import redis_client, db
from app.models.config import SystemConfig

logger = logging.getLogger(__name__)

# 配置缓存键前缀
CONFIG_CACHE_PREFIX = 'system:config:'
# 配置组缓存键
CONFIG_GROUP_KEY = f'{CONFIG_CACHE_PREFIX}all'
# 单个配置键格式：CONFIG_CACHE_PREFIX + key
# 缓存过期时间（秒），默认24小时
DEFAULT_CACHE_TTL = 24 * 60 * 60


def redis_available():
    """检查 Redis 是否可用"""
    return redis_client is not None


class ConfigCacheService:
    """系统配置缓存服务"""

    @staticmethod
    def _serialize_value(value: Any) -> str:
        """序列化配置值为字符串"""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    @staticmethod
    def _deserialize_value(value_str: Optional[str]) -> Any:
        """反序列化配置值"""
        if value_str is None:
            return None
        try:
            # 尝试解析为 JSON
            return json.loads(value_str)
        except (json.JSONDecodeError, TypeError):
            # 如果解析失败则返回原始字符串
            return value_str

    @staticmethod
    def get_all_configs_from_cache() -> Optional[Dict[str, Dict[str, Any]]]:
        """
        从缓存获取所有配置（按分组）
        
        Returns:
            配置字典 {group: {key: value}}，如果缓存不存在返回 None
        """
        if not redis_available():
            return None
        
        try:
            cache_value = redis_client.get(CONFIG_GROUP_KEY)
            if cache_value:
                return json.loads(cache_value)
            return None
        except Exception as e:
            logger.warning(f'从Redis获取配置缓存失败: {e}')
            return None

    @staticmethod
    def set_all_configs_to_cache(configs: Dict[str, Dict[str, Any]]) -> bool:
        """
        将所有配置缓存到 Redis
        
        Args:
            configs: 配置字典 {group: {key: value}}
        
        Returns:
            是否缓存成功
        """
        if not redis_available():
            return False
        
        try:
            cache_value = json.dumps(configs, ensure_ascii=False)
            redis_client.setex(CONFIG_GROUP_KEY, DEFAULT_CACHE_TTL, cache_value)
            
            # 同时也缓存单个配置项
            for group, group_configs in configs.items():
                for key, value in group_configs.items():
                    ConfigCacheService.set_config_to_cache(key, value)
            
            return True
        except Exception as e:
            logger.warning(f'缓存配置到Redis失败: {e}')
            return False

    @staticmethod
    def get_config_from_cache(key: str) -> Optional[Any]:
        """
        从缓存获取单个配置
        
        Args:
            key: 配置键
        
        Returns:
            配置值，如果缓存不存在返回 None
        """
        if not redis_available():
            return None
        
        try:
            cache_value = redis_client.get(f'{CONFIG_CACHE_PREFIX}{key}')
            return ConfigCacheService._deserialize_value(cache_value)
        except Exception as e:
            logger.warning(f'从Redis获取配置{key}缓存失败: {e}')
            return None

    @staticmethod
    def set_config_to_cache(key: str, value: Any) -> bool:
        """
        将单个配置缓存到 Redis
        
        Args:
            key: 配置键
            value: 配置值
        
        Returns:
            是否缓存成功
        """
        if not redis_available():
            return False
        
        try:
            cache_value = ConfigCacheService._serialize_value(value)
            redis_client.setex(f'{CONFIG_CACHE_PREFIX}{key}', DEFAULT_CACHE_TTL, cache_value)
            return True
        except Exception as e:
            logger.warning(f'缓存配置{key}到Redis失败: {e}')
            return False

    @staticmethod
    def invalidate_config_cache(key: Optional[str] = None) -> bool:
        """
        失效配置缓存
        
        Args:
            key: 配置键，如果为 None 则失效所有缓存
        
        Returns:
            是否成功
        """
        if not redis_available():
            return False
        
        try:
            if key:
                redis_client.delete(f'{CONFIG_CACHE_PREFIX}{key}')
            redis_client.delete(CONFIG_GROUP_KEY)
            return True
        except Exception as e:
            logger.warning(f'失效配置缓存失败: {e}')
            return False

    @staticmethod
    def get_config(key: str) -> Optional[Any]:
        """
        获取配置（优先缓存，没有则查数据库
        
        Args:
            key: 配置键
        
        Returns:
            配置值，如果不存在返回 None
        """
        # 优先从缓存获取
        cached_value = ConfigCacheService.get_config_from_cache(key)
        if cached_value is not None:
            return cached_value
        
        # 缓存没有，查数据库
        config = SystemConfig.query.filter_by(config_key=key).first()
        if config:
            # 缓存起来
            ConfigCacheService.set_config_to_cache(key, config.config_value)
            return config.config_value
        
        return None

    @staticmethod
    def get_all_configs() -> Dict[str, Dict[str, Any]]:
        """
        获取所有配置（优先缓存）
        
        Returns:
            配置字典 {group: {key: value}}
        """
        # 优先从缓存获取
        cached_configs = ConfigCacheService.get_all_configs_from_cache()
        if cached_configs is not None:
            return cached_configs
        
        # 缓存没有，查数据库
        configs = SystemConfig.query.all()
        
        result = {}
        for config in configs:
            group = config.config_group
            if group not in result:
                result[group] = {}
            result[group][config.config_key] = config.config_value
        
        # 缓存起来
        ConfigCacheService.set_all_configs_to_cache(result)
        
        return result

    @staticmethod
    def update_config(key: str, value: Any, group: str = 'basic') -> bool:
        """
        更新配置，同时更新缓存
        
        Args:
            key: 配置键
            value: 配置值
            group: 配置分组
        
        Returns:
            是否成功
        """
        # 更新数据库，这个由调用者处理
        
        # 失效缓存（全部失效更简单，也可以只失效相关的
        ConfigCacheService.invalidate_config_cache(key)
        return True

    @staticmethod
    def get_public_configs() -> Dict[str, Dict[str, Any]]:
        """
        获取公开配置（安全相关的配置，用于登录页等未登录场景
        
        Returns:
            公开配置字典
        """
        all_configs = ConfigCacheService.get_all_configs()
        
        public_configs = {}
        
        # 只返回安全配置，用于前端注册等
        if 'security' in all_configs:
            public_configs['security'] = {}
            security_config = all_configs['security']
            
            # 只返回这些安全配置
            public_configs['security']['enable_registration'] = security_config.get('enable_registration', True)
            public_configs['security']['password_min_length'] = security_config.get('password_min_length', 8)
            public_configs['security']['session_timeout'] = security_config.get('session_timeout', 60)
            public_configs['security']['password_require_uppercase'] = security_config.get('password_require_uppercase', False)
            public_configs['security']['password_require_lowercase'] = security_config.get('password_require_lowercase', False)
            public_configs['security']['password_require_digit'] = security_config.get('password_require_digit', False)
            public_configs['security']['password_require_special'] = security_config.get('password_require_special', False)
        
        # 如果有基础配置中的公开部分
        if 'basic' in all_configs:
            public_configs['basic'] = {}
            basic_config = all_configs['basic']
            # 只返回必要的基础配置
            public_configs['basic']['system_name'] = basic_config.get('system_name', '')
            public_configs['basic']['system_description'] = basic_config.get('system_description', '')
        
        return public_configs
