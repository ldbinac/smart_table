# Auto-split skeleton

from .default_email_templates_part1 import USER_REGISTRATION_TEMPLATE
from .default_email_templates_part1 import PASSWORD_RESET_TEMPLATE
from .default_email_templates_part1 import ACCOUNT_SUSPENDED_TEMPLATE
from .default_email_templates_part1 import ACCOUNT_ACTIVATED_TEMPLATE
from .default_email_templates_part1 import PASSWORD_CHANGED_TEMPLATE
from .default_email_templates_part1 import ACCOUNT_UPDATED_TEMPLATE
from .default_email_templates_part1 import ACCOUNT_DELETED_TEMPLATE
from .default_email_templates_part2 import SHARE_INVITATION_TEMPLATE
from .default_email_templates_part2 import SHARE_REMOVED_TEMPLATE
from .default_email_templates_part2 import PERMISSION_CHANGED_TEMPLATE
from .default_email_templates_part2 import BASE_OWNERSHIP_TRANSFERRED_TEMPLATE
from .default_email_templates_part2 import COMMENT_MENTION_TEMPLATE
from .default_email_templates_part2 import COMMENT_REPLY_TEMPLATE
from .default_email_templates_part2 import RECORD_COMMENT_TEMPLATE

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
    BASE_OWNERSHIP_TRANSFERRED_TEMPLATE,
    COMMENT_MENTION_TEMPLATE,
    COMMENT_REPLY_TEMPLATE,
    RECORD_COMMENT_TEMPLATE,
]
