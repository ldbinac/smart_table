"""
邮件模板初始化工具
用于在应用启动时初始化默认邮件模板
"""

from app.extensions import db
from app.models.email_template import EmailTemplate
from app.data.default_email_templates import DEFAULT_EMAIL_TEMPLATES


def init_default_email_templates():
    """
    初始化默认邮件模板
    如果模板已存在则跳过，如果被删除则重新创建
    """
    try:
        print("[InitEmailTemplates] 开始初始化默认邮件模板...")
        
        created_count = 0
        skipped_count = 0
        
        for template_data in DEFAULT_EMAIL_TEMPLATES:
            template_key = template_data["template_key"]
            
            # 检查模板是否已存在
            existing_template = EmailTemplate.query.filter_by(
                template_key=template_key
            ).first()
            
            if existing_template:
                # 如果模板已存在且是默认模板，跳过
                if existing_template.is_default:
                    print(f"[InitEmailTemplates] 模板 '{template_key}' 已存在，跳过")
                    skipped_count += 1
                    continue
                else:
                    # 如果存在同名非默认模板，删除它（用户自定义模板不应该使用系统保留的key）
                    print(f"[InitEmailTemplates] 删除非默认模板 '{template_key}'")
                    db.session.delete(existing_template)
                    db.session.flush()
            
            # 创建新模板
            template = EmailTemplate(
                template_key=template_data["template_key"],
                name=template_data["name"],
                subject=template_data["subject"],
                content_html=template_data["content_html"],
                content_text=template_data["content_text"],
                description=template_data["description"],
                is_default=template_data["is_default"]
            )
            
            db.session.add(template)
            print(f"[InitEmailTemplates] 创建模板 '{template_key}'")
            created_count += 1
        
        db.session.commit()
        print(f"[InitEmailTemplates] 初始化完成：创建 {created_count} 个，跳过 {skipped_count} 个")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"[InitEmailTemplates] 初始化失败：{str(e)}")
        return False


def reset_template_to_default(template_key: str) -> bool:
    """
    将指定模板重置为默认内容
    
    Args:
        template_key: 模板标识
        
    Returns:
        bool: 是否成功
    """
    try:
        # 查找默认模板数据
        default_data = None
        for template_data in DEFAULT_EMAIL_TEMPLATES:
            if template_data["template_key"] == template_key:
                default_data = template_data
                break
        
        if not default_data:
            print(f"[InitEmailTemplates] 未找到默认模板 '{template_key}'")
            return False
        
        # 查找现有模板
        template = EmailTemplate.query.filter_by(template_key=template_key).first()
        
        if template:
            # 更新现有模板
            template.name = default_data["name"]
            template.subject = default_data["subject"]
            template.content_html = default_data["content_html"]
            template.content_text = default_data["content_text"]
            template.description = default_data["description"]
            template.is_default = True
        else:
            # 创建新模板
            template = EmailTemplate(
                template_key=default_data["template_key"],
                name=default_data["name"],
                subject=default_data["subject"],
                content_html=default_data["content_html"],
                content_text=default_data["content_text"],
                description=default_data["description"],
                is_default=default_data["is_default"]
            )
            db.session.add(template)
        
        db.session.commit()
        print(f"[InitEmailTemplates] 模板 '{template_key}' 已重置为默认")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"[InitEmailTemplates] 重置模板失败：{str(e)}")
        return False


def get_default_template_content(template_key: str) -> dict:
    """
    获取指定模板的默认内容
    
    Args:
        template_key: 模板标识
        
    Returns:
        dict: 模板内容，如果不存在则返回空字典
    """
    for template_data in DEFAULT_EMAIL_TEMPLATES:
        if template_data["template_key"] == template_key:
            return {
                "name": template_data["name"],
                "subject": template_data["subject"],
                "content_html": template_data["content_html"],
                "content_text": template_data["content_text"],
                "description": template_data["description"]
            }
    return {}
