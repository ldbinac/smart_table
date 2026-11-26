"""
工作流核心服务模块

提供工作流的 CRUD、状态管理、版本发布与触发匹配能力。

过滤条件操作符直接使用前端 FilterOperator 字符串（驼峰命名），
不进行前后端转换，前后端字符逻辑完全一致。
"""
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
    Workflow,
    WorkflowNode,
    WorkflowTrigger,
    WorkflowVersion,
    WorkflowStatus,
    WorkflowNodeType,
    WorkflowTriggerType,
)
from app.models.workflow_instance import WorkflowInstance, WorkflowInstanceStatus
from app.services.permission_service import PermissionService


log = logging.getLogger(__name__)

# 脚本节点结果变量名合法模式（字母/数字/下划线，首字符为字母或下划线，≤64 字符）
_SCRIPT_RESULT_VAR_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,63}$')


def _parse_datetime(value: Any) -> Optional[datetime]:
    """将任意值解析为 datetime 对象（含时区信息），失败返回 None"""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    try:
        text = str(value).strip()
    except Exception:
        return None
    if not text:
        return None
    # ISO 8601（含时区）
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        pass
    # 常见格式
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d'):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _resolve_date_range(range_key: str) -> tuple:
    """根据前端 isWithin 的 range key 解析 [start, end) 时间范围（UTC）"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_ms = 24 * 60 * 60
    week_ms = 7 * day_ms

    if range_key == 'today':
        return today_start, today_start + timedelta(seconds=day_ms)
    if range_key == 'yesterday':
        return today_start - timedelta(seconds=day_ms), today_start
    if range_key == 'tomorrow':
        return today_start + timedelta(seconds=day_ms), today_start + timedelta(seconds=2 * day_ms)
    if range_key == 'thisWeek':
        day_of_week = today_start.weekday()  # Monday=0
        week_start = today_start - timedelta(days=day_of_week)
        return week_start, week_start + timedelta(seconds=week_ms)
    if range_key == 'lastWeek':
        day_of_week = today_start.weekday()
        this_week_start = today_start - timedelta(days=day_of_week)
        return this_week_start - timedelta(seconds=week_ms), this_week_start
    if range_key == 'nextWeek':
        day_of_week = today_start.weekday()
        this_week_start = today_start - timedelta(days=day_of_week)
        return this_week_start + timedelta(seconds=week_ms), this_week_start + timedelta(seconds=2 * week_ms)
    if range_key == 'thisMonth':
        month_start = today_start.replace(day=1)
        next_month_start = (month_start + timedelta(days=32)).replace(day=1)
        return month_start, next_month_start
    if range_key == 'lastMonth':
        month_start = today_start.replace(day=1) - timedelta(days=1)
        month_start = month_start.replace(day=1)
        this_month_start = today_start.replace(day=1)
        return month_start, this_month_start
    if range_key == 'thisYear':
        year_start = today_start.replace(month=1, day=1)
        next_year_start = year_start.replace(year=year_start.year + 1)
        return year_start, next_year_start
    if range_key == 'lastYear':
        year_start = today_start.replace(month=1, day=1) - timedelta(days=1)
        year_start = year_start.replace(month=1, day=1)
        this_year_start = today_start.replace(month=1, day=1)
        return year_start, this_year_start
    return None, None

class WorkflowServiceGroup01Mixin:
    """Mixin auto-split"""
    
    """工作流核心服务"""
    
    NOTIFY_RECIPIENT_SOURCES = ('fixed', 'field', 'trigger_user', 'record_creator', 'base_members')
    
    
    @staticmethod
    def _to_uuid(value: Any) -> Optional[uuid.UUID]:
        """将字符串或 UUID 对象转换为 UUID 对象"""
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))
    
    @staticmethod
    def _eval_operator(actual: Any, operator: str, expected: Any) -> bool:
        """评估单个过滤条件（操作符直接使用前端 FilterOperator 字符串）"""
        if operator == 'equals':
            return actual == expected
    
        if operator == 'notEquals':
            return actual != expected
    
        if operator == 'contains':
            if actual is None:
                return False
            if isinstance(actual, str):
                return str(expected) in actual
            if isinstance(actual, (list, tuple, set)):
                return expected in actual
            if isinstance(actual, dict):
                return expected in actual
            return str(expected) in str(actual)
    
        if operator == 'notContains':
            if actual is None:
                return True
            if isinstance(actual, str):
                return str(expected) not in actual
            if isinstance(actual, (list, tuple, set)):
                return expected not in actual
            if isinstance(actual, dict):
                return expected not in actual
            return str(expected) not in str(actual)
    
        if operator in ('greaterThan', 'lessThan', 'greaterThanOrEqual', 'lessThanOrEqual'):
            try:
                actual_num = float(actual)
                expected_num = float(expected)
            except (TypeError, ValueError):
                return False
            if operator == 'greaterThan':
                return actual_num > expected_num
            if operator == 'lessThan':
                return actual_num < expected_num
            if operator == 'greaterThanOrEqual':
                return actual_num >= expected_num
            return actual_num <= expected_num
    
        if operator == 'startsWith':
            if actual is None:
                return False
            return str(actual).startswith(str(expected))
    
        if operator == 'endsWith':
            if actual is None:
                return False
            return str(actual).endswith(str(expected))
    
        if operator == 'isAnyOf':
            if expected is None:
                return False
            if isinstance(expected, (list, tuple, set)):
                return actual in expected
            return False
    
        if operator == 'isNoneOf':
            if expected is None:
                return False
            if isinstance(expected, (list, tuple, set)):
                return actual not in expected
            return False
    
        if operator == 'isEmpty':
            if actual is None:
                return True
            if isinstance(actual, str):
                return actual.strip() == ''
            if isinstance(actual, (list, tuple, set, dict)):
                return len(actual) == 0
            return False
    
        if operator == 'isNotEmpty':
            if actual is None:
                return False
            if isinstance(actual, str):
                return actual.strip() != ''
            if isinstance(actual, (list, tuple, set, dict)):
                return len(actual) > 0
            return True
    
        if operator in ('isBefore', 'isAfter', 'isOnOrBefore', 'isOnOrAfter'):
            actual_dt = _parse_datetime(actual)
            expected_dt = _parse_datetime(expected)
            if actual_dt is None or expected_dt is None:
                return False
            if operator == 'isBefore':
                return actual_dt < expected_dt
            if operator == 'isAfter':
                return actual_dt > expected_dt
            if operator == 'isOnOrBefore':
                return actual_dt <= expected_dt
            return actual_dt >= expected_dt
    
        if operator == 'isWithin':
            actual_dt = _parse_datetime(actual)
            if actual_dt is None:
                return False
            range_start, range_end = _resolve_date_range(str(expected))
            if range_start is None or range_end is None:
                return False
            return range_start <= actual_dt < range_end
    
        return False
    
    @classmethod
    def _evaluate_filter_condition(
        cls,
        condition: Dict[str, Any],
        record_values: Dict[str, Any],
        changes: Optional[Dict[str, Any]]
    ) -> bool:
        """递归评估过滤条件（支持 AND/OR 组合）
    
        group 结构通过 conditions 数组判断（与前端一致）；
        conjunction 缺失时默认 'and'（前端 filterConjunction 未被用户修改时不会显式写入该字段）。
        """
        if not isinstance(condition, dict):
            return False
    
        # group 结构通过 conditions 数组判断（conjunction 默认 'and'，与前端一致）
        sub_conditions = condition.get('conditions')
        if isinstance(sub_conditions, list):
            conjunction = condition.get('conjunction', 'and')
            if conjunction == 'or':
                return any(
                    cls._evaluate_filter_condition(c, record_values, changes)
                    for c in sub_conditions
                )
            return all(
                cls._evaluate_filter_condition(c, record_values, changes)
                for c in sub_conditions
            )
    
        # 叶子条件：直接读取 operator 字段（无需转换）
        operator = condition.get('operator')
        field_id = condition.get('field_id')
        expected = condition.get('value')
    
        actual = None
        if record_values and field_id in record_values:
            actual = record_values[field_id]
        elif changes and field_id in changes:
            actual = changes[field_id].get('new_value')
    
        return cls._eval_operator(actual, operator, expected)
    
    @staticmethod
    def _clean_filter_config(filter_config: Any) -> Dict[str, Any]:
        """清理空条件结构：conditions 为空数组时返回空 dict，但保留定时器 schedule 配置"""
        if not isinstance(filter_config, dict):
            return {}
        conditions = filter_config.get('conditions')
        if isinstance(conditions, list) and len(conditions) == 0 and 'schedule' not in filter_config:
            return {}
        return filter_config
    
    @staticmethod
    def _normalize_condition_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """将条件节点配置归一化为多分支结构。
    
        旧配置 {conditions, conjunction} 自动迁移为单分支；
        新配置 {branches: [...]} 直接返回，并为缺少 id 的分支补全 id。
        """
        if not isinstance(config, dict):
            config = {}
        branches = config.get('branches')
        if isinstance(branches, list):
            normalized_branches = []
            for branch in branches:
                if not isinstance(branch, dict):
                    continue
                normalized_branches.append({
                    'id': branch.get('id') or f'branch_{uuid.uuid4().hex[:8]}',
                    'name': branch.get('name', '满足条件'),
                    'conditions': branch.get('conditions', []),
                    'conjunction': branch.get('conjunction', 'and'),
                    'target_node_id': branch.get('target_node_id'),
                })
            if normalized_branches:
                return {**config, 'branches': normalized_branches}
    
        old_conditions = config.get('conditions', [])
        old_conjunction = config.get('conjunction', 'and')
        return {
            'branches': [
                {
                    'id': f'branch_{uuid.uuid4().hex[:8]}',
                    'name': '满足条件',
                    'conditions': old_conditions,
                    'conjunction': old_conjunction,
                    'target_node_id': None,
                }
            ]
        }
    
    @staticmethod
    def _clean_condition_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """清理条件节点配置：branches 为空数组时返回空 dict"""
        if not isinstance(config, dict):
            return {}
        branches = config.get('branches')
        if isinstance(branches, list) and len(branches) == 0:
            return {}
        return config
    
    @staticmethod
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
    
    @staticmethod
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
    
    @classmethod
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
    
    @classmethod
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
    
    @staticmethod
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
    
    @staticmethod
    def _build_version_snapshot(workflow: Workflow) -> Dict[str, Any]:
        """为工作流构建版本快照"""
        return {
            'name': workflow.name,
            'description': workflow.description,
            'nodes': [node.to_dict() for node in workflow.nodes.order_by(WorkflowNode.order).all()],
            'triggers': [trigger.to_dict() for trigger in workflow.triggers.all()]
        }
    
