import copy
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm.attributes import flag_modified

from app.i18n import translate
from app.extensions import db
from app.models.base import MemberRole
from app.models.workflow import (
    Workflow, WorkflowNode, WorkflowTrigger, WorkflowVersion,
    WorkflowStatus, WorkflowNodeType, WorkflowTriggerType,
)
from app.models.workflow_instance import WorkflowInstance, WorkflowInstanceStatus

log = logging.getLogger(__name__)

class WorkflowValidateVersionMixin:
    """WorkflowValidateVersionMixin — 13 个方法"""

    def _validate_loop_node(node_config: Dict[str, Any], depth: int = 1) -> None:
        """校验循环节点配置，depth 为当前嵌套深度（1=顶层）。

        校验失败时抛出 ValueError，由调用方转为 400 响应。
        """
        if not isinstance(node_config, dict):
            raise ValueError('loop_node_configuration_object')

        if depth > 3:
            raise ValueError('loop_nesting_depth_exceed_levels')

        config = node_config.get('config', {}) or {}

        # 校验 loop_body_nodes 为非空 list
        loop_body_nodes = config.get('loop_body_nodes')
        if not isinstance(loop_body_nodes, list) or len(loop_body_nodes) == 0:
            raise ValueError('loop_nodes_contain_non_empty_loop_body_nodes')

        # 校验循环体子节点不包含 condition
        for child in loop_body_nodes:
            if not isinstance(child, dict):
                continue
            if child.get('node_type') == 'condition':
                raise ValueError('conditional_branch_nodes_not_supported_loop_bodies')

        # 校验 max_iterations 为 1-1000 正整数
        max_iterations = config.get('max_iterations', 100)
        if (
            not isinstance(max_iterations, int)
            or isinstance(max_iterations, bool)
            or max_iterations < 1
            or max_iterations > 1000
        ):
            raise ValueError('max_iterations_positive_integer_between')

        # 校验 error_handling
        error_handling = config.get('error_handling', 'skip')
        if error_handling not in ('skip', 'terminate'):
            raise ValueError("error_handling_skip_terminate")

        # 校验 empty_result_action
        empty_result_action = config.get('empty_result_action', 'skip')
        if empty_result_action not in ('skip', 'error'):
            raise ValueError("empty_result_action_skip_error")

        # 递归校验嵌套循环
        for child in loop_body_nodes:
            if not isinstance(child, dict):
                continue
            if child.get('node_type') == 'loop':
                WorkflowService._validate_loop_node(child, depth + 1)

    def _validate_script_node(node_config: Dict[str, Any], all_node_ids: set = None) -> None:
        """校验脚本节点配置，失败抛 ValueError。

        Args:
            node_config: 节点配置（含 config 字段）
            all_node_ids: 工作流内所有节点 id 集合（str 形式），用于校验分支目标存在性
        """
        if not isinstance(node_config, dict):
            raise ValueError('script_node_configuration_object')
        config = node_config.get('config', {}) or {}

        # language
        language = config.get('language')
        if language != 'python':
            raise ValueError("script_language_python")

        # script_source 非空且 ≤50000 字符
        script_source = config.get('script_source', '')
        if not isinstance(script_source, str) or not script_source.strip():
            raise ValueError('script_content_empty')
        if len(script_source) > 50000:
            raise ValueError('script_content_exceed_characters')

        # timeout 1-300 正整数
        timeout = config.get('timeout', 30)
        if (
            not isinstance(timeout, int)
            or isinstance(timeout, bool)
            or timeout < 1
            or timeout > 300
        ):
            raise ValueError('timeout_positive_integer_between')

        # result_variable 合法变量名，缺省 script_result
        result_variable = config.get('result_variable', 'script_result') or 'script_result'
        if not _SCRIPT_RESULT_VAR_PATTERN.match(result_variable):
            raise ValueError('result_variable_name_alphanumeric_underscore_start_letter_unders')

        # branches：label 非空且唯一、target_node_id 存在
        branches = config.get('branches', []) or []
        if not isinstance(branches, list):
            raise ValueError('branch_routing_configuration_array')
        labels = set()
        for b in branches:
            if not isinstance(b, dict):
                raise ValueError('branch_configuration_items_objects')
            label = b.get('label')
            target = b.get('target_node_id')
            if not label or not isinstance(label, str):
                raise ValueError('branch_label_empty')
            if label in labels:
                raise ValueError(translate('branch_label_duplicate', label))
            labels.add(label)
            if not target:
                raise ValueError(translate('branch_missing_target_node_id', label))
            if all_node_ids is not None and str(target) not in all_node_ids:
                raise ValueError(translate('branch_target_node_not_found', label, target))

    def _validate_update_record_node(cls, node_config: Dict[str, Any]) -> None:
        """校验「更新记录」节点配置，失败抛 ValueError。

        校验范围：主记录字段映射（updates）与关联表同步更新（related_updates）的结构合法性。
        目标表/字段是否存在等依赖运行期数据的校验交由执行引擎在运行时处理。
        """
        if not isinstance(node_config, dict):
            raise ValueError('update_record_node_configuration_object')
        config = node_config.get('config', {}) or {}

        # 主记录字段映射
        updates = config.get('updates', []) or []
        if not isinstance(updates, list):
            raise ValueError('update_record_updates_array')
        for m in updates:
            if not isinstance(m, dict):
                raise ValueError('update_record_updates_item_object')
            if 'field_id' in m and not isinstance(m.get('field_id'), str):
                raise ValueError('update_record_updates_field_id_string')

        # 关联表同步更新
        related = config.get('related_updates', []) or []
        if not isinstance(related, list):
            raise ValueError('related_updates_array')
        for task in related:
            if not isinstance(task, dict):
                raise ValueError('related_updates_item_object')
            if task.get('target_table_id') is not None and not isinstance(task.get('target_table_id'), str):
                raise ValueError('related_updates_target_table_id_string')
            if 'link_field_id' in task and task.get('link_field_id') is not None \
                    and not isinstance(task.get('link_field_id'), str):
                raise ValueError('related_updates_link_field_id_string')
            if 'field_mappings' in task and not isinstance(task.get('field_mappings'), list):
                raise ValueError('related_updates_field_mappings_array')
            if 'conditions' in task and not isinstance(task.get('conditions'), list):
                raise ValueError('related_updates_conditions_array')
            if 'trigger_condition' in task and not isinstance(task.get('trigger_condition'), list):
                raise ValueError('related_updates_trigger_condition_array')
            trigger = task.get('trigger', 'always')
            if trigger not in ('always', 'condition'):
                raise ValueError('related_updates_trigger_invalid')
            for conj_key in ('conditions_conjunction', 'trigger_condition_conjunction'):
                if conj_key in task and task.get(conj_key) not in ('and', 'or'):
                    raise ValueError('related_updates_conjunction_invalid')

    def _validate_notify_node(cls, node_config: Dict[str, Any]) -> None:
        """校验「站内信通知」节点配置，失败抛 ValueError。

        校验范围：接收人来源合法性、各来源对应的取值非空、标题/正文类型。
        用户是否存在、字段是否能解析出成员等依赖运行期数据的校验交由执行引擎处理。
        """
        if not isinstance(node_config, dict):
            raise ValueError('notify_node_configuration_object')
        config = node_config.get('config', {}) or {}

        sources = config.get('recipient_sources')
        if isinstance(sources, str):
            sources = [sources]
        if not sources:
            # 兼容单来源结构
            legacy_type = config.get('recipient_type')
            sources = [legacy_type] if legacy_type else []
        if not isinstance(sources, list) or not sources:
            raise ValueError('notify_recipient_source_required')

        for source in sources:
            if source not in cls.NOTIFY_RECIPIENT_SOURCES:
                raise ValueError(translate('notify_recipient_source_invalid', source))

        if 'fixed' in sources:
            user_ids = config.get('recipient_user_ids') or []
            if not isinstance(user_ids, list) or not user_ids:
                raise ValueError('notify_fixed_recipients_required')

        if 'field' in sources:
            field_ids = config.get('recipient_field_ids') or []
            if not isinstance(field_ids, list) or not field_ids:
                raise ValueError('notify_field_recipients_required')

        for key in ('subject', 'body'):
            if key in config and config.get(key) is not None \
                    and not isinstance(config.get(key), str):
                raise ValueError(translate('notify_content_string', key))

        # 标题为空会在运行时中断流程，保存阶段即拦截，把问题前置
        if not str(config.get('subject') or '').strip():
            raise ValueError('notify_title_required')

    def _validate_schedule_config(schedule: Dict[str, Any]) -> datetime:
        """校验定时器配置完整性与时间合法性，返回带时区的 start_datetime"""
        if not isinstance(schedule, dict):
            raise ValueError('timer_configuration_object')

        required_fields = ['start_date', 'start_time', 'repeat_type', 'end_type']
        for field in required_fields:
            if field not in schedule or schedule[field] is None or schedule[field] == '':
                raise ValueError(translate('timer_config_missing_required', field))

        valid_repeat_types = {'no_repeat', 'daily', 'weekly', 'monthly', 'yearly', 'weekdays', 'custom'}
        repeat_type = schedule['repeat_type']
        if repeat_type not in valid_repeat_types:
            raise ValueError(translate('repeat_type_invalid', repeat_type))

        if repeat_type == 'custom':
            custom_interval = schedule.get('custom_interval')
            if not isinstance(custom_interval, int) or isinstance(custom_interval, bool) or custom_interval <= 0:
                raise ValueError('custom_interval_positive_integer')
            custom_unit = schedule.get('custom_unit')
            if custom_unit not in {'day', 'week', 'month', 'year'}:
                raise ValueError('custom_unit_one_day_week_month_year')

        end_type = schedule['end_type']
        if end_type not in {'never', 'end_date'}:
            raise ValueError(translate('end_type_invalid', end_type))

        timezone_name = schedule.get('timezone')
        if timezone_name:
            try:
                tz = ZoneInfo(str(timezone_name))
            except Exception as e:
                raise ValueError(translate('timezone_invalid', timezone_name)) from e
        else:
            # 未指定时区时，使用服务器本地时区解释用户配置的日期时间
            tz = datetime.now().astimezone().tzinfo

        start_date = schedule['start_date']
        start_time = schedule['start_time']
        try:
            start_dt = datetime.strptime(f'{start_date} {start_time}', '%Y-%m-%d %H:%M')
        except ValueError:
            try:
                start_dt = datetime.strptime(f'{start_date} {start_time}', '%Y-%m-%dT%H:%M')
            except ValueError as e:
                raise ValueError(translate('start_datetime_format_invalid', start_date, start_time)) from e

        start_dt = start_dt.replace(tzinfo=tz)

        if end_type == 'end_date':
            end_date = schedule.get('end_date')
            if not end_date:
                raise ValueError('end_date_required_when_end_type_end_date')
            try:
                end_dt = datetime.strptime(str(end_date), '%Y-%m-%d').replace(tzinfo=tz)
            except ValueError as e:
                raise ValueError(translate('end_date_format_invalid', end_date)) from e
            if end_dt < start_dt:
                raise ValueError('end_date_earlier_than_start_date')

        if repeat_type == 'no_repeat':
            if start_dt <= datetime.now(timezone.utc):
                raise ValueError('start_time_after_current_utc_time_no_repeat_mode')

        return start_dt

    def _validate_record_time_config(trigger: 'WorkflowTrigger', table_id) -> None:
        """校验 record_time_reached 触发器配置：time_field_id 必须存在且为日期/日期时间类型字段"""
        from app.models.field import Field, FieldType

        filter_config = trigger.filter_config or {}
        time_field_id = filter_config.get('time_field_id')
        if not time_field_id:
            raise ValueError('select_time_field')

        field = Field.query.filter_by(id=time_field_id, table_id=table_id).first()
        if not field:
            raise ValueError(translate('time_field_not_found', time_field_id))
        field_type = field.type.value if isinstance(field.type, FieldType) else field.type
        if field_type not in (FieldType.DATE.value, FieldType.DATE_TIME.value):
            raise ValueError(translate('time_field_type_invalid', field_type))

    def _validate_workflow_config(cls, workflow: Workflow) -> None:
        """验证工作流配置完整性，不通过时抛出 ValueError"""
        if not workflow.table_id:
            raise ValueError('workflow_linked_data_table')

        trigger = workflow.triggers.first()
        if trigger and trigger.trigger_type == WorkflowTriggerType.SPECIFIED_TIME:
            schedule = (trigger.filter_config or {}).get('schedule')
            if not schedule:
                raise ValueError('specified_time_trigger_schedule_configured')
            cls._validate_schedule_config(schedule)
        elif trigger and trigger.trigger_type == WorkflowTriggerType.RECORD_TIME_REACHED:
            cls._validate_record_time_config(trigger, workflow.table_id)

    def _count_loop_nodes(nodes_config: List[Dict[str, Any]]) -> int:
        """递归统计 loop 节点总数（含嵌套循环体内的）"""
        if not isinstance(nodes_config, list):
            return 0
        count = 0
        for node in nodes_config:
            if not isinstance(node, dict):
                continue
            if node.get('node_type') == 'loop':
                count += 1
                config = node.get('config', {}) or {}
                count += WorkflowService._count_loop_nodes(config.get('loop_body_nodes', []))
        return count

    def save_version_snapshot(cls, workflow_id: Any, created_by: Any) -> Optional[WorkflowVersion]:
        """
        为暂停状态的工作流保存版本快照。
        仅当当前配置与最新版本快照存在差异时才创建新版本。

        Args:
            workflow_id: 工作流 ID
            created_by: 操作者 ID

        Returns:
            新创建的 WorkflowVersion，若无变更则返回 None

        Raises:
            ValueError: 工作流不存在或非暂停状态
        """
        workflow = Workflow.query.filter_by(
            id=cls._to_uuid(workflow_id),
            is_deleted=False
        ).first()

        if not workflow:
            raise ValueError('workflow_does_not_exist')

        if workflow.status != WorkflowStatus.PAUSED:
            raise ValueError('workflows_paused_status_save_version_snapshots')

        # 构建当前配置快照（仅对比业务字段，排除 id/workflow_id 等非实质字段）
        current_content = cls._build_content_fingerprint(workflow)

        # 获取最新版本快照，提取业务字段进行对比
        latest_version = WorkflowVersion.query.filter_by(
            workflow_id=workflow.id
        ).order_by(WorkflowVersion.version_number.desc()).first()

        if latest_version:
            latest_content = cls._extract_content_from_snapshot(latest_version.config_snapshot)
            if latest_content == current_content:
                log.info(f'[WorkflowService] 工作流 {workflow.id} 内容无变更，跳过版本快照创建')
                return None

        # 存在变更，创建新版本
        workflow.current_version += 1
        version = WorkflowVersion(
            workflow_id=workflow.id,
            version_number=workflow.current_version,
            config_snapshot=cls._build_version_snapshot(workflow),
            created_by=cls._to_uuid(created_by)
        )
        db.session.add(version)
        db.session.commit()

        log.info(
            f'[WorkflowService] 工作流 {workflow.id} 版本快照已保存: '
            f'#{workflow.current_version} (暂停状态修改)'
        )
        return version

    def _build_version_snapshot(workflow: Workflow) -> Dict[str, Any]:
        """为工作流构建版本快照"""
        return {
            'name': workflow.name,
            'description': workflow.description,
            'nodes': [node.to_dict() for node in workflow.nodes.order_by(WorkflowNode.order).all()],
            'triggers': [trigger.to_dict() for trigger in workflow.triggers.all()]
        }

    def _build_content_fingerprint(workflow: Workflow) -> Dict[str, Any]:
        """构建仅包含业务字段的指纹，用于变更对比（排除 id/workflow_id 等每次保存都会变化的字段）"""
        from app.models.workflow import _ACTION_TYPE_TO_FRONTEND, WorkflowNodeType
        nodes = workflow.nodes.order_by(WorkflowNode.order).all()
        triggers = workflow.triggers.all()
        fingerprint_nodes = []
        for node in nodes:
            node_type_value = node.node_type.value if isinstance(node.node_type, WorkflowNodeType) else node.node_type
            # 与 to_dict() 保持一致：将 action 节点转换为前端细粒度 node_type
            if node_type_value == WorkflowNodeType.ACTION.value:
                action_type = (node.config or {}).get('action_type')
                if action_type in _ACTION_TYPE_TO_FRONTEND:
                    node_type_value = _ACTION_TYPE_TO_FRONTEND[action_type]
            fingerprint_nodes.append({
                'node_type': node_type_value,
                'name': node.name,
                'config': node.config or {},
                'order': node.order,
                'next_nodes': node.next_nodes or []
                # ui_layout 为纯展示字段，不参与版本指纹
            })
        return {
            'name': workflow.name,
            'description': workflow.description,
            'nodes': fingerprint_nodes,
            'triggers': [
                {
                    'trigger_type': trigger.trigger_type.value if isinstance(trigger.trigger_type, WorkflowTriggerType) else trigger.trigger_type,
                    'filter_config': trigger.filter_config or {},
                    'field_ids': trigger.field_ids or []
                }
                for trigger in triggers
            ]
        }

    def _extract_content_from_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """从快照中提取业务字段指纹（与 _build_content_fingerprint 保持同构）"""
        nodes = snapshot.get('nodes', [])
        triggers = snapshot.get('triggers', [])
        return {
            'name': snapshot.get('name', ''),
            'description': snapshot.get('description'),
            'nodes': [
                {
                    'node_type': n.get('node_type'),
                    'name': n.get('name'),
                    'config': n.get('config', {}),
                    'order': n.get('order'),
                    'next_nodes': n.get('next_nodes', [])
                    # ui_layout 为纯展示字段，不参与版本指纹
                }
                for n in nodes
            ],
            'triggers': [
                {
                    'trigger_type': t.get('trigger_type'),
                    'filter_config': t.get('filter_config', {}),
                    'field_ids': t.get('field_ids', [])
                }
                for t in triggers
            ]
        }

    def list_workflow_versions(cls, workflow_id: Any) -> List[WorkflowVersion]:
        """
        获取工作流的所有历史版本

        Args:
            workflow_id: 工作流 ID

        Returns:
            WorkflowVersion 列表（按版本号降序）
        """
        workflow = Workflow.query.filter_by(
            id=cls._to_uuid(workflow_id),
            is_deleted=False
        ).first()

        if not workflow:
            return []

        return WorkflowVersion.query.filter_by(
            workflow_id=workflow.id
        ).order_by(WorkflowVersion.version_number.desc()).all()