"""修复循环节点 data_source.type 配置错误的管理脚本

用法:
    # 扫描所有 loop 节点，报告配置问题
    python fix_loop_data_source.py --scan

    # 修复指定节点（将 find_records_column 改为 find_records_all）
    python fix_loop_data_source.py --fix --node-id <node-uuid>

    # 批量修复所有 find_records_column 配置（需确认）
    python fix_loop_data_source.py --fix-all

典型场景:
    用户在前端选择了"查找记录 - 所有记录"但配置被保存为 find_records_column
    （含 field_id），导致循环数据源解析为空数组，循环体节点不执行。
"""
import argparse
import json
import sys
import os

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.workflow import WorkflowNode


def scan():
    """扫描所有 loop 节点，报告 data_source 配置"""
    loop_nodes = WorkflowNode.query.filter_by(node_type='loop').all()
    if not loop_nodes:
        print('未找到 loop 类型的节点')
        return

    issues = []
    for node in loop_nodes:
        config = node.config or {}
        data_source = config.get('data_source', {})
        if not isinstance(data_source, dict):
            continue

        source_type = data_source.get('type')
        field_id = data_source.get('field_id')
        node_id_ref = data_source.get('node_id')

        if source_type == 'find_records_column':
            issues.append({
                'node_id': str(node.id),
                'workflow_id': str(node.workflow_id),
                'node_name': node.name,
                'data_source_type': source_type,
                'field_id': field_id,
                'ref_node_id': node_id_ref,
                'has_field_id': bool(field_id),
            })

    if not issues:
        print(f'扫描了 {len(loop_nodes)} 个 loop 节点，未发现配置问题')
        return

    print(f'扫描了 {len(loop_nodes)} 个 loop 节点，发现 {len(issues)} 个配置问题:\n')
    for i, issue in enumerate(issues, 1):
        print(f'  [{i}] 节点 ID: {issue["node_id"]}')
        print(f'      工作流 ID: {issue["workflow_id"]}')
        print(f'      节点名称: {issue["node_name"]}')
        print(f'      data_source.type: {issue["data_source_type"]}')
        print(f'      field_id: {issue["field_id"]}')
        print(f'      ref_node_id: {issue["ref_node_id"]}')
        print(f'      修复命令: python fix_loop_data_source.py --fix --node-id {issue["node_id"]}')
        print()


def fix_node(node_id_str: str):
    """修复指定节点的 data_source.type"""
    try:
        from uuid import UUID
        node_uuid = UUID(node_id_str)
    except ValueError:
        print(f'无效的节点 ID: {node_id_str}')
        return

    node = WorkflowNode.query.get(node_uuid)
    if not node:
        print(f'未找到节点: {node_id_str}')
        return

    if node.node_type != 'loop':
        print(f'节点 {node_id_str} 不是 loop 类型，跳过')
        return

    config = node.config or {}
    data_source = config.get('data_source', {})
    if not isinstance(data_source, dict):
        print(f'节点 {node_id_str} 的 data_source 不是字典，跳过')
        return

    old_type = data_source.get('type')
    if old_type != 'find_records_column':
        print(f'节点 {node_id_str} 的 data_source.type={old_type}，不是 find_records_column，跳过')
        return

    # 修改配置
    data_source['type'] = 'find_records_all'
    data_source.pop('field_id', None)
    node.config = config
    db.session.commit()

    print(f'已修复节点 {node_id_str}: find_records_column → find_records_all')
    print(f'  field_id 已移除, node_id={data_source.get("node_id")} 保留')


def fix_all():
    """批量修复所有 find_records_column 配置"""
    loop_nodes = WorkflowNode.query.filter_by(node_type='loop').all()
    fixed = 0
    for node in loop_nodes:
        config = node.config or {}
        data_source = config.get('data_source', {})
        if not isinstance(data_source, dict):
            continue
        if data_source.get('type') != 'find_records_column':
            continue

        data_source['type'] = 'find_records_all'
        data_source.pop('field_id', None)
        node.config = config
        fixed += 1
        print(f'修复节点 {node.id} ({node.name})')

    if fixed > 0:
        db.session.commit()
        print(f'\n共修复 {fixed} 个节点')
    else:
        print('无需修复的节点')


def main():
    parser = argparse.ArgumentParser(description='修复循环节点 data_source.type 配置')
    parser.add_argument('--scan', action='store_true', help='扫描所有 loop 节点，报告配置问题')
    parser.add_argument('--fix', action='store_true', help='修复指定节点')
    parser.add_argument('--fix-all', action='store_true', help='批量修复所有 find_records_column 配置')
    parser.add_argument('--node-id', type=str, help='要修复的节点 ID')
    args = parser.parse_args()

    app = create_app(os.getenv('FLASK_ENV', 'production'))
    with app.app_context():
        if args.scan:
            scan()
        elif args.fix:
            if not args.node_id:
                print('请使用 --node-id 指定要修复的节点 ID')
                sys.exit(1)
            fix_node(args.node_id)
        elif args.fix_all:
            confirm = input('确认要批量修复所有 find_records_column 配置吗？(y/N) ')
            if confirm.lower() == 'y':
                fix_all()
            else:
                print('已取消')
        else:
            parser.print_help()


if __name__ == '__main__':
    main()
