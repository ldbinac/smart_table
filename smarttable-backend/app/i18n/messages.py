# Auto-split skeleton

"""
i18n 翻译消息字典

结构：{ key: { lang: text } }
key 命名规范：蛇形命名（snake_case），与后端 error code 风格一致。

新增语言时：
1. 在 SUPPORTED_LANGUAGES 中添加语言代码
2. 为每个 key 添加对应语言的翻译
3. 在 app/__init__.py 的 parse_language 中无需改动（已通用处理）

新增消息时：
1. 添加 key 及各语言翻译
2. 在 response.py / handlers.py 中使用 translate('key') 替换硬编码消息
"""

# 默认语言（回退语言）
DEFAULT_LANGUAGE = 'zh-CN'

# 已支持的语言列表（按优先级排列）
# 新增语言时在此添加，例如 'ja-JP', 'zh-TW'
SUPPORTED_LANGUAGES = ['zh-CN', 'en-US']

# 翻译消息字典
# key → { lang → text }

from .messages_chunk01 import MESSAGES_PART1
from .messages_chunk02 import MESSAGES_PART2
from .messages_chunk03 import MESSAGES_PART3
from .messages_chunk04 import MESSAGES_PART4
from .messages_chunk05 import MESSAGES_PART5
from .messages_chunk06 import MESSAGES_PART6
from .messages_chunk07 import MESSAGES_PART7
from .messages_chunk08 import MESSAGES_PART8
from .messages_chunk09 import MESSAGES_PART9

MESSAGES = {}
MESSAGES.update(MESSAGES_PART1)
MESSAGES.update(MESSAGES_PART2)
MESSAGES.update(MESSAGES_PART3)
MESSAGES.update(MESSAGES_PART4)
MESSAGES.update(MESSAGES_PART5)
MESSAGES.update(MESSAGES_PART6)
MESSAGES.update(MESSAGES_PART7)
MESSAGES.update(MESSAGES_PART8)
MESSAGES.update(MESSAGES_PART9)
