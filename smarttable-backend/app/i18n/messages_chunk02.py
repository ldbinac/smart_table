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

MESSAGES_PART2 = {
    'custom_interval_positive_integer': {
        'zh-CN': 'custom_interval 必须为正整数',
        'en-US': 'custom_interval must be a positive integer',
    },
    'custom_unit_one_day_week_month_year': {
        'zh-CN': 'custom_unit 必须是 day/week/month/year 之一',
        'en-US': 'custom_unit must be one of day/week/month/year',
    },
    "empty_result_action_skip_error": {
        "zh-CN": "empty_result_action 必须为 'skip' 或 'error'",
        "en-US": "empty_result_action must be 'skip' or 'error'",
    },
    'end_date_earlier_than_start_date': {
        'zh-CN': 'end_date 不能早于 start_date',
        'en-US': 'end_date cannot be earlier than start_date',
    },
    'invalid_end_time_format_use_iso_format': {
        'zh-CN': 'end_time 格式不正确，请使用 ISO 格式',
        'en-US': 'Invalid end_time format, please use ISO format',
    },
    'end_date_required_when_end_type_end_date': {
        'zh-CN': 'end_type 为 end_date 时 end_date 必填',
        'en-US': 'end_date is required when end_type is end_date',
    },
    "error_handling_skip_terminate": {
        "zh-CN": "error_handling 必须为 'skip' 或 'terminate'",
        "en-US": "error_handling must be 'skip' or 'terminate'",
    },
    'field_id_empty': {
        'zh-CN': 'field_id 不能为空',
        'en-US': 'field_id cannot be empty',
    },
    'headers_object': {
        'zh-CN': 'headers 必须是对象',
        'en-US': 'headers must be an object',
    },
    'ids_array': {
        'zh-CN': 'ids 必须是数组',
        'en-US': 'ids must be an array',
    },
    'max_iterations_positive_integer_between': {
        'zh-CN': 'max_iterations 必须为 1-1000 之间的正整数',
        'en-US': 'max_iterations must be a positive integer between 1 and 1000',
    },
    'start_time_after_current_utc_time_no_repeat_mode': {
        'zh-CN': 'no_repeat 模式下开始时间必须在当前 UTC 时间之后',
        'en-US': 'start time must be after the current UTC time in no_repeat mode',
    },
    'nodes_config_array': {
        'zh-CN': 'nodes_config 必须是数组',
        'en-US': 'nodes_config must be an array',
    },
    'record_id_empty': {
        'zh-CN': 'record_id 不能为空',
        'en-US': 'record_id cannot be empty',
    },
    'record_ids_empty': {
        'zh-CN': 'record_ids 不能为空',
        'en-US': 'record_ids cannot be empty',
    },
    'retry_policy_object': {
        'zh-CN': 'retry_policy 必须是对象',
        'en-US': 'retry_policy must be an object',
    },
    'specified_time_trigger_schedule_configured': {
        'zh-CN': 'specified_time 触发器必须配置 schedule',
        'en-US': 'the specified_time trigger must have a schedule configured',
    },
    'invalid_start_time_format_use_iso_format': {
        'zh-CN': 'start_time 格式不正确，请使用 ISO 格式',
        'en-US': 'Invalid start_time format, please use ISO format',
    },
    'target_record_ids_array': {
        'zh-CN': 'target_record_ids 必须是数组',
        'en-US': 'target_record_ids must be an array',
    },
    'values_object': {
        'zh-CN': 'values 必须是对象',
        'en-US': 'values must be an object',
    },
    'view_orders_empty': {
        'zh-CN': 'view_orders不能为空',
        'en-US': 'view_orders cannot be empty',
    },
    'watch_detection_failed_try_again_later': {
        'zh-CN': 'watch 检测失败，请稍后重试',
        'en-US': 'Watch detection failed, please try again later',
    },
    'widgets_array': {
        'zh-CN': 'widgets 必须是数组',
        'en-US': 'widgets must be an array',
    },
    'one_one_link_link_one_record': {
        'zh-CN': '一对一关联只能关联一条记录',
        'en-US': 'A one-to-one link can only link one record',
    },
    'one_one_constraint_source_record_already_link': {
        'zh-CN': '一对一关联约束：源记录已有关联',
        'en-US': 'One-to-one constraint: the source record already has a link',
    },
    'one_one_constraint_source_record_already_linked_record': {
        'zh-CN': '一对一关联约束：源记录已有关联记录',
        'en-US': 'One-to-one constraint: the source record already has a linked record',
    },
    'one_one_constraint_target_record_already_linked_another_record': {
        'zh-CN': '一对一关联约束：目标记录已被其他记录关联',
        'en-US': 'One-to-one constraint: the target record is already linked to another record',
    },
    'add_most_members_time': {
        'zh-CN': '一次最多只能添加 100 个成员',
        'en-US': 'You can add at most 100 members at a time',
    },
    'search_most_users_time': {
        'zh-CN': '一次最多查询100个用户',
        'en-US': 'You can search at most 100 users at a time',
    },
    'unsupported_export_format': {
        'zh-CN': '不支持的导出格式',
        'en-US': 'Unsupported export format',
    },
    'unsupported_file_type': {
        'zh-CN': '不支持的文件类型',
        'en-US': 'Unsupported file type',
    },
    'unsupported_file_type_upload_excel_csv_file': {
        'zh-CN': '不支持的文件类型，请上传 Excel 或 CSV 文件',
        'en-US': 'Unsupported file type, please upload an Excel or CSV file',
    },
    'change_own_role': {
        'zh-CN': '不能修改自己的角色',
        'en-US': 'You cannot change your own role',
    },
    'system_default_templates_deleted_use_reset_feature': {
        'zh-CN': '不能删除系统默认模板，请使用重置功能',
        'en-US': 'System default templates cannot be deleted, please use the reset feature',
    },
    'primary_key_status_primary_field_removed': {
        'zh-CN': '不能取消主字段的主键状态',
        'en-US': 'The primary key status of the primary field cannot be removed',
    },
    'reference_current_data_table_choose_another_table': {
        'zh-CN': '不能引用当前数据表，请选择其他表',
        'en-US': 'You cannot reference the current data table, please choose another table',
    },
    'directly_set_user_status_deleted': {
        'zh-CN': '不能直接设置用户状态为已删除',
        'en-US': 'You cannot directly set the user status to deleted',
    },
    'remove_base_owner': {
        'zh-CN': '不能移除基础数据所有者',
        'en-US': 'You cannot remove the base owner',
    },
    'remove_yourself_use_other_methods_leave': {
        'zh-CN': '不能移除自己，如需退出请使用其他方式',
        'en-US': 'You cannot remove yourself, please use other methods to leave',
    },
    'primary_field_deleted': {
        'zh-CN': '主字段不能被删除',
        'en-US': 'The primary field cannot be deleted',
    },
    'workflows_draft_status_change_linked_data_table': {
        'zh-CN': '仅 draft 状态的工作流可变更关联数据表',
        'en-US': 'Only workflows in draft status can change the linked data table',
    },
    'workflows_draft_status_edit_nodes_triggers': {
        'zh-CN': '仅 draft 状态的工作流可编辑节点和触发器',
        'en-US': 'Only workflows in draft status can edit nodes and triggers',
    },
    'workflows_paused_status_save_version_snapshots': {
        'zh-CN': '仅暂停状态的工作流可保存版本快照',
        'en-US': 'Only workflows in paused status can save version snapshots',
    },
    'workflows_draft_paused_status_edit_nodes': {
        'zh-CN': '仅草稿或暂停状态可编辑节点',
        'en-US': 'Only workflows in draft or paused status can edit nodes',
    },
    'workflows_draft_paused_status_edit_triggers': {
        'zh-CN': '仅草稿或暂停状态可编辑触发器',
        'en-US': 'Only workflows in draft or paused status can edit triggers',
    },
    'failed_create_workflow_template_check_whether_template_table_exi': {
        'zh-CN': '从模板创建工作流失败，请检查模板、表格是否存在或是否有权限',
        'en-US': 'Failed to create a workflow from the template, please check whether the template and table exist or whether you have permission',
    },
    'token_refreshed_successfully': {
        'zh-CN': '令牌刷新成功',
        'en-US': 'Token refreshed successfully',
    },
    'token_been_revoked_log_again': {
        'zh-CN': '令牌已被撤销，请重新登录',
        'en-US': 'The token has been revoked, please log in again',
    },
    'token_expired_log_again': {
        'zh-CN': '令牌已过期，请重新登录',
        'en-US': 'The token has expired, please log in again',
    },
    'token_valid': {
        'zh-CN': '令牌有效',
        'en-US': 'The token is valid',
    },
    'token_missing_application_identity_information': {
        'zh-CN': '令牌缺少应用身份信息',
        'en-US': 'The token is missing application identity information',
    },
    'dashboard': {
        'zh-CN': '仪表盘',
        'en-US': 'Dashboard',
    },
    'dashboard_created_successfully': {
        'zh-CN': '仪表盘创建成功',
        'en-US': 'Dashboard created successfully',
    },
    'dashboard_deleted_successfully': {
        'zh-CN': '仪表盘删除成功',
        'en-US': 'Dashboard deleted successfully',
    },
    'dashboard_copied_successfully': {
        'zh-CN': '仪表盘复制成功',
        'en-US': 'Dashboard copied successfully',
    },
    'dashboard_updated_successfully': {
        'zh-CN': '仪表盘更新成功',
        'en-US': 'Dashboard updated successfully',
    },
    'task': {
        'zh-CN': '任务',
        'en-US': 'Task',
    },
    'task_does_not_exist': {
        'zh-CN': '任务不存在',
        'en-US': 'Task does not exist',
    },
    'task_already_been_processed_does_not_exist': {
        'zh-CN': '任务已被处理或不存在',
        'en-US': 'The task has already been processed or does not exist',
    },
    'task_data_abnormal': {
        'zh-CN': '任务数据异常',
        'en-US': 'Task data is abnormal',
    },
    'failed_save_template_check_whether_workflow_exists_whether_permi': {
        'zh-CN': '保存模板失败，请检查工作流是否存在或是否有权限',
        'en-US': 'Failed to save the template, please check whether the workflow exists or whether you have permission',
    },
    'failed_save_configuration_try_again_later': {
        'zh-CN': '保存配置失败，请稍后重试',
        'en-US': 'Failed to save the configuration, please try again later',
    },
    'value_type_field_custom': {
        'zh-CN': '值类型必须为 field 或 custom',
        'en-US': "The value type must be 'field' or 'custom'",
    },
    'failed_clone_workflow': {
        'zh-CN': '克隆工作流失败',
        'en-US': 'Failed to clone the workflow',
    },
    'formula_calculation_failed_try_again_later': {
        'zh-CN': '公式计算失败，请稍后重试',
        'en-US': 'Formula calculation failed, please try again later',
    },
    'link_type_not_changed': {
        'zh-CN': '关系类型未变化',
        'en-US': 'The link type has not changed',
    },
    'linked_value_updated_successfully': {
        'zh-CN': '关联值更新成功',
        'en-US': 'Linked value updated successfully',
    },
    'link_relation_does_not_exist': {
        'zh-CN': '关联关系不存在',
        'en-US': 'Link relation does not exist',
    },
    'link_field_created_successfully': {
        'zh-CN': '关联字段创建成功',
        'en-US': 'Link field created successfully',
    },
    'link_field_deleted_successfully': {
        'zh-CN': '关联字段删除成功',
        'en-US': 'Link field deleted successfully',
    },
    'link_field_updated_successfully': {
        'zh-CN': '关联字段更新成功',
        'en-US': 'Link field updated successfully',
    },
    'link_removed': {
        'zh-CN': '关联已解除',
        'en-US': 'Link removed',
    },
    'linked_data_table_empty': {
        'zh-CN': '关联数据表不能为空',
        'en-US': 'The linked data table cannot be empty',
    },
    'linked_table_does_not_exist': {
        'zh-CN': '关联的表格不存在',
        'en-US': 'The linked table does not exist',
    },
    'linked_table_does_not_exist_does_not_belong_current_base': {
        'zh-CN': '关联表格不存在或不属于当前基础数据',
        'en-US': 'The linked table does not exist or does not belong to the current base',
    },
    'no_content_changes_skipping_version_snapshot_creation': {
        'zh-CN': '内容无变更，跳过版本快照创建',
        'en-US': 'No content changes, skipping version snapshot creation',
    },
    'inline_webhook_does_not_support_redelivery': {
        'zh-CN': '内联 Webhook 不支持重新投递',
        'en-US': 'Inline Webhook does not support redelivery',
    },
    'inline_webhook_does_not_support_redelivery_configuration_not_per': {
        'zh-CN': '内联 Webhook 不支持重新投递（配置未持久化）',
        'en-US': 'Inline Webhook does not support redelivery (configuration is not persisted)',
    },
    'share_link': {
        'zh-CN': '分享链接',
        'en-US': 'Share link',
    },
    'share_link_created_successfully': {
        'zh-CN': '分享链接创建成功',
        'en-US': 'Share link created successfully',
    },
    'share_link_deleted_successfully': {
        'zh-CN': '分享链接删除成功',
        'en-US': 'Share link deleted successfully',
    },
    'share_link_been_disabled': {
        'zh-CN': '分享链接已禁用',
        'en-US': 'Share link has been disabled',
    },
    'share_link_updated_successfully': {
        'zh-CN': '分享链接更新成功',
        'en-US': 'Share link updated successfully',
    },
    'branch_label_empty': {
        'zh-CN': '分支标签不能为空',
        'en-US': 'Branch label cannot be empty',
    },
    'branch_routing_configuration_array': {
        'zh-CN': '分支路由配置必须为数组',
        'en-US': 'Branch routing configuration must be an array',
    },
    'branch_configuration_items_objects': {
        'zh-CN': '分支配置项必须为对象',
        'en-US': 'Branch configuration items must be objects',
    },
    'pagination_parameters_integers': {
        'zh-CN': '分页参数必须是整数',
        'en-US': 'Pagination parameters must be integers',
    },
    'failed_create_link_relation': {
        'zh-CN': '创建关联关系失败',
        'en-US': 'Failed to create the link relation',
    },
    'failed_create_link_relation_try_again_later': {
        'zh-CN': '创建关联关系失败，请稍后重试',
        'en-US': 'Failed to create the link relation, please try again later',
    },
    'failed_create_link_field_try_again_later': {
        'zh-CN': '创建关联字段失败，请稍后重试',
        'en-US': 'Failed to create the link field, please try again later',
    },
    'failed_create_share_link_try_again_later': {
        'zh-CN': '创建分享链接失败，请稍后重试',
        'en-US': 'Failed to create the share link, please try again later',
    },
    'creation_failed_try_again_later': {
        'zh-CN': '创建失败，请稍后重试',
        'en-US': 'Creation failed, please try again later',
    },
    'failed_create_sub_record_try_again_later': {
        'zh-CN': '创建子记录失败，请稍后重试',
        'en-US': 'Failed to create the sub-record, please try again later',
    },
    'failed_fetch_field_after_creating': {
        'zh-CN': '创建字段后获取字段失败',
        'en-US': 'Failed to fetch the field after creating it',
    },
    'failed_create_field_try_again_later': {
        'zh-CN': '创建字段失败，请稍后重试',
        'en-US': 'Failed to create the field, please try again later',
    },
    'failed_create_link_record_try_again_later': {
        'zh-CN': '创建并关联记录失败，请稍后重试',
        'en-US': 'Failed to create and link the record, please try again later',
    },
    'record_created_linked_successfully': {
        'zh-CN': '创建并关联记录成功',
        'en-US': 'Record created and linked successfully',
    },
    'failed_create_data_table': {
        'zh-CN': '创建数据表失败',
        'en-US': 'Failed to create the data table',
    },
    'create_document': {
        'zh-CN': '创建文档',
        'en-US': 'Create document',
    },
    'lookup_field_created_successfully': {
        'zh-CN': '创建查找字段成功',
        'en-US': 'Lookup field created successfully',
    },
    'failed_create_user_try_again_later': {
        'zh-CN': '创建用户失败，请稍后重试',
        'en-US': 'Failed to create the user, please try again later',
    },
    'failed_create_view_try_again_later': {
        'zh-CN': '创建视图失败，请稍后重试',
        'en-US': 'Failed to create the view, please try again later',
    },
    'failed_create_record_try_again_later': {
        'zh-CN': '创建记录失败，请稍后重试',
        'en-US': 'Failed to create the record, please try again later',
    },
    'failed_delete_linked_value_try_again_later': {
        'zh-CN': '删除关联值失败，请稍后重试',
        'en-US': 'Failed to delete the linked value, please try again later',
    },
    'failed_delete_link_relation_try_again_later': {
        'zh-CN': '删除关联关系失败，请稍后重试',
        'en-US': 'Failed to delete the link relation, please try again later',
    },
    'failed_delete_link_field_try_again_later': {
        'zh-CN': '删除关联字段失败，请稍后重试',
        'en-US': 'Failed to delete the link field, please try again later',
    },
    'failed_delete_share_link': {
        'zh-CN': '删除分享链接失败',
        'en-US': 'Failed to delete the share link',
    },
    'deletion_failed_try_again_later': {
        'zh-CN': '删除失败，请稍后重试',
        'en-US': 'Deletion failed, please try again later',
    },
    'failed_delete_field_try_again_later': {
        'zh-CN': '删除字段失败，请稍后重试',
        'en-US': 'Failed to delete the field, please try again later',
    },
    'failed_delete_workflow': {
        'zh-CN': '删除工作流失败',
        'en-US': 'Failed to delete the workflow',
    },
    'failed_delete_old_logs_try_again_later': {
        'zh-CN': '删除旧日志失败，请稍后重试',
        'en-US': 'Failed to delete old logs, please try again later',
    },
    'failed_delete_template_try_again_later': {
        'zh-CN': '删除模板失败，请稍后重试',
        'en-US': 'Failed to delete the template, please try again later',
    },
    'failed_delete_user_try_again_later': {
        'zh-CN': '删除用户失败，请稍后重试',
        'en-US': 'Failed to delete the user, please try again later',
    },
    'failed_delete_notification_try_again_later': {
        'zh-CN': '删除站内信失败，请稍后重试',
        'en-US': 'Failed to delete the notification, please try again later',
    },
    'failed_delete_view_try_again_later': {
        'zh-CN': '删除视图失败，请稍后重试',
        'en-US': 'Failed to delete the view, please try again later',
    },
    'failed_delete_record': {
        'zh-CN': '删除记录失败',
        'en-US': 'Failed to delete the record',
    },
    'failed_delete_record_try_again_later': {
        'zh-CN': '删除记录失败，请稍后重试',
        'en-US': 'Failed to delete the record, please try again later',
    },
    'failed_delete_configuration_try_again_later': {
        'zh-CN': '删除配置失败，请稍后重试',
        'en-US': 'Failed to delete the configuration, please try again later',
    },
    'missing_feature_dependencies_try_again_later': {
        'zh-CN': '功能依赖缺失，请稍后重试',
        'en-US': 'Missing feature dependencies, please try again later',
    },
    'failed_encrypt_password': {
        'zh-CN': '加密密码失败',
        'en-US': 'Failed to encrypt the password',
    },
    'failed_encrypt_password_try_again_later': {
        'zh-CN': '加密密码失败，请稍后重试',
        'en-US': 'Failed to encrypt the password, please try again later',
    },
    'single_workflow_most_loop_nodes': {
        'zh-CN': '单个工作流最多 5 个循环节点',
        'en-US': 'A single workflow can have at most 5 loop nodes',
    },
    'batch_create_more_than_records_time': {
        'zh-CN': '单次批量创建记录数量不能超过1000条',
        'en-US': 'You cannot batch create more than 1000 records at a time',
    }
}
