"""
SmartTable 后端 i18n 模块

提供 API 响应消息的多语言翻译能力。

工作原理：
1. before_request 钩子解析 Accept-Language header，存入 g.language
2. response.py / handlers.py 的默认消息使用 i18n key
3. translate() 函数根据 g.language 查找 MESSAGES 字典返回对应语言文本
4. 未找到 key 时原样返回，确保渐进式迁移期间的向后兼容

使用示例：
    from app.i18n import translate
    msg = translate('operation_success')  # 自动从 g.language 获取语言
    msg = translate('validation_error', lang='en-US')  # 指定语言
"""
from app.i18n.utils import translate, get_current_language, set_current_language
from app.i18n.messages import MESSAGES, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

__all__ = [
    'translate',
    'get_current_language',
    'set_current_language',
    'MESSAGES',
    'SUPPORTED_LANGUAGES',
    'DEFAULT_LANGUAGE',
]
