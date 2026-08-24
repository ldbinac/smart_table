"""添加高级权限管理相关数据表

修订说明：
- 新增高级权限管理相关模型表（角色、权限规则组、权限规则、数据权限条件、角色-规则组关联、用户-规则组关联、数据权限按表配置）
- 修改 base_members 表添加 role_id 字段
- 修改 base_shares 表添加 role_id 和 allow_anonymous 字段
- 修改 data_permission_conditions 表添加 table_id 字段

兼容性说明（重要）：
- 新表的表间外键统一使用 create_table 内联的 sa.ForeignKeyConstraint（SQLite 原生支持，
  与 20260806 通知表迁移保持一致）。
- 对已有表（base_members / base_shares / data_permission_conditions）的 ALTER 操作使用
  op.batch_alter_table（SQLite 不支持 ALTER 添加/删除约束，必须通过 copy-and-move 方案）。
- 外键引用的列类型必须与引用表的主键类型一致（PostgreSQL 上若不一致会报类型不匹配错误），
  此处引用列与被引用列均使用 UUID（CompatUUID）。

Revision ID: 20260807_0025
Revises: 20260806_0024
Create Date: 2026-08-07 00:25:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.db_types import CompatUUID as UUID

# 修订信息
revision = '20260807_0025'
down_revision = '20260806_0024'
branch_labels = None
depends_on = None


def _table_exists(table_name):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _col_exists(table_name, column_name):
    if not _table_exists(table_name):
        return False
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade():
    # ===== 1. 角色表（与模型 Role 对齐） =====
    if not _table_exists('roles'):
        op.create_table(
            'roles',
            sa.Column('id', UUID(), nullable=False),
            sa.Column('base_id', UUID(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['base_id'], ['bases.id'], ondelete='CASCADE'),
        )

    # ===== 2. 权限规则组表（与模型 PermissionRuleGroup 对齐） =====
    if not _table_exists('permission_rule_groups'):
        op.create_table(
            'permission_rule_groups',
            sa.Column('id', UUID(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('base_id', UUID(), nullable=False),
            sa.Column('created_by', UUID(), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, server_default=sa.text("'active'")),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['base_id'], ['bases.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        )
        op.create_index('ix_permission_rule_groups_base_id', 'permission_rule_groups', ['base_id'], unique=False)

    # ===== 3. 权限规则表（与模型 PermissionRule 对齐） =====
    if not _table_exists('permission_rules'):
        op.create_table(
            'permission_rules',
            sa.Column('id', UUID(), nullable=False),
            sa.Column('rule_group_id', UUID(), nullable=False),
            sa.Column('rule_type', sa.String(length=50), nullable=False),
            sa.Column('rule_target_id', UUID(), nullable=False),
            sa.Column('permission', sa.String(length=20), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['rule_group_id'], ['permission_rule_groups.id'], ondelete='CASCADE'),
        )
        op.create_index('ix_permission_rules_rule_group_id', 'permission_rules', ['rule_group_id'], unique=False)

    # ===== 4. 数据权限条件表（与模型 DataPermissionCondition 对齐） =====
    if not _table_exists('data_permission_conditions'):
        op.create_table(
            'data_permission_conditions',
            sa.Column('id', UUID(), nullable=False),
            sa.Column('rule_group_id', UUID(), nullable=False),
            sa.Column('table_id', UUID(), nullable=True),
            sa.Column('field_id', UUID(), nullable=False),
            sa.Column('operator', sa.String(length=50), nullable=False),
            sa.Column('value', sa.Text(), nullable=True),
            sa.Column('logical_operator', sa.String(length=10), nullable=False, server_default=sa.text("'and'")),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['rule_group_id'], ['permission_rule_groups.id'], ondelete='CASCADE'),
        )
        op.create_index('ix_data_permission_conditions_rule_group_id', 'data_permission_conditions', ['rule_group_id'], unique=False)
        op.create_index('ix_data_permission_conditions_table_id', 'data_permission_conditions', ['table_id'], unique=False)

    # ===== 5. 角色-规则组关联表（与模型 RolePermissionGroup 对齐） =====
    if not _table_exists('role_permission_groups'):
        op.create_table(
            'role_permission_groups',
            sa.Column('id', UUID(), nullable=False),
            sa.Column('role_id', UUID(), nullable=False),
            sa.Column('rule_group_id', UUID(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['rule_group_id'], ['permission_rule_groups.id'], ondelete='CASCADE'),
        )
        op.create_index('ix_role_permission_groups_role_id', 'role_permission_groups', ['role_id'], unique=False)
        op.create_index('ix_role_permission_groups_rule_group_id', 'role_permission_groups', ['rule_group_id'], unique=False)

    # ===== 6. 用户-规则组关联表（与模型 UserPermissionGroup 对齐） =====
    if not _table_exists('user_permission_groups'):
        op.create_table(
            'user_permission_groups',
            sa.Column('id', UUID(), nullable=False),
            sa.Column('user_id', UUID(), nullable=False),
            sa.Column('rule_group_id', UUID(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['rule_group_id'], ['permission_rule_groups.id'], ondelete='CASCADE'),
        )
        op.create_index('ix_user_permission_groups_user_id', 'user_permission_groups', ['user_id'], unique=False)
        op.create_index('ix_user_permission_groups_rule_group_id', 'user_permission_groups', ['rule_group_id'], unique=False)

    # ===== 7. 数据权限按表配置表（与模型 DataPermissionTableConfig 对齐） =====
    if not _table_exists('data_permission_table_configs'):
        op.create_table(
            'data_permission_table_configs',
            sa.Column('id', UUID(), nullable=False),
            sa.Column('rule_group_id', UUID(), nullable=False),
            sa.Column('table_id', UUID(), nullable=False),
            sa.Column('mode', sa.String(length=20), nullable=False, server_default=sa.text("'unrestricted'")),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['rule_group_id'], ['permission_rule_groups.id'], ondelete='CASCADE'),
        )
        op.create_index('ix_data_permission_table_configs_rule_group_id', 'data_permission_table_configs', ['rule_group_id'], unique=False)
        op.create_index('ix_data_permission_table_configs_table_id', 'data_permission_table_configs', ['table_id'], unique=False)

    # ===== 8. 修改 base_members 表添加 role_id 字段 =====
    if not _col_exists('base_members', 'role_id'):
        with op.batch_alter_table('base_members') as batch_op:
            batch_op.add_column(sa.Column('role_id', UUID(), nullable=True))
        with op.batch_alter_table('base_members') as batch_op:
            batch_op.create_foreign_key(
                'fk_base_members_role_id_roles',
                'roles', ['role_id'], ['id'],
                ondelete='SET NULL',
            )
        op.create_index('ix_base_members_role_id', 'base_members', ['role_id'], unique=False)

    # ===== 9. 修改 base_shares 表添加 role_id 和 allow_anonymous 字段 =====
    if not _col_exists('base_shares', 'role_id'):
        with op.batch_alter_table('base_shares') as batch_op:
            batch_op.add_column(sa.Column('role_id', UUID(), nullable=True))
        with op.batch_alter_table('base_shares') as batch_op:
            batch_op.create_foreign_key(
                'fk_base_shares_role_id_roles',
                'roles', ['role_id'], ['id'],
                ondelete='SET NULL',
            )
        op.create_index('ix_base_shares_role_id', 'base_shares', ['role_id'], unique=False)

    if not _col_exists('base_shares', 'allow_anonymous'):
        with op.batch_alter_table('base_shares') as batch_op:
            batch_op.add_column(sa.Column('allow_anonymous', sa.Boolean(), nullable=False, server_default=sa.true()))



def downgrade():
    # ===== 1. 回退对已有表的修改（batch 模式兼容 SQLite） =====
    if _col_exists('base_shares', 'allow_anonymous'):
        with op.batch_alter_table('base_shares') as batch_op:
            batch_op.drop_column('allow_anonymous')

    if _col_exists('base_shares', 'role_id'):
        with op.batch_alter_table('base_shares') as batch_op:
            batch_op.drop_constraint('fk_base_shares_role_id_roles', type_='foreignkey')
            batch_op.drop_index('ix_base_shares_role_id')
        with op.batch_alter_table('base_shares') as batch_op:
            batch_op.drop_column('role_id')

    if _col_exists('base_members', 'role_id'):
        with op.batch_alter_table('base_members') as batch_op:
            batch_op.drop_constraint('fk_base_members_role_id_roles', type_='foreignkey')
            batch_op.drop_index('ix_base_members_role_id')
        with op.batch_alter_table('base_members') as batch_op:
            batch_op.drop_column('role_id')

    # ===== 2. 删除本迁移新增的表（按外键依赖逆序：先子表后父表，兼容 PostgreSQL） =====
    op.drop_table('user_permission_groups')
    op.drop_table('role_permission_groups')
    op.drop_table('data_permission_table_configs')
    op.drop_table('data_permission_conditions')
    op.drop_table('permission_rules')
    op.drop_table('permission_rule_groups')
    op.drop_table('roles')
