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

MESSAGES_PART6 = {
    'failed_fetch_notification_logs_try_again_later': {
        'zh-CN': '获取站内信日志失败，请稍后重试',
        'en-US': 'Failed to fetch notification logs, please try again later',
    },
    'fetched_notification_logs_successfully': {
        'zh-CN': '获取站内信日志成功',
        'en-US': 'Fetched notification logs successfully',
    },
    'failed_fetch_notification_statistics_try_again_later': {
        'zh-CN': '获取站内信统计失败，请稍后重试',
        'en-US': 'Failed to fetch notification statistics, please try again later',
    },
    'fetched_notification_statistics_successfully': {
        'zh-CN': '获取站内信统计成功',
        'en-US': 'Fetched notification statistics successfully',
    },
    'failed_fetch_notification_details_try_again_later': {
        'zh-CN': '获取站内信详情失败，请稍后重试',
        'en-US': 'Failed to fetch notification details, please try again later',
    },
    'fetched_notification_details_successfully': {
        'zh-CN': '获取站内信详情成功',
        'en-US': 'Fetched notification details successfully',
    },
    'failed_fetch_system_configuration_try_again_later': {
        'zh-CN': '获取系统配置失败，请稍后重试',
        'en-US': 'Failed to fetch system configuration, please try again later',
    },
    'fetched_system_configuration_successfully': {
        'zh-CN': '获取系统配置成功',
        'en-US': 'Fetched system configuration successfully',
    },
    'failed_fetch_statistics_try_again_later': {
        'zh-CN': '获取统计失败，请稍后重试',
        'en-US': 'Failed to fetch statistics, please try again later',
    },
    'fetched_node_list_successfully': {
        'zh-CN': '获取节点列表成功',
        'en-US': 'Fetched node list successfully',
    },
    'fetched_form_share_list_successfully': {
        'zh-CN': '获取表单分享列表成功',
        'en-US': 'Fetched form share list successfully',
    },
    'fetched_form_share_details_successfully': {
        'zh-CN': '获取表单分享详情成功',
        'en-US': 'Fetched form share details successfully',
    },
    'failed_fetch_form_structure': {
        'zh-CN': '获取表单结构失败',
        'en-US': 'Failed to fetch the form structure',
    },
    'fetched_form_structure_successfully': {
        'zh-CN': '获取表单结构成功',
        'en-US': 'Fetched the form structure successfully',
    },
    'fetched_table_list_successfully': {
        'zh-CN': '获取表格列表成功',
        'en-US': 'Fetched table list successfully',
    },
    'fetched_table_successfully': {
        'zh-CN': '获取表格成功',
        'en-US': 'Fetched table successfully',
    },
    'failed_fetch_view_list_try_again_later': {
        'zh-CN': '获取视图列表失败，请稍后重试',
        'en-US': 'Failed to fetch the view list, please try again later',
    },
    'failed_fetch_view_details_try_again_later': {
        'zh-CN': '获取视图详情失败，请稍后重试',
        'en-US': 'Failed to fetch view details, please try again later',
    },
    'fetched_role_list_successfully': {
        'zh-CN': '获取角色列表成功',
        'en-US': 'Fetched role list successfully',
    },
    'fetched_trigger_successfully': {
        'zh-CN': '获取触发器成功',
        'en-US': 'Fetched trigger successfully',
    },
    'failed_fetch_record_list_try_again_later': {
        'zh-CN': '获取记录列表失败，请稍后重试',
        'en-US': 'Failed to fetch the record list, please try again later',
    },
    'failed_fetch_record_approval_history_try_again_later': {
        'zh-CN': '获取记录审批历史失败，请稍后重试',
        'en-US': 'Failed to fetch record approval history, please try again later',
    },
    'failed_fetch_record_details_try_again_later': {
        'zh-CN': '获取记录详情失败，请稍后重试',
        'en-US': 'Failed to fetch record details, please try again later',
    },
    'failed_fetch_email_sending_logs_try_again_later': {
        'zh-CN': '获取邮件发送日志失败，请稍后重试',
        'en-US': 'Failed to fetch email sending logs, please try again later',
    },
    'failed_fetch_email_sending_statistics_try_again_later': {
        'zh-CN': '获取邮件发送统计失败，请稍后重试',
        'en-US': 'Failed to fetch email sending statistics, please try again later',
    },
    'fetched_email_sending_statistics_successfully': {
        'zh-CN': '获取邮件发送统计成功',
        'en-US': 'Fetched email sending statistics successfully',
    },
    'failed_fetch_email_template_list_try_again_later': {
        'zh-CN': '获取邮件模板列表失败，请稍后重试',
        'en-US': 'Failed to fetch the email template list, please try again later',
    },
    'fetched_email_template_list_successfully': {
        'zh-CN': '获取邮件模板列表成功',
        'en-US': 'Fetched the email template list successfully',
    },
    'fetched_email_template_details_successfully': {
        'zh-CN': '获取邮件模板详情成功',
        'en-US': 'Fetched email template details successfully',
    },
    'failed_fetch_email_queue_statistics_try_again_later': {
        'zh-CN': '获取邮件队列统计失败，请稍后重试',
        'en-US': 'Failed to fetch email queue statistics, please try again later',
    },
    'fetched_email_queue_statistics_successfully': {
        'zh-CN': '获取邮件队列统计成功',
        'en-US': 'Fetched email queue statistics successfully',
    },
    'fetched_attachment_successfully': {
        'zh-CN': '获取附件成功',
        'en-US': 'Fetched attachment successfully',
    },
    'form_share_does_not_exist': {
        'zh-CN': '表单分享不存在',
        'en-US': 'Form share does not exist',
    },
    'form_share_invalid': {
        'zh-CN': '表单分享无效',
        'en-US': 'Invalid form share',
    },
    'form_share_created_successfully': {
        'zh-CN': '表单分享创建成功',
        'en-US': 'Form share created successfully',
    },
    'form_share_deleted_successfully': {
        'zh-CN': '表单分享删除成功',
        'en-US': 'Form share deleted successfully',
    },
    'form_share_updated_successfully': {
        'zh-CN': '表单分享更新成功',
        'en-US': 'Form share updated successfully',
    },
    'form_share_valid': {
        'zh-CN': '表单分享有效',
        'en-US': 'The form share is valid',
    },
    'table': {
        'zh-CN': '表格',
        'en-US': 'Table',
    },
    'table_does_not_exist': {
        'zh-CN': '表格不存在',
        'en-US': 'Table does not exist',
    },
    'table_created_successfully': {
        'zh-CN': '表格创建成功',
        'en-US': 'Table created successfully',
    },
    'table_deleted_successfully': {
        'zh-CN': '表格删除成功',
        'en-US': 'Table deleted successfully',
    },
    'table_name_exceed_characters': {
        'zh-CN': '表格名称不能超过100个字符',
        'en-US': 'Table name cannot exceed 100 characters',
    },
    'table_copied_successfully': {
        'zh-CN': '表格复制成功',
        'en-US': 'Table copied successfully',
    },
    'table_order_updated_successfully': {
        'zh-CN': '表格排序更新成功',
        'en-US': 'Table order updated successfully',
    },
    'table_updated_successfully': {
        'zh-CN': '表格更新成功',
        'en-US': 'Table updated successfully',
    },
    'view_does_not_exist': {
        'zh-CN': '视图不存在',
        'en-US': 'View does not exist',
    },
    'view_does_not_exist_does_not_belong_table': {
        'zh-CN': '视图不存在或不属于该表格',
        'en-US': 'The view does not exist or does not belong to this table',
    },
    'view_created_successfully': {
        'zh-CN': '视图创建成功',
        'en-US': 'View created successfully',
    },
    'view_deleted_successfully': {
        'zh-CN': '视图删除成功',
        'en-US': 'View deleted successfully',
    },
    'view_copied_successfully': {
        'zh-CN': '视图复制成功',
        'en-US': 'View copied successfully',
    },
    'view_order_updated_successfully': {
        'zh-CN': '视图排序更新成功',
        'en-US': 'View order updated successfully',
    },
    'view_updated_successfully': {
        'zh-CN': '视图更新成功',
        'en-US': 'View updated successfully',
    },
    'failed_decrypt_password_check_configuration': {
        'zh-CN': '解密密码失败，请检查配置',
        'en-US': 'Failed to decrypt the password, please check the configuration',
    },
    'trigger_updated': {
        'zh-CN': '触发器已更新',
        'en-US': 'Trigger updated',
    },
    'failed_trigger_workflow_try_again_later': {
        'zh-CN': '触发工作流失败，请稍后重试',
        'en-US': 'Failed to trigger the workflow, please try again later',
    },
    'invalid_computation_type': {
        'zh-CN': '计算方式不合法',
        'en-US': 'Invalid computation type',
    },
    'computation_type_empty': {
        'zh-CN': '计算方式不能为空',
        'en-US': 'Computation type cannot be empty',
    },
    'authentication_token_expired_log_again': {
        'zh-CN': '认证令牌已过期，请重新登录',
        'en-US': 'The authentication token has expired, please log in again',
    },
    'record_id_list_empty': {
        'zh-CN': '记录ID列表不能为空',
        'en-US': 'Record ID list cannot be empty',
    },
    'record_does_not_exist': {
        'zh-CN': '记录不存在',
        'en-US': 'Record does not exist',
    },
    'record_does_not_belong_table': {
        'zh-CN': '记录不属于该表格',
        'en-US': 'The record does not belong to this table',
    },
    'record_created_successfully': {
        'zh-CN': '记录创建成功',
        'en-US': 'Record created successfully',
    },
    'record_deleted_successfully': {
        'zh-CN': '记录删除成功',
        'en-US': 'Record deleted successfully',
    },
    'record_been_modified_another_user_refresh_try_again': {
        'zh-CN': '记录已被其他用户修改，请刷新后重试',
        'en-US': 'The record has been modified by another user, please refresh and try again',
    },
    'failed_log_record_try_again_later': {
        'zh-CN': '记录日志失败，请稍后重试',
        'en-US': 'Failed to log the record, please try again later',
    },
    'record_updated_successfully': {
        'zh-CN': '记录更新成功',
        'en-US': 'Record updated successfully',
    },
    'failed_set_default_view_try_again_later': {
        'zh-CN': '设置默认视图失败，请稍后重试',
        'en-US': 'Failed to set the default view, please try again later',
    },
    'access_succeeded': {
        'zh-CN': '访问成功',
        'en-US': 'Access succeeded',
    },
    'token_not_applicable_open_api': {
        'zh-CN': '该令牌不适用于开放 API',
        'en-US': 'This token is not applicable to the open API',
    },
    'share_link_been_invalidated': {
        'zh-CN': '该分享链接已失效',
        'en-US': 'This share link has been invalidated',
    },
    'share_link_expired_2': {
        'zh-CN': '该分享链接已过期',
        'en-US': 'This share link has expired',
    },
    'field_not_link_field': {
        'zh-CN': '该字段不是关联字段',
        'en-US': 'This field is not a link field',
    },
    'field_not_self_referencing_link_field_pointing_table': {
        'zh-CN': '该字段不是指向本表的自引用关联字段',
        'en-US': 'This field is not a self-referencing link field pointing to this table',
    },
    'field_already_link_relation': {
        'zh-CN': '该字段已存在关联关系',
        'en-US': 'This field already has a link relation',
    },
    'match_field_not_in_target_table': {
        'zh-CN': '匹配字段不属于关联字段的目标表',
        'en-US': 'The match field does not belong to the target table of the link field',
    },
    'failed_batch_match_link_values_try_again_later': {
        'zh-CN': '批量匹配关联失败，请稍后重试',
        'en-US': 'Failed to batch match link values, please try again later',
    },
    'provide_field_id': {
        'zh-CN': '请提供字段 ID',
        'en-US': 'Please provide the field ID',
    },
    'provide_match_field_id': {
        'zh-CN': '请提供匹配字段 ID',
        'en-US': 'Please provide the match field ID',
    },
    'pairs_must_be_array': {
        'zh-CN': 'pairs 必须是数组',
        'en-US': 'pairs must be an array',
    },
    'batch_match_more_than_pairs_limit': {
        'zh-CN': '批量匹配每次最多处理 1000 条数据',
        'en-US': 'Batch matching supports up to 1000 pairs per request',
    },
    'batch_match_link_completed': {
        'zh-CN': '批量匹配关联完成',
        'en-US': 'Batch link matching completed',
    },
    'user_already_member': {
        'zh-CN': '该用户已经是成员',
        'en-US': 'This user is already a member',
    },
    'form_does_not_allow_anonymous_file_uploads': {
        'zh-CN': '该表单不允许匿名上传附件',
        'en-US': 'This form does not allow anonymous file uploads',
    },
    'form_does_not_require_captcha': {
        'zh-CN': '该表单不需要验证码',
        'en-US': 'This form does not require a captcha',
    },
    'form_share_been_invalidated': {
        'zh-CN': '该表单分享已失效',
        'en-US': 'This form share has been invalidated',
    },
    'form_share_expired': {
        'zh-CN': '该表单分享已过期',
        'en-US': 'This form share has expired',
    },
    'email_already_used_another_user': {
        'zh-CN': '该邮箱已被其他用户使用',
        'en-US': 'This email is already used by another user',
    },
    'language_python': {
        'zh-CN': '语言必须为 \'python\'',
        'en-US': 'The language must be \'python\'',
    },
    'upload_excel_file_xlsx_xls_format': {
        'zh-CN': '请上传Excel文件(.xlsx或.xls格式)',
        'en-US': 'Please upload an Excel file (.xlsx or .xls format)',
    },
    'watch_project_before_accessing': {
        'zh-CN': '请先 watch 本项目后再访问',
        'en-US': 'Please watch this project before accessing',
    },
    'log_first': {
        'zh-CN': '请先登录',
        'en-US': 'Please log in first',
    },
    'install_pandas_pip_install_pandas_openpyxl': {
        'zh-CN': '请安装 pandas: pip install pandas openpyxl',
        'en-US': 'Please install pandas: pip install pandas openpyxl',
    },
    'specify_base_id': {
        'zh-CN': '请指定Base ID',
        'en-US': 'Please specify a Base ID',
    },
    'specify_target_table_id': {
        'zh-CN': '请指定目标表格 ID',
        'en-US': 'Please specify the target table ID',
    },
    'specify_table_id': {
        'zh-CN': '请指定表格 ID',
        'en-US': 'Please specify the table ID',
    },
    'provide_link_type': {
        'zh-CN': '请提供关联类型',
        'en-US': 'Please provide the link type',
    },
    'provide_workflow_id': {
        'zh-CN': '请提供工作流 ID',
        'en-US': 'Please provide the workflow ID',
    },
    'provide_member_list': {
        'zh-CN': '请提供成员列表',
        'en-US': 'Please provide the member list',
    },
    'provide_sort_data': {
        'zh-CN': '请提供排序数据',
        'en-US': 'Please provide the sort data',
    },
    'provide_file_id': {
        'zh-CN': '请提供文件标识',
        'en-US': 'Please provide the file ID',
    },
    'provide_new_role': {
        'zh-CN': '请提供新角色',
        'en-US': 'Please provide the new role',
    },
    'provide_valid_json_data_array': {
        'zh-CN': '请提供有效的 JSON 数据数组',
        'en-US': 'Please provide a valid JSON data array',
    },
    'provide_template_name': {
        'zh-CN': '请提供模板名称',
        'en-US': 'Please provide the template name',
    },
    'provide_target_table_id': {
        'zh-CN': '请提供目标表ID',
        'en-US': 'Please provide the target table ID',
    },
    'provide_widget_type': {
        'zh-CN': '请提供组件类型',
        'en-US': 'Please provide the widget type',
    },
    'provide_table_id': {
        'zh-CN': '请提供表格 ID',
        'en-US': 'Please provide the table ID',
    },
    'provide_table_id_2': {
        'zh-CN': '请提供表格ID',
        'en-US': 'Please provide the table ID',
    },
    'provide_email_address_invited_user': {
        'zh-CN': '请提供被邀请用户的邮箱地址',
        'en-US': 'Please provide the email address of the invited user',
    },
    'provide_email_address': {
        'zh-CN': '请提供邮箱地址',
        'en-US': 'Please provide an email address',
    },
    'provide_verification_token': {
        'zh-CN': '请提供验证令牌',
        'en-US': 'Please provide the verification token',
    },
    'request_body_empty_2': {
        'zh-CN': '请求体不能为空',
        'en-US': 'The request body cannot be empty',
    },
    'request_content_json_format': {
        'zh-CN': '请求内容必须是 JSON 格式',
        'en-US': 'The request content must be in JSON format',
    },
    'request_data_empty': {
        'zh-CN': '请求数据不能为空',
        'en-US': 'The request data cannot be empty',
    },
    'request_method_get_post_put': {
        'zh-CN': '请求方法必须是 GET、POST 或 PUT',
        'en-US': 'The request method must be GET, POST or PUT',
    },
    'request_missing_authentication_token': {
        'zh-CN': '请求缺少认证令牌',
        'en-US': 'The request is missing the authentication token',
    },
    'select_least_one_field': {
        'zh-CN': '请至少选择一个字段',
        'en-US': 'Please select at least one field',
    },
    'enter_search_keyword': {
        'zh-CN': '请输入搜索关键词',
        'en-US': 'Please enter a search keyword',
    },
    'enter_data_table_name': {
        'zh-CN': '请输入数据表名称',
        'en-US': 'Please enter the data table name',
    },
    'select_linked_data_table': {
        'zh-CN': '请选择关联数据表',
        'en-US': 'Please select a linked data table',
    },
    'select_file_upload': {
        'zh-CN': '请选择要上传的文件',
        'en-US': 'Please select the file to upload',
    },
    'select_file_analyze': {
        'zh-CN': '请选择要分析的文件',
        'en-US': 'Please select the file to analyze',
    },
    'select_file_import': {
        'zh-CN': '请选择要导入的文件',
        'en-US': 'Please select the file to import',
    },
    'verify_email_address': {
        'zh-CN': '请验证您的邮箱地址',
        'en-US': 'Please verify your email address',
    },
    'timeout_positive_integer_between': {
        'zh-CN': '超时时间必须为 1-300 之间的正整数',
        'en-US': 'The timeout must be a positive integer between 1 and 300',
    },
    'expiry_time_past': {
        'zh-CN': '过期时间不能是过去的时间',
        'en-US': 'The expiry time cannot be in the past',
    },
    'expiry_time_valid_unix_timestamp': {
        'zh-CN': '过期时间必须是有效的 Unix 时间戳',
        'en-US': 'The expiry time must be a valid Unix timestamp',
    },
    'invalid_share_permission': {
        'zh-CN': '分享权限不合法（仅支持 editor/commenter/viewer）',
        'en-US': 'Invalid share permission (only editor/commenter/viewer are supported)',
    },
    'invalid_view_selection': {
        'zh-CN': '可见视图范围选择不合法',
        'en-US': 'Invalid visible view selection',
    },
    'joined_table_successfully': {
        'zh-CN': '已成功加入该数据表',
        'en-US': 'Successfully joined the table',
    },
    'fetched_share_member_list_successfully': {
        'zh-CN': '获取分享成员列表成功',
        'en-US': 'Successfully fetched share member list',
    },
    'table_share_member_removed_successfully': {
        'zh-CN': '已将该用户移出分享',
        'en-US': 'Member removed from table share',
    },
    'table_share_member_does_not_exist': {
        'zh-CN': '该用户不在此分享的成员列表中',
        'en-US': 'User is not a member of this table share',
    },
    'table_share_member_cannot_remove_yourself': {
        'zh-CN': '不能移除自己',
        'en-US': 'You cannot remove yourself',
    }
}
