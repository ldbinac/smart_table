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

MESSAGES_PART4 = {
    'do_not_permission_copy_field': {
        'zh-CN': '您没有权限复制此字段',
        'en-US': 'You do not have permission to copy this field',
    },
    'do_not_permission_copy_table': {
        'zh-CN': '您没有权限复制此表格',
        'en-US': 'You do not have permission to copy this table',
    },
    'do_not_permission_import_data_into_table': {
        'zh-CN': '您没有权限导入数据到此表格',
        'en-US': 'You do not have permission to import data into this table',
    },
    'do_not_permission_export_data_table': {
        'zh-CN': '您没有权限导出此表格数据',
        'en-US': 'You do not have permission to export data from this table',
    },
    'do_not_permission_resume_workflow': {
        'zh-CN': '您没有权限恢复此工作流',
        'en-US': 'You do not have permission to resume this workflow',
    },
    'do_not_permission_pause_workflow': {
        'zh-CN': '您没有权限暂停此工作流',
        'en-US': 'You do not have permission to pause this workflow',
    },
    'do_not_permission_update_share_link': {
        'zh-CN': '您没有权限更新此分享链接',
        'en-US': 'You do not have permission to update this share link',
    },
    'do_not_permission_view_share_list': {
        'zh-CN': '您没有权限查看分享列表',
        'en-US': 'You do not have permission to view the share list',
    },
    'do_not_permission_view_reference_information_webhook': {
        'zh-CN': '您没有权限查看此 Webhook 的引用信息',
        'en-US': 'You do not have permission to view the reference information of this Webhook',
    },
    'do_not_permission_view_delivery_logs_webhook': {
        'zh-CN': '您没有权限查看此 Webhook 的投递日志',
        'en-US': 'You do not have permission to view the delivery logs of this Webhook',
    },
    'do_not_permission_view_task': {
        'zh-CN': '您没有权限查看此任务',
        'en-US': 'You do not have permission to view this task',
    },
    'do_not_permission_view_attachment': {
        'zh-CN': '您没有权限查看此附件',
        'en-US': 'You do not have permission to view this attachment',
    },
    'do_not_permission_test_webhook': {
        'zh-CN': '您没有权限测试此 Webhook',
        'en-US': 'You do not have permission to test this Webhook',
    },
    'do_not_permission_add_members': {
        'zh-CN': '您没有权限添加成员',
        'en-US': 'You do not have permission to add members',
    },
    'do_not_permission_disable_share_link': {
        'zh-CN': '您没有权限禁用此分享链接',
        'en-US': 'You do not have permission to disable this share link',
    },
    'do_not_permission_remove_members': {
        'zh-CN': '您没有权限移除成员',
        'en-US': 'You do not have permission to remove members',
    },
    'do_not_permission_manage_members': {
        'zh-CN': '您没有权限管理成员',
        'en-US': 'You do not have permission to manage members',
    },
    'do_not_permission_manage_shares_dashboard': {
        'zh-CN': '您没有权限管理此仪表盘的分享',
        'en-US': 'You do not have permission to manage the shares of this Dashboard',
    },
    'do_not_permission_trigger_workflow_record': {
        'zh-CN': '您没有权限触发此记录的工作流',
        'en-US': 'You do not have permission to trigger the workflow of this record',
    },
    'do_not_permission_redeliver_webhook': {
        'zh-CN': '您没有权限重新投递此 Webhook',
        'en-US': 'You do not have permission to redeliver this Webhook',
    },
    'do_not_edit_permission': {
        'zh-CN': '您没有编辑权限',
        'en-US': 'You do not have edit permission',
    },
    'member_does_not_exist': {
        'zh-CN': '成员不存在',
        'en-US': 'Member does not exist',
    },
    'member_does_not_exist_removal_failed': {
        'zh-CN': '成员不存在或移除失败',
        'en-US': 'Member does not exist or removal failed',
    },
    'member_removed_successfully': {
        'zh-CN': '成员移除成功',
        'en-US': 'Member removed successfully',
    },
    'member_role_updated_successfully': {
        'zh-CN': '成员角色更新成功',
        'en-US': 'Member role updated successfully',
    },
    'owner_owner_base_added_member': {
        'zh-CN': '所有者是基础数据的拥有者，不能添加为成员',
        'en-US': 'The owner is the owner of the base and cannot be added as a member',
    },
    'phone_number_empty': {
        'zh-CN': '手机号码不能为空',
        'en-US': 'Phone number cannot be empty',
    },
    'invalid_phone_number_format': {
        'zh-CN': '手机号码格式不正确',
        'en-US': 'Invalid phone number format',
    },
    'failed_batch_create_records_try_again_later': {
        'zh-CN': '批量创建记录失败，请稍后重试',
        'en-US': 'Failed to batch create records, please try again later',
    },
    'failed_batch_delete_records_try_again_later': {
        'zh-CN': '批量删除记录失败，请稍后重试',
        'en-US': 'Failed to batch delete records, please try again later',
    },
    'failed_batch_update_records_try_again_later': {
        'zh-CN': '批量更新记录失败，请稍后重试',
        'en-US': 'Failed to batch update records, please try again later',
    },
    'failed_batch_mark_notifications_read_try_again_later': {
        'zh-CN': '批量标记站内信已读失败，请稍后重试',
        'en-US': 'Failed to batch mark notifications as read, please try again later',
    },
    'delivery_log': {
        'zh-CN': '投递记录',
        'en-US': 'Delivery log',
    },
    'specified_workflow_does_not_exist_manually_triggered': {
        'zh-CN': '指定的工作流不存在或不可手动触发',
        'en-US': 'The specified workflow does not exist or cannot be manually triggered',
    },
    'authorization_url_generated_successfully': {
        'zh-CN': '授权地址生成成功',
        'en-US': 'Authorization URL generated successfully',
    },
    'authorization_state_expired_invalid': {
        'zh-CN': '授权状态已过期或无效',
        'en-US': 'The authorization state has expired or is invalid',
    },
    'failed_reorder_try_again_later': {
        'zh-CN': '排序失败，请稍后重试',
        'en-US': 'Failed to reorder, please try again later',
    },
    'submission_failed_try_again_later': {
        'zh-CN': '提交失败，请稍后重试',
        'en-US': 'Submission failed, please try again later',
    },
    'submission_limit_reached': {
        'zh-CN': '提交次数已达上限',
        'en-US': 'Submission limit reached',
    },
    'submissions_too_frequent_try_again_later': {
        'zh-CN': '提交过于频繁，请稍后再试',
        'en-US': 'Submissions are too frequent, please try again later',
    },
    'failed_search_members_try_again_later': {
        'zh-CN': '搜索成员失败，请稍后重试',
        'en-US': 'Failed to search members, please try again later',
    },
    'members_searched_successfully': {
        'zh-CN': '搜索成员成功',
        'en-US': 'Members searched successfully',
    },
    'failed_search_templates_try_again_later': {
        'zh-CN': '搜索模板失败，请稍后重试',
        'en-US': 'Failed to search templates, please try again later',
    },
    'failed_search_records_try_again_later': {
        'zh-CN': '搜索记录失败，请稍后重试',
        'en-US': 'Failed to search records, please try again later',
    },
    'recipient_address_was_rejected': {
        'zh-CN': '收件人地址被拒绝',
        'en-US': 'The recipient address was rejected',
    },
    'failed_import_data_try_again_later': {
        'zh-CN': '数据导入失败，请稍后重试',
        'en-US': 'Failed to import data, please try again later',
    },
    'data_imported_successfully': {
        'zh-CN': '数据导入成功',
        'en-US': 'Data imported successfully',
    },
    'failed_export_data_try_again_later': {
        'zh-CN': '数据导出失败，请稍后重试',
        'en-US': 'Failed to export data, please try again later',
    },
    'data_table_created_successfully': {
        'zh-CN': '数据表创建成功',
        'en-US': 'Data table created successfully',
    },
    'data_validation_failed': {
        'zh-CN': '数据验证失败',
        'en-US': 'Data validation failed',
    },
    'failed_upload_file_try_again_later': {
        'zh-CN': '文件上传失败，请稍后重试',
        'en-US': 'Failed to upload the file, please try again later',
    },
    'file_uploaded_successfully': {
        'zh-CN': '文件上传成功',
        'en-US': 'File uploaded successfully',
    },
    'failed_download_file_try_again_later': {
        'zh-CN': '文件下载失败，请稍后重试',
        'en-US': 'Failed to download the file, please try again later',
    },
    'file_does_not_exist': {
        'zh-CN': '文件不存在',
        'en-US': 'The file does not exist',
    },
    'file_does_not_exist_been_deleted': {
        'zh-CN': '文件不存在或已被删除',
        'en-US': 'The file does not exist or has been deleted',
    },
    'file_content_not_valid_text_format': {
        'zh-CN': '文件内容不是有效的文本格式',
        'en-US': 'The file content is not a valid text format',
    },
    'file_content_empty': {
        'zh-CN': '文件内容为空',
        'en-US': 'The file content is empty',
    },
    'failed_analyze_file_try_again_later': {
        'zh-CN': '文件分析失败，请稍后重试',
        'en-US': 'Failed to analyze the file, please try again later',
    },
    'file_analysis_succeeded': {
        'zh-CN': '文件分析成功',
        'en-US': 'File analysis succeeded',
    },
    'file_name_empty': {
        'zh-CN': '文件名不能为空',
        'en-US': 'File name cannot be empty',
    },
    'file_expired_upload_again': {
        'zh-CN': '文件已过期，请重新上传',
        'en-US': 'The file has expired, please upload it again',
    },
    'file_access_failed': {
        'zh-CN': '文件访问失败',
        'en-US': 'File access failed',
    },
    'failed_preview_file_try_again_later': {
        'zh-CN': '文件预览失败，请稍后重试',
        'en-US': 'Failed to preview the file, please try again later',
    },
    'document_does_not_exist': {
        'zh-CN': '文档不存在',
        'en-US': 'Document does not exist',
    },
    'document_been_modified_someone_else_refresh_try_again': {
        'zh-CN': '文档已被他人修改，请刷新后重试',
        'en-US': 'The document has been modified by someone else, please refresh and try again',
    },
    'new_assignee_id_invalid': {
        'zh-CN': '新审批人 ID 无效',
        'en-US': 'The new assignee ID is invalid',
    },
    'invalid_uuid_format': {
        'zh-CN': '无效的 UUID 格式',
        'en-US': 'Invalid UUID format',
    },
    'invalid_token': {
        'zh-CN': '无效的令牌',
        'en-US': 'Invalid token',
    },
    'invalid_recipient_user_id': {
        'zh-CN': '无效的收件人用户 ID',
        'en-US': 'Invalid recipient user ID',
    },
    'invalid_file_path': {
        'zh-CN': '无效的文件路径',
        'en-US': 'Invalid file path',
    },
    'invalid_status_value': {
        'zh-CN': '无效的状态值',
        'en-US': 'Invalid status value',
    },
    'invalid_role_type': {
        'zh-CN': '无效的角色类型',
        'en-US': 'Invalid role type',
    },
    'invalid_authentication_token': {
        'zh-CN': '无效的认证令牌',
        'en-US': 'Invalid authentication token',
    },
    'invalid_access_token': {
        'zh-CN': '无效的访问令牌',
        'en-US': 'Invalid access token',
    },
    'no_permission_modify_document_administrator_rights_required': {
        'zh-CN': '无权修改文档，需要编辑者或更高权限',
        'en-US': 'No permission to modify the document, editor role or higher is required',
    },
    'no_permission_modify_record': {
        'zh-CN': '无权修改该记录',
        'en-US': 'No permission to modify this record',
    },
    'no_permission_create_field': {
        'zh-CN': '无权创建字段',
        'en-US': 'No permission to create a field',
    },
    'no_permission_create_document_administrator_rights_required': {
        'zh-CN': '无权创建文档，需要管理员权限',
        'en-US': 'No permission to create the document, administrator rights are required',
    },
    'no_permission_create_form_share': {
        'zh-CN': '无权创建表单分享',
        'en-US': 'No permission to create a form share',
    },
    'no_permission_delete_document_administrator_rights_required': {
        'zh-CN': '无权删除文档，需要管理员权限',
        'en-US': 'No permission to delete the document, administrator rights are required',
    },
    'no_permission_delete_form_share': {
        'zh-CN': '无权删除此表单分享',
        'en-US': 'No permission to delete this form share',
    },
    'no_permission_delete_notification': {
        'zh-CN': '无权删除该站内信',
        'en-US': 'No permission to delete this notification',
    },
    'no_permission_delete_record': {
        'zh-CN': '无权删除该记录',
        'en-US': 'No permission to delete this record',
    },
    'no_permission_create_records_table': {
        'zh-CN': '无权在该表格中创建记录',
        'en-US': 'No permission to create records in this table',
    },
    'no_permission_process_task': {
        'zh-CN': '无权处理该任务',
        'en-US': 'No permission to process this task',
    },
    'no_permission_process_approval_task': {
        'zh-CN': '无权处理该审批任务',
        'en-US': 'No permission to process this approval task',
    },
    'no_permission_operate_notification': {
        'zh-CN': '无权操作该站内信',
        'en-US': 'No permission to operate on this notification',
    },
    'no_permission_update_field': {
        'zh-CN': '无权更新字段',
        'en-US': 'No permission to update the field',
    },
    'no_permission_update_form_share': {
        'zh-CN': '无权更新此表单分享',
        'en-US': 'No permission to update this form share',
    },
    'no_permission_view_submission_records_form': {
        'zh-CN': '无权查看此表单的提交记录',
        'en-US': 'No permission to view the submission records of this form',
    },
    'no_permission_view_approval_task': {
        'zh-CN': '无权查看该审批任务',
        'en-US': 'No permission to view this approval task',
    },
    'no_permission_edit': {
        'zh-CN': '无权编辑',
        'en-US': 'No permission to edit',
    },
    'connect_smtp_server_check_server_address_port': {
        'zh-CN': '无法连接到 SMTP 服务器，请检查服务器地址和端口',
        'en-US': 'Cannot connect to the SMTP server, please check the server address and port',
    },
    'date_empty': {
        'zh-CN': '日期不能为空',
        'en-US': 'Date cannot be empty',
    },
    'old_password_incorrect': {
        'zh-CN': '旧密码错误',
        'en-US': 'The old password is incorrect',
    },
    'star_status_updated_successfully': {
        'zh-CN': '星标状态更新成功',
        'en-US': 'Star status updated successfully',
    },
    'failed_pause_workflow': {
        'zh-CN': '暂停工作流失败',
        'en-US': 'Failed to pause the workflow',
    },
    'failed_suspend_user_try_again_later': {
        'zh-CN': '暂停用户失败，请稍后重试',
        'en-US': 'Failed to suspend the user, please try again later',
    },
    'no_bases_been_shared_yet': {
        'zh-CN': '暂无分享给您的 Base',
        'en-US': 'No bases have been shared with you yet',
    },
    'failed_update_linked_value_try_again_later': {
        'zh-CN': '更新关联值失败，请稍后重试',
        'en-US': 'Failed to update the linked value, please try again later',
    },
    'failed_update_link_relation_try_again_later': {
        'zh-CN': '更新关联关系失败，请稍后重试',
        'en-US': 'Failed to update the link relation, please try again later',
    },
    'failed_update_link_relation_type_try_again_later': {
        'zh-CN': '更新关联关系类型失败，请稍后重试',
        'en-US': 'Failed to update the link relation type, please try again later',
    },
    'failed_update_link_field_try_again_later': {
        'zh-CN': '更新关联字段失败，请稍后重试',
        'en-US': 'Failed to update the link field, please try again later',
    },
    'update_failed': {
        'zh-CN': '更新失败',
        'en-US': 'Update failed',
    },
    'update_failed_try_again_later': {
        'zh-CN': '更新失败，请稍后重试',
        'en-US': 'Update failed, please try again later',
    },
    'failed_update_field_try_again_later': {
        'zh-CN': '更新字段失败，请稍后重试',
        'en-US': 'Failed to update the field, please try again later',
    },
    'updated_successfully': {
        'zh-CN': '更新成功',
        'en-US': 'Updated successfully',
    },
    'lookup_field_updated_successfully': {
        'zh-CN': '更新查找字段成功',
        'en-US': 'Lookup field updated successfully',
    },
    'failed_update_template_try_again_later': {
        'zh-CN': '更新模板失败，请稍后重试',
        'en-US': 'Failed to update the template, please try again later',
    },
    'failed_update_status_try_again_later': {
        'zh-CN': '更新状态失败，请稍后重试',
        'en-US': 'Failed to update the status, please try again later',
    },
    'failed_update_user_try_again_later': {
        'zh-CN': '更新用户失败，请稍后重试',
        'en-US': 'Failed to update the user, please try again later',
    },
    'failed_update_view_try_again_later': {
        'zh-CN': '更新视图失败，请稍后重试',
        'en-US': 'Failed to update the view, please try again later',
    },
    'failed_update_view_order_try_again_later': {
        'zh-CN': '更新视图排序失败，请稍后重试',
        'en-US': 'Failed to update the view order, please try again later',
    },
    'failed_update_record_try_again_later': {
        'zh-CN': '更新记录失败，请稍后重试',
        'en-US': 'Failed to update the record, please try again later',
    },
    'failed_update_email_template_try_again_later': {
        'zh-CN': '更新邮件模板失败，请稍后重试',
        'en-US': 'Failed to update the email template, please try again later',
    },
    'most_lookup_conditions_supported': {
        'zh-CN': '最多支持 5 个查找条件',
        'en-US': 'At most 5 lookup conditions are supported',
    },
    'server_not_configured_encryption_key': {
        'zh-CN': '服务器未配置加密密钥',
        'en-US': 'The server is not configured with an encryption key',
    },
    'service_configuration_error_contact_administrator': {
        'zh-CN': '服务配置错误，请联系管理员',
        'en-US': 'Service configuration error, please contact the administrator',
    },
    'untitled_record': {
        'zh-CN': '未命名记录',
        'en-US': 'Untitled record',
    },
    'default_content_template_not_found': {
        'zh-CN': '未找到该模板的默认内容',
        'en-US': 'Default content for this template not found',
    },
    'no_assignee_resolved': {
        'zh-CN': '未解析到审批人',
        'en-US': 'No assignee resolved',
    },
    'secret_key_not_configured': {
        'zh-CN': '未配置 SECRET_KEY',
        'en-US': 'SECRET_KEY is not configured',
    },
    'insufficient_permissions_perform_operation': {
        'zh-CN': '权限不足，无法执行此操作',
        'en-US': 'Insufficient permissions to perform this operation',
    },
    'permission_type_view_edit': {
        'zh-CN': '权限类型必须是 view 或 edit',
        'en-US': "Permission type must be 'view' or 'edit'",
    },
    'condition_connector': {
        'zh-CN': '条件连接符必须为 and 或 or',
        'en-US': "Condition connector must be 'and' or 'or'",
    },
    'failed_query_logs_try_again_later': {
        'zh-CN': '查询日志失败，请稍后重试',
        'en-US': 'Failed to query logs, please try again later',
    },
    'failed_mark_notification_read_try_again_later': {
        'zh-CN': '标记站内信已读失败，请稍后重试',
        'en-US': 'Failed to mark the notification as read, please try again later',
    }
}
