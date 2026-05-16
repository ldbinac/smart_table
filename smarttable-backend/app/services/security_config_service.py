"""
安全配置服务模块
处理系统安全配置的获取和应用，包括密码策略、会话超时、注册开关等
"""
import logging
from typing import Optional, Tuple, Any

from app.models.config import SystemConfig

logger = logging.getLogger(__name__)


class SecurityConfigService:
    """
    安全配置服务类
    提供系统安全相关配置的获取和验证功能
    """
    
    # 配置默认值
    DEFAULT_PASSWORD_MIN_LENGTH = 8
    DEFAULT_SESSION_TIMEOUT_MINUTES = 60  # 1小时
    DEFAULT_ENABLE_2FA = False
    DEFAULT_ENABLE_REGISTRATION = True
    DEFAULT_PASSWORD_REQUIRE_UPPERCASE = False
    DEFAULT_PASSWORD_REQUIRE_LOWERCASE = False
    DEFAULT_PASSWORD_REQUIRE_DIGIT = False
    DEFAULT_PASSWORD_REQUIRE_SPECIAL = False
    
    # 配置键名常量
    KEY_PASSWORD_MIN_LENGTH = 'password_min_length'
    KEY_SESSION_TIMEOUT = 'session_timeout'
    KEY_ENABLE_2FA = 'enable_2fa'
    KEY_ENABLE_REGISTRATION = 'enable_registration'
    KEY_PASSWORD_REQUIRE_UPPERCASE = 'password_require_uppercase'
    KEY_PASSWORD_REQUIRE_LOWERCASE = 'password_require_lowercase'
    KEY_PASSWORD_REQUIRE_DIGIT = 'password_require_digit'
    KEY_PASSWORD_REQUIRE_SPECIAL = 'password_require_special'
    
    @staticmethod
    def get_password_min_length() -> int:
        """
        获取密码最小长度配置
        
        Returns:
            密码最小长度，默认 8
        """
        try:
            config = SystemConfig.query.filter_by(
                config_key=SecurityConfigService.KEY_PASSWORD_MIN_LENGTH
            ).first()
            
            if config and config.config_value is not None:
                value = int(config.config_value)
                # 确保在合理范围内
                if 6 <= value <= 50:
                    return value
                logger.warning(f"配置值 {value} 超出合理范围，使用默认值")
            
            return SecurityConfigService.DEFAULT_PASSWORD_MIN_LENGTH
            
        except Exception as e:
            logger.error(f"获取密码最小长度配置失败: {str(e)}")
            return SecurityConfigService.DEFAULT_PASSWORD_MIN_LENGTH
    
    @staticmethod
    def get_session_timeout_minutes() -> int:
        """
        获取会话超时时间配置（分钟）
        
        Returns:
            会话超时时间，单位：分钟，默认 60
        """
        try:
            config = SystemConfig.query.filter_by(
                config_key=SecurityConfigService.KEY_SESSION_TIMEOUT
            ).first()
            
            if config and config.config_value is not None:
                value = int(config.config_value)
                # 确保在合理范围内（5分钟 - 24小时）
                if 5 <= value <= 1440:
                    return value
                logger.warning(f"配置值 {value} 超出合理范围，使用默认值")
            
            return SecurityConfigService.DEFAULT_SESSION_TIMEOUT_MINUTES
            
        except Exception as e:
            logger.error(f"获取会话超时配置失败: {str(e)}")
            return SecurityConfigService.DEFAULT_SESSION_TIMEOUT_MINUTES
    
    @staticmethod
    def get_enable_2fa() -> bool:
        """
        获取是否启用双因素认证配置
        
        Returns:
            是否启用，默认 False
        """
        try:
            config = SystemConfig.query.filter_by(
                config_key=SecurityConfigService.KEY_ENABLE_2FA
            ).first()
            
            if config and config.config_value is not None:
                return bool(config.config_value)
            
            return SecurityConfigService.DEFAULT_ENABLE_2FA
            
        except Exception as e:
            logger.error(f"获取双因素认证配置失败: {str(e)}")
            return SecurityConfigService.DEFAULT_ENABLE_2FA
    
    @staticmethod
    def get_enable_registration() -> bool:
        """
        获取是否允许用户注册配置
        
        Returns:
            是否允许，默认 True
        """
        try:
            config = SystemConfig.query.filter_by(
                config_key=SecurityConfigService.KEY_ENABLE_REGISTRATION
            ).first()
            
            if config and config.config_value is not None:
                return bool(config.config_value)
            
            return SecurityConfigService.DEFAULT_ENABLE_REGISTRATION
            
        except Exception as e:
            logger.error(f"获取注册开关配置失败: {str(e)}")
            return SecurityConfigService.DEFAULT_ENABLE_REGISTRATION
    
    @staticmethod
    def get_password_require_uppercase() -> bool:
        """
        获取密码是否需要大写字母
        
        Returns:
            是否需要，默认 False
        """
        try:
            config = SystemConfig.query.filter_by(
                config_key=SecurityConfigService.KEY_PASSWORD_REQUIRE_UPPERCASE
            ).first()
            
            if config and config.config_value is not None:
                return bool(config.config_value)
            
            return SecurityConfigService.DEFAULT_PASSWORD_REQUIRE_UPPERCASE
            
        except Exception as e:
            logger.error(f"获取密码大写字母要求配置失败: {str(e)}")
            return SecurityConfigService.DEFAULT_PASSWORD_REQUIRE_UPPERCASE
    
    @staticmethod
    def get_password_require_lowercase() -> bool:
        """
        获取密码是否需要小写字母
        
        Returns:
            是否需要，默认 False
        """
        try:
            config = SystemConfig.query.filter_by(
                config_key=SecurityConfigService.KEY_PASSWORD_REQUIRE_LOWERCASE
            ).first()
            
            if config and config.config_value is not None:
                return bool(config.config_value)
            
            return SecurityConfigService.DEFAULT_PASSWORD_REQUIRE_LOWERCASE
            
        except Exception as e:
            logger.error(f"获取密码小写字母要求配置失败: {str(e)}")
            return SecurityConfigService.DEFAULT_PASSWORD_REQUIRE_LOWERCASE
    
    @staticmethod
    def get_password_require_digit() -> bool:
        """
        获取密码是否需要数字
        
        Returns:
            是否需要，默认 False
        """
        try:
            config = SystemConfig.query.filter_by(
                config_key=SecurityConfigService.KEY_PASSWORD_REQUIRE_DIGIT
            ).first()
            
            if config and config.config_value is not None:
                return bool(config.config_value)
            
            return SecurityConfigService.DEFAULT_PASSWORD_REQUIRE_DIGIT
            
        except Exception as e:
            logger.error(f"获取密码数字要求配置失败: {str(e)}")
            return SecurityConfigService.DEFAULT_PASSWORD_REQUIRE_DIGIT
    
    @staticmethod
    def get_password_require_special() -> bool:
        """
        获取密码是否需要特殊字符
        
        Returns:
            是否需要，默认 False
        """
        try:
            config = SystemConfig.query.filter_by(
                config_key=SecurityConfigService.KEY_PASSWORD_REQUIRE_SPECIAL
            ).first()
            
            if config and config.config_value is not None:
                return bool(config.config_value)
            
            return SecurityConfigService.DEFAULT_PASSWORD_REQUIRE_SPECIAL
            
        except Exception as e:
            logger.error(f"获取密码特殊字符要求配置失败: {str(e)}")
            return SecurityConfigService.DEFAULT_PASSWORD_REQUIRE_SPECIAL
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
        """
        验证密码强度是否符合配置要求
        
        Args:
            password: 密码字符串
            
        Returns:
            (是否有效, 错误信息) - 有效时错误信息为 None
        """
        min_length = SecurityConfigService.get_password_min_length()
        require_uppercase = SecurityConfigService.get_password_require_uppercase()
        require_lowercase = SecurityConfigService.get_password_require_lowercase()
        require_digit = SecurityConfigService.get_password_require_digit()
        require_special = SecurityConfigService.get_password_require_special()
        
        # 检查长度
        if len(password) < min_length:
            return False, f'密码长度至少为 {min_length} 位'
        
        # 检查大写字母
        if require_uppercase and not any(c.isupper() for c in password):
            return False, '密码必须包含大写字母'
        
        # 检查小写字母
        if require_lowercase and not any(c.islower() for c in password):
            return False, '密码必须包含小写字母'
        
        # 检查数字
        if require_digit and not any(c.isdigit() for c in password):
            return False, '密码必须包含数字'
        
        # 检查特殊字符
        special_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?/'
        if require_special and not any(c in special_chars for c in password):
            return False, '密码必须包含特殊字符 (!@#$%^&*()_+-=[]{}|;:,.<>?/)'
        
        return True, None
    
    @staticmethod
    def is_registration_enabled() -> bool:
        """
        检查是否允许新用户注册
        
        Returns:
            是否允许注册
        """
        return SecurityConfigService.get_enable_registration()
    
    @staticmethod
    def get_all_security_configs() -> dict:
        """
        获取所有安全配置（用于管理接口）
        
        Returns:
            包含所有安全配置的字典
        """
        return {
            SecurityConfigService.KEY_PASSWORD_MIN_LENGTH: SecurityConfigService.get_password_min_length(),
            SecurityConfigService.KEY_SESSION_TIMEOUT: SecurityConfigService.get_session_timeout_minutes(),
            SecurityConfigService.KEY_ENABLE_2FA: SecurityConfigService.get_enable_2fa(),
            SecurityConfigService.KEY_ENABLE_REGISTRATION: SecurityConfigService.get_enable_registration(),
            SecurityConfigService.KEY_PASSWORD_REQUIRE_UPPERCASE: SecurityConfigService.get_password_require_uppercase(),
            SecurityConfigService.KEY_PASSWORD_REQUIRE_LOWERCASE: SecurityConfigService.get_password_require_lowercase(),
            SecurityConfigService.KEY_PASSWORD_REQUIRE_DIGIT: SecurityConfigService.get_password_require_digit(),
            SecurityConfigService.KEY_PASSWORD_REQUIRE_SPECIAL: SecurityConfigService.get_password_require_special()
        }
