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

class LookupServiceGroup02Mixin:
    """Mixin auto-split"""
    
    """查找字段服务类，所有方法静态化便于调用"""
    
    
    @staticmethod
    def _compare_values(
        field_value: Any,
        operator: str,
        compare_value: Any,
        is_link_field: bool = False,
        source_field: Optional[Field] = None,
        resolve_cache: Optional[Dict[str, List[str]]] = None,
        source_candidates: Optional[set] = None,
        compare_candidates: Optional[set] = None,
    ) -> bool:
        """根据操作符比较字段值与比较值"""
        try:
            if is_link_field:
                return LookupService._compare_link_values(
                    field_value, operator, compare_value, source_field, resolve_cache
                )
    
            # 选择类字段（单选/多选）与文本值之间的匹配
            if source_candidates is not None or compare_candidates is not None:
                return LookupService._compare_candidates(
                    source_candidates,
                    compare_candidates,
                    field_value,
                    compare_value,
                    operator,
                )
    
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
    
    @staticmethod
    def _filter_source_records(
        source_records: List[Record],
        conditions: List[Dict[str, Any]],
        conjunction: str,
        current_record: Optional[Record],
        source_fields_map: Dict[str, Field],
        current_fields_map: Optional[Dict[str, Field]] = None,
    ) -> List[Record]:
        """
        根据过滤条件筛选源表记录
        """
        if not conditions:
            return list(source_records)
    
        # 单次过滤内共享的显示值 → 记录 ID 解析缓存
        resolve_cache: Dict[str, List[str]] = {}
        filtered: List[Record] = []
        for record in source_records:
            results = [
                LookupService._evaluate_condition(
                    record, cond, current_record, source_fields_map, resolve_cache,
                    current_fields_map,
                )
                for cond in conditions
            ]
            if conjunction == 'or':
                if any(results):
                    filtered.append(record)
            else:  # and
                if all(results):
                    filtered.append(record)
        return filtered
    
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
            total = 0.0
            has_number = False
            for v in values:
                num = _to_number(v)
                if num is None:
                    continue
                total += num
                has_number = True
            return _normalize_number(total) if has_number else 0
    
        if aggregation_type == LookupAggregationType.AVG.value:
            nums = [n for n in (_to_number(v) for v in values) if n is not None]
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
    def _parse_date_value(value: Any) -> Optional[float]:
        """
        把日期值解析为可比较的时间戳（秒），无法解析时返回 None。
    
        支持：毫秒/秒级时间戳（数字或纯数字字符串）、ISO 字符串、YYYY-MM-DD 字符串。
        """
        if value is None or isinstance(value, bool):
            return None
    
        # 数字时间戳：大于 1e11 视为毫秒
        if isinstance(value, (int, float)):
            return float(value) / 1000 if abs(value) > 1e11 else float(value)
    
        if isinstance(value, str):
            s = value.strip()
            if not s:
                return None
            if s.isdigit() and len(s) >= 9:
                ts = int(s)
                return ts / 1000 if ts > 1e11 else float(ts)
            try:
                normalized = s.replace('Z', '+00:00') if 'T' in s else s
                if 'T' in normalized:
                    dt = datetime.fromisoformat(normalized)
                else:
                    dt = datetime.strptime(normalized[:10], '%Y-%m-%d')
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.timestamp()
            except (ValueError, TypeError):
                return None
    
        return None
    
    @staticmethod
    def _aggregate_min_max(values: List[Any], source_field: Optional[Field], take_max: bool) -> Any:
        """
        求最大/最小值。
    
        比较策略按优先级：
        1. 所有非空值都能转为数字 → 按数值比较（返回数字）
        2. 源字段为日期类型 → 按时间戳比较（返回原始值）
        3. 其他 → 按字符串字典序比较
        """
        # 过滤空值
        non_empty = [v for v in values if v is not None and v != '']
        if not non_empty:
            return None
    
        # 1) 数值比较：不依赖源字段类型，只要值本身是（或可转为）数字即可，
        #    避免 "9" > "100" 这类字符串字典序误判
        nums = [_to_number(v) for v in non_empty]
        if all(n is not None for n in nums):
            best = max(nums) if take_max else min(nums)
            return _normalize_number(best)
    
        # 2) 日期比较：统一转为时间戳后再比较，返回值保持原始形态
        is_date_field = source_field is not None and source_field.type in _DATE_LIKE_TYPES
        if is_date_field:
            parsed = [(LookupService._parse_date_value(v), v) for v in non_empty]
            parsed = [(ts, v) for ts, v in parsed if ts is not None]
            if parsed:
                best_ts, best_value = (max(parsed, key=lambda x: x[0]) if take_max
                                       else min(parsed, key=lambda x: x[0]))
                return best_value
    
        # 3) 其他类型按字符串比较
        strs = [str(v) for v in non_empty]
        return max(strs) if take_max else min(strs)
    
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
            num = _to_number(value)
            if num is None:
                return value
            precision_int = max(0, _safe_int(field_format_config.get('precision'), 0))
            return f'{num:.{precision_int}f}'
    
        if field_format == LookupFieldFormat.CURRENCY.value:
            num = _to_number(value)
            if num is None:
                return value
            symbol = field_format_config.get('currencySymbol', '¥')
            precision_int = max(0, _safe_int(field_format_config.get('precision'), 2))
            return f'{symbol}{num:.{precision_int}f}'
    
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
    
    @classmethod
    def build_lookup_context(
        cls,
        table_id: str,
        lookup_fields: List['Field'],
        current_fields: Optional[List['Field']] = None,
    ) -> Dict[str, Any]:
        """
        按源表聚合预加载 lookup 计算所需的全部数据，返回可在请求级复用的上下文。
    
        同一源表只会查一次 DB；循环内的 compute_lookup_value 直接命中缓存，
        把原本 N×(1+3L) 的 SQL 降为 2 + 涉及的源表数。
    
        Args:
            table_id: 当前表 ID
            lookup_fields: 当前表的所有 lookup 字段列表
            current_fields: 当前表字段列表（可选，传入避免重复查询）
    
        Returns:
            dict: {
                '__sources__': {source_table_id: {'records': [...], 'fields_map': {...}}},
                '__current_fields_map__': {field_id: Field},
            }
        """
        source_cache: Dict[str, Dict[str, Any]] = {}
        # 收集所有涉及的源表
        source_table_ids = set()
        for lf in lookup_fields:
            sid = (lf.config or {}).get('sourceTableId')
            if sid:
                source_table_ids.add(str(sid))
    
        # 每个源表只加载一次
        for sid in source_table_ids:
            recs = Record.query.filter_by(
                table_id=sid, is_deleted=False
            ).all()
            fs = Field.query.filter_by(table_id=sid).all()
            source_cache[sid] = {
                'records': recs,
                'fields_map': {str(f.id): f for f in fs},
            }
    
        # 当前表字段（如果调用方没预取）
        if current_fields is None:
            current_fields = Field.query.filter_by(table_id=table_id).all()
    
        return {
            '__sources__': source_cache,
            '__current_fields_map__': {str(f.id): f for f in current_fields},
        }
    
    @staticmethod
    def compute_lookup_value(
        record: Record,
        lookup_field: Field,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        计算单条记录的查找字段值
    
        Args:
            record: 当前表记录
            lookup_field: 查找字段对象（config 中包含完整配置）
            context: 可选的批量预加载上下文（由 build_lookup_context 生成），
                     传入时复用预加载数据避免 N+1；为 None 时回退旧逻辑（兼容其他调用点）
    
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
    
            # ===== 从 context 取数据；无 context 时回退逐条查询 =====
            if context is not None:
                source_data = context.get('__sources__', {}).get(str(source_table_id))
                if source_data is None:
                    # context 里没有这个源表 → 回退单表加载
                    source_records = Record.query.filter_by(
                        table_id=str(source_table_id), is_deleted=False
                    ).all()
                    source_fields = Field.query.filter_by(table_id=str(source_table_id)).all()
                    source_fields_map = {str(f.id): f for f in source_fields}
                else:
                    source_records = source_data['records']
                    source_fields_map = source_data['fields_map']
                current_fields_map = context.get('__current_fields_map__', {})
            else:
                # 回退路径：逐条查询（保持与旧逻辑完全一致）
                source_records = Record.query.filter_by(
                    table_id=str(source_table_id), is_deleted=False
                ).all()
                source_fields = Field.query.filter_by(table_id=str(source_table_id)).all()
                source_fields_map = {str(f.id): f for f in source_fields}
                current_fields = Field.query.filter_by(table_id=str(record.table_id)).all()
                current_fields_map = {str(f.id): f for f in current_fields}
    
            target_field = source_fields_map.get(str(target_field_id))
    
            # 过滤记录
            filtered_records = LookupService._filter_source_records(
                source_records, conditions, conjunction, record, source_fields_map,
                current_fields_map,
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
    
