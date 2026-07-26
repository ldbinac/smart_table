"""将 workflow_nodes 中 node_type='action' 的记录升级为细粒度类型

根据 config.action_type 将 'action' 升级为 'find_records'/'send_email'/'update_record'/
'create_record'/'trigger_webhook'。同步修正 workflow_execution_logs 中的 node_type。

Revision ID: 20260726_0018
Revises: 20260725_0017
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa

revision = '20260726_0018'
down_revision = '20260725_0017'
branch_labels = None
depends_on = None

# action_type → 细粒度 node_type 映射
ACTION_TYPE_UPGRADE = {
    'find_records': 'find_records',
    'send_email': 'send_email',
    'update_record': 'update_record',
    'create_record': 'create_record',
    'trigger_webhook': 'trigger_webhook',
}


def upgrade():
    bind = op.get_bind()

    # 1. PostgreSQL ENUM 类型新增细粒度值
    if bind.dialect.name == 'postgresql':
        for value in ('find_records', 'send_email', 'update_record', 'create_record', 'trigger_webhook'):
            op.execute(f"ALTER TYPE workflownodetype ADD VALUE IF NOT EXISTS '{value}'")

    # 2. 升级 workflow_nodes 表中 node_type='action' 的记录
    #    使用原始 SQL 逐条更新，避免 ORM 枚举校验问题
    for action_type, fine_type in ACTION_TYPE_UPGRADE.items():
        # SQLite 的 JSON 查询使用 json_extract，PostgreSQL 使用 ->>
        if bind.dialect.name == 'postgresql':
            op.execute(
                f"UPDATE workflow_nodes SET node_type = '{fine_type}' "
                f"WHERE node_type = 'action' AND config->>'action_type' = '{action_type}'"
            )
        else:
            # SQLite
            op.execute(
                f"UPDATE workflow_nodes SET node_type = '{fine_type}' "
                f"WHERE node_type = 'action' AND json_extract(config, '$.action_type') = '{action_type}'"
            )

    # 3. 同步修正 workflow_execution_logs 中 node_type='action' 的记录
    #    通过关联 workflow_nodes 获取正确的 node_type
    if bind.dialect.name == 'postgresql':
        op.execute(
            "UPDATE workflow_execution_logs SET node_type = n.node_type "
            "FROM workflow_nodes n "
            "WHERE workflow_execution_logs.node_id = n.id "
            "AND workflow_execution_logs.node_type = 'action' "
            "AND n.node_type != 'action'"
        )
    else:
        # SQLite: 使用子查询
        op.execute(
            "UPDATE workflow_execution_logs SET node_type = "
            "(SELECT n.node_type FROM workflow_nodes n WHERE n.id = workflow_execution_logs.node_id) "
            "WHERE node_type = 'action' "
            "AND node_id IN (SELECT id FROM workflow_nodes WHERE node_type != 'action')"
        )

    # 4. 修正无 node_id 关联但可通过 input_context 推断的执行日志
    #    （循环体子节点的执行日志 node_id 为 NULL，无法通过 JOIN 推断，
    #     这些在下次执行时会自动使用正确的 node_type）


def downgrade():
    # 将细粒度类型回退为 'action'，并在 config 中恢复 action_type
    bind = op.get_bind()
    for action_type, fine_type in ACTION_TYPE_UPGRADE.items():
        if bind.dialect.name == 'postgresql':
            op.execute(
                f"UPDATE workflow_nodes SET node_type = 'action', "
                f"config = jsonb_set(config, '{{action_type}}', '\"{action_type}\"') "
                f"WHERE node_type = '{fine_type}'"
            )
        else:
            # SQLite: 需要读取 → 修改 → 写回，此处使用简单方式
            op.execute(
                f"UPDATE workflow_nodes SET node_type = 'action' "
                f"WHERE node_type = '{fine_type}'"
            )
        # 同步回退执行日志
        op.execute(
            f"UPDATE workflow_execution_logs SET node_type = 'action' "
            f"WHERE node_type = '{fine_type}'"
        )
