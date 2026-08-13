"""
i18n 翻译工具函数

提供 translate() 函数和语言上下文管理。
"""
from flask import g, has_request_context
from typing import Optional

from app.i18n.messages import MESSAGES, DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES


def _normalize_language(accept_language: str) -> str:
    """
    从 Accept-Language header 值中解析出首选语言代码。

    Accept-Language 格式示例："zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    取第一个匹配 SUPPORTED_LANGUAGES 的语言；若无匹配则返回 DEFAULT_LANGUAGE。

    支持的匹配策略：
    1. 精确匹配（如 "zh-CN" → "zh-CN"）
    2. 前缀匹配（如 "zh" → "zh-CN"，"en" → "en-US"）

    Args:
        accept_language: Accept-Language header 原始值

    Returns:
        匹配的语言代码，或默认语言
    """
    if not accept_language:
        return DEFAULT_LANGUAGE

    # 解析 Accept-Language 值，按 q 值排序
    # 格式: "zh-CN,zh;q=0.9,en-US;q=0.8"
    languages = []
    for part in accept_language.split(','):
        part = part.strip()
        if not part:
            continue
        if ';q=' in part:
            lang, q_str = part.split(';q=', 1)
            try:
                q = float(q_str)
            except ValueError:
                q = 1.0
        else:
            lang = part
            q = 1.0
        languages.append((lang.strip(), q))

    # 按 q 值降序排序
    languages.sort(key=lambda x: x[1], reverse=True)

    # 依次尝试匹配
    for lang, _ in languages:
        lang_lower = lang.lower()

        # 精确匹配
        for supported in SUPPORTED_LANGUAGES:
            if lang_lower == supported.lower():
                return supported

        # 前缀匹配（zh → zh-CN, en → en-US）
        for supported in SUPPORTED_LANGUAGES:
            prefix = supported.split('-')[0].lower()
            if lang_lower == prefix:
                return supported

    return DEFAULT_LANGUAGE


def get_current_language() -> str:
    """
    获取当前请求的语言代码。

    优先级：
    1. g.language（由 before_request 钩子设置）
    2. DEFAULT_LANGUAGE（回退）

    Returns:
        当前语言代码（如 'zh-CN'、'en-US'）
    """
    if has_request_context():
        lang = getattr(g, 'language', None)
        if lang:
            return lang
    return DEFAULT_LANGUAGE


def set_current_language(lang: str) -> None:
    """
    设置当前请求的语言代码（存储在 g 对象上）。

    Args:
        lang: 语言代码
    """
    if has_request_context():
        g.language = lang


def parse_accept_language(accept_language: str) -> str:
    """
    解析 Accept-Language header，返回标准化语言代码。
    供 before_request 钩子调用。

    Args:
        accept_language: Accept-Language header 值

    Returns:
        标准化后的语言代码
    """
    return _normalize_language(accept_language)


def translate(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """
    翻译消息 key 为指定语言的文本。

    采用"key 优先、原文兜底"策略：
    - 若 key 在 MESSAGES 中存在，返回对应语言的翻译
    - 若 key 不在 MESSAGES 中，原样返回 key（兼容未改造的硬编码消息）
    - 若指定语言无翻译，回退到 DEFAULT_LANGUAGE
    - 若 DEFAULT_LANGUAGE 也无翻译，返回 key 原文

    Args:
        key: 消息 key（如 'operation_success'）或原始消息文本
        lang: 语言代码，None 时自动从请求上下文获取
        **kwargs: 模板参数（用于 {field} 等占位符替换）

    Returns:
        翻译后的文本
    """
    # 确定语言
    if lang is None:
        lang = get_current_language()

    # key 不在翻译字典中 → 原样返回（兼容硬编码中文消息）
    if key not in MESSAGES:
        result = key
    else:
        translations = MESSAGES[key]
        # 优先使用指定语言
        result = translations.get(lang)
        # 回退到默认语言
        if result is None:
            result = translations.get(DEFAULT_LANGUAGE)
        # 默认语言也没有 → 返回 key 原文
        if result is None:
            result = key

    # 模板参数替换（如 translate('field_required', field='邮箱') → '邮箱不能为空'）
    if kwargs:
        try:
            result = result.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            # 模板参数不匹配时保留原文
            pass

    return result
