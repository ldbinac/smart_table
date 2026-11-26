"""
查找字段（LOOKUP）核心服务模块

参照飞书查找引用字段，实现：
- 配置校验（源表/目标字段/过滤条件/计算方式/字段格式）
- 过滤条件求值引擎（7 种操作符 + AND/OR 连接）
- 聚合计算（8 种：原值/去重/去重计数/求和/计数/平均值/最大值/最小值）
- 字段格式化（数字/日期/货币）
- 实时计算入口 compute_lookup_value
"""
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

from app.extensions import db
from app.models.field import Field, FieldType
from app.models.lookup import (
    LookupAggregationType,
    LookupFieldFormat,
    LookupFilterOperator,
)
from app.models.record import Record
from app.models.table import Table


logger = logging.getLogger(__name__)


# 字段类型分组常量，用于判断操作符适用性
_TEXT_LIKE_TYPES = {
    FieldType.SINGLE_LINE_TEXT.value,
    FieldType.LONG_TEXT.value,
    FieldType.RICH_TEXT.value,
    FieldType.EMAIL.value,
    FieldType.PHONE.value,
    FieldType.URL.value,
}

_SELECT_MEMBER_LINK_TYPES = {
    FieldType.SINGLE_SELECT.value,
    FieldType.MULTI_SELECT.value,
    FieldType.COLLABORATOR.value,
    FieldType.LINK.value,
    FieldType.LINK_TO_RECORD.value,
}

_DATE_LIKE_TYPES = {
    FieldType.DATE.value,
    FieldType.DATE_TIME.value,
}

# 关联字段类型：记录中存储的是目标表的记录 ID（单个 ID 或 ID 数组）
_LINK_FIELD_TYPES = {
    FieldType.LINK.value,
    FieldType.LINK_TO_RECORD.value,
}

# 选择类字段类型：记录中存储的是选项 ID，显示给用户的则是选项名称
_SELECT_FIELD_TYPES = {
    FieldType.SINGLE_SELECT.value,
    FieldType.MULTI_SELECT.value,
}

# 数字字段类型
_NUMBER_TYPES = {
    FieldType.NUMBER.value,
    FieldType.CURRENCY.value,
    FieldType.PERCENT.value,
    FieldType.RATING.value,
    FieldType.DURATION.value,
}

# 基础操作符（所有类型均支持）
_BASE_OPERATORS = [
    LookupFilterOperator.EQUAL.value,
    LookupFilterOperator.NOT_EQUAL.value,
    LookupFilterOperator.IS_EMPTY.value,
    LookupFilterOperator.IS_NOT_EMPTY.value,
]


def _is_number(v: Any) -> bool:
    """判断是否为数字（排除 bool）"""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# 数值字符串前缀（货币符号、单位等），如 "¥1,200.50"
_NUMERIC_PREFIX_RE = re.compile(r'^[^\d\-\+\.]+')


def _to_number(v: Any) -> Optional[float]:
    """
    尽力把值转换为数字，无法转换时返回 None。

    支持：int/float、数字字符串（可含千分位分隔符、货币符号、百分号、前后空白）。
    源字段值在实际数据中常以字符串形式存储（导入数据、文本/公式字段、API 写入等），
    聚合计算必须容忍这种情况，否则求和/平均值恒为 0、最大最小值恒为空。
    """
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(',', '').replace('，', '')
        if not s:
            return None
        s = _NUMERIC_PREFIX_RE.sub('', s)
        if s.endswith('%'):
            s = s[:-1]
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _normalize_number(v: float) -> Any:
    """整数结果的浮点数还原为 int，避免出现 129.0 这类显示"""
    if v == int(v):
        return int(v)
    return v


def _safe_int(v: Any, default: int) -> int:
    """安全地转换为 int，失败时返回默认值"""
    try:
        return int(v)
    except (TypeError, ValueError):
        return default

