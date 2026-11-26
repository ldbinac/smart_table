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

class WorkflowConditionMixin:
    """WorkflowConditionMixin — 5 个方法"""

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

    def _clean_filter_config(filter_config: Any) -> Dict[str, Any]:
        """清理空条件结构：conditions 为空数组时返回空 dict，但保留定时器 schedule 配置"""
        if not isinstance(filter_config, dict):
            return {}
        conditions = filter_config.get('conditions')
        if isinstance(conditions, list) and len(conditions) == 0 and 'schedule' not in filter_config:
            return {}
        return filter_config

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

    def _clean_condition_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """清理条件节点配置：branches 为空数组时返回空 dict"""
        if not isinstance(config, dict):
            return {}
        branches = config.get('branches')
        if isinstance(branches, list) and len(branches) == 0:
            return {}
        return config