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

MESSAGES_PART5 = {
    'title_content_empty': {
        'zh-CN': '标题和内容不能为空',
        'en-US': 'Title and content cannot be empty',
    },
    'template_deleted_successfully': {
        'zh-CN': '模板删除成功',
        'en-US': 'Template deleted successfully',
    },
    'template_name_exceed_characters': {
        'zh-CN': '模板名称不能超过200个字符',
        'en-US': 'Template name cannot exceed 200 characters',
    },
    'welcome_smarttable': {
        'zh-CN': '欢迎注册 SmartTable',
        'en-US': 'Welcome to SmartTable',
    },
    'file_no_thumbnail': {
        'zh-CN': '此文件没有缩略图',
        'en-US': 'This file has no thumbnail',
    },
    'file_type_does_not_support_preview': {
        'zh-CN': '此文件类型不支持预览',
        'en-US': 'This file type does not support preview',
    },
    'each_base_most_documents': {
        'zh-CN': '每个 Base 最多创建 10 个文档',
        'en-US': 'Each Base can have at most 10 documents',
    },
    'no_pending_notifications': {
        'zh-CN': '没有待处理的站内信',
        'en-US': 'No pending notifications',
    },
    'no_pending_emails': {
        'zh-CN': '没有待处理的邮件',
        'en-US': 'No pending emails',
    },
    'no_valid_update_fields_provided': {
        'zh-CN': '没有提供有效的更新字段',
        'en-US': 'No valid update fields provided',
    },
    'test_failed_try_again_later': {
        'zh-CN': '测试失败，请稍后重试',
        'en-US': 'Test failed, please try again later',
    },
    'invalid_test_email_address_format': {
        'zh-CN': '测试邮箱地址格式不正确',
        'en-US': 'Invalid test email address format',
    },
    'member_added_successfully': {
        'zh-CN': '添加成员成功',
        'en-US': 'Member added successfully',
    },
    'failed_clear_email_queue_statistics_try_again_later': {
        'zh-CN': '清除邮件队列统计失败，请稍后重试',
        'en-US': 'Failed to clear email queue statistics, please try again later',
    },
    'failed_render_template_check_template_format': {
        'zh-CN': '渲染模板失败，请检查模板格式',
        'en-US': 'Failed to render the template, please check the template format',
    },
    'source_base_does_not_exist': {
        'zh-CN': '源基础数据不存在',
        'en-US': 'Source base does not exist',
    },
    'source_field_does_not_exist': {
        'zh-CN': '源字段不存在',
        'en-US': 'Source field does not exist',
    },
    'source_field_link_type': {
        'zh-CN': '源字段必须是关联字段类型',
        'en-US': 'The source field must be a link type',
    },
    'source_data_table_empty': {
        'zh-CN': '源数据表不能为空',
        'en-US': 'Source data table cannot be empty',
    },
    'source_data_table_same_base_current_table': {
        'zh-CN': '源数据表必须与当前表在同一个多维表格中',
        'en-US': 'The source data table must be in the same base as the current table',
    },
    'source_table_does_not_exist': {
        'zh-CN': '源表不存在',
        'en-US': 'Source table does not exist',
    },
    'source_record_does_not_exist': {
        'zh-CN': '源记录不存在',
        'en-US': 'Source record does not exist',
    },
    'condition_met': {
        'zh-CN': '满足条件',
        'en-US': 'Condition met',
    },
    'demo_environment_not_enabled': {
        'zh-CN': '演示环境未启用',
        'en-US': 'Demo environment is not enabled',
    },
    'failed_activate_user_try_again_later': {
        'zh-CN': '激活用户失败，请稍后重试',
        'en-US': 'Failed to activate the user, please try again later',
    },
    'parent_record_does_not_exist': {
        'zh-CN': '父记录不存在',
        'en-US': 'Parent record does not exist',
    },
    'parent_record_field_created_successfully': {
        'zh-CN': '父记录字段创建成功',
        'en-US': 'Parent record field created successfully',
    },
    'version_does_not_exist': {
        'zh-CN': '版本不存在',
        'en-US': 'Version does not exist',
    },
    'user': {
        'zh-CN': '用户',
        'en-US': 'User',
    },
    'user_information_updated_successfully': {
        'zh-CN': '用户信息更新成功',
        'en-US': 'User information updated successfully',
    },
    'user_created_successfully': {
        'zh-CN': '用户创建成功',
        'en-US': 'User created successfully',
    },
    'user_deleted_successfully': {
        'zh-CN': '用户删除成功',
        'en-US': 'User deleted successfully',
    },
    'user_already_active': {
        'zh-CN': '用户已是激活状态',
        'en-US': 'The user is already active',
    },
    'user_been_suspended': {
        'zh-CN': '用户已被暂停',
        'en-US': 'The user has been suspended',
    },
    'email_verification_email_sent_after_registration': {
        'zh-CN': '用户注册后发送的邮箱验证邮件',
        'en-US': 'Email verification email sent after registration',
    },
    'welcome_email_sent_after_successful_registration': {
        'zh-CN': '用户注册成功后发送的欢迎邮件',
        'en-US': 'Welcome email sent after successful registration',
    },
    'user_registration_welcome_email': {
        'zh-CN': '用户注册欢迎邮件',
        'en-US': 'User registration welcome email',
    },
    'user_status_updated_successfully': {
        'zh-CN': '用户状态更新成功',
        'en-US': 'User status updated successfully',
    },
    'email_sent_when_user_requests_password_reset': {
        'zh-CN': '用户请求密码重置时发送的邮件',
        'en-US': 'Email sent when a user requests a password reset',
    },
    'logout_failed_try_again_later': {
        'zh-CN': '登出失败，请稍后重试',
        'en-US': 'Logout failed, please try again later',
    },
    'logged_out_successfully': {
        'zh-CN': '登出成功',
        'en-US': 'Logged out successfully',
    },
    'target_table_does_not_exist': {
        'zh-CN': '目标表不存在',
        'en-US': 'Target table does not exist',
    },
    'failed_disable_share_link': {
        'zh-CN': '禁用分享链接失败',
        'en-US': 'Failed to disable the share link',
    },
    'notification': {
        'zh-CN': '站内信',
        'en-US': 'Notification',
    },
    'notification_does_not_exist': {
        'zh-CN': '站内信不存在',
        'en-US': 'Notification does not exist',
    },
    'notification_deleted': {
        'zh-CN': '站内信已删除',
        'en-US': 'Notification deleted',
    },
    'notification_retry_processed_successfully': {
        'zh-CN': '站内信重试处理成功',
        'en-US': 'Notification retry processed successfully',
    },
    'system_configuration_updated_successfully': {
        'zh-CN': '系统配置更新成功',
        'en-US': 'System configuration updated successfully',
    },
    'widget': {
        'zh-CN': '组件',
        'en-US': 'Widget',
    },
    'widget_deleted_successfully': {
        'zh-CN': '组件删除成功',
        'en-US': 'Widget deleted successfully',
    },
    'widgets_batch_updated_successfully': {
        'zh-CN': '组件批量更新成功',
        'en-US': 'Widgets batch updated successfully',
    },
    'widget_updated_successfully': {
        'zh-CN': '组件更新成功',
        'en-US': 'Widget updated successfully',
    },
    'widget_added_successfully': {
        'zh-CN': '组件添加成功',
        'en-US': 'Widget added successfully',
    },
    'invalid_end_time_format': {
        'zh-CN': '结束时间格式错误',
        'en-US': 'Invalid end time format',
    },
    'result_variable_name_alphanumeric_underscore_start_letter_unders': {
        'zh-CN': '结果变量名必须为字母数字下划线且以字母或下划线开头（≤64 字符）',
        'en-US': 'The result variable name must be alphanumeric/underscore and start with a letter or underscore (max 64 characters)',
    },
    'thumbnail_does_not_exist': {
        'zh-CN': '缩略图不存在',
        'en-US': 'Thumbnail does not exist',
    },
    'failed_fetch_thumbnail': {
        'zh-CN': '缩略图获取失败',
        'en-US': 'Failed to fetch the thumbnail',
    },
    'missing_new_assignee_id_parameter': {
        'zh-CN': '缺少 new_assignee_id 参数',
        'en-US': 'Missing new_assignee_id parameter',
    },
    'missing_target_record_id_parameter': {
        'zh-CN': '缺少 target_record_id 参数',
        'en-US': 'Missing target_record_id parameter',
    },
    'missing_required_parameters': {
        'zh-CN': '缺少必要参数',
        'en-US': 'Missing required parameters',
    },
    'missing_user_id_list': {
        'zh-CN': '缺少用户ID列表',
        'en-US': 'Missing user ID list',
    },
    'missing_user_identifier': {
        'zh-CN': '缺少用户标识',
        'en-US': 'Missing user identifier',
    },
    'missing_target_table_id': {
        'zh-CN': '缺少目标表格 ID',
        'en-US': 'Missing target table ID',
    },
    'missing_target_record_id': {
        'zh-CN': '缺少目标记录 ID',
        'en-US': 'Missing target record ID',
    },
    'related_update_missing_target_table': {
        'zh-CN': '关联表同步更新任务 #{0} 未指定目标表',
        'en-US': 'Related update task #{0} is missing a target table',
    },
    'missing_email_template_key': {
        'zh-CN': '缺少邮件模板 key',
        'en-US': 'Missing email template key',
    },
    'script_runner_output_format_abnormal': {
        'zh-CN': '脚本 runner 输出格式异常',
        'en-US': 'Script runner output format is abnormal',
    },
    'failed_parse_script_runner_output': {
        'zh-CN': '脚本 runner 输出解析失败',
        'en-US': 'Failed to parse the script runner output',
    },
    'script_content_empty': {
        'zh-CN': '脚本内容不能为空',
        'en-US': 'Script content cannot be empty',
    },
    'script_content_exceed_characters': {
        'zh-CN': '脚本内容不能超过 50000 字符',
        'en-US': 'Script content cannot exceed 50000 characters',
    },
    'script_node_configuration_object': {
        'zh-CN': '脚本节点配置必须是一个对象',
        'en-US': 'Script node configuration must be an object',
    },
    'script_language_python': {
        'zh-CN': '脚本语言必须为 \'python\'',
        'en-US': 'The script language must be \'python\'',
    },
    'script_output_exceeds_mb_limit': {
        'zh-CN': '脚本输出超过 1MB 限制',
        'en-US': 'Script output exceeds the 1MB limit',
    },
    'failed_auto_create_parent_record_field_try_again_later': {
        'zh-CN': '自动创建父记录字段失败，请稍后重试',
        'en-US': 'Failed to auto-create the parent record field, please try again later',
    },
    'custom_value_empty': {
        'zh-CN': '自定义值不能为空',
        'en-US': 'Custom value cannot be empty',
    },
    'node_updated': {
        'zh-CN': '节点已更新',
        'en-US': 'Node updated',
    },
    'fetched_webhook_list_successfully': {
        'zh-CN': '获取 Webhook 列表成功',
        'en-US': 'Fetched Webhook list successfully',
    },
    'fetched_webhook_reference_information_successfully': {
        'zh-CN': '获取 Webhook 引用信息成功',
        'en-US': 'Fetched Webhook reference information successfully',
    },
    'fetched_webhook_delivery_logs_successfully': {
        'zh-CN': '获取 Webhook 投递日志成功',
        'en-US': 'Fetched Webhook delivery logs successfully',
    },
    'fetched_webhook_details_successfully': {
        'zh-CN': '获取 Webhook 详情成功',
        'en-US': 'Fetched Webhook details successfully',
    },
    'fetched_dashboard_list_successfully': {
        'zh-CN': '获取仪表盘列表成功',
        'en-US': 'Fetched Dashboard list successfully',
    },
    'fetched_dashboard_successfully': {
        'zh-CN': '获取仪表盘成功',
        'en-US': 'Fetched Dashboard successfully',
    },
    'fetched_task_status_successfully': {
        'zh-CN': '获取任务状态成功',
        'en-US': 'Fetched task status successfully',
    },
    'failed_fetch_public_configuration_try_again_later': {
        'zh-CN': '获取公开配置失败，请稍后重试',
        'en-US': 'Failed to fetch public configuration, please try again later',
    },
    'fetched_public_configuration_successfully': {
        'zh-CN': '获取公开配置成功',
        'en-US': 'Fetched public configuration successfully',
    },
    'failed_fetch_link_relation_list_try_again_later': {
        'zh-CN': '获取关联关系列表失败，请稍后重试',
        'en-US': 'Failed to fetch the link relation list, please try again later',
    },
    'fetched_link_relation_list_successfully': {
        'zh-CN': '获取关联关系列表成功',
        'en-US': 'Fetched the link relation list successfully',
    },
    'failed_fetch_linked_data_try_again_later': {
        'zh-CN': '获取关联数据失败，请稍后重试',
        'en-US': 'Failed to fetch linked data, please try again later',
    },
    'fetched_linked_data_successfully': {
        'zh-CN': '获取关联数据成功',
        'en-US': 'Fetched linked data successfully',
    },
    'failed_fetch_linked_records_try_again_later': {
        'zh-CN': '获取关联记录失败，请稍后重试',
        'en-US': 'Failed to fetch linked records, please try again later',
    },
    'failed_fetch_linked_record_details_try_again_later': {
        'zh-CN': '获取关联记录详情失败，请稍后重试',
        'en-US': 'Failed to fetch linked record details, please try again later',
    },
    'fetched_linked_record_details_successfully': {
        'zh-CN': '获取关联记录详情成功',
        'en-US': 'Fetched linked record details successfully',
    },
    'fetched_share_list_successfully': {
        'zh-CN': '获取分享列表成功',
        'en-US': 'Fetched share list successfully',
    },
    'fetched_bases_shared_successfully': {
        'zh-CN': '获取分享给您的 Base 成功',
        'en-US': 'Fetched bases shared with you successfully',
    },
    'fetched_table_shares_shared_successfully': {
        'zh-CN': '获取分享给您的数据表成功',
        'en-US': 'Fetched tables shared with you successfully',
    },
    'fetched_share_link_list_successfully': {
        'zh-CN': '获取分享链接列表成功',
        'en-US': 'Fetched share link list successfully',
    },
    'failed_fetch_change_history_try_again_later': {
        'zh-CN': '获取变更历史失败，请稍后重试',
        'en-US': 'Failed to fetch change history, please try again later',
    },
    'fetched_manually_triggerable_workflow_list_successfully': {
        'zh-CN': '获取可手动触发的工作流列表成功',
        'en-US': 'Fetched manually triggerable workflow list successfully',
    },
    'fetched_base_list_successfully': {
        'zh-CN': '获取基础数据列表成功',
        'en-US': 'Fetched base list successfully',
    },
    'fetched_base_successfully': {
        'zh-CN': '获取基础数据成功',
        'en-US': 'Fetched base successfully',
    },
    'failed_fetch_failed_emails_try_again_later': {
        'zh-CN': '获取失败邮件失败，请稍后重试',
        'en-US': 'Failed to fetch failed emails, please try again later',
    },
    'fetched_field_list_successfully': {
        'zh-CN': '获取字段列表成功',
        'en-US': 'Fetched field list successfully',
    },
    'fetched_field_successfully': {
        'zh-CN': '获取字段成功',
        'en-US': 'Fetched field successfully',
    },
    'fetched_field_type_list_successfully': {
        'zh-CN': '获取字段类型列表成功',
        'en-US': 'Fetched field type list successfully',
    },
    'fetched_field_type_details_successfully': {
        'zh-CN': '获取字段类型详情成功',
        'en-US': 'Fetched field type details successfully',
    },
    'fetched_instance_details_successfully': {
        'zh-CN': '获取实例详情成功',
        'en-US': 'Fetched instance details successfully',
    },
    'failed_fetch_approval_task_details_try_again_later': {
        'zh-CN': '获取审批任务详情失败，请稍后重试',
        'en-US': 'Failed to fetch approval task details, please try again later',
    },
    'fetched_approval_task_details_successfully': {
        'zh-CN': '获取审批任务详情成功',
        'en-US': 'Fetched approval task details successfully',
    },
    'failed_fetch_approval_list_try_again_later': {
        'zh-CN': '获取审批列表失败，请稍后重试',
        'en-US': 'Failed to fetch the approval list, please try again later',
    },
    'fetched_approval_list_successfully': {
        'zh-CN': '获取审批列表成功',
        'en-US': 'Fetched the approval list successfully',
    },
    'fetched_approval_history_successfully': {
        'zh-CN': '获取审批历史成功',
        'en-US': 'Fetched approval history successfully',
    },
    'fetched_workflow_list_successfully': {
        'zh-CN': '获取工作流列表成功',
        'en-US': 'Fetched workflow list successfully',
    },
    'fetched_workflow_details_successfully': {
        'zh-CN': '获取工作流详情成功',
        'en-US': 'Fetched workflow details successfully',
    },
    'failed_fetch_pending_emails_try_again_later': {
        'zh-CN': '获取待发送邮件失败，请稍后重试',
        'en-US': 'Failed to fetch pending emails, please try again later',
    },
    'fetched_shares_created_successfully': {
        'zh-CN': '获取您创建的分享成功',
        'en-US': 'Fetched shares you created successfully',
    },
    'fetched_successfully': {
        'zh-CN': '获取成功',
        'en-US': 'Fetched successfully',
    },
    'fetched_member_list_successfully': {
        'zh-CN': '获取成员列表成功',
        'en-US': 'Fetched member list successfully',
    },
    'failed_fetch_submission_records': {
        'zh-CN': '获取提交记录失败',
        'en-US': 'Failed to fetch submission records',
    },
    'failed_fetch_operation_logs_try_again_later': {
        'zh-CN': '获取操作日志失败，请稍后重试',
        'en-US': 'Failed to fetch operation logs, please try again later',
    },
    'failed_fetch_data_table_change_history_try_again_later': {
        'zh-CN': '获取数据表变更历史失败，请稍后重试',
        'en-US': 'Failed to fetch data table change history, please try again later',
    },
    'failed_fetch_log_details_try_again_later': {
        'zh-CN': '获取日志详情失败，请稍后重试',
        'en-US': 'Failed to fetch log details, please try again later',
    },
    'failed_fetch_unread_count_try_again_later': {
        'zh-CN': '获取未读数量失败，请稍后重试',
        'en-US': 'Failed to fetch the unread count, please try again later',
    },
    'fetched_unread_count_successfully': {
        'zh-CN': '获取未读数量成功',
        'en-US': 'Fetched the unread count successfully',
    },
    'failed_fetch_tree_records_try_again_later': {
        'zh-CN': '获取树形记录失败，请稍后重试',
        'en-US': 'Failed to fetch tree records, please try again later',
    },
    'failed_fetch_template_list_try_again_later': {
        'zh-CN': '获取模板列表失败，请稍后重试',
        'en-US': 'Failed to fetch the template list, please try again later',
    },
    'failed_fetch_template_try_again_later': {
        'zh-CN': '获取模板失败，请稍后重试',
        'en-US': 'Failed to fetch the template, please try again later',
    },
    'fetched_version_list_successfully': {
        'zh-CN': '获取版本列表成功',
        'en-US': 'Fetched version list successfully',
    },
    'fetched_user_information_successfully': {
        'zh-CN': '获取用户信息成功',
        'en-US': 'Fetched user information successfully',
    },
    'failed_fetch_user_list_try_again_later': {
        'zh-CN': '获取用户列表失败，请稍后重试',
        'en-US': 'Failed to fetch the user list, please try again later',
    },
    'failed_fetch_notification_list_try_again_later': {
        'zh-CN': '获取站内信列表失败，请稍后重试',
        'en-US': 'Failed to fetch the notification list, please try again later',
    },
    'fetched_notification_list_successfully': {
        'zh-CN': '获取站内信列表成功',
        'en-US': 'Fetched the notification list successfully',
    }
}
