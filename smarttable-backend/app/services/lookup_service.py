# Auto-split skeleton

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

from .lookup_service_group01 import LookupServiceGroup01Mixin
from .lookup_service_group02 import LookupServiceGroup02Mixin

class LookupService(LookupServiceGroup01Mixin, LookupServiceGroup02Mixin):
    """LookupService — 主类，方法在 mixin 中"""
    
    """查找字段服务类，所有方法静态化便于调用"""
    


class RecordComputeContext:
    """
    单次 GET /tables/{id}/records 请求的计算上下文。

    负责：
    1. 按源表聚合预加载 lookup 所需数据（build_lookup_context）
    2. 为 (record_id, field_id) 做结果去重缓存 —— 同一次请求内，
       records.py 循环调 + formula_service._build_formula_context 调的
       同一个 lookup 值只算 1 次（消灭 P0-2 双算）

    用法：
        ctx = RecordComputeContext(table_id, all_fields, lookup_fields)
        for record in records:
            ctx.get_lookup_value(record, lookup_field)   # 循环内复用缓存
            FormulaService.compute_record_formulas(..., compute_ctx=ctx)  # 公式构建也走同缓存
    """

    def __init__(
        self,
        table_id: str,
        all_fields: Optional[List['Field']] = None,
        lookup_fields: Optional[List['Field']] = None,
    ) -> None:
        self.table_id = str(table_id)
        self._all_fields = all_fields
        self._lookup_fields = lookup_fields or []
        self._lookup_context: Optional[Dict[str, Any]] = None  # 懒构建
        self._value_cache: Dict[Tuple[str, str], Any] = {}     # (record_id, field_id) -> value

    @property
    def lookup_context(self) -> Optional[Dict[str, Any]]:
        if self._lookup_context is None and self._lookup_fields:
            self._lookup_context = LookupService.build_lookup_context(
                self.table_id,
                self._lookup_fields,
                current_fields=self._all_fields,
            )
        return self._lookup_context

    def get_lookup_value(self, record: 'Record', lookup_field: 'Field') -> Any:
        """带去重缓存的 lookup 计算入口"""
        record_id = str(record.id)
        field_id = str(lookup_field.id)
        cache_key = (record_id, field_id)
        if cache_key not in self._value_cache:
            self._value_cache[cache_key] = LookupService.compute_lookup_value(
                record, lookup_field, context=self.lookup_context
            )
        return self._value_cache[cache_key]


# === 反向注入：把主类注入到所有 group mixin 模块 ===
# PyArmor 加密后模块加载顺序不确定，mixin 里硬编码引用主类会 NameError
from app.services._inject import inject_main_class
inject_main_class(LookupService, 'lookup_service_group01', 'lookup_service_group02')
