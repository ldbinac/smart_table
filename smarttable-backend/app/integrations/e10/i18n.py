"""E10 集成内部使用的最小 i18n 文案，避免修改上游 i18n 字典。"""
from __future__ import annotations

_MESSAGES = {
    'e10_sso_not_enabled': {
        'zh-CN': '泛微 E10 单点登录未启用',
        'en-US': 'Weaver E10 SSO is not enabled',
    },
    'e10_sso_misconfigured': {
        'zh-CN': '泛微 E10 单点登录配置不完整，请联系管理员',
        'en-US': 'Weaver E10 SSO is misconfigured, please contact the administrator',
    },
    'e10_sso_only_login': {
        'zh-CN': '本系统已启用泛微 E10 单点登录，请从 E10 登录',
        'en-US': 'This system uses Weaver E10 single sign-on. Please sign in from E10.',
    },
    'e10_login_success': {
        'zh-CN': '登录成功',
        'en-US': 'Logged in successfully',
    },
    'e10_ticket_missing': {
        'zh-CN': '登录票据缺失，请重新登录',
        'en-US': 'Login ticket is missing, please sign in again',
    },
    'e10_ticket_invalid': {
        'zh-CN': '登录票据无效或已过期，请重新登录',
        'en-US': 'Login ticket is invalid or expired, please sign in again',
    },
    'e10_ticket_used': {
        'zh-CN': '登录票据已被使用，请重新登录',
        'en-US': 'Login ticket has already been used, please sign in again',
    },
    'e10_user_not_provisioned': {
        'zh-CN': '您的 E10 账号尚未开通 SmartTable 访问权限，请联系管理员',
        'en-US': 'Your E10 account has not been provisioned for SmartTable, please contact the administrator',
    },
    'e10_email_not_configured': {
        'zh-CN': 'E10 账号映射未配置邮箱，请联系管理员',
        'en-US': 'E10 account mapping has no email address, please contact the administrator',
    },
    'e10_account_disabled': {
        'zh-CN': '账号已被停用，请联系管理员',
        'en-US': 'Your account is disabled, please contact the administrator',
    },
    'e10_internal_error': {
        'zh-CN': 'E10 登录处理失败，请稍后重试',
        'en-US': 'E10 login failed, please try again later',
    },
}


def t(key: str) -> str:
    """按当前请求语言返回文案；未知 key 原样返回。"""
    try:
        from app.i18n import get_current_language

        lang = get_current_language() or 'zh-CN'
    except Exception:
        lang = 'zh-CN'
    messages = _MESSAGES.get(key, {})
    return messages.get(lang) or messages.get('zh-CN') or key
