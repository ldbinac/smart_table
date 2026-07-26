"""扫描并报告循环节点 data_source.type 配置问题

检查 loop 节点中 data_source.type='find_records_column' 但缺少 field_id 的
无效配置，自动修正为 'find_records_all'。

对于有 field_id 的 find_records_column 配置，仅输出警告日志（可能为用户
误选列值选项，需人工确认），不做自动修改。

Revision ID: 20260727_0019
Revises: 20260726_0018
Create Date: 2026-07-27
"""
from alembic import op
import sqlalchemy as sa
import json
import logging

revision = '20260727_0019'
down_revision = '20260726_0018'
branch_labels = None
depends_on = None

log = logging.getLogger(__name__)


def upgrade():
    """扫描 workflow_nodes 中 loop 节点，修正/报告 data_source 配置问题"""
    bind = op.get_bind()
    metadata = sa.MetaData()
    metadata.reflect(bind=bind)
    workflow_nodes = sa.Table('workflow_nodes', metadata, autoload_with=bind)

    # 查询所有 loop 类型的节点
    results = bind.execute(
        sa.select(workflow_nodes.c.id, workflow_nodes.c.config)
        .where(workflow_nodes.c.node_type == 'loop')
    ).fetchall()

    fixed_count = 0
    warned_count = 0
    for node_id, config_json in results:
        if not config_json:
            continue
        config = config_json if isinstance(config_json, dict) else json.loads(config_json)
        data_source = config.get('data_source')
        if not isinstance(data_source, dict):
            continue

        source_type = data_source.get('type')
        if source_type != 'find_records_column':
            continue

        field_id = data_source.get('field_id')
        node_id_val = data_source.get('node_id')

        if not field_id:
            # 缺少 field_id，find_records_column 无法工作，自动修正
            data_source['type'] = 'find_records_all'
            data_source.pop('field_id', None)
            _update_config(bind, workflow_nodes, node_id, config)
            fixed_count += 1
            log.info(f'修复节点 {node_id}: find_records_column(无 field_id) → find_records_all')
        else:
            # 有 field_id，仅警告（可能为用户误选列值选项而非"所有记录"）
            warned_count += 1
            log.warning(
                f'循环节点 {node_id} data_source.type=find_records_column, '
                f'field_id={field_id}, node_id={node_id_val}. '
                f'如需遍历全部记录，请在前端重新选择"所有记录"或手动执行修复脚本'
            )

    log.info(f'修复 {fixed_count} 个, 警告 {warned_count} 个循环节点 data_source 配置')


def _update_config(bind, workflow_nodes, node_id, config):
    """更新节点 config"""
    bind.execute(
        workflow_nodes.update()
        .where(workflow_nodes.c.id == node_id)
        .values(config=config)
    )


def downgrade():
    """downgrade 不做操作"""
    log.info('downgrade: 无法恢复原始 find_records_column 配置，跳过')
