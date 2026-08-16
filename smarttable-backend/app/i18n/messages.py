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
MESSAGES = {
    # ===== 通用操作 =====
    'operation_success': {
        'zh-CN': '操作成功',
        'en-US': 'Operation successful',
    },
    'operation_failed': {
        'zh-CN': '操作失败',
        'en-US': 'Operation failed',
    },
    'fetch_success': {
        'zh-CN': '获取成功',
        'en-US': 'Fetched successfully',
    },
    'create_success': {
        'zh-CN': '创建成功',
        'en-US': 'Created successfully',
    },
    'update_success': {
        'zh-CN': '更新成功',
        'en-US': 'Updated successfully',
    },
    'delete_success': {
        'zh-CN': '删除成功',
        'en-US': 'Deleted successfully',
    },

    # ===== 请求错误 =====
    'bad_request': {
        'zh-CN': '请求格式错误',
        'en-US': 'Bad request format',
    },
    'param_error': {
        'zh-CN': '请求参数错误',
        'en-US': 'Invalid request parameters',
    },
    'request_body_empty': {
        'zh-CN': '请求体不能为空',
        'en-US': 'Request body cannot be empty',
    },
    'method_not_allowed': {
        'zh-CN': '不支持的请求方法',
        'en-US': 'Request method not allowed',
    },

    # ===== 认证与授权 =====
    'unauthorized': {
        'zh-CN': '请先登录',
        'en-US': 'Please log in first',
    },
    'unauthorized_access': {
        'zh-CN': '未授权访问',
        'en-US': 'Unauthorized access',
    },
    'forbidden': {
        'zh-CN': '权限不足',
        'en-US': 'Permission denied',
    },
    'permission_denied': {
        'zh-CN': '权限不足',
        'en-US': 'Permission denied',
    },
    'authentication_failed': {
        'zh-CN': '认证失败',
        'en-US': 'Authentication failed',
    },
    'token_invalid': {
        'zh-CN': '认证令牌无效，请重新登录',
        'en-US': 'Authentication token is invalid, please log in again',
    },
    'login_expired': {
        'zh-CN': '登录已过期，请重新登录',
        'en-US': 'Login expired, please log in again',
    },

    # ===== 资源相关 =====
    'not_found': {
        'zh-CN': '请求的资源不存在',
        'en-US': 'The requested resource was not found',
    },
    'resource_not_found': {
        'zh-CN': '资源不存在',
        'en-US': 'Resource not found',
    },
    'conflict': {
        'zh-CN': '资源冲突',
        'en-US': 'Resource conflict',
    },
    'duplicate_entry': {
        'zh-CN': '数据已存在，请勿重复添加',
        'en-US': 'Data already exists, please do not add duplicates',
    },
    'foreign_key_constraint': {
        'zh-CN': '关联的数据不存在',
        'en-US': 'Associated data does not exist',
    },
    'not_null_constraint': {
        'zh-CN': '必填字段不能为空',
        'en-US': 'Required field cannot be empty',
    },

    # ===== 数据验证 =====
    'validation_error': {
        'zh-CN': '数据验证失败',
        'en-US': 'Data validation failed',
    },
    'validation_failed': {
        'zh-CN': '数据验证失败',
        'en-US': 'Data validation failed',
    },

    # ===== 数据库错误 =====
    'integrity_error': {
        'zh-CN': '数据操作失败',
        'en-US': 'Data operation failed',
    },
    'database_error': {
        'zh-CN': '数据库操作失败，请稍后重试',
        'en-US': 'Database operation failed, please try again later',
    },

    # ===== 服务器错误 =====
    'http_error': {
        'zh-CN': '服务器错误',
        'en-US': 'Server error',
    },
    'internal_server_error': {
        'zh-CN': '服务器内部错误，请稍后重试',
        'en-US': 'Internal server error, please try again later',
    },

    # ===== 默认表格视图（创建空白表格时自动生成的视图）=====
    'default_table_view_name': {
        'zh-CN': '表格视图',
        'en-US': 'Table View',
    },
    'default_table_view_description': {
        'zh-CN': '默认表格视图',
        'en-US': 'Default table view',
    },
}
