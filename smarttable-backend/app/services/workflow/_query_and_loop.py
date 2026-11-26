import html
import json
import logging
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

from app.i18n import translate
from app.extensions import db
from app.models.webhook import WebhookConfig
from app.models.record import Record
from app.models.table import Table
from app.models.workflow import Workflow, WorkflowNode, WorkflowNodeType
from app.models.workflow_instance import (
    WorkflowInstance,
    WorkflowExecutionLog,
    WorkflowInstanceStatus,
)
from app.services.email_queue_service import email_queue
from app.services.record_service import RecordService
from app.services.workflow_event_bus import workflow_event_bus, WorkflowEvent

log = logging.getLogger(__name__)

class WorkflowQueryLoopMixin:
    """WorkflowQueryLoopMixin — 6 个方法"""

    def _execute_find_records(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行查找记录动作"""
        config = node.config or {}

        target_table_id = config.get('target_table_id')
        if not target_table_id:
            raise ValueError('missing_target_table_id')

        table = Table.query.get(self._to_uuid(target_table_id))
        if not table:
            raise ValueError(translate('target_table_not_found', target_table_id))

        conditions = config.get('conditions', [])
        conjunction = config.get('conjunction', 'and')
        sort_field_id = config.get('sort_field_id')
        sort_direction = config.get('sort_direction', 'asc')

        limit = config.get('limit', 100)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 100
        limit = max(1, min(limit, 1000))

        result_variable = config.get('result_variable', 'records') or 'records'
        empty_result_action = config.get('empty_result_action', 'continue')

        records = Record.query.filter_by(
            table_id=self._to_uuid(target_table_id),
            is_deleted=False
        ).all()

        matching_records = []
        condition_config = {'conditions': conditions, 'conjunction': conjunction}
        for record in records:
            context = {field_id: record.values.get(field_id) for field_id in (record.values or {})}
            if self.evaluate_condition(condition_config, context):
                matching_records.append(record)

        if sort_field_id:
            reverse = sort_direction == 'desc'
            matching_records.sort(
                key=lambda r: (r.values or {}).get(sort_field_id),
                reverse=reverse
            )

        matching_records = matching_records[:limit]

        result = {
            'count': len(matching_records),
            'records': [r.to_dict() if hasattr(r, 'to_dict') else r.values for r in matching_records]
        }

        context = instance.context or {}
        context[result_variable] = result
        instance.context = context
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(instance, 'context')
        db.session.commit()

        if not matching_records and empty_result_action == 'stop':
            return {'result': result, 'next_nodes': []}

        return {'result': result, 'next_nodes': node.next_nodes or []}

    def _resolve_find_records_variable(self, instance: WorkflowInstance, node_id: Any) -> str:
        """根据 node_id 查找 find_records 节点配置以确定 result_variable，未配置则默认 'records'"""
        if not node_id:
            return 'records'
        try:
            node = WorkflowNode.query.get(self._to_uuid(node_id))
        except (ValueError, TypeError):
            return 'records'
        if node and node.config:
            return node.config.get('result_variable', 'records') or 'records'
        return 'records'

    def _execute_loop_node(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行循环节点：解析数据源 → 依次迭代循环体 → 返回主链 next_nodes。

        循环结束后返回 {next_nodes: node.next_nodes} 以继续主链。
        """
        config = node.config or {}
        data_source_config = config.get('data_source', {}) or {}
        max_iterations = config.get('max_iterations', 100)
        error_handling = config.get('error_handling', 'skip')
        empty_result_action = config.get('empty_result_action', 'skip')
        loop_body_nodes = config.get('loop_body_nodes', []) or []

        log.info(
            f'[WorkflowExecutionEngine] 循环节点 {node.id}: '
            f'data_source={data_source_config}, '
            f'loop_body_nodes 数量={len(loop_body_nodes)}, '
            f'loop_body_nodes 类型={[type(n).__name__ for n in loop_body_nodes]}'
        )

        data_array = self._resolve_loop_data_source(instance, data_source_config)

        log.info(
            f'[WorkflowExecutionEngine] 循环节点 {node.id}: '
            f'data_array 长度={len(data_array)}, '
            f'instance.context keys={list((instance.context or {}).keys())}'
        )

        if not data_array:
            # 记录诊断执行日志，便于前端排查循环未执行的原因
            diagnostic_log = WorkflowExecutionLog(
                instance_id=instance.id,
                node_id=str(node.id) if node.id else None,
                node_name=node.name if hasattr(node, 'name') else None,
                node_type='loop',
                status='success' if empty_result_action != 'error' else 'error',
                input_context={
                    'data_source': data_source_config,
                    'array_length': 0,
                    'loop_body_nodes_count': len(loop_body_nodes),
                    'context_keys': list((instance.context or {}).keys()),
                },
                output_result={
                    'total_iterations': 0,
                    'success_count': 0,
                    'failure_count': 0,
                    'early_terminated': False,
                    'skipped_reason': 'data_array_empty',
                },
                completed_at=datetime.now(timezone.utc)
            )
            db.session.add(diagnostic_log)
            db.session.commit()

            if empty_result_action == 'error':
                raise ValueError('loop_data_source_empty')
            # skip 模式：跳过循环，继续主链
            return {'next_nodes': node.next_nodes or []}

        try:
            max_iterations_int = int(max_iterations)
        except (TypeError, ValueError):
            max_iterations_int = 100
        max_iterations_int = max(1, min(max_iterations_int, 1000))

        total = min(len(data_array), max_iterations_int)

        execution_log = WorkflowExecutionLog(
            instance_id=instance.id,
            node_id=str(node.id) if node.id else None,
            node_name=node.name if hasattr(node, 'name') else None,
            node_type='loop',
            status='running',
            input_context={
                'data_source': data_source_config,
                'array_length': len(data_array),
                'loop_body_nodes_count': len(loop_body_nodes),
                'max_iterations': max_iterations_int,
                'total': total
            }
        )
        db.session.add(execution_log)
        db.session.flush()

        success_count = 0
        failure_count = 0
        early_terminated = False
        error_message: Optional[str] = None

        try:
            for index in range(total):
                current_data = data_array[index]
                try:
                    self._execute_loop_body(
                        instance, loop_body_nodes, current_data, index, total
                    )
                    success_count += 1
                except Exception as e:
                    failure_count += 1
                    if error_handling == 'terminate':
                        early_terminated = True
                        error_message = str(e)
                        raise
                    # skip 模式：异常已通过 _execute_loop_body_chain 传播中断当前迭代剩余节点，
                    # 此处记录日志后继续下一次迭代
                    log.warning(
                        f'[WorkflowExecutionEngine] 循环体第 {index + 1}/{total} 轮执行失败'
                        f'（error_handling=skip，跳过当次剩余节点）: {e}'
                    )
        finally:
            execution_log.status = 'error' if early_terminated else 'success'
            execution_log.error_message = error_message
            execution_log.output_result = {
                'total_iterations': success_count + failure_count,
                'success_count': success_count,
                'failure_count': failure_count,
                'early_terminated': early_terminated
            }
            execution_log.completed_at = datetime.now(timezone.utc)
            db.session.commit()

        return {'next_nodes': node.next_nodes or []}

    def _execute_loop_body(
        self,
        instance: WorkflowInstance,
        loop_body_nodes: List[Dict[str, Any]],
        current_data: Any,
        index: int,
        total: int
    ) -> None:
        """执行单次循环体：写入 loop_context → 执行子节点链 → 恢复外层 loop_context。

        异常向上抛出（由 _execute_loop_node 根据 error_handling 决定处理方式）。
        finally 中保证外层 loop_context 被恢复，以支持嵌套循环。
        """
        from sqlalchemy.orm.attributes import flag_modified

        context = instance.context or {}
        outer_loop_context = context.get('loop_context')

        context['loop_context'] = {
            'current_data': current_data,
            'index': index,
            'round': index + 1,
            'total': total
        }
        instance.context = context
        flag_modified(instance, 'context')
        db.session.commit()

        try:
            if not loop_body_nodes:
                return

            valid_nodes = [n for n in loop_body_nodes if isinstance(n, dict)]
            if not valid_nodes:
                return

            nodes_by_id: Dict[str, Dict[str, Any]] = {}
            all_next_ids: set = set()
            for n in valid_nodes:
                node_id = n.get('id')
                if node_id is not None:
                    nodes_by_id[node_id] = n
                all_next_ids.update(n.get('next_nodes', []) or [])

            # 入口节点：order 最小且不在其他节点 next_nodes 中的节点
            sorted_nodes = sorted(valid_nodes, key=lambda n: n.get('order', 0))
            entry_node: Optional[Dict[str, Any]] = None
            for n in sorted_nodes:
                if n.get('id') not in all_next_ids:
                    entry_node = n
                    break
            if entry_node is None:
                entry_node = sorted_nodes[0]

            self._execute_loop_body_chain(instance, entry_node, nodes_by_id)
        finally:
            # 恢复外层 loop_context（嵌套支持）；若无外层则清除
            context = instance.context or {}
            if outer_loop_context is not None:
                context['loop_context'] = outer_loop_context
            else:
                context.pop('loop_context', None)
            instance.context = context
            flag_modified(instance, 'context')
            db.session.commit()

    def _execute_loop_body_chain(
        self,
        instance: WorkflowInstance,
        node_dict: Dict[str, Any],
        nodes_by_id: Dict[str, Dict[str, Any]]
    ) -> None:
        """递归执行循环体子节点链（不使用 visited_node_ids，每次迭代独立）。

        子节点通过 _LoopBodyNodeWrapper 包装后调用 execute_node 复用现有节点执行器。
        异常向上抛出，由 _execute_loop_node 根据 error_handling 决定是否终止循环。
        """
        wrapper = _LoopBodyNodeWrapper(node_dict)
        result = self.execute_node(instance, wrapper)

        # 兼容 continue_on_error 的错误返回（理论上 execute_node 会 raise，保险起见）
        if (
            isinstance(result, dict)
            and result.get('status') == 'error'
            and not (node_dict.get('config') or {}).get('continue_on_error')
        ):
            raise Exception(result.get('error_message', '节点执行失败'))

        next_ids = node_dict.get('next_nodes', []) or []
        for next_id in next_ids:
            next_node = nodes_by_id.get(next_id)
            if next_node:
                self._execute_loop_body_chain(instance, next_node, nodes_by_id)
            else:
                log.warning(
                    f'[WorkflowExecutionEngine] 循环体子节点 next_node 未找到: {next_id}'
                )

    def _resolve_loop_data_source(
        self,
        instance: WorkflowInstance,
        data_source_config: Dict[str, Any]
    ) -> List[Any]:
        """解析循环节点数据源，返回待迭代的数组。

        支持四种数据源类型：
        - find_records_all: 取 find_records 节点输出的 records 数组
        - find_records_column: 从 records 数组中提取指定字段值并扁平化（人员/群组/附件字段自动去重）
        - trigger_field: 取触发记录中指定字段值（列表直接返回，否则包装为单元素列表）
        - webhook_array: 从 webhook 节点输出的 json.array 中读取数组

        非 dict 配置、未知类型或数据为空时返回空列表。
        """
        if not isinstance(data_source_config, dict):
            return []

        source_type = data_source_config.get('type')
        context = instance.context or {}

        if source_type == 'find_records_all':
            result_variable = self._resolve_find_records_variable(instance, data_source_config.get('node_id'))
            result = context.get(result_variable, {})
            if isinstance(result, dict):
                records = result.get('records', [])
                return records if isinstance(records, list) else []
            return []

        if source_type == 'find_records_column':
            field_id = data_source_config.get('field_id')
            node_id = data_source_config.get('node_id')
            if not field_id:
                log.warning(
                    f'[WorkflowExecutionEngine] find_records_column 数据源缺少 field_id，'
                    f'node_id={node_id}，返回空数组'
                )
                return []
            result_variable = self._resolve_find_records_variable(instance, node_id)
            result = context.get(result_variable, {})
            records = result.get('records', []) if isinstance(result, dict) else []
            if not isinstance(records, list):
                records = []

            flattened: List[Any] = []
            seen_ids: set = set()
            for record in records:
                if not isinstance(record, dict):
                    continue
                value = record.get(field_id)
                if value is None:
                    continue
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and 'id' in item:
                            item_id = item.get('id')
                            if item_id and item_id not in seen_ids:
                                seen_ids.add(item_id)
                                flattened.append(item)
                        elif item is not None:
                            flattened.append(item)
                else:
                    flattened.append(value)

            if not flattened:
                log.warning(
                    f'[WorkflowExecutionEngine] find_records_column 提取为空: '
                    f'field_id={field_id}, node_id={node_id}, '
                    f'records 数量={len(records)}, '
                    f'提示: 如果需要遍历全部记录，请将 data_source.type 改为 find_records_all'
                )

            return flattened

        if source_type == 'trigger_field':
            trigger_field_id = data_source_config.get('trigger_field_id') or data_source_config.get('field_id')
            trigger_event = context.get('trigger_event', {}) or {}
            record = trigger_event.get('record', {}) or {}
            value = record.get(trigger_field_id) if trigger_field_id else None
            if isinstance(value, list):
                return value
            if value is None:
                return []
            return [value]

        if source_type == 'webhook_array':
            node_id = data_source_config.get('node_id')
            if not node_id:
                return []
            webhook_result = context.get(f'{node_id}_result', {})
            if not isinstance(webhook_result, dict):
                return []
            json_data = webhook_result.get('json', {}) or {}
            array = json_data.get('array')
            return array if isinstance(array, list) else []

        return []