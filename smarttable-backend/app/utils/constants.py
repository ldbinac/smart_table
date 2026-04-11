"""
公共常量定义模块
"""
from app.models.base import MemberRole

ROLE_LEVELS = {
    MemberRole.OWNER: 5,
    MemberRole.ADMIN: 4,
    MemberRole.EDITOR: 3,
    MemberRole.COMMENTER: 2,
    MemberRole.VIEWER: 1,
}
