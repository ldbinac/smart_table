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

MESSAGES_PART9 = {
    'plugin_proxy_response_too_large': {
        'zh-CN': '上游响应超过 {limit} 字节上限',
        'en-US': 'The upstream response exceeds {limit} bytes',
    },
    'print_template_not_found': {
        'zh-CN': '打印模板不存在',
        'en-US': 'Print template not found',
    },
    'print_template_name_empty': {
        'zh-CN': '模板名称不能为空',
        'en-US': 'Template name cannot be empty',
    },
    'print_template_name_exceed_characters': {
        'zh-CN': '模板名称不能超过 100 个字符',
        'en-US': 'Template name cannot exceed 100 characters',
    },
    'print_template_description_exceed_limit': {
        'zh-CN': '模板描述过长',
        'en-US': 'Template description is too long',
    },
    'print_template_table_empty': {
        'zh-CN': '缺少绑定表格',
        'en-US': 'Missing bound table',
    },
    'print_template_table_not_in_base': {
        'zh-CN': '表格不属于当前 Base',
        'en-US': 'Table does not belong to the current base',
    },
    'print_template_json_empty': {
        'zh-CN': '模板内容不能为空',
        'en-US': 'Template content cannot be empty',
    },
    'print_template_json_invalid': {
        'zh-CN': '模板内容不是有效的 JSON 对象',
        'en-US': 'Template content is not a valid JSON object',
    },
    'print_template_json_exceed_limit': {
        'zh-CN': '模板内容过大（超过 1MB）',
        'en-US': 'Template content is too large (exceeds 1MB)',
    },
    'print_template_visibility_invalid': {
        'zh-CN': '无效的模板可见性',
        'en-US': 'Invalid template visibility',
    },
    'print_template_min_role_invalid': {
        'zh-CN': '无效的最低使用角色',
        'en-US': 'Invalid minimum role',
    },
    'print_template_no_permission_create': {
        'zh-CN': '没有权限创建打印模板',
        'en-US': 'No permission to create print templates',
    },
    'print_template_no_permission_view': {
        'zh-CN': '没有权限访问该打印模板',
        'en-US': 'No permission to access this print template',
    },
    'print_template_no_permission_modify': {
        'zh-CN': '只有模板创建者或 Base 管理员可以编辑该模板',
        'en-US': 'Only the template creator or base admin can modify this template',
    },
    'print_template_no_permission_delete': {
        'zh-CN': '只有模板创建者或 Base 管理员可以删除该模板',
        'en-US': 'Only the template creator or base admin can delete this template',
    },
    'print_template_created_successfully': {
        'zh-CN': '打印模板创建成功',
        'en-US': 'Print template created successfully',
    },
    'print_template_updated_successfully': {
        'zh-CN': '打印模板更新成功',
        'en-US': 'Print template updated successfully',
    },
    'print_template_deleted_successfully': {
        'zh-CN': '打印模板删除成功',
        'en-US': 'Print template deleted successfully',
    },
    'fetched_print_template_list_successfully': {
        'zh-CN': '获取打印模板列表成功',
        'en-US': 'Print template list retrieved successfully',
    },
    'fetched_print_template_details_successfully': {
        'zh-CN': '获取打印模板详情成功',
        'en-US': 'Print template details retrieved successfully',
    },
    'folder_not_empty': {
        'zh-CN': '文件夹不为空，无法删除',
        'en-US': 'The folder is not empty and cannot be deleted',
    },
    'folder_name_required': {
        'zh-CN': '文件夹名称不能为空',
        'en-US': 'Folder name is required',
    },
    'folder_name_exceed_characters': {
        'zh-CN': '文件夹名称不能超过 100 个字符',
        'en-US': 'Folder name cannot exceed 100 characters',
    },
    'folder_not_in_base': {
        'zh-CN': '文件夹不存在或不属于当前 Base',
        'en-US': 'The folder does not exist or does not belong to this base',
    },
    'table_folder_not_found': {
        'zh-CN': '文件夹不存在',
        'en-US': 'The folder does not exist',
    },
    'fetched_table_folder_list_successfully': {
        'zh-CN': '获取文件夹列表成功',
        'en-US': 'Folder list fetched successfully',
    },
    'table_folder_created_successfully': {
        'zh-CN': '文件夹创建成功',
        'en-US': 'Folder created successfully',
    },
    'table_folder_updated_successfully': {
        'zh-CN': '文件夹更新成功',
        'en-US': 'Folder updated successfully',
    },
    'table_folder_deleted_successfully': {
        'zh-CN': '文件夹删除成功',
        'en-US': 'Folder deleted successfully',
    },
    '获取应用列表成功': {
        'zh-CN': '获取应用列表成功',
        'en-US': 'Application list retrieved successfully'
    },
    '应用创建成功': {
        'zh-CN': '应用创建成功',
        'en-US': 'Application created successfully'
    },
    '获取应用详情成功': {
        'zh-CN': '获取应用详情成功',
        'en-US': 'Application details retrieved successfully'
    },
    '应用更新成功': {
        'zh-CN': '应用更新成功',
        'en-US': 'Application updated successfully'
    },
    '应用删除成功': {
        'zh-CN': '应用删除成功',
        'en-US': 'Application deleted successfully'
    },
    '获取菜单树成功': {
        'zh-CN': '获取菜单树成功',
        'en-US': 'Menu tree retrieved successfully'
    },
    '菜单创建成功': {
        'zh-CN': '菜单创建成功',
        'en-US': 'Menu created successfully'
    },
    '菜单更新成功': {
        'zh-CN': '菜单更新成功',
        'en-US': 'Menu updated successfully'
    },
    '菜单删除成功': {
        'zh-CN': '菜单删除成功',
        'en-US': 'Menu deleted successfully'
    },
    '菜单重排序成功': {
        'zh-CN': '菜单重排序成功',
        'en-US': 'Menu reordered successfully'
    },
    '获取页面列表成功': {
        'zh-CN': '获取页面列表成功',
        'en-US': 'Page list retrieved successfully'
    },
    '页面创建成功': {
        'zh-CN': '页面创建成功',
        'en-US': 'Page created successfully'
    },
    '页面更新成功': {
        'zh-CN': '页面更新成功',
        'en-US': 'Page updated successfully'
    },
    '页面删除成功': {
        'zh-CN': '页面删除成功',
        'en-US': 'Page deleted successfully'
    },
    '组件添加成功': {
        'zh-CN': '组件添加成功',
        'en-US': 'Component added successfully'
    },
    '组件更新成功': {
        'zh-CN': '组件更新成功',
        'en-US': 'Component updated successfully'
    },
    '组件重排序成功': {
        'zh-CN': '组件重排序成功',
        'en-US': 'Component reordered successfully'
    },
    '组件删除成功': {
        'zh-CN': '组件删除成功',
        'en-US': 'Component deleted successfully'
    },
    '获取权限配置成功': {
        'zh-CN': '获取权限配置成功',
        'en-US': 'Permission configuration retrieved successfully'
    },
    '权限配置更新成功': {
        'zh-CN': '权限配置更新成功',
        'en-US': 'Permission configuration updated successfully'
    },
    '应用发布成功': {
        'zh-CN': '应用发布成功',
        'en-US': 'Application published successfully'
    },
    '应用已取消发布': {
        'zh-CN': '应用已取消发布',
        'en-US': 'Application unpublished'
    },
    '获取模板列表成功': {
        'zh-CN': '获取模板列表成功',
        'en-US': 'Template list retrieved successfully'
    },
    '模板导入成功': {
        'zh-CN': '模板导入成功',
        'en-US': 'Template imported successfully'
    },
    '从模板创建应用成功': {
        'zh-CN': '从模板创建应用成功',
        'en-US': 'Application created from template successfully'
    },
    '获取组件列表成功': {
        'zh-CN': '获取组件列表成功',
        'en-US': 'Component list retrieved successfully'
    },
    '获取登录页配置成功': {
        'zh-CN': '获取登录页配置成功',
        'en-US': 'Login page configuration retrieved successfully'
    },
    '应用登录成功': {
        'zh-CN': '应用登录成功',
        'en-US': 'Application login successful'
    },
    '应用登出成功': {
        'zh-CN': '应用登出成功',
        'en-US': 'Application logout successful'
    },
    '会话有效': {
        'zh-CN': '会话有效',
        'en-US': 'Session is valid'
    },
    '游客会话创建成功': {
        'zh-CN': '游客会话创建成功',
        'en-US': 'Guest session created successfully'
    },
    '密码修改成功': {
        'zh-CN': '密码修改成功',
        'en-US': 'Password changed successfully'
    },
    '获取应用列表失败': {
        'zh-CN': '获取应用列表失败',
        'en-US': 'Failed to retrieve application list'
    },
    '获取菜单树失败': {
        'zh-CN': '获取菜单树失败',
        'en-US': 'Failed to retrieve menu tree'
    },
    '获取组件列表失败': {
        'zh-CN': '获取组件列表失败',
        'en-US': 'Failed to retrieve component list'
    },
    '该应用未启用独立登录页': {
        'zh-CN': '该应用未启用独立登录页',
        'en-US': 'This application has not enabled the independent login page'
    },
    '应用未发布，无法访问': {
        'zh-CN': '应用未发布，无法访问',
        'en-US': 'Application is not published and cannot be accessed'
    },
    '新密码不能与旧密码相同': {
        'zh-CN': '新密码不能与旧密码相同',
        'en-US': 'New password cannot be the same as the old password'
    },
    '无法获取当前用户信息': {
        'zh-CN': '无法获取当前用户信息',
        'en-US': 'Unable to retrieve current user information'
    },
    '您没有权限访问此应用': {
        'zh-CN': '您没有权限访问此应用',
        'en-US': 'You do not have permission to access this application'
    },
    '缺少应用级会话 Token': {
        'zh-CN': '缺少应用级会话 Token',
        'en-US': 'Missing application-level session token'
    },
    '请上传模板文件': {
        'zh-CN': '请上传模板文件',
        'en-US': 'Please upload a template file'
    },
    '未选择文件': {
        'zh-CN': '未选择文件',
        'en-US': 'No file selected'
    },
    '仅支持 .json 格式的模板文件': {
        'zh-CN': '仅支持 .json 格式的模板文件',
        'en-US': 'Only .json format template files are supported'
    },
    'file_encoding_error': {
        'zh-CN': '文件编码错误，请使用 UTF-8 编码：{error}',
        'en-US': 'File encoding error, please use UTF-8 encoding: {error}'
    },
    'file_read_error': {
        'zh-CN': '文件读取失败：{error}',
        'en-US': 'Failed to read file: {error}'
    },
    '应用不存在': {
        'zh-CN': '应用不存在',
        'en-US': 'Application not found'
    },
    '菜单不存在': {
        'zh-CN': '菜单不存在',
        'en-US': 'Menu not found'
    },
    '页面不存在': {
        'zh-CN': '页面不存在',
        'en-US': 'Page not found'
    },
    '组件不存在': {
        'zh-CN': '组件不存在',
        'en-US': 'Component not found'
    },
    '模板不存在': {
        'zh-CN': '模板不存在',
        'en-US': 'Template not found'
    },
    '需要应用管理员权限': {
        'zh-CN': '需要应用管理员权限',
        'en-US': 'Application administrator permission is required'
    },
    '仅系统管理员或应用 Owner 可更新应用': {
        'zh-CN': '仅系统管理员或应用 Owner 可更新应用',
        'en-US': 'Only system administrator or application Owner can update the application'
    },
    '仅系统管理员或应用 Owner 可删除应用': {
        'zh-CN': '仅系统管理员或应用 Owner 可删除应用',
        'en-US': 'Only system administrator or application Owner can delete the application'
    },
    '仅系统管理员或应用 Owner 可发布应用': {
        'zh-CN': '仅系统管理员或应用 Owner 可发布应用',
        'en-US': 'Only system administrator or application Owner can publish the application'
    },
    '仅系统管理员或应用 Owner 可取消发布应用': {
        'zh-CN': '仅系统管理员或应用 Owner 可取消发布应用',
        'en-US': 'Only system administrator or application Owner can unpublish the application'
    },
    '无编辑权限': {
        'zh-CN': '无编辑权限',
        'en-US': 'No edit permission'
    },
    '仅自定义页面支持添加组件': {
        'zh-CN': '仅自定义页面支持添加组件',
        'en-US': 'Only custom pages support adding components'
    },
    '该应用未启用游客访问': {
        'zh-CN': '该应用未启用游客访问',
        'en-US': 'This application has not enabled guest access'
    },
    '应用未发布': {
        'zh-CN': '应用未发布',
        'en-US': 'Application is not published'
    },
    '应用未发布，无法登录': {
        'zh-CN': '应用未发布，无法登录',
        'en-US': 'Application is not published and cannot be logged into'
    },
    '登录失败，请稍后重试': {
        'zh-CN': '登录失败，请稍后重试',
        'en-US': 'Login failed, please try again later'
    },
    '用户名或密码错误': {
        'zh-CN': '用户名或密码错误',
        'en-US': 'Incorrect username or password'
    },
    '账号已被禁用，请联系管理员': {
        'zh-CN': '账号已被禁用，请联系管理员',
        'en-US': 'Account has been disabled, please contact the administrator'
    },
    '您没有访问该应用的权限': {
        'zh-CN': '您没有访问该应用的权限',
        'en-US': 'You do not have permission to access this application'
    },
    '缺少会话 Token': {
        'zh-CN': '缺少会话 Token',
        'en-US': 'Missing session token'
    },
    '会话不存在或已失效': {
        'zh-CN': '会话不存在或已失效',
        'en-US': 'Session does not exist or has expired'
    },
    '会话已过期': {
        'zh-CN': '会话已过期',
        'en-US': 'Session has expired'
    },
    '用户不存在': {
        'zh-CN': '用户不存在',
        'en-US': 'User does not exist'
    },
    '用户账号已被禁用': {
        'zh-CN': '用户账号已被禁用',
        'en-US': 'User account has been disabled'
    },
    'app_create_failed': {
        'zh-CN': '创建应用失败：{error}',
        'en-US': 'Failed to create application: {error}'
    },
    'app_update_failed': {
        'zh-CN': '更新应用失败：{error}',
        'en-US': 'Failed to update application: {error}'
    },
    'app_delete_failed': {
        'zh-CN': '删除应用失败：{error}',
        'en-US': 'Failed to delete application: {error}'
    },
    'app_publish_failed': {
        'zh-CN': '发布应用失败：{error}',
        'en-US': 'Failed to publish application: {error}'
    },
    'app_unpublish_failed': {
        'zh-CN': '取消发布应用失败：{error}',
        'en-US': 'Failed to unpublish application: {error}'
    },
    'menu_create_failed': {
        'zh-CN': '创建菜单失败：{error}',
        'en-US': 'Failed to create menu: {error}'
    },
    'menu_update_failed': {
        'zh-CN': '更新菜单失败：{error}',
        'en-US': 'Failed to update menu: {error}'
    },
    'menu_delete_failed': {
        'zh-CN': '删除菜单失败：{error}',
        'en-US': 'Failed to delete menu: {error}'
    },
    'menu_reorder_failed': {
        'zh-CN': '重排序菜单失败：{error}',
        'en-US': 'Failed to reorder menu: {error}'
    },
    'page_create_failed': {
        'zh-CN': '创建页面失败：{error}',
        'en-US': 'Failed to create page: {error}'
    },
    'page_update_failed': {
        'zh-CN': '更新页面失败：{error}',
        'en-US': 'Failed to update page: {error}'
    },
    'page_delete_failed': {
        'zh-CN': '删除页面失败：{error}',
        'en-US': 'Failed to delete page: {error}'
    },
    'component_add_failed': {
        'zh-CN': '添加组件失败：{error}',
        'en-US': 'Failed to add component: {error}'
    },
    'component_update_failed': {
        'zh-CN': '更新组件失败：{error}',
        'en-US': 'Failed to update component: {error}'
    },
    'component_delete_failed': {
        'zh-CN': '删除组件失败：{error}',
        'en-US': 'Failed to delete component: {error}'
    },
    'component_reorder_failed': {
        'zh-CN': '重排序组件失败：{error}',
        'en-US': 'Failed to reorder component: {error}'
    },
    'permission_config_get_failed': {
        'zh-CN': '获取权限配置失败：{error}',
        'en-US': 'Failed to get permission configuration: {error}'
    },
    'permission_config_update_failed': {
        'zh-CN': '更新权限配置失败：{error}',
        'en-US': 'Failed to update permission configuration: {error}'
    },
    'role_assign_failed': {
        'zh-CN': '分配角色失败：{error}',
        'en-US': 'Failed to assign role: {error}'
    },
    'role_revoke_failed': {
        'zh-CN': '撤销角色失败：{error}',
        'en-US': 'Failed to revoke role: {error}'
    },
    'template_import_failed': {
        'zh-CN': '导入模板失败：{error}',
        'en-US': 'Failed to import template: {error}'
    },
    'template_export_failed': {
        'zh-CN': '导出模板失败：{error}',
        'en-US': 'Failed to export template: {error}'
    },
    'template_builtin_missing_config': {
        'zh-CN': '内置模板 "{error}" 缺少配置数据，请刷新页面后重试',
        'en-US': 'Built-in template "{error}" is missing configuration data, please refresh and retry'
    },
    'app_create_from_template_failed': {
        'zh-CN': '从模板创建应用失败：{error}',
        'en-US': 'Failed to create application from template: {error}'
    },
    'json_parse_failed': {
        'zh-CN': 'JSON 解析失败：{error}',
        'en-US': 'JSON parsing failed: {error}'
    },
    'template_import_from_file_failed': {
        'zh-CN': '从文件导入模板失败：{error}',
        'en-US': 'Failed to import template from file: {error}'
    },
    'app_export_as_template_failed': {
        'zh-CN': '导出应用为模板失败：{error}',
        'en-US': 'Failed to export application as template: {error}'
    },
    'auth_logout_failed': {
        'zh-CN': '登出失败：{error}',
        'en-US': 'Failed to logout: {error}'
    },
    'auth_session_validate_failed': {
        'zh-CN': '验证会话失败：{error}',
        'en-US': 'Failed to validate session: {error}'
    },
    'auth_guest_session_create_failed': {
        'zh-CN': '创建游客会话失败：{error}',
        'en-US': 'Failed to create guest session: {error}'
    },
    '仅系统管理员或应用 Owner 可配置权限': {
        'zh-CN': '仅系统管理员或应用 Owner 可配置权限',
        'en-US': 'Only system administrator or application Owner can configure permissions'
    },
    '仅系统管理员或应用 Owner 可分配角色': {
        'zh-CN': '仅系统管理员或应用 Owner 可分配角色',
        'en-US': 'Only system administrator or application Owner can assign roles'
    },
    '不能修改 Owner 角色': {
        'zh-CN': '不能修改 Owner 角色',
        'en-US': 'Cannot modify the owner role'
    },
    '仅系统管理员或应用 Owner 可撤销角色': {
        'zh-CN': '仅系统管理员或应用 Owner 可撤销角色',
        'en-US': 'Only system administrator or application Owner can revoke roles'
    },
    '用户未分配角色': {
        'zh-CN': '用户未分配角色',
        'en-US': 'User has not been assigned a role'
    },
    '不能撤销 Owner 角色': {
        'zh-CN': '不能撤销 Owner 角色',
        'en-US': 'Cannot revoke the owner role'
    },
    '仅系统管理员或应用 Owner 可导出模板': {
        'zh-CN': '仅系统管理员或应用 Owner 可导出模板',
        'en-US': 'Only system administrator or application Owner can export the template'
    },
    '文件内容为空': {
        'zh-CN': '文件内容为空',
        'en-US': 'File content is empty'
    },
    '模板根结构必须是 JSON 对象': {
        'zh-CN': '模板根结构必须是 JSON 对象',
        'en-US': 'Template root structure must be a JSON object'
    },
    '模板缺少必填字段：name': {
        'zh-CN': '模板缺少必填字段：name',
        'en-US': 'Template is missing required field: name'
    },
    '所有者，完全控制': {
        'zh-CN': '所有者，完全控制',
        'en-US': 'Owner, with full control'
    },
    '编辑者，可编辑内容和结构': {
        'zh-CN': '编辑者，可编辑内容和结构',
        'en-US': 'Editor, can edit content and structure'
    },
    '查看者，只读访问': {
        'zh-CN': '查看者，只读访问',
        'en-US': 'Viewer, read-only access'
    },
    '自定义角色': {
        'zh-CN': '自定义角色',
        'en-US': 'Custom role'
    },
    '完全控制': {
        'zh-CN': '完全控制',
        'en-US': 'Full control'
    },
    '编辑内容和结构': {
        'zh-CN': '编辑内容和结构',
        'en-US': 'Edit content and structure'
    },
    '只读访问': {
        'zh-CN': '只读访问',
        'en-US': 'Read-only access'
    }
}
