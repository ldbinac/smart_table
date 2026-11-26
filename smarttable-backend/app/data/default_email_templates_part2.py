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

BASE_OWNERSHIP_TRANSFERRED_TEMPLATE = {
    "template_key": "base_ownership_transferred",
    "name": "多维表所有权转移通知",
    "subject": "Smart Table - {{old_owner_name}} 已将多维表 {{base_name}} 的所有权转移给您",
    "content_html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>所有权转移通知</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; }
        .content { padding: 40px 30px; }
        .content p { color: #666666; line-height: 1.6; margin-bottom: 20px; }
        .info-box { background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 15px; margin: 20px 0; }
        .button { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: 500; margin: 20px 0; }
        .footer { padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #999999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>所有权已转移给您</h1>
        </div>
        <div class="content">
            <p>您好，{{user_name}}！</p>
            <p><strong>{{old_owner_name}}</strong> 已将多维表 <strong>{{base_name}}</strong> 的所有权转移给您。</p>
            <div class="info-box">
                <p><strong>转移时间：</strong>{{operation_time}}</p>
                <p><strong>原所有者：</strong>{{old_owner_name}}</p>
            </div>
            <p>您现在是该多维表的所有者，可以在成员管理中对协作者进行管理，也可以再次转移所有权。</p>
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
多维表所有权转移通知

您好，{{user_name}}！

{{old_owner_name}} 已将多维表 {{base_name}} 的所有权转移给您。

转移时间：{{operation_time}}
原所有者：{{old_owner_name}}

您现在是该多维表的所有者，可以在成员管理中对协作者进行管理，也可以再次转移所有权。

查看多维表：{{base_link}}

---
此邮件由 Smart Table 系统自动发送，请勿回复。
""",
    "description": "转移多维表所有权时发送给新所有者的通知",
    "is_default": True
}

COMMENT_MENTION_TEMPLATE = {
    "template_key": "comment_mention",
    "name": "评论提及通知",
    "subject": "{{actor_name}} 在记录中提到了你 - {{base_name}}",
    "content_html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>评论提及通知</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; }
        .content { padding: 40px 30px; }
        .content p { color: #666666; line-height: 1.6; margin-bottom: 20px; }
        .comment-box { background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 15px; margin: 20px 0; border-radius: 4px; }
        .button { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: 500; margin: 20px 0; }
        .footer { padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #999999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>你在记录中被提到了</h1>
        </div>
        <div class="content">
            <p>您好！</p>
            <p><strong>{{actor_name}}</strong> 在多维表 <strong>{{base_name}}</strong> 的表格 <strong>{{table_name}}</strong> 中评论记录「{{record_title}}」时提到了你。</p>
            <div class="comment-box">{{comment_snippet}}</div>
            <p style="text-align: center;">
                <a href="{{record_url}}" class="button">查看评论</a>
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
评论提及通知

您好！

{{actor_name}} 在多维表 {{base_name}} 的表格 {{table_name}} 中评论记录「{{record_title}}」时提到了你。

评论内容：
{{comment_snippet}}

查看评论：{{record_url}}

---
此邮件由 Smart Table 系统自动发送，请勿回复。
""",
    "description": "评论中 @提及成员时发送的通知",
    "is_default": True
}

COMMENT_REPLY_TEMPLATE = {
    "template_key": "comment_reply",
    "name": "评论回复通知",
    "subject": "{{actor_name}} 回复了你的评论 - {{base_name}}",
    "content_html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>评论回复通知</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #17a2b8 0%, #138496 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; }
        .content { padding: 40px 30px; }
        .content p { color: #666666; line-height: 1.6; margin-bottom: 20px; }
        .comment-box { background-color: #f8f9fa; border-left: 4px solid #17a2b8; padding: 15px; margin: 20px 0; border-radius: 4px; }
        .button { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: 500; margin: 20px 0; }
        .footer { padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #999999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>有人回复了你的评论</h1>
        </div>
        <div class="content">
            <p>您好！</p>
            <p><strong>{{actor_name}}</strong> 在多维表 <strong>{{base_name}}</strong> 的表格 <strong>{{table_name}}</strong> 中回复了你对记录「{{record_title}}」的评论。</p>
            <div class="comment-box">{{comment_snippet}}</div>
            <p style="text-align: center;">
                <a href="{{record_url}}" class="button">查看回复</a>
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
评论回复通知

您好！

{{actor_name}} 在多维表 {{base_name}} 的表格 {{table_name}} 中回复了你对记录「{{record_title}}」的评论。

回复内容：
{{comment_snippet}}

查看回复：{{record_url}}

---
此邮件由 Smart Table 系统自动发送，请勿回复。
""",
    "description": "回复他人评论时向父评论作者发送的通知",
    "is_default": True
}

RECORD_COMMENT_TEMPLATE = {
    "template_key": "record_comment",
    "name": "记录评论通知",
    "subject": "{{actor_name}} 评论了你关注的记录 - {{base_name}}",
    "content_html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>记录评论通知</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #28a745 0%, #20c997 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; }
        .content { padding: 40px 30px; }
        .content p { color: #666666; line-height: 1.6; margin-bottom: 20px; }
        .comment-box { background-color: #f8f9fa; border-left: 4px solid #28a745; padding: 15px; margin: 20px 0; border-radius: 4px; }
        .button { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: 500; margin: 20px 0; }
        .footer { padding: 20px 30px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #999999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>你关注的记录有了新评论</h1>
        </div>
        <div class="content">
            <p>您好！</p>
            <p><strong>{{actor_name}}</strong> 在多维表 <strong>{{base_name}}</strong> 的表格 <strong>{{table_name}}</strong> 中评论了你关注的记录「{{record_title}}」。</p>
            <div class="comment-box">{{comment_snippet}}</div>
            <p style="text-align: center;">
                <a href="{{record_url}}" class="button">查看评论</a>
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
记录评论通知

您好！

{{actor_name}} 在多维表 {{base_name}} 的表格 {{table_name}} 中评论了你关注的记录「{{record_title}}」。

评论内容：
{{comment_snippet}}

查看评论：{{record_url}}

---
此邮件由 Smart Table 系统自动发送，请勿回复。
""",
    "description": "关注记录新增顶层评论时向关注者发送的通知",
    "is_default": True
}
