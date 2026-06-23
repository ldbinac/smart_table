"""
字段权限服务
负责字段级权限的读取、校验、批量查询
"""
from typing import Dict, Optional

from flask import current_app

from app.extensions import db
from app.models.field import (
    Field,
    FIELD_PERMISSION_READ,
    FIELD_PERMISSION_WRITE,
    FIELD_PERMISSION_NONE,
    DEFAULT_FIELD_PERMISSIONS,
    UNRESTRICTABLE_ROLES,
)
from app.models.base import Base, BaseMember, MemberRole
from app.models.table import Table


class FieldPermissionService:
    """字段权限服务"""

    @staticmethod
    def get_user_role_in_base(base_id: str, user_id: str) -> Optional[str]:
        """获取用户在 Base 中的角色字符串（小写）。

        复用 BaseService 的逻辑：先检查 base.owner_id，再查询 BaseMember 表。

        Args:
            base_id: Base ID
            user_id: 用户 ID

        Returns:
            'owner'/'admin'/'editor'/'commenter'/'viewer' 或 None
            owner_id 匹配也返回 'owner'。
        """
        base = Base.query.get(base_id)
        if not base:
            return None

        # 检查是否为所有者
        if str(base.owner_id) == str(user_id):
            return MemberRole.OWNER.value

        # 检查成员关系
        membership = BaseMember.query.filter_by(
            base_id=base_id,
            user_id=user_id
        ).first()

        if membership:
            return membership.role.value

        return None

    @staticmethod
    def get_field_permission(field_id: str, user_id: str) -> str:
        """获取用户对某字段的权限。

        Args:
            field_id: 字段 ID
            user_id: 用户 ID

        Returns:
            'read'/'write'/'none'
            - owner/admin 直接返回 'write'
            - 其他角色读取字段配置，未配置返回默认值
            - 无 Base 权限返回 'none'
        """
        # 1. 查询 Field，不存在返回 'none'
        field = Field.query.get(field_id)
        if not field:
            return FIELD_PERMISSION_NONE

        # 2. 查询 Table，不存在返回 'none'
        table = Table.query.get(field.table_id)
        if not table:
            return FIELD_PERMISSION_NONE

        # 3. 获取用户角色，无角色返回 'none'
        role = FieldPermissionService.get_user_role_in_base(
            str(table.base_id), user_id
        )
        if not role:
            return FIELD_PERMISSION_NONE

        # 4. 调用 field.get_effective_permission(role)
        return field.get_effective_permission(role)

    @staticmethod
    def get_table_field_permissions(table_id: str, user_id: str) -> Dict[str, str]:
        """批量获取用户在某表所有字段的权限。

        仅需一次 Base 权限检查，避免 N+1 查询。

        Args:
            table_id: 表格 ID
            user_id: 用户 ID

        Returns:
            {field_id: 'read'/'write'/'none'}
        """
        # 1. 查询 Table，不存在返回 {}
        table = Table.query.get(table_id)
        if not table:
            return {}

        # 2. 获取用户角色（一次查询）
        role = FieldPermissionService.get_user_role_in_base(
            str(table.base_id), user_id
        )

        # 3. 查询该表所有字段（一次查询）
        fields = Field.query.filter_by(table_id=table_id).all()

        # 4. 若用户无角色，所有字段返回 'none'
        if not role:
            return {str(f.id): FIELD_PERMISSION_NONE for f in fields}

        # 5. 对每个字段调用 get_effective_permission(role)
        return {str(f.id): f.get_effective_permission(role) for f in fields}

    @staticmethod
    def check_field_read_permission(field_id: str, user_id: str) -> bool:
        """检查用户对字段是否有读权限（read 或 write）。

        Args:
            field_id: 字段 ID
            user_id: 用户 ID

        Returns:
            是否有读权限
        """
        perm = FieldPermissionService.get_field_permission(field_id, user_id)
        return perm in (FIELD_PERMISSION_READ, FIELD_PERMISSION_WRITE)

    @staticmethod
    def check_field_write_permission(field_id: str, user_id: str) -> bool:
        """检查用户对字段是否有写权限。

        Args:
            field_id: 字段 ID
            user_id: 用户 ID

        Returns:
            是否有写权限
        """
        perm = FieldPermissionService.get_field_permission(field_id, user_id)
        return perm == FIELD_PERMISSION_WRITE

    @staticmethod
    def filter_values_by_permission(
        values: Dict[str, any],
        field_permissions: Dict[str, str]
    ) -> Dict[str, any]:
        """根据字段权限过滤记录值字典。

        - 'none' 权限的字段值被移除
        - 'read'/'write' 权限的字段值保留

        Args:
            values: 记录值字典 {field_id: value}
            field_permissions: 字段权限字典 {field_id: 'read'/'write'/'none'}

        Returns:
            过滤后的值字典
        """
        return {
            k: v for k, v in values.items()
            if field_permissions.get(k, FIELD_PERMISSION_READ) in (
                FIELD_PERMISSION_READ, FIELD_PERMISSION_WRITE
            )
        }

    @staticmethod
    def filter_writable_values(
        values: Dict[str, any],
        field_permissions: Dict[str, str]
    ) -> Dict[str, any]:
        """过滤出用户有写权限的字段值（用于创建/更新记录）。

        - 'write' 权限的字段值保留
        - 'read'/'none' 权限的字段值被移除

        Args:
            values: 记录值字典 {field_id: value}
            field_permissions: 字段权限字典 {field_id: 'read'/'write'/'none'}

        Returns:
            过滤后的值字典
        """
        return {
            k: v for k, v in values.items()
            if field_permissions.get(k, FIELD_PERMISSION_WRITE) == FIELD_PERMISSION_WRITE
        }
