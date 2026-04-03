"""
验证器模块
提供各种数据验证函数
"""
import re
import uuid
from typing import Optional, Tuple
from datetime import datetime


class ValidationError(Exception):
    """验证错误异常"""
    pass


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    验证邮箱地址
    
    Args:
        email: 邮箱地址
        
    Returns:
        (是否有效, 错误信息)
    """
    if not email:
        return False, '邮箱地址不能为空'
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, '邮箱地址格式不正确'
    
    return True, None


def validate_password(password: str, min_length: int = 8) -> Tuple[bool, Optional[str]]:
    """
    验证密码强度
    
    Args:
        password: 密码
        min_length: 最小长度
        
    Returns:
        (是否有效, 错误信息)
    """
    if not password:
        return False, '密码不能为空'
    
    if len(password) < min_length:
        return False, f'密码长度至少为 {min_length} 位'
    
    # 检查是否包含至少一个大写字母
    if not re.search(r'[A-Z]', password):
        return False, '密码必须包含至少一个大写字母'
    
    # 检查是否包含至少一个小写字母
    if not re.search(r'[a-z]', password):
        return False, '密码必须包含至少一个小写字母'
    
    # 检查是否包含至少一个数字
    if not re.search(r'\d', password):
        return False, '密码必须包含至少一个数字'
    
    return True, None


def validate_uuid(value: str) -> Tuple[bool, Optional[str]]:
    """
    验证 UUID 格式
    
    Args:
        value: UUID 字符串
        
    Returns:
        (是否有效, 错误信息)
    """
    if not value:
        return False, 'UUID 不能为空'
    
    try:
        uuid.UUID(value)
        return True, None
    except ValueError:
        return False, '无效的 UUID 格式'


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    验证 URL 格式
    
    Args:
        url: URL 字符串
        
    Returns:
        (是否有效, 错误信息)
    """
    if not url:
        return False, 'URL 不能为空'
    
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    if not re.match(pattern, url):
        return False, 'URL 格式不正确'
    
    return True, None


def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """
    验证手机号码格式（中国大陆）
    
    Args:
        phone: 手机号码
        
    Returns:
        (是否有效, 错误信息)
    """
    if not phone:
        return False, '手机号码不能为空'
    
    pattern = r'^1[3-9]\d{9}$'
    if not re.match(pattern, phone):
        return False, '手机号码格式不正确'
    
    return True, None


def validate_hex_color(color: str) -> Tuple[bool, Optional[str]]:
    """
    验证十六进制颜色代码
    
    Args:
        color: 颜色代码（如 #FF5733）
        
    Returns:
        (是否有效, 错误信息)
    """
    if not color:
        return False, '颜色代码不能为空'
    
    pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
    if not re.match(pattern, color):
        return False, '颜色代码格式不正确（如 #FF5733）'
    
    return True, None


def validate_date_string(date_str: str, format: str = '%Y-%m-%d') -> Tuple[bool, Optional[str]]:
    """
    验证日期字符串格式
    
    Args:
        date_str: 日期字符串
        format: 日期格式
        
    Returns:
        (是否有效, 错误信息)
    """
    if not date_str:
        return False, '日期不能为空'
    
    try:
        datetime.strptime(date_str, format)
        return True, None
    except ValueError:
        return False, f'日期格式不正确，应为 {format}'


def validate_length(
    value: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    field_name: str = '字段'
) -> Tuple[bool, Optional[str]]:
    """
    验证字符串长度
    
    Args:
        value: 字符串值
        min_length: 最小长度
        max_length: 最大长度
        field_name: 字段名称
        
    Returns:
        (是否有效, 错误信息)
    """
    if value is None:
        return False, f'{field_name}不能为空'
    
    length = len(value)
    
    if min_length is not None and length < min_length:
        return False, f'{field_name}长度至少为 {min_length} 个字符'
    
    if max_length is not None and length > max_length:
        return False, f'{field_name}长度不能超过 {max_length} 个字符'
    
    return True, None


def validate_number(
    value,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    allow_float: bool = True,
    field_name: str = '数值'
) -> Tuple[bool, Optional[str]]:
    """
    验证数值范围
    
    Args:
        value: 数值
        min_value: 最小值
        max_value: 最大值
        allow_float: 是否允许小数
        field_name: 字段名称
        
    Returns:
        (是否有效, 错误信息)
    """
    if value is None:
        return False, f'{field_name}不能为空'
    
    try:
        if allow_float:
            num_value = float(value)
        else:
            num_value = int(value)
    except (ValueError, TypeError):
        return False, f'{field_name}必须是{"小数" if allow_float else "整数"}'
    
    if min_value is not None and num_value < min_value:
        return False, f'{field_name}不能小于 {min_value}'
    
    if max_value is not None and num_value > max_value:
        return False, f'{field_name}不能大于 {max_value}'
    
    return True, None


def sanitize_string(value: str, max_length: int = 255) -> str:
    """
    清理字符串，移除危险字符
    
    Args:
        value: 原始字符串
        max_length: 最大长度
        
    Returns:
        清理后的字符串
    """
    if not value:
        return ''
    
    # 移除 HTML 标签
    value = re.sub(r'<[^>]+>', '', value)
    
    # 限制长度
    value = value[:max_length]
    
    # 去除首尾空白
    value = value.strip()
    
    return value


def validate_field_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    验证字段名称
    
    Args:
        name: 字段名称
        
    Returns:
        (是否有效, 错误信息)
    """
    if not name:
        return False, '字段名称不能为空'
    
    if len(name) > 100:
        return False, '字段名称不能超过 100 个字符'
    
    # 检查是否包含非法字符
    if re.search(r'[<>&"\']', name):
        return False, '字段名称包含非法字符'
    
    return True, None
