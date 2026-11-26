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

class WorkflowRecordMixin:
    """WorkflowRecordMixin — 5 个方法"""

    def _execute_update_record(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行更新记录动作。

        在更新主记录自身表内容的同时，支持通过 ``related_updates`` 配置同步更新
        其他关联表的内容。所有更新（主记录 + 全部关联表记录）在同一个数据库事务中
        完成：只要任一环节失败，整体回滚并记录执行日志，保证多表数据一致性。
        """
        config = node.config or {}
        record_id = config.get('record_id') or instance.trigger_record_id
        if not record_id:
            raise ValueError('missing_target_record_id')

        main_record = RecordService.get_record_by_id(str(record_id))
        if not main_record:
            raise ValueError(translate('record_not_found', record_id))

        context = self._build_render_context(instance)

        # 1) 主记录（自身表）字段更新
        updates = config.get('updates', []) or []
        main_values: Dict[str, Any] = {}
        for mapping in updates:
            field_id = mapping.get('field_id')
            if not field_id:
                continue
            main_values[field_id] = self.render_template(mapping.get('value_template', ''), context)

        # 2) 解析关联表同步更新任务
        related_updates = config.get('related_updates', []) or []
        resolved: List[Tuple[Record, Dict[str, Any]]] = []
        for idx, task in enumerate(related_updates):
            if not isinstance(task, dict):
                continue
            target_table_id = task.get('target_table_id')
            if not target_table_id:
                raise ValueError(translate('related_update_missing_target_table', idx + 1))

            table = Table.query.get(self._to_uuid(target_table_id))
            if not table:
                raise ValueError(translate('target_table_not_found', target_table_id))

            candidate_ids = self._resolve_related_record_ids(main_record, task, context)
            field_mappings = task.get('field_mappings', []) or []
            if not field_mappings:
                continue

            query = Record.query.filter_by(
                table_id=self._to_uuid(target_table_id), is_deleted=False
            )
            if candidate_ids is not None:
                query = query.filter(Record.id.in_(candidate_ids))
            candidate_records = query.all()

            # 同步触发方式：condition 模式下，仅当关联表中存在满足「同步触发条件」的记录时才执行本次同步。
            # 注意：条件字段取自关联表，需逐条在关联记录上下文（rec_context）中求值的「存在性」判断。
            trigger = task.get('trigger', 'always')
            if trigger == 'condition':
                trigger_condition = self._render_condition_values(
                    task.get('trigger_condition', []) or [], context
                )
                trigger_conjunction = task.get('trigger_condition_conjunction', 'and')
                trigger_matched = False
                for rec in candidate_records:
                    rec_context = self._build_related_context(context, main_record, rec)
                    if self.evaluate_condition(
                        {'conditions': trigger_condition, 'conjunction': trigger_conjunction}, rec_context
                    ):
                        trigger_matched = True
                        break
                if not trigger_matched:
                    continue

            conditions = self._render_condition_values(task.get('conditions', []) or [], context)
            conditions_conjunction = task.get('conditions_conjunction', 'and')
            for rec in candidate_records:
                rec_context = self._build_related_context(context, main_record, rec)
                if conditions and not self.evaluate_condition(
                    {'conditions': conditions, 'conjunction': conditions_conjunction}, rec_context
                ):
                    continue
                values: Dict[str, Any] = {}
                for m in field_mappings:
                    tf = m.get('target_field_id')
                    if not tf:
                        continue
                    values[tf] = self.render_template(m.get('value_template', ''), rec_context)
                if values:
                    resolved.append((rec, values))

        # 3) 单事务执行：任一环节失败则整体回滚，保证多表一致性
        try:
            if main_values:
                RecordService.update_record(
                    main_record, main_values, updated_by=self.SYSTEM_USER_ID, commit=False
                )
            related_updated = 0
            for rec, values in resolved:
                RecordService.update_record(
                    rec, values, updated_by=self.SYSTEM_USER_ID, commit=False
                )
                related_updated += 1
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            log.error(
                f'[WorkflowExecutionEngine] 更新记录节点多表更新失败，已整体回滚: '
                f'instance={instance.id}, node={node.id}, error={e}'
            )
            raise

        return {
            'record_id': str(main_record.id),
            'main_updated': bool(main_values),
            'related_updated': related_updated,
        }

    def _resolve_related_record_ids(
        self, main_record: Record, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Optional[List[str]]:
        """根据关联字段解析出需要同步更新的目标记录 ID 列表。

        返回 ``None`` 表示不限定（将对目标表全表按条件过滤）；
        返回空列表表示没有关联到任何记录（即本次关联更新无目标）。
        """
        link_field_id = task.get('link_field_id')
        if not link_field_id:
            return None
        raw = (main_record.values or {}).get(link_field_id)
        if raw is None:
            return []
        if isinstance(raw, str):
            return [raw]
        if isinstance(raw, list):
            ids: List[str] = []
            for item in raw:
                if isinstance(item, str):
                    ids.append(item)
                elif isinstance(item, dict) and item.get('id'):
                    ids.append(str(item['id']))
            return ids
        return []

    def _build_related_context(
        self, context: Dict[str, Any], main_record: Record, rec: Record
    ) -> Dict[str, Any]:
        """构建关联记录更新时的模板渲染上下文。

        主记录仍通过 ``record`` 访问；关联记录字段除了以 ``target_record`` 显式暴露外，
        其字段值（以字段 ID 为键）也提升到顶层，便于在条件与映射中直接引用。
        """
        rec_values = dict(rec.values or {})
        related_ctx = dict(context)
        related_ctx['target_record'] = rec_values
        for k, v in rec_values.items():
            related_ctx.setdefault(k, v)
        return related_ctx

    def _render_condition_values(
        self, conditions: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """递归渲染条件中的模板值（如 ``{{record.field_id}}``），便于在条件中引用主记录。"""
        rendered: List[Dict[str, Any]] = []
        for c in conditions:
            if not isinstance(c, dict):
                continue
            rc = dict(c)
            if isinstance(rc.get('value'), str):
                rc['value'] = self.render_template(rc['value'], context)
            if isinstance(rc.get('conditions'), list):
                rc['conditions'] = self._render_condition_values(rc['conditions'], context)
            rendered.append(rc)
        return rendered

    def _execute_create_record(self, instance: WorkflowInstance, node: WorkflowNode) -> Dict[str, Any]:
        """执行创建记录动作"""
        config = node.config or {}
        table_id = config.get('target_table_id')
        if not table_id:
            raise ValueError('missing_target_table_id')

        # 前端存储为 field_mappings 数组，需转为字段ID→值的字典
        field_mappings = config.get('field_mappings', [])
        context = self._build_render_context(instance)
        rendered_values = {}
        for mapping in field_mappings:
            target_field_id = mapping.get('target_field_id')
            if not target_field_id:
                continue
            value_template = mapping.get('value_template', '')
            rendered_values[target_field_id] = self.render_template(value_template, context)

        record = RecordService.create_record(
            str(table_id),
            rendered_values,
            created_by=self.SYSTEM_USER_ID
        )
        return {'record_id': str(record.id)}