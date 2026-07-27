"""1.6.3 版本数据库升级脚本

合并以下迁移：
- 20260725_0017: 为 WorkflowNodeType 添加 loop 值
- 20260726_0018: 升级 action 类型为细粒度节点类型
- 20260727_0019: 修复 loop 节点数据源类型
- 20260727_0020: webhook_delivery_logs.webhook_config_id 改为可空
- 20260727_0021: workflow_execution_logs.node_id 改为 String 并新增 node_name 字段

Revision ID: 20260727_163
Revises: 20260718_0016
Create Date: 2026-07-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import table, column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = '20260727_163'
down_revision = '20260718_0016'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # ==================== 1. ENUM 类型扩展 ====================
    if is_postgres:
        # 添加 loop 值
        op.execute("ALTER TYPE workflownodetype ADD VALUE IF NOT EXISTS 'loop'")

        # 添加细粒度节点类型
        fine_grained_types = ['find_records', 'send_email', 'update_record', 'create_record', 'trigger_webhook']
        for node_type in fine_grained_types:
            op.execute(f"ALTER TYPE workflownodetype ADD VALUE IF NOT EXISTS '{node_type}'")

    # ==================== 2. 升级 action 节点类型 ====================
    # action_type 到细粒度类型的映射
    action_type_mapping = {
        'find_records': 'find_records',
        'send_email': 'send_email',
        'update_record': 'update_record',
        'create_record': 'create_record',
        'trigger_webhook': 'trigger_webhook',
    }

    for action_type, fine_type in action_type_mapping.items():
        if is_postgres:
            op.execute(f"""
                UPDATE workflow_nodes
                SET node_type = '{fine_type}'
                WHERE node_type = 'action'
                  AND config->>'action_type' = '{action_type}'
            """)
        else:
            op.execute(f"""
                UPDATE workflow_nodes
                SET node_type = '{fine_type}'
                WHERE node_type = 'action'
                  AND json_extract(config, '$.action_type') = '{action_type}'
            """)

    # 同步更新 workflow_execution_logs 表
    if is_postgres:
        op.execute("""
            UPDATE workflow_execution_logs l
            SET node_type = n.node_type
            FROM workflow_nodes n
            WHERE l.node_id = n.id
              AND l.node_type = 'action'
              AND n.node_type != 'action'
        """)
    else:
        op.execute("""
            UPDATE workflow_execution_logs
            SET node_type = (
                SELECT n.node_type
                FROM workflow_nodes n
                WHERE n.id = workflow_execution_logs.node_id
            )
            WHERE node_type = 'action'
              AND node_id IN (SELECT id FROM workflow_nodes WHERE node_type != 'action')
        """)

    # ==================== 3. 修复 loop 节点数据源配置 ====================
    workflow_nodes = table(
        'workflow_nodes',
        column('id', sa.String),
        column('config', sa.JSON),
        column('node_type', sa.String)
    )

    conn = bind.connect()
    result = conn.execute(
        sa.select(workflow_nodes.c.id, workflow_nodes.c.config)
          .where(workflow_nodes.c.node_type == 'loop')
    )

    for row in result:
        node_id = row.id
        config = row.config or {}

        data_source = config.get('data_source')
        if isinstance(data_source, dict):
            ds_type = data_source.get('type')
            field_id = data_source.get('field_id')

            # 自动修复：无 field_id 的无效 find_records_column 配置
            if ds_type == 'find_records_column' and not field_id:
                config['data_source'] = {
                    'type': 'find_records_all',
                    'node_id': data_source.get('node_id')
                }
                conn.execute(
                    workflow_nodes.update()
                      .where(workflow_nodes.c.id == node_id)
                      .values(config=config)
                )

    conn.close()

    # ==================== 4. webhook_delivery_logs.webhook_config_id 改为可空 ====================
    with op.batch_alter_table('webhook_delivery_logs', schema=None) as batch_op:
        batch_op.alter_column(
            'webhook_config_id',
            existing_type=sa.UUID(as_uuid=True) if is_postgres else sa.String(36),
            nullable=True,
        )

    # ==================== 5. workflow_execution_logs 表结构修改 ====================
    with op.batch_alter_table('workflow_execution_logs', schema=None) as batch_op:
        # 修改 node_id 类型为 String(64)
        batch_op.alter_column(
            'node_id',
            existing_type=sa.UUID(as_uuid=True) if is_postgres else sa.String(36),
            type_=sa.String(64),
            nullable=True,
        )

        # 新增 node_name 字段
        batch_op.add_column(
            sa.Column('node_name', sa.String(200), nullable=True)
        )

    # 回填 node_name
    op.execute("""
        UPDATE workflow_execution_logs
        SET node_name = (
            SELECT wn.name
            FROM workflow_nodes wn
            WHERE workflow_execution_logs.node_id = CAST(wn.id AS TEXT)
        )
        WHERE node_id IS NOT NULL
    """)


def downgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # ==================== 5. 恢复 workflow_execution_logs 表结构 ====================
    with op.batch_alter_table('workflow_execution_logs', schema=None) as batch_op:
        batch_op.drop_column('node_name')

        batch_op.alter_column(
            'node_id',
            existing_type=sa.String(64),
            type_=sa.UUID(as_uuid=True) if is_postgres else sa.String(36),
            nullable=True,
        )

    # ==================== 4. 恢复 webhook_delivery_logs.webhook_config_id 非空约束 ====================
    op.execute("DELETE FROM webhook_delivery_logs WHERE webhook_config_id IS NULL")

    with op.batch_alter_table('webhook_delivery_logs', schema=None) as batch_op:
        batch_op.alter_column(
            'webhook_config_id',
            existing_type=sa.UUID(as_uuid=True) if is_postgres else sa.String(36),
            nullable=False,
        )

    # ==================== 2. 回退 action 节点类型 ====================
    action_type_mapping = {
        'find_records': 'find_records',
        'send_email': 'send_email',
        'update_record': 'update_record',
        'create_record': 'create_record',
        'trigger_webhook': 'trigger_webhook',
    }

    for action_type, fine_type in action_type_mapping.items():
        if is_postgres:
            op.execute(f"""
                UPDATE workflow_nodes
                SET node_type = 'action',
                    config = jsonb_set(config, '{{action_type}}', '"{action_type}"')
                WHERE node_type = '{fine_type}'
            """)
        else:
            op.execute(f"""
                UPDATE workflow_nodes
                SET node_type = 'action'
                WHERE node_type = '{fine_type}'
            """)

    # 回退 workflow_execution_logs
    for fine_type in action_type_mapping.values():
        op.execute(f"""
            UPDATE workflow_execution_logs
            SET node_type = 'action'
            WHERE node_type = '{fine_type}'
        """)

    # ==================== 1. ENUM 类型值无法删除 ====================
    # PostgreSQL 不支持直接删除 ENUM 值，跳过
    pass