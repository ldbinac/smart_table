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

MESSAGES_PART7 = {
    'no_permission_manage_views': {
        'zh-CN': '无权管理该表格的视图',
        'en-US': 'No permission to manage views of this table',
    },
    'no_permission_manage_fields': {
        'zh-CN': '无权管理该表格的字段',
        'en-US': 'No permission to manage fields of this table',
    },
    'filter_value_field_belong_current_table': {
        'zh-CN': '过滤条件值字段必须属于当前表',
        'en-US': 'The filter value field must belong to the current table',
    },
    'filter_field_belong_source_data_table': {
        'zh-CN': '过滤条件字段必须属于源数据表',
        'en-US': 'The filter field must belong to the source data table',
    },
    'invalid_filter_operator': {
        'zh-CN': '过滤条件操作符不合法',
        'en-US': 'Invalid filter operator',
    },
    'filter_operator_empty': {
        'zh-CN': '过滤条件操作符不能为空',
        'en-US': 'Filter operator cannot be empty',
    },
    'invalid_filter_condition_format': {
        'zh-CN': '过滤条件格式不正确',
        'en-US': 'Invalid filter condition format',
    },
    'email_content_empty': {
        'zh-CN': '邮件内容不能为空',
        'en-US': 'Email content cannot be empty',
    },
    'email_service_not_enabled': {
        'zh-CN': '邮件服务未启用',
        'en-US': 'The email service is not enabled',
    },
    'email_service_not_enabled_configuration_incomplete': {
        'zh-CN': '邮件服务未启用或配置不完整',
        'en-US': 'The email service is not enabled or the configuration is incomplete',
    },
    'email_template': {
        'zh-CN': '邮件模板',
        'en-US': 'Email template',
    },
    'email_template_been_reset_default_content': {
        'zh-CN': '邮件模板已重置为默认内容',
        'en-US': 'The email template has been reset to default content',
    },
    'email_template_updated_successfully': {
        'zh-CN': '邮件模板更新成功',
        'en-US': 'Email template updated successfully',
    },
    'email_configuration_verified_successfully': {
        'zh-CN': '邮件配置验证成功',
        'en-US': 'Email configuration verified successfully',
    },
    'email_retry_sent_successfully': {
        'zh-CN': '邮件重试发送成功',
        'en-US': 'Email retry sent successfully',
    },
    'email_queue_statistics_cleared': {
        'zh-CN': '邮件队列统计已清除',
        'en-US': 'Email queue statistics cleared',
    },
    'email_address_empty': {
        'zh-CN': '邮箱地址不能为空',
        'en-US': 'Email address cannot be empty',
    },
    'invalid_email_address_format': {
        'zh-CN': '邮箱地址格式不正确',
        'en-US': 'Invalid email address format',
    },
    'email_verified': {
        'zh-CN': '邮箱已验证',
        'en-US': 'Email verified',
    },
    'email_verification_succeeded': {
        'zh-CN': '邮箱验证成功',
        'en-US': 'Email verification succeeded',
    },
    'email_verification_email': {
        'zh-CN': '邮箱验证邮件',
        'en-US': 'Email verification email',
    },
    'configuration_does_not_exist': {
        'zh-CN': '配置不存在',
        'en-US': 'Configuration does not exist',
    },
    'configuration_empty': {
        'zh-CN': '配置不能为空',
        'en-US': 'Configuration cannot be empty',
    },
    'configuration_saved_successfully': {
        'zh-CN': '配置保存成功',
        'en-US': 'Configuration saved successfully',
    },
    'redelivered_successfully': {
        'zh-CN': '重新投递成功',
        'en-US': 'Redelivered successfully',
    },
    'reset_token_invalid_expired': {
        'zh-CN': '重置令牌无效或已过期',
        'en-US': 'The reset token is invalid or has expired',
    },
    'failed_reset_password_try_again_later_2': {
        'zh-CN': '重置密码失败，请稍后重试',
        'en-US': 'Failed to reset the password, please try again later',
    },
    'failed_reset_template_try_again_later': {
        'zh-CN': '重置模板失败，请稍后重试',
        'en-US': 'Failed to reset the template, please try again later',
    },
    'failed_reset_email_template_try_again_later': {
        'zh-CN': '重置邮件模板失败，请稍后重试',
        'en-US': 'Failed to reset the email template, please try again later',
    },
    'failed_retry_try_again_later': {
        'zh-CN': '重试失败，请稍后重试',
        'en-US': 'Failed to retry, please try again later',
    },
    'failed_retry_notification_try_again_later': {
        'zh-CN': '重试站内信失败，请稍后重试',
        'en-US': 'Failed to retry the notification, please try again later',
    },
    'attachment': {
        'zh-CN': '附件',
        'en-US': 'Attachment',
    },
    'attachment_deleted_successfully': {
        'zh-CN': '附件删除成功',
        'en-US': 'Attachment deleted successfully',
    },
    'gitee_watch_status_needs_checked': {
        'zh-CN': '需要检测 Gitee watch 状态',
        'en-US': 'The Gitee watch status needs to be checked',
    },
    'access_password_required': {
        'zh-CN': '需要访问密码',
        'en-US': 'An access password is required',
    },
    'color_code_empty': {
        'zh-CN': '颜色代码不能为空',
        'en-US': 'Color code cannot be empty',
    },
    'invalid_color_code_format_ff': {
        'zh-CN': '颜色代码格式不正确（如 #FF5733）',
        'en-US': 'Invalid color code format (e.g. #FF5733)',
    },
    'verification_token_expired': {
        'zh-CN': '验证令牌已过期',
        'en-US': 'The verification token has expired',
    },
    'verification_token_invalid': {
        'zh-CN': '验证令牌无效',
        'en-US': 'The verification token is invalid',
    },
    'verification_failed_try_again_later': {
        'zh-CN': '验证失败，请稍后重试',
        'en-US': 'Verification failed, please try again later',
    },
    'verification_succeeded': {
        'zh-CN': '验证成功',
        'en-US': 'Verification succeeded',
    },
    'failed_generate_captcha_try_again_later': {
        'zh-CN': '验证码生成失败，请稍后重试',
        'en-US': 'Failed to generate the captcha, please try again later',
    },
    'captcha_generated_successfully': {
        'zh-CN': '验证码生成成功',
        'en-US': 'Captcha generated successfully',
    },
    'verified': {
        'zh-CN': '验证通过',
        'en-US': 'Verified',
    },
    'verification_email_sent_check_inbox': {
        'zh-CN': '验证邮件已发送，请查收',
        'en-US': 'Verification email sent, please check your inbox',
    },
    'default_dashboard_set_successfully': {
        'zh-CN': '默认仪表盘设置成功',
        'en-US': 'Default Dashboard set successfully',
    },
    'default_view_deleted': {
        'zh-CN': '默认视图不能删除',
        'en-US': 'The default view cannot be deleted',
    },
    'webhook_config_not_found': {
        'zh-CN': 'Webhook 配置不存在: {0}',
        'en-US': 'Webhook config not found: {0}',
    },
    'webhook_config_not_found_node': {
        'zh-CN': 'Webhook 配置不存在: {0}（节点: {1}, 工作流实例: {2}）',
        'en-US': 'Webhook config not found: {0} (node: {1}, workflow instance: {2})',
    },
    'end_date_format_invalid': {
        'zh-CN': 'end_date 格式不正确: {0}',
        'en-US': 'Invalid end_date format: {0}',
    },
    'end_type_invalid': {
        'zh-CN': 'end_type 不合法: {0}',
        'en-US': 'Invalid end_type: {0}',
    },
    'repeat_type_invalid': {
        'zh-CN': 'repeat_type 不合法: {0}',
        'en-US': 'Invalid repeat_type: {0}',
    },
    'start_datetime_format_invalid': {
        'zh-CN': 'start_date/start_time 格式不正确: {0} {1}',
        'en-US': 'Invalid start_date/start_time format: {0} {1}',
    },
    'repeat_type_unsupported': {
        'zh-CN': '不支持的 repeat_type: {0}',
        'en-US': 'Unsupported repeat_type: {0}',
    },
    'file_type_unsupported_detail': {
        'zh-CN': '不支持的文件类型: {0}',
        'en-US': 'Unsupported file type: {0}',
    },
    'workflow_publish_status_invalid': {
        'zh-CN': '仅草稿或暂停状态可发布，当前状态: {0}',
        'en-US': 'Only workflows in draft or paused status can be published, current status: {0}',
    },
    'link_type_must_be': {
        'zh-CN': '关联类型必须是: {0}',
        'en-US': 'The link type must be one of: {0}',
    },
    'branch_target_node_not_found': {
        'zh-CN': '分支 {0} 的目标节点不存在: {1}',
        'en-US': 'The target node of branch {0} does not exist: {1}',
    },
    'branch_missing_target_node_id': {
        'zh-CN': '分支 {0} 缺少目标节点 ID',
        'en-US': 'Branch {0} is missing the target node ID',
    },
    'branch_label_duplicate': {
        'zh-CN': '分支标签重复: {0}',
        'en-US': 'Duplicate branch label: {0}',
    },
    'workflow_creation_failed': {
        'zh-CN': '创建工作流失败: {0}',
        'en-US': 'Failed to create the workflow: {0}',
    },
    'parent_record_field_creation_failed': {
        'zh-CN': '创建父记录字段失败: {0}',
        'en-US': 'Failed to create the parent record field: {0}',
    },
    'timer_config_missing_required': {
        'zh-CN': '定时器配置缺少必填字段: {0}',
        'en-US': 'Timer configuration is missing the required field: {0}',
    },
    'import_rows_exceed_limit': {
        'zh-CN': '导入数据行数超过限制（最大 {0} 行）',
        'en-US': 'Import row count exceeds the limit (max {0} rows)',
    },
    'records_created_success': {
        'zh-CN': '成功创建 {0} 条记录',
        'en-US': 'Successfully created {0} records',
    },
    'records_deleted_success': {
        'zh-CN': '成功删除 {0} 条记录',
        'en-US': 'Successfully deleted {0} records',
    },
    'records_updated_success': {
        'zh-CN': '成功更新 {0} 条记录',
        'en-US': 'Successfully updated {0} records',
    },
    'batch_add_completed': {
        'zh-CN': '批量添加完成：成功 {0} 个，失败 {1} 个',
        'en-US': 'Batch add completed: {0} succeeded, {1} failed',
    },
    'file_save_failed': {
        'zh-CN': '文件保存失败: {0}',
        'en-US': 'Failed to save the file: {0}',
    },
    'file_size_exceed_limit': {
        'zh-CN': '文件大小超过限制 ({0}MB)',
        'en-US': 'File size exceeds the limit ({0}MB)',
    },
    'file_validation_failed': {
        'zh-CN': '文件验证失败: {0}',
        'en-US': 'File validation failed: {0}',
    },
    'invalid_status_value_detail': {
        'zh-CN': '无效的状态值: {0}',
        'en-US': 'Invalid status value: {0}',
    },
    'no_permission_modify_records_in_table': {
        'zh-CN': '无权修改表格 {0} 中的记录',
        'en-US': 'No permission to modify records in table {0}',
    },
    'no_permission_delete_records_in_table': {
        'zh-CN': '无权删除表格 {0} 中的记录',
        'en-US': 'No permission to delete records in table {0}',
    },
    'csv_read_failed': {
        'zh-CN': '无法读取 CSV 文件: {0}',
        'en-US': 'Failed to read the CSV file: {0}',
    },
    'excel_read_failed': {
        'zh-CN': '无法读取 Excel 文件: {0}',
        'en-US': 'Failed to read the Excel file: {0}',
    },
    'excel_read_failed_short': {
        'zh-CN': '无法读取Excel文件: {0}',
        'en-US': 'Failed to read the Excel file: {0}',
    },
    'timezone_invalid': {
        'zh-CN': '时区无效: {0}',
        'en-US': 'Invalid timezone: {0}',
    },
    'time_field_not_found': {
        'zh-CN': '时间字段不存在: {0}',
        'en-US': 'Time field not found: {0}',
    },
    'time_field_type_invalid': {
        'zh-CN': '时间字段必须为日期或日期时间类型，当前类型: {0}',
        'en-US': 'The time field must be of date or datetime type, current type: {0}',
    },
    'unknown_action_type': {
        'zh-CN': '未知动作类型: {0}',
        'en-US': 'Unknown action type: {0}',
    },
    'unknown_node_type': {
        'zh-CN': '未知节点类型: {0}',
        'en-US': 'Unknown node type: {0}',
    },
    'ai_node_prompt_required': {
        'zh-CN': 'AI 节点缺少 prompt_template 配置',
        'en-US': 'AI node is missing the prompt_template config',
    },
    'test_email_sent_to': {
        'zh-CN': '测试邮件已发送至 {0}',
        'en-US': 'Test email sent to {0}',
    },
    'version_snapshot_saved': {
        'zh-CN': '版本快照已保存: v{0}',
        'en-US': 'Version snapshot saved: v{0}',
    },
    'login_attempts_exceeded': {
        'zh-CN': '登录尝试次数过多，请 {0} 分 {1} 秒后再试',
        'en-US': 'Too many login attempts, please try again in {0} minutes {1} seconds',
    },
    'login_attempts_locked': {
        'zh-CN': '登录尝试次数过多，账户已锁定 {0} 分钟',
        'en-US': 'Too many login attempts, the account has been locked for {0} minutes',
    },
    'target_table_not_found': {
        'zh-CN': '目标表格不存在: {0}',
        'en-US': 'Target table not found: {0}',
    },
    'node_must_be_object': {
        'zh-CN': '第 {0} 个节点必须是对象',
        'en-US': 'Node {0} must be an object',
    },
    'node_type_invalid': {
        'zh-CN': '第 {0} 个节点类型不合法',
        'en-US': 'Invalid type for node {0}',
    },
    'webhook_config_id_missing': {
        'zh-CN': '缺少 Webhook 配置 ID 或内联配置（节点: {0}, 工作流实例: {1}）',
        'en-US': 'Missing Webhook config ID or inline config (node: {0}, workflow instance: {1})',
    },
    'missing_required_fields': {
        'zh-CN': '缺少必需字段: {0}',
        'en-US': 'Missing required fields: {0}',
    },
    'missing_required_scope': {
        'zh-CN': '缺少所需权限范围（scope）：{0}',
        'en-US': 'Missing required scope: {0}',
    },
    'auto_link_creation_failed': {
        'zh-CN': '自动创建关联关系失败: {0}',
        'en-US': 'Failed to auto-create the link relation: {0}',
    },
    'record_not_found': {
        'zh-CN': '记录不存在: {0}',
        'en-US': 'Record not found: {0}',
    },
    'webhook_referenced_cannot_delete': {
        'zh-CN': '该 Webhook 已被 {0} 个工作流节点引用，无法删除，请先解除引用',
        'en-US': 'This Webhook is referenced by {0} workflow nodes and cannot be deleted, please remove the references first',
    },
    'request_too_frequent': {
        'zh-CN': '请求过于频繁，请 {0}后再试',
        'en-US': 'Too many requests, please try again after {0}',
    },
    'notification_send_failed': {
        'zh-CN': '通知发送失败: {0}',
        'en-US': 'Failed to send the notification: {0}',
    },
    'redelivery_failed': {
        'zh-CN': '重新投递失败: {0}',
        'en-US': 'Redelivery failed: {0}',
    },
    'form_share_invalid_fields': {
        'zh-CN': '以下字段不存在: {0}',
        'en-US': 'The following fields do not exist: {0}',
    },
    'form_share_create_failed': {
        'zh-CN': '创建失败: {0}',
        'en-US': 'Creation failed: {0}',
    },
    'form_share_update_failed': {
        'zh-CN': '更新失败: {0}',
        'en-US': 'Update failed: {0}',
    },
    'form_share_delete_failed': {
        'zh-CN': '删除失败: {0}',
        'en-US': 'Deletion failed: {0}',
    },
    'invalid_field_type_supported_types': {
        'zh-CN': '无效的字段类型。支持的类型: {0}',
        'en-US': 'Invalid field type. Supported types: {0}',
    },
    'options_required_for_field_type': {
        'zh-CN': '{0} 类型字段必须提供选项列表',
        'en-US': 'Options list is required for field type {0}',
    },
    'formula_expression_required': {
        'zh-CN': '公式表达式不能为空',
        'en-US': 'Formula expression is required',
    },
    'formula_unknown_field_reference': {
        'zh-CN': '公式引用了不存在的字段: {0}',
        'en-US': 'Formula references unknown field(s): {0}',
    },
    'cannot_convert_field_type': {
        'zh-CN': '不能将 {0} 转换为 {1}',
        'en-US': 'Cannot convert {0} to {1}',
    },
    'field_type_conversion_requires_confirmation': {
        'zh-CN': '将 {0} 转换为 {1} 会丢失部分数据，请确认后重试',
        'en-US': 'Converting {0} to {1} will lose some data. Please confirm and try again',
    },
    'field_type_conversion_incompatible_values': {
        'zh-CN': '存在 {0} 条数据无法转换为目标类型，已取消本次转换',
        'en-US': '{0} value(s) cannot be converted to the target type. Conversion cancelled',
    },
    'field_type_conversion_blocked_system_type': {
        'zh-CN': '系统字段类型不支持转换字段类型',
        'en-US': 'System field types do not support changing the field type',
    },
    'field_type_conversion_blocked_reference_type': {
        'zh-CN': '关联、查找、汇总等引用类型不支持转换字段类型',
        'en-US': 'Reference types such as link, lookup and rollup do not support changing the field type',
    },
    'field_type_conversion_blocked_target_formula': {
        'zh-CN': '不支持将字段转换为公式类型',
        'en-US': 'Converting a field to the formula type is not supported',
    },
    'field_type_conversion_blocked_lossy': {
        'zh-CN': '该字段已有数据，不支持此类型转换（可能会丢失数据）',
        'en-US': 'This field already has data; this conversion is not supported because it would lose data',
    },
    'field_type_conversion_text_to_contact_blocked': {
        'zh-CN': '文本字段已有数据，不支持转换为电话/邮箱/链接（原有文本可能不符合目标格式校验）',
        'en-US': 'Text fields with existing data cannot be converted to phone, email or URL (the existing text may fail the target format validation)',
    },
    'field_type_conversion_primary_text_only': {
        'zh-CN': '主字段仅支持在文本类型之间转换',
        'en-US': 'The primary field can only be converted between text types',
    },
    'field_type_conversion_notice_formula_freeze': {
        'zh-CN': '转换后该字段将不再自动重算，当前计算结果会被保留为静态值',
        'en-US': 'After conversion this field will no longer recalculate; the current result is kept as a static value',
    },
    'field_type_conversion_notice_keep_member_id': {
        'zh-CN': '转换后将保留成员 ID 文本，不再与成员关联',
        'en-US': 'After conversion the member ID text is kept and the member link is removed',
    },
    'field_type_conversion_notice_keep_option_id': {
        'zh-CN': '转换后将保留选项 ID 文本，不再与选项关联',
        'en-US': 'After conversion the option ID text is kept and the option link is removed',
    },
    'field_type_conversion_lossy_datetime_to_date': {
        'zh-CN': '转换后将仅保留日期部分，时间部分会被丢弃且不可恢复',
        'en-US': 'After conversion only the date part is kept; the time part is discarded and cannot be recovered',
    },
    'system_field_type_cannot_delete': {
        'zh-CN': '{0} 是系统字段类型，不能被删除',
        'en-US': 'Field type {0} is a system field type and cannot be deleted',
    },
    'approval_task_create_failed': {
        'zh-CN': '创建审批任务失败: {0}',
        'en-US': 'Failed to create approval task: {0}',
    },
    'approval_transfer_task_failed': {
        'zh-CN': '创建转交任务失败: {0}',
        'en-US': 'Failed to create transfer task: {0}',
    },
    'link_relationship_conflict': {
        'zh-CN': '关联关系冲突: {0}',
        'en-US': 'Link relationship conflict: {0}',
    },
    'link_conflict_existing_type': {
        'zh-CN': '已存在不同类型的关联字段 "{0}"，类型为 {1}',
        'en-US': 'A link field "{0}" with a different type already exists, type: {1}',
    },
    'template_not_found': {
        'zh-CN': '模板不存在：{0}',
        'en-US': 'Template not found: {0}',
    },
    'default_template_not_found': {
        'zh-CN': '不存在默认模板：{0}',
        'en-US': 'Default template not found: {0}',
    },
    'email_log_not_found': {
        'zh-CN': '日志不存在：{0}',
        'en-US': 'Email log not found: {0}',
    },
    'email_status_not_retriable': {
        'zh-CN': '邮件状态不允许重试：{0}',
        'en-US': 'Email status does not allow retry: {0}',
    }
}
