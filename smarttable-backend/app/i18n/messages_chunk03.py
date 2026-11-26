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

MESSAGES_PART3 = {
    'batch_delete_more_than_records_time': {
        'zh-CN': '单次批量删除记录数量不能超过1000条',
        'en-US': 'You cannot batch delete more than 1000 records at a time',
    },
    'batch_update_more_than_records_time': {
        'zh-CN': '单次批量更新记录数量不能超过1000条',
        'en-US': 'You cannot batch update more than 1000 records at a time',
    },
    'bidirectional_link_sync_failed_try_again_later': {
        'zh-CN': '双向关联同步失败，请稍后重试',
        'en-US': 'Bidirectional link sync failed, please try again later',
    },
    'failed_publish_workflow': {
        'zh-CN': '发布工作流失败',
        'en-US': 'Failed to publish the workflow',
    },
    'sending_failed_try_again_later': {
        'zh-CN': '发送失败，请稍后重试',
        'en-US': 'Sending failed, please try again later',
    },
    'failed_send_notification_try_again_later': {
        'zh-CN': '发送站内信失败，请稍后重试',
        'en-US': 'Failed to send the notification, please try again later',
    },
    'failed_send_verification_email_try_again_later': {
        'zh-CN': '发送验证邮件失败，请稍后重试',
        'en-US': 'Failed to send the verification email, please try again later',
    },
    'cancellation_failed_try_again_later': {
        'zh-CN': '取消失败，请稍后重试',
        'en-US': 'Cancellation failed, please try again later',
    },
    'base_owner_delete': {
        'zh-CN': '只有基础数据所有者可以删除',
        'en-US': 'Only the base owner can delete',
    },
    'system_default_templates_support_reset': {
        'zh-CN': '只有系统默认模板支持重置操作',
        'en-US': 'Only system default templates support reset',
    },
    'resource_owner_perform_operation': {
        'zh-CN': '只有资源所有者可以执行此操作',
        'en-US': 'Only the resource owner can perform this operation',
    },
    'name_exceed_characters': {
        'zh-CN': '名称不能超过100个字符',
        'en-US': 'Name cannot exceed 100 characters',
    },
    'base': {
        'zh-CN': '基础数据',
        'en-US': 'Base',
    },
    'base_does_not_exist_2': {
        'zh-CN': '基础数据不存在',
        'en-US': 'Base does not exist',
    },
    'base_created_successfully': {
        'zh-CN': '基础数据创建成功',
        'en-US': 'Base created successfully',
    },
    'base_deleted_successfully': {
        'zh-CN': '基础数据删除成功',
        'en-US': 'Base deleted successfully',
    },
    'base_updated_successfully': {
        'zh-CN': '基础数据更新成功',
        'en-US': 'Base updated successfully',
    },
    'processing_failed_try_again_later': {
        'zh-CN': '处理失败，请稍后重试',
        'en-US': 'Processing failed, please try again later',
    },
    'copy_failed_try_again_later': {
        'zh-CN': '复制失败，请稍后重试',
        'en-US': 'Copy failed, please try again later',
    },
    'failed_copy_field_try_again_later': {
        'zh-CN': '复制字段失败，请稍后重试',
        'en-US': 'Failed to copy the field, please try again later',
    },
    'copied_successfully': {
        'zh-CN': '复制成功',
        'en-US': 'Copied successfully',
    },
    'failed_copy_view_try_again_later': {
        'zh-CN': '复制视图失败，请稍后重试',
        'en-US': 'Failed to copy the view, please try again later',
    },
    'if_email_registered_password_reset_email_will_sent': {
        'zh-CN': '如果该邮箱已注册，重置邮件将发送至您的邮箱',
        'en-US': 'If this email is registered, a password reset email will be sent to it',
    },
    'sub_record_created_successfully': {
        'zh-CN': '子记录创建成功',
        'en-US': 'Sub-record created successfully',
    },
    'field': {
        'zh-CN': '字段',
        'en-US': 'Field',
    },
    'field_does_not_exist': {
        'zh-CN': '字段不存在',
        'en-US': 'Field does not exist',
    },
    'field_not_link_type': {
        'zh-CN': '字段不是关联类型',
        'en-US': 'The field is not a link type',
    },
    'field_created_successfully': {
        'zh-CN': '字段创建成功',
        'en-US': 'Field created successfully',
    },
    'field_deleted_successfully': {
        'zh-CN': '字段删除成功',
        'en-US': 'Field deleted successfully',
    },
    'field_name_empty': {
        'zh-CN': '字段名称不能为空',
        'en-US': 'Field name cannot be empty',
    },
    'field_name_exceed_characters': {
        'zh-CN': '字段名称不能超过 100 个字符',
        'en-US': 'Field name cannot exceed 100 characters',
    },
    'field_name_exceed_characters_2': {
        'zh-CN': '字段名称不能超过100个字符',
        'en-US': 'Field name cannot exceed 100 characters',
    },
    'field_name_contains_invalid_characters': {
        'zh-CN': '字段名称包含非法字符',
        'en-US': 'Field name contains invalid characters',
    },
    'field_copied_successfully': {
        'zh-CN': '字段复制成功',
        'en-US': 'Field copied successfully',
    },
    'field_order_updated_successfully': {
        'zh-CN': '字段排序更新成功',
        'en-US': 'Field order updated successfully',
    },
    'invalid_field_mapping_format': {
        'zh-CN': '字段映射格式无效',
        'en-US': 'Invalid field mapping format',
    },
    'field_updated_successfully': {
        'zh-CN': '字段更新成功',
        'en-US': 'Field updated successfully',
    },
    'field_format_incompatible_computation_type': {
        'zh-CN': '字段格式与计算方式不兼容',
        'en-US': 'The field format is incompatible with the computation type',
    },
    'field_type_empty': {
        'zh-CN': '字段类型不能为空',
        'en-US': 'Field type cannot be empty',
    },
    'field_configuration_missing_linked_table_id': {
        'zh-CN': '字段配置缺少关联表ID',
        'en-US': 'Field configuration is missing the linked table ID',
    },
    'field_configuration_missing_formula': {
        'zh-CN': '公式字段配置缺少公式表达式',
        'en-US': 'Formula field configuration is missing the formula expression',
    },
    'failed_schedule_retry_try_again_later': {
        'zh-CN': '安排重试失败，请稍后重试',
        'en-US': 'Failed to schedule a retry, please try again later',
    },
    'timer_configuration_object': {
        'zh-CN': '定时器配置必须是一个对象',
        'en-US': 'Timer configuration must be an object',
    },
    'scheduled_auto_save': {
        'zh-CN': '定时自动保存',
        'en-US': 'Scheduled auto-save',
    },
    'instance': {
        'zh-CN': '实例',
        'en-US': 'Instance',
    },
    'approval_task_does_not_exist': {
        'zh-CN': '审批任务不存在',
        'en-US': 'Approval task does not exist',
    },
    'failed_approve_task_try_again_later': {
        'zh-CN': '审批同意失败，请稍后重试',
        'en-US': 'Failed to approve the task, please try again later',
    },
    'approval_been_recorded_but_subsequent_processing_failed': {
        'zh-CN': '审批已记录，但后续处理失败',
        'en-US': 'The approval has been recorded, but subsequent processing failed',
    },
    'approval_transferred': {
        'zh-CN': '审批已转办',
        'en-US': 'Approval transferred',
    },
    'approval_approved': {
        'zh-CN': '审批已通过',
        'en-US': 'Approval approved',
    },
    'approval_rejected': {
        'zh-CN': '审批已驳回',
        'en-US': 'Approval rejected',
    },
    'failed_transfer_approval_try_again_later': {
        'zh-CN': '审批转办失败，请稍后重试',
        'en-US': 'Failed to transfer the approval, please try again later',
    },
    'failed_reject_approval_try_again_later': {
        'zh-CN': '审批驳回失败，请稍后重试',
        'en-US': 'Failed to reject the approval, please try again later',
    },
    'password_empty': {
        'zh-CN': '密码不能为空',
        'en-US': 'Password cannot be empty',
    },
    'failed_change_password_try_again_later': {
        'zh-CN': '密码修改失败，请稍后重试',
        'en-US': 'Failed to change the password, please try again later',
    },
    'password_changed_successfully_log_again_new_password': {
        'zh-CN': '密码修改成功，请使用新密码重新登录',
        'en-US': 'Password changed successfully, please log in again with the new password',
    },
    'password_contain_least_one_uppercase_letter': {
        'zh-CN': '密码必须包含至少一个大写字母',
        'en-US': 'Password must contain at least one uppercase letter',
    },
    'password_contain_least_one_lowercase_letter': {
        'zh-CN': '密码必须包含至少一个小写字母',
        'en-US': 'Password must contain at least one lowercase letter',
    },
    'password_contain_least_one_number': {
        'zh-CN': '密码必须包含至少一个数字',
        'en-US': 'Password must contain at least one number',
    },
    'failed_reset_password_try_again_later': {
        'zh-CN': '密码重置失败，请稍后重试',
        'en-US': 'Failed to reset the password, please try again later',
    },
    'password_reset_successfully_log_new_password': {
        'zh-CN': '密码重置成功，请使用新密码登录',
        'en-US': 'Password reset successfully, please log in with the new password',
    },
    'password_reset_successfully_notify_user_change_password_promptly': {
        'zh-CN': '密码重置成功，请通知用户及时修改密码',
        'en-US': 'Password reset successfully, please notify the user to change the password promptly',
    },
    'password_reset_email': {
        'zh-CN': '密码重置邮件',
        'en-US': 'Password reset email',
    },
    'failed_preview_import_try_again_later': {
        'zh-CN': '导入预览失败，请稍后重试',
        'en-US': 'Failed to preview the import, please try again later',
    },
    'import_preview_succeeded': {
        'zh-CN': '导入预览成功',
        'en-US': 'Import preview succeeded',
    },
    'failed_export_operation_logs_try_again_later': {
        'zh-CN': '导出操作日志失败，请稍后重试',
        'en-US': 'Failed to export operation logs, please try again later',
    },
    'workflow': {
        'zh-CN': '工作流',
        'en-US': 'Workflow',
    },
    'workflow_does_not_exist': {
        'zh-CN': '工作流不存在',
        'en-US': 'Workflow does not exist',
    },
    'workflow_cloned_successfully': {
        'zh-CN': '工作流克隆成功',
        'en-US': 'Workflow cloned successfully',
    },
    'workflow_created_successfully': {
        'zh-CN': '工作流创建成功',
        'en-US': 'Workflow created successfully',
    },
    'workflow_deleted_successfully': {
        'zh-CN': '工作流删除成功',
        'en-US': 'Workflow deleted successfully',
    },
    'workflow_published_successfully': {
        'zh-CN': '工作流发布成功',
        'en-US': 'Workflow published successfully',
    },
    'workflow_name_empty': {
        'zh-CN': '工作流名称不能为空',
        'en-US': 'Workflow name cannot be empty',
    },
    'workflow_name_exceed_characters': {
        'zh-CN': '工作流名称不能超过200个字符',
        'en-US': 'Workflow name cannot exceed 200 characters',
    },
    'workflow_saved_template': {
        'zh-CN': '工作流已保存为模板',
        'en-US': 'Workflow saved as template',
    },
    'workflow_resumed': {
        'zh-CN': '工作流已恢复',
        'en-US': 'Workflow resumed',
    },
    'workflow_paused': {
        'zh-CN': '工作流已暂停',
        'en-US': 'Workflow paused',
    },
    'workflow_linked_data_table': {
        'zh-CN': '工作流必须关联数据表格',
        'en-US': 'The workflow must be linked to a data table',
    },
    'workflow_updated_successfully': {
        'zh-CN': '工作流更新成功',
        'en-US': 'Workflow updated successfully',
    },
    'workflow_triggered_successfully': {
        'zh-CN': '工作流触发成功',
        'en-US': 'Workflow triggered successfully',
    },
    'logged_out_all_devices': {
        'zh-CN': '已从所有设备登出',
        'en-US': 'Logged out from all devices',
    },
    'workflow_created_template': {
        'zh-CN': '已从模板创建工作流',
        'en-US': 'Workflow created from template',
    },
    'all_marked_read': {
        'zh-CN': '已全部标记为已读',
        'en-US': 'All marked as read',
    },
    'retry_cancelled': {
        'zh-CN': '已取消重试',
        'en-US': 'Retry cancelled',
    },
    'marked_sending_failed': {
        'zh-CN': '已标记为发送失败',
        'en-US': 'Marked as sending failed',
    },
    'marked_sent_successfully': {
        'zh-CN': '已标记为发送成功',
        'en-US': 'Marked as sent successfully',
    },
    'marked_read': {
        'zh-CN': '已标记为已读',
        'en-US': 'Marked as read',
    },
    'marked_retrying': {
        'zh-CN': '已标记为重试中',
        'en-US': 'Marked as retrying',
    },
    'set_default_view': {
        'zh-CN': '已设置为默认视图',
        'en-US': 'Set as default view',
    },
    'maximum_retry_count_reached': {
        'zh-CN': '已达到最大重试次数',
        'en-US': 'Maximum retry count reached',
    },
    'layout_updated_successfully': {
        'zh-CN': '布局更新成功',
        'en-US': 'Layout updated successfully',
    },
    'layout_type_grid_free': {
        'zh-CN': '布局类型必须是 grid 或 free',
        'en-US': "Layout type must be 'grid' or 'free'",
    },
    'application_does_not_exist_been_deleted': {
        'zh-CN': '应用不存在或已被删除',
        'en-US': 'The application does not exist or has been deleted',
    },
    'application_been_disabled': {
        'zh-CN': '应用已被停用',
        'en-US': 'The application has been disabled',
    },
    'invalid_start_time_format': {
        'zh-CN': '开始时间格式错误',
        'en-US': 'Invalid start time format',
    },
    'referenced_field_empty': {
        'zh-CN': '引用字段不能为空',
        'en-US': 'Referenced field cannot be empty',
    },
    'referenced_field_belong_source_data_table': {
        'zh-CN': '引用字段必须属于源数据表',
        'en-US': 'The referenced field must belong to the source data table',
    },
    'registration_currently_disabled_system': {
        'zh-CN': '当前系统暂不开放注册功能',
        'en-US': 'Registration is currently disabled on this system',
    },
    'conditional_branch_nodes_not_supported_loop_bodies': {
        'zh-CN': '循环体不支持条件分支节点',
        'en-US': 'Conditional branch nodes are not supported in loop bodies',
    },
    'loop_nesting_depth_exceed_levels': {
        'zh-CN': '循环嵌套深度不能超过 3 层',
        'en-US': 'Loop nesting depth cannot exceed 3 levels',
    },
    'loop_data_source_empty': {
        'zh-CN': '循环数据源为空',
        'en-US': 'The loop data source is empty',
    },
    'loop_nodes_contain_non_empty_loop_body_nodes': {
        'zh-CN': '循环节点必须包含非空的 loop_body_nodes',
        'en-US': 'Loop nodes must contain a non-empty loop_body_nodes',
    },
    'loop_node_configuration_object': {
        'zh-CN': '循环节点配置必须是一个对象',
        'en-US': 'Loop node configuration must be an object',
    },
    'select_time_field': {
        'zh-CN': '必须选择时间字段',
        'en-US': 'You must select a time field',
    },
    'failed_resume_workflow': {
        'zh-CN': '恢复工作流失败',
        'en-US': 'Failed to resume the workflow',
    },
    'not_member_base': {
        'zh-CN': '您不是该 Base 的成员',
        'en-US': 'You are not a member of this Base',
    },
    'do_not_permission_upload_files_base': {
        'zh-CN': '您没有权限上传文件到此基础数据',
        'en-US': 'You do not have permission to upload files to this base',
    },
    'do_not_permission_change_member_roles': {
        'zh-CN': '您没有权限修改成员角色',
        'en-US': 'You do not have permission to change member roles',
    },
    'do_not_permission_modify_webhook': {
        'zh-CN': '您没有权限修改此 Webhook',
        'en-US': 'You do not have permission to modify this Webhook',
    },
    'do_not_permission_modify_dashboard': {
        'zh-CN': '您没有权限修改此仪表盘',
        'en-US': 'You do not have permission to modify this Dashboard',
    },
    'do_not_permission_modify_base': {
        'zh-CN': '您没有权限修改此基础数据',
        'en-US': 'You do not have permission to modify this base',
    },
    'do_not_permission_modify_field': {
        'zh-CN': '您没有权限修改此字段',
        'en-US': 'You do not have permission to modify this field',
    },
    'do_not_permission_modify_workflow': {
        'zh-CN': '您没有权限修改此工作流',
        'en-US': 'You do not have permission to modify this workflow',
    },
    'do_not_permission_modify_table': {
        'zh-CN': '您没有权限修改此表格',
        'en-US': 'You do not have permission to modify this table',
    },
    'do_not_permission_clone_workflow': {
        'zh-CN': '您没有权限克隆此工作流',
        'en-US': 'You do not have permission to clone this workflow',
    },
    'do_not_permission_create_dashboard': {
        'zh-CN': '您没有权限创建仪表盘',
        'en-US': 'You do not have permission to create a Dashboard',
    },
    'do_not_permission_create_share_link': {
        'zh-CN': '您没有权限创建分享链接',
        'en-US': 'You do not have permission to create a share link',
    },
    'do_not_permission_delete_webhook': {
        'zh-CN': '您没有权限删除此 Webhook',
        'en-US': 'You do not have permission to delete this Webhook',
    },
    'do_not_permission_delete_dashboard': {
        'zh-CN': '您没有权限删除此仪表盘',
        'en-US': 'You do not have permission to delete this Dashboard',
    },
    'do_not_permission_delete_share_link': {
        'zh-CN': '您没有权限删除此分享链接',
        'en-US': 'You do not have permission to delete this share link',
    },
    'do_not_permission_delete_field': {
        'zh-CN': '您没有权限删除此字段',
        'en-US': 'You do not have permission to delete this field',
    },
    'do_not_permission_delete_workflow': {
        'zh-CN': '您没有权限删除此工作流',
        'en-US': 'You do not have permission to delete this workflow',
    },
    'do_not_permission_delete_table': {
        'zh-CN': '您没有权限删除此表格',
        'en-US': 'You do not have permission to delete this table',
    },
    'do_not_permission_delete_attachment': {
        'zh-CN': '您没有权限删除此附件',
        'en-US': 'You do not have permission to delete this attachment',
    },
    'do_not_permission_publish_workflow': {
        'zh-CN': '您没有权限发布此工作流',
        'en-US': 'You do not have permission to publish this workflow',
    },
    'do_not_permission_create_data_table_base': {
        'zh-CN': '您没有权限在此Base中创建数据表',
        'en-US': 'You do not have permission to create a data table in this Base',
    },
    'do_not_permission_create_webhook_base': {
        'zh-CN': '您没有权限在此基础数据中创建 Webhook',
        'en-US': 'You do not have permission to create a Webhook in this base',
    },
    'do_not_permission_create_workflow_base': {
        'zh-CN': '您没有权限在此基础数据中创建工作流',
        'en-US': 'You do not have permission to create a workflow in this base',
    },
    'do_not_permission_create_table_base': {
        'zh-CN': '您没有权限在此基础数据中创建表格',
        'en-US': 'You do not have permission to create a table in this base',
    },
    'do_not_permission_create_field_table': {
        'zh-CN': '您没有权限在此表格中创建字段',
        'en-US': 'You do not have permission to create a field in this table',
    },
    'do_not_permission_copy_dashboard': {
        'zh-CN': '您没有权限复制此仪表盘',
        'en-US': 'You do not have permission to copy this Dashboard',
    },
    'do_not_permission_copy_base': {
        'zh-CN': '您没有权限复制此基础数据',
        'en-US': 'You do not have permission to copy this base',
    }
}
