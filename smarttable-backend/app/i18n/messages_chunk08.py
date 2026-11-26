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

MESSAGES_PART8 = {
    'email_status_not_cancellable': {
        'zh-CN': '邮件状态不允许取消：{0}',
        'en-US': 'Email status does not allow cancellation: {0}',
    },
    'notification_status_not_retriable': {
        'zh-CN': '站内信状态不允许重试：{0}',
        'en-US': 'Notification status does not allow retry: {0}',
    },
    'notification_status_not_cancellable': {
        'zh-CN': '站内信状态不允许取消：{0}',
        'en-US': 'Notification status does not allow cancellation: {0}',
    },
    'unsupported_script_language': {
        'zh-CN': '不支持的脚本语言: {0}（仅支持 python）',
        'en-US': 'Unsupported script language: {0} (only python is supported)',
    },
    'script_execution_timeout': {
        'zh-CN': '脚本执行超时（{0}秒）',
        'en-US': 'Script execution timed out ({0}s)',
    },
    'script_output_not_json_serializable': {
        'zh-CN': '脚本输出无法 JSON 序列化: {0}',
        'en-US': 'Script output could not be JSON serialized: {0}',
    },
    'notification_write_failed': {
        'zh-CN': '写入站内信失败：{0}',
        'en-US': 'Failed to write notification: {0}',
    },
    'notify_node_configuration_object': {
        'zh-CN': '站内信节点的配置必须是对象',
        'en-US': 'The notification node configuration must be an object',
    },
    'notify_recipient_source_required': {
        'zh-CN': '站内信节点至少需要一个接收人来源',
        'en-US': 'The notification node requires at least one recipient source',
    },
    'notify_recipient_source_invalid': {
        'zh-CN': '站内信节点接收人来源无效：{0}',
        'en-US': 'Invalid notification recipient source: {0}',
    },
    'notify_fixed_recipients_required': {
        'zh-CN': '站内信节点选择了「指定成员」，请至少选择一名成员',
        'en-US': 'The notification node uses "Specific members", please select at least one member',
    },
    'notify_field_recipients_required': {
        'zh-CN': '站内信节点选择了「成员字段」，请至少选择一个成员类型字段',
        'en-US': 'The notification node uses "Member field", please select at least one member field',
    },
    'notify_content_string': {
        'zh-CN': '站内信节点的 {0} 必须是字符串',
        'en-US': 'The notification node {0} must be a string',
    },
    'notify_title_required': {
        'zh-CN': '站内信标题不能为空',
        'en-US': 'The notification title cannot be empty',
    },
    'operation_failed_try_again': {
        'zh-CN': '{0}失败，请稍后重试',
        'en-US': '{0} failed, please try again later',
    },
    'webhook_test_send_failed': {
        'zh-CN': 'Webhook 测试发送失败',
        'en-US': 'Webhook test sending failed',
    },
    'unknown_error': {
        'zh-CN': '未知错误',
        'en-US': 'Unknown error',
    },
    'smtp_recipient_refused': {
        'zh-CN': '收件人地址被拒绝：{0}',
        'en-US': 'Recipient address refused: {0}',
    },
    'smtp_sender_refused': {
        'zh-CN': '发件人地址被拒绝：{0}',
        'en-US': 'Sender address refused: {0}',
    },
    'smtp_error': {
        'zh-CN': 'SMTP 错误：{0}',
        'en-US': 'SMTP error: {0}',
    },
    'email_send_failed': {
        'zh-CN': '发送邮件失败：{0}',
        'en-US': 'Failed to send email: {0}',
    },
    'email_template_fetch_failed': {
        'zh-CN': '获取模板失败：{0}',
        'en-US': 'Failed to fetch template: {0}',
    },
    'smtp_auth_failed_check_credentials': {
        'zh-CN': 'SMTP 认证失败：请检查用户名和密码',
        'en-US': 'SMTP authentication failed: please check the username and password',
    },
    'smtp_connection_failed': {
        'zh-CN': '无法连接到 SMTP 服务器：{0}:{1}',
        'en-US': 'Unable to connect to SMTP server: {0}:{1}',
    },
    'invalid_role': {
        'zh-CN': '无效的角色：{0}',
        'en-US': 'Invalid role: {0}',
    },
    'invalid_status': {
        'zh-CN': '无效的状态：{0}',
        'en-US': 'Invalid status: {0}',
    },
    'missing_required_field': {
        'zh-CN': '缺少必需字段：{0}',
        'en-US': 'Missing required field: {0}',
    },
    'file_content_mismatch_extension': {
        'zh-CN': '文件内容与扩展名不匹配（检测到: {0}）',
        'en-US': 'File content does not match extension (detected: {0})',
    },
    'content_changed_size_chars': {
        'zh-CN': '内容变化 {0} 个字符',
        'en-US': 'Content changed by {0} characters',
    },
    'field_type_no_dynamic_default': {
        'zh-CN': '字段类型 {0} 不支持动态默认值',
        'en-US': 'Field type {0} does not support dynamic default values',
    },
    'field_default_value_must_be_string': {
        'zh-CN': '字段类型 {0} 的默认值必须是字符串',
        'en-US': 'Default value for field type {0} must be a string',
    },
    'field_default_value_must_be_number': {
        'zh-CN': '字段类型 {0} 的默认值必须是数字',
        'en-US': 'Default value for field type {0} must be a number',
    },
    'field_default_value_must_be_date_string': {
        'zh-CN': '字段类型 {0} 的默认值必须是日期字符串',
        'en-US': 'Default value for field type {0} must be a date string',
    },
    'field_default_value_must_be_valid_date_format': {
        'zh-CN': '字段类型 {0} 的默认值必须是有效的日期格式',
        'en-US': 'Default value for field type {0} must be a valid date format',
    },
    'field_default_value_must_be_boolean': {
        'zh-CN': '字段类型 {0} 的默认值必须是布尔值',
        'en-US': 'Default value for field type {0} must be a boolean',
    },
    'field_default_value_must_be_option_id': {
        'zh-CN': '字段类型 {0} 的默认值必须是选项 ID',
        'en-US': 'Default value for field type {0} must be an option ID',
    },
    'field_default_value_option_not_exist': {
        'zh-CN': '字段类型 {0} 的默认值对应的选项不存在',
        'en-US': 'The option corresponding to the default value of field type {0} does not exist',
    },
    'field_default_value_must_be_option_id_array': {
        'zh-CN': '字段类型 {0} 的默认值必须是选项 ID 数组',
        'en-US': 'Default value for field type {0} must be an option ID array',
    },
    'field_default_value_contains_nonexistent_options': {
        'zh-CN': '字段类型 {0} 的默认值包含不存在的选项',
        'en-US': 'The default value of field type {0} contains nonexistent options',
    },
    'field_default_value_must_be_array': {
        'zh-CN': '字段类型 {0} 的默认值必须是数组',
        'en-US': 'Default value for field type {0} must be an array',
    },
    'field_default_value_must_be_object': {
        'zh-CN': '字段类型 {0} 的默认值必须是地理信息对象',
        'en-US': 'Default value for field type {0} must be a geo object',
    },
    'invalid_link_type': {
        'zh-CN': '无效的关联类型: {0}',
        'en-US': 'Invalid link type: {0}',
    },
    'target_record_not_exist': {
        'zh-CN': '目标记录不存在: {0}',
        'en-US': 'Target record does not exist: {0}',
    },
    'target_record_not_in_target_table': {
        'zh-CN': '目标记录 {0} 不属于目标表',
        'en-US': 'Target record {0} does not belong to the target table',
    },
    'bidirectional_sync_failed': {
        'zh-CN': '双向同步失败: {0}',
        'en-US': 'Bidirectional sync failed: {0}',
    },
    'sync_record_failed': {
        'zh-CN': '同步记录 {0} 失败: {1}',
        'en-US': 'Failed to sync record {0}: {1}',
    },
    'link_creation_failed': {
        'zh-CN': '建立关联失败: {0}',
        'en-US': 'Failed to create the link: {0}',
    },
    'fetched_user_list_successfully': {
        'zh-CN': '获取用户列表成功',
        'en-US': 'User list retrieved successfully',
    },
    'fetched_operation_logs_successfully': {
        'zh-CN': '获取操作日志成功',
        'en-US': 'Operation logs retrieved successfully',
    },
    'fetched_attachment_list_successfully': {
        'zh-CN': '获取附件列表成功',
        'en-US': 'Attachment list retrieved successfully',
    },
    'fetched_email_sending_logs_successfully': {
        'zh-CN': '获取邮件发送日志成功',
        'en-US': 'Email sending logs retrieved successfully',
    },
    'fetched_delivery_logs_successfully': {
        'zh-CN': '获取投递日志成功',
        'en-US': 'Delivery logs retrieved successfully',
    },
    'fetched_workflow_template_list_successfully': {
        'zh-CN': '获取工作流模板列表成功',
        'en-US': 'Workflow template list retrieved successfully',
    },
    'fetched_instance_list_successfully': {
        'zh-CN': '获取实例列表成功',
        'en-US': 'Workflow instances retrieved successfully',
    },
    'plugin_not_found': {
        'zh-CN': '插件不存在',
        'en-US': 'Plugin not found',
    },
    'plugin_install_failed': {
        'zh-CN': '插件安装失败',
        'en-US': 'Plugin installation failed',
    },
    'plugin_not_enabled': {
        'zh-CN': '插件未启用，需系统管理员先全局启用',
        'en-US': 'Plugin is not enabled; a system admin must enable it globally first',
    },
    'plugin_not_enabled_in_base': {
        'zh-CN': '插件未在当前多维表格启用',
        'en-US': 'Plugin is not enabled in the current Base',
    },
    'plugin_not_ui_type': {
        'zh-CN': '该插件不是前端 UI 插件',
        'en-US': 'This plugin is not a UI plugin',
    },
    'plugin_not_script_type': {
        'zh-CN': '该插件不是后端脚本插件',
        'en-US': 'This plugin is not a script plugin',
    },
    'plugin_endpoint_not_found': {
        'zh-CN': '插件未声明该自定义接口',
        'en-US': 'The plugin does not declare this endpoint',
    },
    'plugin_network_not_declared': {
        'zh-CN': '插件未声明 network 网络访问权限',
        'en-US': 'The plugin does not declare the network permission',
    },
    'plugin_sandbox_token_invalid': {
        'zh-CN': '插件沙箱访问凭证无效或已过期',
        'en-US': 'The plugin sandbox token is invalid or has expired',
    },
    'plugin_loader_error': {
        'zh-CN': '插件加载失败',
        'en-US': 'Failed to load the plugin',
    },
    'plugin_vendor_not_found': {
        'zh-CN': '插件内置资源不存在',
        'en-US': 'Plugin vendor asset not found',
    },
    'package_file_required': {
        'zh-CN': '请上传 .stplugin.zip 安装包',
        'en-US': 'A .stplugin.zip package file is required',
    },
    'package_too_large': {
        'zh-CN': '安装包超过 50MB 大小上限',
        'en-US': 'The package exceeds the 50MB size limit',
    },
    'base_id_required': {
        'zh-CN': '缺少 base_id 参数',
        'en-US': 'base_id is required',
    },
    'base_id_and_enabled_required': {
        'zh-CN': '缺少 base_id 或 enabled 参数',
        'en-US': 'base_id and enabled are required',
    },
    'version_required': {
        'zh-CN': '缺少 version 参数',
        'en-US': 'version is required',
    },
    'scope_and_config_required': {
        'zh-CN': 'scope 与 config 参数无效',
        'en-US': 'Invalid scope or config parameter',
    },
    'proxy_url_required': {
        'zh-CN': '缺少 url 参数',
        'en-US': 'url is required',
    },
    'admin_required_for_global_config': {
        'zh-CN': '仅系统管理员可修改全局配置',
        'en-US': 'Only system admins can modify the global configuration',
    },
    'no_permission_manage_plugin_in_base': {
        'zh-CN': '仅该多维表格的创建者可以管理插件',
        'en-US': 'Only the creator of this Base can manage plugins',
    },
    'no_permission_run_plugin': {
        'zh-CN': '无权运行该插件，需多维表格编辑及以上权限',
        'en-US': 'No permission to run this plugin; editor role or above is required',
    },
    'plugin_type_not_installable': {
        'zh-CN': '仅 UI 插件支持 Base 级安装（脚本插件由 RBAC 与全局启停控制，不依赖 Base 安装）',
        'en-US': 'Only UI plugins support Base-level installation (script plugins are governed by RBAC and the global status)',
    },
    'plugin_version_already_installed': {
        'zh-CN': '插件 {plugin_id} 的 {version} 版本已安装',
        'en-US': 'Version {version} of plugin {plugin_id} is already installed',
    },
    'plugin_downgrade_forbidden': {
        'zh-CN': '不允许降级安装：当前 {current}，上传 {uploaded}',
        'en-US': 'Downgrade is not allowed: current {current}, uploaded {uploaded}',
    },
    'plugin_rollback_version_not_retained': {
        'zh-CN': '插件 {plugin_id} 未保留版本 {version}，无法回滚',
        'en-US': 'Version {version} of plugin {plugin_id} is not retained; rollback is not possible',
    },
    'plugin_invalid_status': {
        'zh-CN': '无效的插件状态：{status}',
        'en-US': 'Invalid plugin status: {status}',
    },
    'plugin_invalid_scope': {
        'zh-CN': '无效的配置作用域：{scope}',
        'en-US': 'Invalid config scope: {scope}',
    },
    'plugin_config_incompatible': {
        'zh-CN': '现有配置与新 configSchema 不兼容：{detail}',
        'en-US': 'The existing configuration is incompatible with the new configSchema: {detail}',
    },
    'plugin_config_schema_invalid': {
        'zh-CN': '配置不符合插件 configSchema 校验：{error}',
        'en-US': 'The configuration does not satisfy the plugin configSchema: {error}',
    },
    'plugin_manifest_missing_field': {
        'zh-CN': 'manifest 缺少必填字段：{field}',
        'en-US': 'manifest is missing a required field: {field}',
    },
    'plugin_manifest_missing_in_package': {
        'zh-CN': '安装包根目录缺少 manifest.json',
        'en-US': 'manifest.json is missing from the package root',
    },
    'plugin_manifest_parse_error': {
        'zh-CN': 'manifest.json 解析失败：{error}',
        'en-US': 'Failed to parse manifest.json: {error}',
    },
    'plugin_manifest_invalid': {
        'zh-CN': 'manifest 校验失败：{error}',
        'en-US': 'manifest validation failed: {error}',
    },
    'plugin_invalid_id': {
        'zh-CN': '插件 ID 需为反向域名格式（如 com.example.name）：{id}',
        'en-US': 'The plugin id must be in reverse-domain format (e.g. com.example.name): {id}',
    },
    'plugin_invalid_type': {
        'zh-CN': '无效的插件类型：{type}',
        'en-US': 'Invalid plugin type: {type}',
    },
    'plugin_version_invalid': {
        'zh-CN': 'version 字段 "{version}" 不是合法的语义化版本号（需 x.y.z 形式，如 1.0.0）',
        'en-US': 'The version field "{version}" is not a valid semantic version (expected x.y.z, e.g. 1.0.0)',
    },
    'plugin_api_version_mismatch': {
        'zh-CN': '插件 apiVersion 与宿主不兼容，宿主支持：{supported}',
        'en-US': 'The plugin apiVersion is incompatible with the host; supported: {supported}',
    },
    'plugin_engines_incompatible': {
        'zh-CN': '当前宿主版本 {host} 不满足插件声明的引擎兼容范围 engines.smarttable: "{range}"（请升级宿主或放宽插件声明）',
        'en-US': 'Host version {host} does not satisfy the plugin engines.smarttable range "{range}"; upgrade the host or relax the plugin declaration',
    },
    'plugin_entry_must_be_js': {
        'zh-CN': 'UI 插件入口必须是 .js 文件：{entry}',
        'en-US': 'A UI plugin entry must be a .js file: {entry}',
    },
    'plugin_script_entry_must_be_py': {
        'zh-CN': '脚本插件入口必须是 .py 文件：{entry}',
        'en-US': 'A script plugin entry must be a .py file: {entry}',
    },
    'plugin_no_extension_points': {
        'zh-CN': 'UI 插件至少需声明一个扩展点',
        'en-US': 'A UI plugin must declare at least one extension point',
    },
    'plugin_invalid_extension_point': {
        'zh-CN': '无效的扩展点类型：{type}',
        'en-US': 'Invalid extension point type: {type}',
    },
    'plugin_script_timeout_invalid': {
        'zh-CN': 'script.timeout 必须是 1~300 之间的整数（秒）',
        'en-US': 'script.timeout must be an integer between 1 and 300 (seconds)',
    },
    'plugin_asset_style_must_be_css': {
        'zh-CN': '样式资源必须是 .css 文件：{path}',
        'en-US': 'A style asset must be a .css file: {path}',
    },
    'plugin_asset_script_must_be_js': {
        'zh-CN': '脚本资源必须是 .js 文件：{path}',
        'en-US': 'A script asset must be a .js file: {path}',
    },
    'plugin_invalid_endpoint_name': {
        'zh-CN': '无效的接口名称：{name}（需小写字母开头，可含数字与连字符）',
        'en-US': 'Invalid endpoint name: {name} (must start with a lowercase letter; digits and hyphens allowed)',
    },
    'plugin_endpoint_entry_must_be_py': {
        'zh-CN': '接口入口必须是 .py 文件：{entry}',
        'en-US': 'An endpoint entry must be a .py file: {entry}',
    },
    'plugin_endpoint_timeout_invalid': {
        'zh-CN': '接口 timeout 必须是 1~300 之间的整数（秒）',
        'en-US': 'The endpoint timeout must be an integer between 1 and 300 (seconds)',
    },
    'plugin_entry_missing': {
        'zh-CN': '安装包缺少入口文件：{entry}',
        'en-US': 'The package is missing the entry file: {entry}',
    },
    'plugin_asset_missing': {
        'zh-CN': '安装包缺少声明的资源文件：{path}',
        'en-US': 'The package is missing a declared asset file: {path}',
    },
    'plugin_endpoint_entry_missing': {
        'zh-CN': '安装包缺少接口文件：{path}',
        'en-US': 'The package is missing an endpoint file: {path}',
    },
    'plugin_package_not_valid_zip': {
        'zh-CN': '安装包不是合法的 zip 文件',
        'en-US': 'The package is not a valid zip file',
    },
    'plugin_package_too_many_files': {
        'zh-CN': '安装包文件数超过上限（{count} > {limit}）',
        'en-US': 'The package contains too many files ({count} > {limit})',
    },
    'plugin_package_unsafe_path': {
        'zh-CN': '安装包包含不安全的路径：{path}',
        'en-US': 'The package contains an unsafe path: {path}',
    },
    'plugin_package_too_large': {
        'zh-CN': '安装包解压后大小超过 {limit}MB 上限',
        'en-US': 'The extracted package exceeds the {limit}MB size limit',
    },
    'plugin_package_suspicious_compression': {
        'zh-CN': '安装包压缩率异常，已拒绝解压：{path}',
        'en-US': 'Suspicious compression ratio; extraction refused: {path}',
    },
    'plugin_package_file_too_large': {
        'zh-CN': '安装包内单个文件过大：{path}',
        'en-US': 'A file inside the package is too large: {path}',
    },
    'plugin_package_files_missing': {
        'zh-CN': '插件包文件缺失：{path}',
        'en-US': 'Plugin package files are missing: {path}',
    },
    'plugin_proxy_rate_limited': {
        'zh-CN': '插件 {plugin_id} 的代理请求过于频繁（上限 {limit} 次/{window} 秒）',
        'en-US': 'Plugin {plugin_id} exceeded the proxy rate limit ({limit} requests/{window}s)',
    },
    'plugin_proxy_invalid_scheme': {
        'zh-CN': '代理地址仅支持 http/https，当前为 {scheme}',
        'en-US': 'Only http/https are allowed for proxying, got {scheme}',
    },
    'plugin_proxy_missing_host': {
        'zh-CN': '代理地址缺少主机名',
        'en-US': 'The proxy URL is missing a host',
    },
    'plugin_proxy_network_not_declared': {
        'zh-CN': '插件未声明 permissions.network 白名单',
        'en-US': 'The plugin did not declare a permissions.network whitelist',
    },
    'plugin_proxy_host_not_allowed': {
        'zh-CN': '目标域名不在 network 白名单内：{host}',
        'en-US': 'The host is not in the network whitelist: {host}',
    },
    'plugin_proxy_ssrf_blocked': {
        'zh-CN': '目标地址解析到受限网段，已拦截：{host}',
        'en-US': 'The target resolves to a restricted address and was blocked: {host}',
    },
    'plugin_proxy_upstream_timeout': {
        'zh-CN': '上游请求超时',
        'en-US': 'The upstream request timed out',
    },
    'plugin_proxy_upstream_error': {
        'zh-CN': '上游请求失败：{error}',
        'en-US': 'The upstream request failed: {error}',
    }
}
