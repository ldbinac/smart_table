"""
默认邮件模板数据
包含系统所需的所有默认邮件模板
"""

# 用户注册验证邮件模板
USER_REGISTRATION_TEMPLATE = {
    "template_key": "user_registration",
    "name": "用户注册验证",
    "subject": "欢迎注册 Smart Table - 请验证您的邮箱",
    "content_html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>邮箱验证</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; font-weight: 600; }
        .content { padding: 40px 30px; }
        .content h2 { color: #333333; font-size: 20px; margin-bottom: 20px; }
        .content p { color: #666666; line-height: 1.6; margin-bottom: 20px; }
        .button { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: 500; margin: 20px 0; }
        .link-box { background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 15px; margin: 20px 0; word-break: break-all; }
        .footer { padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #999999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Smart Table</h1>
        </div>
        <div class="content">
            <h2>您好，{{user_name}}！</h2>
            <p>感谢您注册 Smart Table！为了完成注册流程，请验证您的邮箱地址。</p>
            <p style="text-align: center;">
                <a href="{{verification_link}}" class="button">验证邮箱地址</a>
            </p>
            <p>或者，您可以复制以下链接到浏览器地址栏：</p>
            <div class="link-box">{{verification_link}}</div>
            <p><strong>此链接将在24小时后过期。</strong>如果您没有注册 Smart Table，请忽略此邮件。</p>
        </div>
        <div class="footer">
            <p>此邮件由 Smart Table 系统自动发送，请勿回复。</p>
            <p>&copy; 2024 Smart Table. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
""",
    "content_text": """
您好，{{user_name}}！

感谢您注册 Smart Table！为了完成注册流程，请验证您的邮箱地址。

请点击以下链接验证您的邮箱：
{{verification_link}}

此链接将在24小时后过期。如果您没有注册 Smart Table，请忽略此邮件。

---
此邮件由 Smart Table 系统自动发送，请勿回复。
&copy; 2024 Smart Table. All rights reserved.
""",
    "description": "新用户注册后发送的邮箱验证邮件",
    "is_default": True
}

# 密码重置邮件模板
PASSWORD_RESET_TEMPLATE = {
    "template_key": "password_reset",
    "name": "密码重置",
    "subject": "Smart Table - 密码重置请求",
    "content_html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>密码重置</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; font-weight: 600; }
        .content { padding: 40px 30px; }
        .content h2 { color: #333333; font-size: 20px; margin-bottom: 20px; }
        .content p { color: #666666; line-height: 1.6; margin-bottom: 20px; }
        .button { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: 500; margin: 20px 0; }
        .link-box { background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 15px; margin: 20px 0; word-break: break-all; }
        .warning { background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px; }
        .footer { padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #999999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Smart Table</h1>
        </div>
        <div class="content">
            <h2>密码重置请求</h2>
            <p>您好，{{user_name}}！</p>
            <p>我们收到了您的密码重置请求。请点击下方按钮重置您的密码：</p>
            <p style="text-align: center;">
                <a href="{{reset_link}}" class="button">重置密码</a>
            </p>
            <p>或者，您可以复制以下链接到浏览器地址栏：</p>
            <div class="link-box">{{reset_link}}</div>
            <div class="warning">
                <strong>安全提示：</strong>此链接将在1小时后过期。如果您没有请求重置密码，请忽略此邮件，您的账号仍然安全。
            </div>
        </div>
        <div class="footer">
            <p>此邮件由 Smart Table 系统自动发送，请勿回复。</p>
            <p>&copy; 2024 Smart Table. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
""",
    "content_text": """
密码重置请求

您好，{{user_name}}！

我们收到了您的密码重置请求。请点击以下链接重置您的密码：
{{reset_link}}

此链接将在1小时后过期。

安全提示：如果您没有请求重置密码，请忽略此邮件，您的账号仍然安全。

---
此邮件由 Smart Table 系统自动发送，请勿回复。
&copy; 2024 Smart Table. All rights reserved.
""",
    "description": "用户请求密码重置时发送的邮件",
    "is_default": True
}

# 账号停用通知模板
ACCOUNT_SUSPENDED_TEMPLATE = {
    "template_key": "account_suspended",
    "name": "账号停用通知",
    "subject": "Smart Table - 您的账号已被停用",
    "content_html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>账号停用通知</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background-color: #dc3545; padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; }
        .content { padding: 40px 30px; }
        .content h2 { color: #dc3545; font-size: 20px; }
        .content p { color: #666666; line-height: 1.6; margin-bottom: 20px; }
        .info-box { background-color: #f8f9fa; border-left: 4px solid #dc3545; padding: 15px; margin: 20px 0; }
        .footer { padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #999999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>账号停用通知</h1>
        </div>
        <div class="content">
            <h2>您好，{{user_name}}</h2>
            <p>您的 Smart Table 账号已被管理员停用。</p>
            <div class="info-box">
                <p><strong>停用时间：</strong>{{operation_time}}</p>
                <p><strong>停用原因：</strong>{{reason}}</p>
            </div>
            <p>如果您对此有疑问，请联系管理员：{{admin_name}}</p>
            <p>感谢您的理解与支持。</p>
        </div>
        <div class="footer">
            <p>此邮件由 Smart Table 系统自动发送，请勿回复。</p>
        </div>
    </div>
</body>
</html>
""",
    "content_text": """
账号停用通知

您好，{{user_name}}

您的 Smart Table 账号已被管理员停用。

停用时间：{{operation_time}}
停用原因：{{reason}}

如果您对此有疑问，请联系管理员：{{admin_name}}

感谢您的理解与支持。

---
此邮件由 Smart Table 系统自动发送，请勿回复。
""",
    "description": "管理员停用用户账号时发送的通知",
    "is_default": True
}

# 账号启用通知模板
ACCOUNT_ACTIVATED_TEMPLATE = {
    "template_key": "account_activated",
    "name": "账号启用通知",
    "subject": "Smart Table - 您的账号已恢复使用",
    "content_html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>账号启用通知</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #28a745 0%, #20c997 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; }
        .content { padding: 40px 30px; }
        .content h2 { color: #28a745; font-size: 20px; }
        .content p { color: #666666; line-height: 1.6; margin-bottom: 20px; }
        .button { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: 500; margin: 20px 0; }
        .footer { padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #999999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>账号已恢复</h1>
        </div>
        <div class="content">
            <h2>欢迎回来，{{user_name}}！</h2>
            <p>您的 Smart Table 账号已恢复使用。</p>
            <p><strong>恢复时间：</strong>{{operation_time}}</p>
            <p>您现在可以正常登录并使用所有功能。</p>
            <p style="text-align: center;">
                <a href="{{login_link}}" class="button">立即登录</a>
            </p>
        </div>
        <div class="footer">
            <p>此邮件由 Smart Table 系统自动发送，请勿回复。</p>
        </div>
    </div>
</body>
</html>
""",
    "content_text": """
账号启用通知

欢迎回来，{{user_name}}！

您的 Smart Table 账号已恢复使用。

恢复时间：{{operation_time}}

您现在可以正常登录并使用所有功能。

立即登录：{{login_link}}

---
此邮件由 Smart Table 系统自动发送，请勿回复。
""",
    "description": "管理员启用用户账号时发送的通知",
    "is_default": True
}

# 密码重置通知模板
PASSWORD_CHANGED_TEMPLATE = {
    "template_key": "password_changed",
    "name": "密码重置通知",
    "subject": "Smart Table - 您的密码已重置",
    "content_html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>密码重置通知</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #17a2b8 0%, #138496 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; }
        .content { padding: 40px 30px; }
        .content p { color: #666666; line-height: 1.6; margin-bottom: 20px; }
        .warning { background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px; }
        .footer { padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #999999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>密码已重置</h1>
        </div>
        <div class="content">
            <p>您好，{{user_name}}！</p>
            <p>您的 Smart Table 账号密码已被重置。</p>
            <p><strong>重置时间：</strong>{{operation_time}}</p>
            <div class="warning">
                <strong>安全提示：</strong>如果您没有进行此操作，请立即联系管理员或修改您的密码。
            </div>
        </div>
        <div class="footer">
            <p>此邮件由 Smart Table 系统自动发送，请勿回复。</p>
        </div>
    </div>
</body>
</html>
""",
    "content_text": """
密码重置通知

您好，{{user_name}}！

您的 Smart Table 账号密码已被重置。

重置时间：{{operation_time}}

安全提示：如果您没有进行此操作，请立即联系管理员或修改您的密码。

---
此邮件由 Smart Table 系统自动发送，请勿回复。
""",
    "description": "密码被重置后发送的通知",
    "is_default": True
}

# 账号信息变更通知模板
ACCOUNT_UPDATED_TEMPLATE = {
    "template_key": "account_updated",
    "name": "账号信息变更通知",
    "subject": "Smart Table - 您的账号信息已更新",
    "content_html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>账号信息变更</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; }
        .content { padding: 40px 30px; }
        .content p { color: #666666; line-height: 1.6; margin-bottom: 20px; }
        .changes { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; padding: 20px; margin: 20px 0; }
        .changes ul { margin: 0; padding-left: 20px; }
        .changes li { margin-bottom: 10px; color: #495057; }
        .footer { padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #999999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>账号信息更新</h1>
        </div>
        <div class="content">
            <p>您好，{{user_name}}！</p>
            <p>您的 Smart Table 账号信息已被更新。</p>
            <p><strong>更新时间：</strong>{{operation_time}}</p>
            <div class="changes">
                <p><strong>变更内容：</strong></p>
                <ul>
                    {{changes_list}}
                </ul>
            </div>
            <p>如果您没有进行这些更改，请联系管理员。</p>
        </div>
        <div class="footer">
            <p>此邮件由 Smart Table 系统自动发送，请勿回复。</p>
        </div>
    </div>
</body>
</html>
""",
    "content_text": """
账号信息变更通知

您好，{{user_name}}！

您的 Smart Table 账号信息已被更新。

更新时间：{{operation_time}}

变更内容：
{{changes_list}}

如果您没有进行这些更改，请联系管理员。

---
此邮件由 Smart Table 系统自动发送，请勿回复。
""",
    "description": "账号信息被修改后发送的通知",
    "is_default": True
}

# 账号删除通知模板
ACCOUNT_DELETED_TEMPLATE = {
    "template_key": "account_deleted",
    "name": "账号删除通知",
    "subject": "Smart Table - 您的账号将被删除",
    "content_html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>账号删除通知</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background-color: #dc3545; padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; }
        .content { padding: 40px 30px; }
        .content p { color: #666666; line-height: 1.6; margin-bottom: 20px; }
        .warning { background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 6px; padding: 20px; margin: 20px 0; color: #721c24; }
        .footer { padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #999999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>账号删除通知</h1>
        </div>
        <div class="content">
            <p>您好，{{user_name}}！</p>
            <p>您的 Smart Table 账号已被管理员删除。</p>
            <p><strong>删除时间：</strong>{{operation_time}}</p>
            <div class="warning">
                <p><strong>重要提示：</strong></p>
                <ul>
                    <li>您的所有数据将被永久删除，无法恢复</li>
                    <li>您创建的多维表将由管理员决定保留或删除</li>
                    <li>您将无法再使用此账号登录系统</li>
                </ul>
            </div>
            <p>如果您对此有疑问，请联系管理员：{{admin_name}}</p>
        </div>
        <div class="footer">
            <p>此邮件由 Smart Table 系统自动发送，请勿回复。</p>
        </div>
    </div>
</body>
</html>
""",
    "content_text": """
账号删除通知

您好，{{user_name}}！

您的 Smart Table 账号已被管理员删除。

删除时间：{{operation_time}}

重要提示：
- 您的所有数据将被永久删除，无法恢复
- 您创建的多维表将由管理员决定保留或删除
- 您将无法再使用此账号登录系统

如果您对此有疑问，请联系管理员：{{admin_name}}

---
此邮件由 Smart Table 系统自动发送，请勿回复。
""",
    "description": "管理员删除用户账号前发送的通知",
    "is_default": True
}

# 多维表分享邀请模板
SHARE_INVITATION_TEMPLATE = {
    "template_key": "share_invitation",
    "name": "多维表分享邀请",
    "subject": "{{sharer_name}} 邀请您协作编辑多维表 - {{base_name}}",
    "content_html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>多维表分享邀请</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; }
        .content { padding: 40px 30px; }
        .content p { color: #666666; line-height: 1.6; margin-bottom: 20px; }
        .base-info { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; padding: 20px; margin: 20px 0; }
        .base-info h3 { margin-top: 0; color: #333333; }
        .permission { display: inline-block; background-color: #e9ecef; padding: 5px 12px; border-radius: 4px; font-size: 14px; color: #495057; margin-top: 10px; }
        .button { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: 500; margin: 20px 0; }
        .footer { padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #999999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>多维表分享邀请</h1>
        </div>
        <div class="content">
            <p>您好！</p>
            <p><strong>{{sharer_name}}</strong> 邀请您协作编辑多维表：</p>
            <div class="base-info">
                <h3>{{base_name}}</h3>
                <p>{{base_description}}</p>
                <span class="permission">权限：{{permission}}</span>
            </div>
            <p style="text-align: center;">
                <a href="{{base_link}}" class="button">查看多维表</a>
            </p>
            <p>如果您没有 Smart Table 账号，请先注册。</p>
        </div>
        <div class="footer">
            <p>此邮件由 Smart Table 系统自动发送，请勿回复。</p>
        </div>
    </div>
</body>
</html>
""",
    "content_text": """
多维表分享邀请

您好！

{{sharer_name}} 邀请您协作编辑多维表：

多维表名称：{{base_name}}
描述：{{base_description}}
权限：{{permission}}

查看多维表：{{base_link}}

如果您没有 Smart Table 账号，请先注册。

---
此邮件由 Smart Table 系统自动发送，请勿回复。
""",
    "description": "添加分享成员时发送的邀请邮件",
    "is_default": True
}

# 分享移除通知模板
SHARE_REMOVED_TEMPLATE = {
    "template_key": "share_removed",
    "name": "分享移除通知",
    "subject": "Smart Table - 您对多维表 {{base_name}} 的访问权限已被移除",
    "content_html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>分享移除通知</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background-color: #6c757d; padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; }
        .content { padding: 40px 30px; }
        .content p { color: #666666; line-height: 1.6; margin-bottom: 20px; }
        .info-box { background-color: #f8f9fa; border-left: 4px solid #6c757d; padding: 15px; margin: 20px 0; }
        .footer { padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #999999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>访问权限已移除</h1>
        </div>
        <div class="content">
            <p>您好，{{user_name}}！</p>
            <p>您对多维表 <strong>{{base_name}}</strong> 的访问权限已被移除。</p>
            <div class="info-box">
                <p><strong>移除时间：</strong>{{operation_time}}</p>
                <p><strong>操作人：</strong>{{operator_name}}</p>
            </div>
            <p>您将无法再访问此多维表。如果您对此有疑问，请联系多维表所有者。</p>
        </div>
        <div class="footer">
            <p>此邮件由 Smart Table 系统自动发送，请勿回复。</p>
        </div>
    </div>
</body>
</html>
""",
    "content_text": """
分享移除通知

您好，{{user_name}}！

您对多维表 {{base_name}} 的访问权限已被移除。

移除时间：{{operation_time}}
操作人：{{operator_name}}

您将无法再访问此多维表。如果您对此有疑问，请联系多维表所有者。

---
此邮件由 Smart Table 系统自动发送，请勿回复。
""",
    "description": "移除分享成员时发送的通知",
    "is_default": True
}

# 权限变更通知模板
PERMISSION_CHANGED_TEMPLATE = {
    "template_key": "permission_changed",
    "name": "权限变更通知",
    "subject": "Smart Table - 您对多维表 {{base_name}} 的权限已变更",
    "content_html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>权限变更通知</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #17a2b8 0%, #138496 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; }
        .content { padding: 40px 30px; }
        .content p { color: #666666; line-height: 1.6; margin-bottom: 20px; }
        .permission-box { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; padding: 20px; margin: 20px 0; }
        .permission-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e9ecef; }
        .permission-row:last-child { border-bottom: none; }
        .old { color: #dc3545; text-decoration: line-through; }
        .new { color: #28a745; font-weight: bold; }
        .button { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: 500; margin: 20px 0; }
        .footer { padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #999999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>权限已变更</h1>
        </div>
        <div class="content">
            <p>您好，{{user_name}}！</p>
            <p>您对多维表 <strong>{{base_name}}</strong> 的访问权限已变更。</p>
            <div class="permission-box">
                <div class="permission-row">
                    <span>原权限：</span>
                    <span class="old">{{old_permission}}</span>
                </div>
                <div class="permission-row">
                    <span>新权限：</span>
                    <span class="new">{{new_permission}}</span>
                </div>
            </div>
            <p><strong>变更时间：</strong>{{operation_time}}</p>
            <p><strong>操作人：</strong>{{operator_name}}</p>
            <p style="text-align: center;">
                <a href="{{base_link}}" class="button">查看多维表</a>
            </p>
        </div>
        <div class="footer">
            <p>此邮件由 Smart Table 系统自动发送，请勿回复。</p>
        </div>
    </div>
</body>
</html>
""",
    "content_text": """
权限变更通知

您好，{{user_name}}！

您对多维表 {{base_name}} 的访问权限已变更。

原权限：{{old_permission}}
新权限：{{new_permission}}

变更时间：{{operation_time}}
操作人：{{operator_name}}

查看多维表：{{base_link}}

---
此邮件由 Smart Table 系统自动发送，请勿回复。
""",
    "description": "修改分享成员权限时发送的通知",
    "is_default": True
}

# 所有默认模板列表
DEFAULT_EMAIL_TEMPLATES = [
    USER_REGISTRATION_TEMPLATE,
    PASSWORD_RESET_TEMPLATE,
    ACCOUNT_SUSPENDED_TEMPLATE,
    ACCOUNT_ACTIVATED_TEMPLATE,
    PASSWORD_CHANGED_TEMPLATE,
    ACCOUNT_UPDATED_TEMPLATE,
    ACCOUNT_DELETED_TEMPLATE,
    SHARE_INVITATION_TEMPLATE,
    SHARE_REMOVED_TEMPLATE,
    PERMISSION_CHANGED_TEMPLATE,
]
