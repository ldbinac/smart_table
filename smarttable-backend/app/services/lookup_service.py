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
from datetime import datetime
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


class LookupService:
    """查找字段服务类，所有方法静态化便于调用"""

    # ------------------------------------------------------------------
    # 校验
    # ------------------------------------------------------------------
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
            return False, '配置不能为空'

        # 1. 源数据表
        source_table_id = config.get('sourceTableId')
        if not source_table_id:
            return False, '源数据表不能为空'

        if str(source_table_id) == str(current_table_id):
            return False, '不能引用当前数据表，请选择其他表'

        source_table = Table.query.get(str(source_table_id))
        if not source_table:
            return False, '源数据表必须与当前表在同一个多维表格中'

        current_table = Table.query.get(str(current_table_id))
        if not current_table or str(source_table.base_id) != str(current_table.base_id):
            return False, '源数据表必须与当前表在同一个多维表格中'

        # 2. 引用字段
        target_field_id = config.get('targetFieldId')
        if not target_field_id:
            return False, '引用字段不能为空'

        source_fields = Field.query.filter_by(table_id=str(source_table_id)).all()
        source_fields_map = {str(f.id): f for f in source_fields}
        if str(target_field_id) not in source_fields_map:
            return False, '引用字段必须属于源数据表'

        # 3. 过滤条件
        conditions = config.get('filterConditions') or []
        if not isinstance(conditions, list):
            return False, '过滤条件格式不正确'

        if len(conditions) > 5:
            return False, '最多支持 5 个查找条件'

        # 当前表字段，用于校验 valueType=field 时的 valueFieldId
        current_fields = Field.query.filter_by(table_id=str(current_table_id)).all()
        current_field_ids = {str(f.id) for f in current_fields}

        valid_operator_values = {op.value for op in LookupFilterOperator}
        for cond in conditions:
            if not isinstance(cond, dict):
                return False, '过滤条件格式不正确'

            # 3.1 过滤条件字段
            cond_field_id = cond.get('fieldId')
            if not cond_field_id:
                return False, '过滤条件字段必须属于源数据表'
            if str(cond_field_id) not in source_fields_map:
                return False, '过滤条件字段必须属于源数据表'

            # 3.2 操作符
            operator = cond.get('operator')
            if not operator:
                return False, '过滤条件操作符不能为空'
            if operator not in valid_operator_values:
                return False, '过滤条件操作符不合法'

            # 3.3 值类型与值
            if operator in (LookupFilterOperator.IS_EMPTY.value, LookupFilterOperator.IS_NOT_EMPTY.value):
                # is_empty / is_not_empty 无需 value
                continue

            value_type = cond.get('valueType')
            if value_type not in ('field', 'custom'):
                return False, '值类型必须为 field 或 custom'

            if value_type == 'field':
                value_field_id = cond.get('valueFieldId')
                if not value_field_id or str(value_field_id) not in current_field_ids:
                    return False, '过滤条件值字段必须属于当前表'
            else:  # custom
                value_custom = cond.get('valueCustom')
                if value_custom is None or value_custom == '':
                    return False, '自定义值不能为空'

        # 4. 计算方式
        aggregation_type = config.get('aggregationType')
        if not aggregation_type:
            return False, '计算方式不能为空'
        valid_agg_values = {t.value for t in LookupAggregationType}
        if aggregation_type not in valid_agg_values:
            return False, '计算方式不合法'

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
                return False, '字段格式与计算方式不兼容'
        elif aggregation_type in (LookupAggregationType.MAX.value, LookupAggregationType.MIN.value):
            # number / currency / date（仅当源字段是日期类型时 date 才合法）
            allowed = [LookupFieldFormat.NUMBER.value, LookupFieldFormat.CURRENCY.value]
            target_field = source_fields_map.get(str(target_field_id))
            if target_field and target_field.type in _DATE_LIKE_TYPES:
                allowed.append(LookupFieldFormat.DATE.value)
            if field_format_type and field_format_type not in allowed:
                return False, '字段格式与计算方式不兼容'
        # original / distinct：fieldFormat 跟随源字段，后端不强制

        # 6. 条件连接符
        conjunction = config.get('filterConjunction', 'and')
        if conjunction not in ('and', 'or'):
            return False, '条件连接符必须为 and 或 or'

        return True, None

    # ------------------------------------------------------------------
    # 操作符映射
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 条件求值
    # ------------------------------------------------------------------
    @staticmethod
    def _evaluate_condition(
        record: Record,
        condition: Dict[str, Any],
        current_record: Optional[Record],
        source_fields_map: Dict[str, Field],
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
            if value_type == 'field':
                value_field_id = str(condition.get('valueFieldId', ''))
                if not current_record:
                    return False
                cur_values = current_record.values if isinstance(current_record.values, dict) else {}
                compare_value = cur_values.get(value_field_id)
            elif value_type == 'custom':
                compare_value = condition.get('valueCustom')

            return LookupService._compare_values(field_value, operator, compare_value)
        except Exception as e:
            current_app.logger.error(f'[LookupService] 评估过滤条件异常: {e}')
            return False

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
    def _compare_values(field_value: Any, operator: str, compare_value: Any) -> bool:
        """根据操作符比较字段值与比较值"""
        try:
            if operator == LookupFilterOperator.EQUAL.value:
                if isinstance(field_value, list):
                    return compare_value in field_value
                return field_value == compare_value

            if operator == LookupFilterOperator.NOT_EQUAL.value:
                if isinstance(field_value, list):
                    return compare_value not in field_value
                return field_value != compare_value

            if operator == LookupFilterOperator.CONTAINS.value:
                if isinstance(field_value, list):
                    return compare_value in field_value
                if isinstance(field_value, str):
                    return str(compare_value) in field_value
                if field_value is None:
                    return False
                return str(compare_value) in str(field_value)

            if operator == LookupFilterOperator.BEFORE.value:
                if not field_value or not compare_value:
                    return False
                return str(field_value) < str(compare_value)

            if operator == LookupFilterOperator.AFTER.value:
                if not field_value or not compare_value:
                    return False
                return str(field_value) > str(compare_value)
        except Exception as e:
            current_app.logger.error(f'[LookupService] 比较值异常: {e}')
            return False
        return False

    # ------------------------------------------------------------------
    # 过滤记录
    # ------------------------------------------------------------------
    @staticmethod
    def _filter_source_records(
        source_records: List[Record],
        conditions: List[Dict[str, Any]],
        conjunction: str,
        current_record: Optional[Record],
        source_fields_map: Dict[str, Field],
    ) -> List[Record]:
        """
        根据过滤条件筛选源表记录
        """
        if not conditions:
            return list(source_records)

        filtered: List[Record] = []
        for record in source_records:
            results = [
                LookupService._evaluate_condition(record, cond, current_record, source_fields_map)
                for cond in conditions
            ]
            if conjunction == 'or':
                if any(results):
                    filtered.append(record)
            else:  # and
                if all(results):
                    filtered.append(record)
        return filtered

    # ------------------------------------------------------------------
    # 聚合
    # ------------------------------------------------------------------
    @staticmethod
    def _apply_aggregation(
        values: List[Any],
        aggregation_type: str,
        source_field: Optional[Field],
    ) -> Any:
        """
        对提取出的字段值列表应用聚合计算
        """
        if aggregation_type == LookupAggregationType.ORIGINAL.value:
            return [v for v in values if v is not None and v != '']

        if aggregation_type == LookupAggregationType.DISTINCT.value:
            seen = set()
            result = []
            for v in values:
                if v is None or v == '':
                    continue
                try:
                    key = json.dumps(v, sort_keys=True, ensure_ascii=False, default=str)
                except TypeError:
                    key = str(v)
                if key not in seen:
                    seen.add(key)
                    result.append(v)
            return result

        if aggregation_type == LookupAggregationType.DISTINCT_COUNT.value:
            seen = set()
            for v in values:
                if v is None or v == '':
                    continue
                try:
                    key = json.dumps(v, sort_keys=True, ensure_ascii=False, default=str)
                except TypeError:
                    key = str(v)
                seen.add(key)
            return len(seen)

        if aggregation_type == LookupAggregationType.COUNT.value:
            return len(values)

        if aggregation_type == LookupAggregationType.SUM.value:
            total = 0
            has_number = False
            for v in values:
                if _is_number(v):
                    total += v
                    has_number = True
            return total if has_number else 0

        if aggregation_type == LookupAggregationType.AVG.value:
            nums = [v for v in values if _is_number(v)]
            if not nums:
                return None
            return sum(nums) / len(nums)

        if aggregation_type == LookupAggregationType.MAX.value:
            return LookupService._aggregate_min_max(values, source_field, take_max=True)

        if aggregation_type == LookupAggregationType.MIN.value:
            return LookupService._aggregate_min_max(values, source_field, take_max=False)

        # 兜底
        return values

    @staticmethod
    def _aggregate_min_max(values: List[Any], source_field: Optional[Field], take_max: bool) -> Any:
        """求最大/最小值：数字字段返回数字，日期字段返回日期字符串，其他类型返回字符串最值"""
        # 过滤空值
        non_empty = [v for v in values if v is not None and v != '']
        if not non_empty:
            return None

        is_date_field = source_field is not None and source_field.type in _DATE_LIKE_TYPES
        is_number_field = source_field is not None and source_field.type in _NUMBER_TYPES

        if is_number_field:
            nums = [v for v in non_empty if _is_number(v)]
            if not nums:
                return None
            return max(nums) if take_max else min(nums)

        if is_date_field:
            strs = [str(v) for v in non_empty if v]
            if not strs:
                return None
            return max(strs) if take_max else min(strs)

        # 其他类型按字符串比较
        strs = [str(v) for v in non_empty]
        return max(strs) if take_max else min(strs)

    # ------------------------------------------------------------------
    # 格式化
    # ------------------------------------------------------------------
    @staticmethod
    def _format_value(
        value: Any,
        field_format_config: Dict[str, Any],
        source_field: Optional[Field],
    ) -> Any:
        """
        根据 field_format 格式化值
        
        Args:
            value: 要格式化的值
            field_format_config: 格式配置对象 {type, precision, currencySymbol, dateFormat}
            source_field: 源字段对象
        """
        if value is None:
            return None

        # 从配置对象中提取 type 字段
        field_format = field_format_config.get('type') if isinstance(field_format_config, dict) else field_format_config

        if field_format == LookupFieldFormat.NUMBER.value:
            if not _is_number(value):
                return value
            precision = field_format_config.get('precision', 0)
            try:
                precision_int = int(precision)
            except (TypeError, ValueError):
                precision_int = 0
            return f'{value:.{precision_int}f}'

        if field_format == LookupFieldFormat.CURRENCY.value:
            if not _is_number(value):
                return value
            symbol = field_format_config.get('currencySymbol', '¥')
            precision = field_format_config.get('precision', 2)
            try:
                precision_int = int(precision)
            except (TypeError, ValueError):
                precision_int = 2
            return f'{symbol}{value:.{precision_int}f}'

        if field_format == LookupFieldFormat.DATE.value:
            if not isinstance(value, str) or not value:
                return value
            date_format = field_format_config.get('dateFormat', 'YYYY-MM-DD')
            try:
                # 尝试解析为日期
                normalized = value.replace('Z', '+00:00') if 'T' in value else value
                if 'T' in normalized:
                    dt = datetime.fromisoformat(normalized)
                else:
                    dt = datetime.strptime(normalized[:10], '%Y-%m-%d')
                # 简化映射
                format_map = {
                    'YYYY-MM-DD': '%Y-%m-%d',
                    'YYYY/MM/DD': '%Y/%m/%d',
                    'YYYY-MM': '%Y-%m',
                    'YYYY': '%Y',
                }
                py_fmt = format_map.get(date_format, '%Y-%m-%d')
                return dt.strftime(py_fmt)
            except (ValueError, TypeError):
                # 解析失败，截取前 10 位
                return value[:10]

        return value

    # ------------------------------------------------------------------
    # 主入口：实时计算查找值
    # ------------------------------------------------------------------
    @staticmethod
    def compute_lookup_value(record: Record, lookup_field: Field) -> Any:
        """
        计算单条记录的查找字段值

        Args:
            record: 当前表记录
            lookup_field: 查找字段对象（config 中包含完整配置）

        Returns:
            计算结果（数组或标量），异常时返回 None
        """
        try:
            config = lookup_field.config or {}
            source_table_id = config.get('sourceTableId')
            target_field_id = config.get('targetFieldId')
            conditions = config.get('filterConditions') or []
            conjunction = config.get('filterConjunction', 'and')
            aggregation_type = config.get('aggregationType', LookupAggregationType.ORIGINAL.value)
            # fieldFormat 可能是对象 {type, precision, ...} 或字符串
            ff = config.get('fieldFormat')
            if isinstance(ff, dict):
                field_format_config = ff
            else:
                # 兼容旧格式
                field_format_config = {
                    'type': ff,
                    'precision': config.get('precision'),
                    'currencySymbol': config.get('currencySymbol'),
                    'dateFormat': config.get('dateFormat'),
                }

            if not source_table_id or not target_field_id:
                return None

            # 加载源表所有未删除记录
            source_records = Record.query.filter_by(
                table_id=str(source_table_id), is_deleted=False
            ).all()

            # 加载源表所有字段并构建 map
            source_fields = Field.query.filter_by(table_id=str(source_table_id)).all()
            source_fields_map = {str(f.id): f for f in source_fields}

            target_field = source_fields_map.get(str(target_field_id))

            # 过滤记录
            filtered_records = LookupService._filter_source_records(
                source_records, conditions, conjunction, record, source_fields_map
            )

            # 提取引用字段值
            values = []
            for r in filtered_records:
                r_values = r.values if isinstance(r.values, dict) else {}
                values.append(r_values.get(str(target_field_id)))

            # 应用聚合
            aggregated = LookupService._apply_aggregation(values, aggregation_type, target_field)

            # 格式化：仅对单一标量值（数字/日期字符串）应用格式化，数组形式不格式化
            if not isinstance(aggregated, list):
                aggregated = LookupService._format_value(
                    aggregated, field_format_config, target_field
                )

            return aggregated
        except Exception as e:
            current_app.logger.error(
                f'[LookupService] 计算查找字段值失败 (field_id={getattr(lookup_field, "id", None)}): {e}'
            )
            return None

    # ------------------------------------------------------------------
    # 预览
    # ------------------------------------------------------------------
    @staticmethod
    def preview_lookup_value(record_id: str, config: Dict[str, Any]) -> Any:
        """
        预览查找结果：根据 record_id 加载当前记录，构造临时 Field 对象，调用 compute_lookup_value

        Args:
            record_id: 当前表记录 ID
            config: 查找字段配置

        Returns:
            计算结果
        """
        try:
            record = Record.query.get(str(record_id))
            if not record:
                return None

            # 构造临时 Field 对象
            tmp_field = Field()
            tmp_field.id = None
            tmp_field.table_id = record.table_id
            tmp_field.type = FieldType.LOOKUP.value
            tmp_field.config = config

            return LookupService.compute_lookup_value(record, tmp_field)
        except Exception as e:
            current_app.logger.error(f'[LookupService] 预览查找值失败: {e}')
            return None