class LookupServiceGroup01Mixin:
    """Mixin auto-split"""
    
    """查找字段服务类，所有方法静态化便于调用"""
    
    
    @staticmethod
    def validate_config(config: Dict[str, Any], current_table_id: str) -> Tuple[bool, Optional[str]]:
        """
        校验查找字段配置
    
        Args:
            config: 查找字段配置字典
            current_table_id: 当前表 ID（字符串）
    
        Returns:
            (是否合法, 错误信息)
        """
        if not config or not isinstance(config, dict):
            return False, 'configuration_empty'
    
        # 1. 源数据表
        source_table_id = config.get('sourceTableId')
        if not source_table_id:
            return False, 'source_data_table_empty'
    
        if str(source_table_id) == str(current_table_id):
            return False, 'reference_current_data_table_choose_another_table'
    
        source_table = Table.query.get(str(source_table_id))
        if not source_table:
            return False, 'source_data_table_same_base_current_table'
    
        current_table = Table.query.get(str(current_table_id))
        if not current_table or str(source_table.base_id) != str(current_table.base_id):
            return False, 'source_data_table_same_base_current_table'
    
        # 2. 引用字段
        target_field_id = config.get('targetFieldId')
        if not target_field_id:
            return False, 'referenced_field_empty'
    
        source_fields = Field.query.filter_by(table_id=str(source_table_id)).all()
        source_fields_map = {str(f.id): f for f in source_fields}
        if str(target_field_id) not in source_fields_map:
            return False, 'referenced_field_belong_source_data_table'
    
        # 3. 过滤条件
        conditions = config.get('filterConditions') or []
        if not isinstance(conditions, list):
            return False, 'invalid_filter_condition_format'
    
        if len(conditions) > 5:
            return False, 'most_lookup_conditions_supported'
    
        # 当前表字段，用于校验 valueType=field 时的 valueFieldId
        current_fields = Field.query.filter_by(table_id=str(current_table_id)).all()
        current_field_ids = {str(f.id) for f in current_fields}
    
        valid_operator_values = {op.value for op in LookupFilterOperator}
        for cond in conditions:
            if not isinstance(cond, dict):
                return False, 'invalid_filter_condition_format'
    
            # 3.1 过滤条件字段
            cond_field_id = cond.get('fieldId')
            if not cond_field_id:
                return False, 'filter_field_belong_source_data_table'
            if str(cond_field_id) not in source_fields_map:
                return False, 'filter_field_belong_source_data_table'
    
            # 3.2 操作符
            operator = cond.get('operator')
            if not operator:
                return False, 'filter_operator_empty'
            if operator not in valid_operator_values:
                return False, 'invalid_filter_operator'
    
            # 3.3 值类型与值
            if operator in (LookupFilterOperator.IS_EMPTY.value, LookupFilterOperator.IS_NOT_EMPTY.value):
                # is_empty / is_not_empty 无需 value
                continue
    
            value_type = cond.get('valueType')
            if value_type not in ('field', 'custom', 'current_record'):
                return False, 'value_type_field_custom'
    
            # current_record：与当前记录本身比较（关联字段场景无需选择字段）
            if value_type == 'current_record':
                continue
    
            if value_type == 'field':
                value_field_id = cond.get('valueFieldId')
                if not value_field_id or str(value_field_id) not in current_field_ids:
                    return False, 'filter_value_field_belong_current_table'
            else:  # custom
                value_custom = cond.get('valueCustom')
                if value_custom is None or value_custom == '':
                    return False, 'custom_value_empty'
    
        # 4. 计算方式
        aggregation_type = config.get('aggregationType')
        if not aggregation_type:
            return False, 'computation_type_empty'
        valid_agg_values = {t.value for t in LookupAggregationType}
        if aggregation_type not in valid_agg_values:
            return False, 'invalid_computation_type'
    
        # 5. 字段格式兼容性
        field_format = config.get('fieldFormat')
        # fieldFormat 可能是字符串或对象（{type, precision, ...}）
        if isinstance(field_format, dict):
            field_format_type = field_format.get('type')
        else:
            field_format_type = field_format
    
        if aggregation_type in (
            LookupAggregationType.DISTINCT_COUNT.value,
            LookupAggregationType.SUM.value,
            LookupAggregationType.COUNT.value,
            LookupAggregationType.AVG.value,
        ):
            # 必须是 number 或 currency
            allowed = (LookupFieldFormat.NUMBER.value, LookupFieldFormat.CURRENCY.value)
            if field_format_type and field_format_type not in allowed:
                return False, 'field_format_incompatible_computation_type'
        elif aggregation_type in (LookupAggregationType.MAX.value, LookupAggregationType.MIN.value):
            # number / currency / date（仅当源字段是日期类型时 date 才合法）
            allowed = [LookupFieldFormat.NUMBER.value, LookupFieldFormat.CURRENCY.value]
            target_field = source_fields_map.get(str(target_field_id))
            if target_field and target_field.type in _DATE_LIKE_TYPES:
                allowed.append(LookupFieldFormat.DATE.value)
            if field_format_type and field_format_type not in allowed:
                return False, 'field_format_incompatible_computation_type'
        # original / distinct：fieldFormat 跟随源字段，后端不强制
    
        # 6. 条件连接符
        conjunction = config.get('filterConjunction', 'and')
        if conjunction not in ('and', 'or'):
            return False, 'condition_connector'
    
        return True, None
    
    @staticmethod
    def _get_applicable_operators(field_type: str) -> List[str]:
        """
        返回字段类型适用的操作符 value 列表
        """
        operators = list(_BASE_OPERATORS)
        if field_type in _TEXT_LIKE_TYPES or field_type in _SELECT_MEMBER_LINK_TYPES:
            operators.append(LookupFilterOperator.CONTAINS.value)
        if field_type in _DATE_LIKE_TYPES:
            operators.append(LookupFilterOperator.BEFORE.value)
            operators.append(LookupFilterOperator.AFTER.value)
        return operators
    
    @staticmethod
    def _evaluate_condition(
        record: Record,
        condition: Dict[str, Any],
        current_record: Optional[Record],
        source_fields_map: Dict[str, Field],
        resolve_cache: Optional[Dict[str, List[str]]] = None,
        current_fields_map: Optional[Dict[str, Field]] = None,
    ) -> bool:
        """
        对单条源表记录评估单个过滤条件
        """
        try:
            field_id = str(condition.get('fieldId', ''))
            operator = condition.get('operator')
            source_field = source_fields_map.get(field_id)
            if not source_field:
                return False
    
            # 字段值（从 record.values 取，键为字段 ID 字符串）
            record_values = record.values if isinstance(record.values, dict) else {}
            field_value = record_values.get(field_id)
    
            # is_empty / is_not_empty 不需要比较值
            if operator == LookupFilterOperator.IS_EMPTY.value:
                return LookupService._is_empty_value(field_value)
            if operator == LookupFilterOperator.IS_NOT_EMPTY.value:
                return not LookupService._is_empty_value(field_value)
    
            # 获取比较值
            value_type = condition.get('valueType')
            compare_value: Any = None
            compare_field: Optional[Field] = None
            if value_type == 'current_record':
                # 与当前记录本身比较：关联字段存的是记录 ID，因此用当前记录 ID 参与比较
                if not current_record:
                    return False
                compare_value = str(current_record.id)
            elif value_type == 'field':
                value_field_id = str(condition.get('valueFieldId', ''))
                if not current_record:
                    return False
                cur_values = current_record.values if isinstance(current_record.values, dict) else {}
                compare_value = cur_values.get(value_field_id)
                if current_fields_map:
                    compare_field = current_fields_map.get(value_field_id)
            elif value_type == 'custom':
                compare_value = condition.get('valueCustom')
    
            # 选择类字段（单选/多选）存的是选项 ID，另一张表可能用文本存选项名称，
            # 需要展开为「选项 ID + 选项名称」的候选集合后再比较
            source_candidates = LookupService._expand_select_candidates(field_value, source_field)
            compare_candidates = LookupService._expand_select_candidates(compare_value, compare_field)
    
            return LookupService._compare_values(
                field_value,
                operator,
                compare_value,
                is_link_field=source_field.type in _LINK_FIELD_TYPES,
                source_field=source_field,
                resolve_cache=resolve_cache,
                source_candidates=source_candidates,
                compare_candidates=compare_candidates,
            )
        except Exception as e:
            current_app.logger.error(f'[LookupService] 评估过滤条件异常: {e}')
            return False
    
    @staticmethod
    def _get_field_choices(field: Optional[Field]) -> Dict[str, str]:
        """
        读取选择类字段的「选项 ID → 选项名称」映射。
    
        单选/多选字段在记录中存的是选项 ID，而另一张表可能用单行文本存选项名称，
        两者直接比较永远不会相等，需要先把 ID 与名称建立映射。
        """
        if field is None:
            return {}
    
        options = getattr(field, 'options', None)
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except (ValueError, TypeError):
                options = None
        if not isinstance(options, dict):
            return {}
    
        choices = options.get('choices') or options.get('options') or []
        choice_map: Dict[str, str] = {}
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            choice_id = choice.get('id')
            choice_name = choice.get('name')
            if choice_id is not None and choice_name is not None:
                choice_map[str(choice_id)] = str(choice_name)
        return choice_map
    
    @staticmethod
    def _expand_select_candidates(value: Any, field: Optional[Field]) -> Optional[set]:
        """
        把选择类字段的值展开为可比较的候选集合（同时包含选项 ID 与选项名称）。
    
        非选择类字段返回 None，表示不需要候选匹配，走原有比较逻辑。
        """
        if field is None or field.type not in _SELECT_FIELD_TYPES:
            return None
    
        choice_map = LookupService._get_field_choices(field)
        raw_values = value if isinstance(value, list) else [value]
    
        candidates = set()
        for raw in raw_values:
            if raw is None or raw == '':
                continue
            # 对象形态（{id, name}）时同时取 id 与 name
            if isinstance(raw, dict):
                raw_id = raw.get('id')
                raw_name = raw.get('name')
                if raw_id is not None:
                    candidates.add(str(raw_id))
                if raw_name is not None:
                    candidates.add(str(raw_name))
                    continue
                if raw_id is None:
                    continue
                raw = raw_id
    
            text = str(raw)
            candidates.add(text)
            # ID → 名称
            if text in choice_map:
                candidates.add(choice_map[text])
            else:
                # 名称 → ID（用选项名称作为比较值时反查）
                for choice_id, choice_name in choice_map.items():
                    if choice_name == text:
                        candidates.add(choice_id)
                        break
    
        return candidates
    
    @staticmethod
    def _plain_values(value: Any) -> set:
        """把普通值（标量或数组）转为字符串集合，用于候选匹配"""
        if value is None or value == '':
            return set()
        items = value if isinstance(value, list) else [value]
        result = set()
        for item in items:
            if item is None or item == '':
                continue
            if isinstance(item, dict):
                item_id = item.get('id')
                if item_id is not None:
                    result.add(str(item_id))
                continue
            result.add(str(item))
        return result
    
    @staticmethod
    def _is_empty_value(value: Any) -> bool:
        """判断字段值是否为空"""
        if value is None:
            return True
        if isinstance(value, str) and value == '':
            return True
        if isinstance(value, (list, dict)) and len(value) == 0:
            return True
        return False
    
    @staticmethod
    def _extract_id_values(value: Any) -> List[str]:
        """
        把关联字段值归一化为记录 ID 字符串列表。
    
        关联字段在记录中的形态可能是：单个 ID 字符串、ID 数组、
        {id, name} 对象或对象数组。统一转为小写字符串便于比较。
        """
        if value is None:
            return []
    
        items = value if isinstance(value, list) else [value]
        result: List[str] = []
        for item in items:
            if isinstance(item, dict):
                item_id = item.get('id') or item.get('record_id') or item.get('recordId')
                if item_id:
                    result.append(str(item_id).lower())
            elif isinstance(item, (str, int)) and not isinstance(item, bool):
                result.append(str(item).lower())
        return result
    
    @staticmethod
    def _resolve_value_to_record_ids(
        source_field: Optional[Field],
        compare_value: Any,
        resolve_cache: Optional[Dict[str, List[str]]],
    ) -> List[str]:
        """
        把非 ID 的比较值（如项目名等显示值）解析为关联目标表的记录 ID。
    
        用于「源表关联字段 = 当前表某个文本字段」的场景：关联字段存的是记录 ID，
        而当前表字段存的是显示值，直接比较永远不相等，需要先把显示值解析为记录 ID。
        解析结果在单次查找计算内缓存，避免逐条源记录重复查表。
        """
        if compare_value is None or isinstance(compare_value, (list, dict, bool)):
            return []
    
        key = str(compare_value)
        cache = resolve_cache if resolve_cache is not None else {}
        if key in cache:
            return cache[key]
    
        ids: List[str] = []
        try:
            config = getattr(source_field, 'config', None)
            config = config if isinstance(config, dict) else {}
            linked_table_id = config.get('linkedTableId') or config.get('targetTableId')
            if not linked_table_id:
                cache[key] = ids
                return ids
    
            linked_table_id = str(linked_table_id)
            target_fields = Field.query.filter_by(table_id=linked_table_id).all()
            primary_field = next(
                (f for f in target_fields if getattr(f, 'is_primary', False)), None
            )
            if not primary_field:
                cache[key] = ids
                return ids
    
            records = Record.query.filter_by(
                table_id=linked_table_id, is_deleted=False
            ).all()
            for r in records:
                r_values = r.values if isinstance(r.values, dict) else {}
                val = r_values.get(str(primary_field.id))
                if val is None:
                    continue
                if isinstance(val, list):
                    matched = any(str(x) == key for x in val)
                else:
                    matched = str(val) == key
                if matched:
                    ids.append(str(r.id).lower())
        except Exception as e:
            current_app.logger.error(f'[LookupService] 解析关联显示值为记录 ID 失败: {e}')
    
        cache[key] = ids
        return ids
    
    @staticmethod
    def _compare_link_values(
        field_value: Any,
        operator: str,
        compare_value: Any,
        source_field: Optional[Field],
        resolve_cache: Optional[Dict[str, List[str]]],
    ) -> bool:
        """
        关联字段比较：两边都归一化为记录 ID 集合后判断交集。
    
        关联字段存储的是目标表记录 ID，因此不能用显示值直接比较。
        """
        source_ids = set(LookupService._extract_id_values(field_value))
        target_ids = set(LookupService._extract_id_values(compare_value))
    
        # 比较值不是 ID 形态（如主字段的项目名），尝试解析为记录 ID
        if compare_value is not None and not target_ids:
            target_ids = set(LookupService._resolve_value_to_record_ids(
                source_field, compare_value, resolve_cache
            ))
    
        # 任一侧无法解析出记录 ID 时，只有「不等于」成立
        if not source_ids or not target_ids:
            return operator == LookupFilterOperator.NOT_EQUAL.value
    
        has_intersection = bool(source_ids & target_ids)
        if operator in (
            LookupFilterOperator.EQUAL.value,
            LookupFilterOperator.CONTAINS.value,
        ):
            return has_intersection
        if operator == LookupFilterOperator.NOT_EQUAL.value:
            return not has_intersection
        return False
    
    @staticmethod
    def _compare_candidates(
        source_candidates: Optional[set],
        compare_candidates: Optional[set],
        field_value: Any,
        compare_value: Any,
        operator: str,
    ) -> bool:
        """
        按候选集合比较：用于单选/多选字段与文本字段之间的匹配。
    
        选择类字段存的是选项 ID，文本字段存的是选项名称，
        两边都展开为「ID + 名称」的候选集合后取交集即可正确匹配。
        """
        left = source_candidates if source_candidates is not None else LookupService._plain_values(field_value)
        right = compare_candidates if compare_candidates is not None else LookupService._plain_values(compare_value)
    
        # 任一侧没有可比较的值：只有「不等于」成立
        if not left or not right:
            return operator == LookupFilterOperator.NOT_EQUAL.value
    
        matched = bool(left & right)
        if operator in (
            LookupFilterOperator.EQUAL.value,
            LookupFilterOperator.CONTAINS.value,
        ):
            return matched
        if operator == LookupFilterOperator.NOT_EQUAL.value:
            return not matched
        return False
    
