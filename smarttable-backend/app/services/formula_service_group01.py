"""
公式计算服务模块
提供完整的公式引擎功能，包括：
- 公式解析与求值（29.1）
- 数学函数：SUM/AVG/MAX/MIN/ROUND/ABS 等（29.2）
- 文本函数：CONCAT/UPPER/LOWER/TRIM/REPLACE 等（29.3）
- 日期函数：YEAR/MONTH/DAY/NOW/TODAY/DATEDIFF 等（29.4）
- 逻辑函数：IF/AND/OR/NOT/ISBLANK/IFS/SWITCH 等（29.5）
- 统计函数：COUNT/COUNTA/COUNTIF/SUMIF/AVERAGEIF 等（29.6）
- 记录保存时自动计算公式值（30.1）
- 批量重新计算公式值（30.2）
- 公式计算结果缓存（30.3）
"""

import re

import math

import json

import hashlib

import time

from datetime import datetime, date, timedelta, timezone

from typing import Any, Dict, List, Optional, Set, Tuple, Union

from functools import lru_cache

from app.extensions import db, cache

from app.models.field import Field, FieldType

# Cross-import: 其他子模块的类/函数
from .formula_service_errors import FormulaError
from .formula_service_parser import FormulaParser, _ASTParser
from .formula_service_evaluator import FormulaEvaluator
from .formula_service_helpers import *
from .formula_service_functions_part1 import *
from .formula_service_functions_part2 import *

class FormulaServiceGroup01Mixin:
    """group01 mixin"""

    _parser = FormulaParser()

    _COLUMN_REF_RE = re.compile(r'\[([^\[\]{}]+)\]\s*\.\s*\[([^\[\]{}]+)\]')

    _TABLE_CONTEXT_CACHE: Dict[str, Tuple[float, Optional[str], Optional[Dict[str, Dict[str, List[Any]]]]]] = {}

    _TABLE_CONTEXT_TTL_SECONDS: float = 10.0


    @classmethod
    def evaluate_formula(
        cls,
        formula: str,
        context: Dict[str, Any],
        use_cache: bool = True,
        table_context: Optional[Dict[str, Dict[str, List[Any]]]] = None
    ) -> Any:
        """
        计算单个公式表达式（任务 29.1）

        Args:
            formula: 公式字符串，如 "{price} * {quantity}"
            context: 字段上下文，如 {"price": 100, "quantity": 5}
            use_cache: 是否使用缓存
            table_context: 整列引用数据上下文 {表名小写: {字段名: [整列值]}}；
                          含 [表].[字段] 引用的公式必须提供，否则整列引用求值为 None

        Returns:
            计算结果

        Raises:
            FormulaError: 公式语法或执行错误
        """
        if not formula or not formula.strip():
            return None

        # 含整列引用的公式结果依赖全表数据，禁用结果缓存避免脏数据
        has_column_ref = bool(cls._COLUMN_REF_RE.search(formula))

        cache_key = None
        if use_cache and not has_column_ref:
            cache_key = cls._build_cache_key(formula, context)
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        try:
            ast = cls._parser.parse(formula)
            evaluator = FormulaEvaluator(context, table_context=table_context)
            result = evaluator.evaluate(ast)

            if cache_key:
                cache.set(cache_key, result, timeout=300)

            return result

        except FormulaError:
            raise
        except Exception as e:
            raise FormulaError(f"公式计算失败: {str(e)}")

    @classmethod
    def build_table_context_for_fields(
        cls,
        table_id: str,
        formula_fields: List[Field]
    ) -> Optional[Dict[str, Dict[str, List[Any]]]]:
        """
        按需构建整列引用数据上下文：仅当公式字段中存在 [表].[字段] 引用时查询全表

        构建结果带 TTL 进程内缓存（P3）：整列数据为全表快照，记录/字段/表变更时
        通过 invalidate_table_context_cache 主动失效；TTL 兜底防止漏挂钩导致脏数据。

        Args:
            table_id: 表格 ID
            formula_fields: 公式字段列表

        Returns:
            {表名小写: {字段名: [整列值]}}；无整列引用时返回 None（零开销）
        """
        table_id = str(table_id)
        has_column_ref = any(
            cls._COLUMN_REF_RE.search(
                (f.config or {}).get('formula', '')
                or (f.options or {}).get('formula', '')
            )
            for f in formula_fields
        )
        if not has_column_ref:
            return None

        now = time.monotonic()
        cached = cls._TABLE_CONTEXT_CACHE.get(table_id)
        if cached and cached[0] > now:
            return cached[2]

        context = cls._build_table_context(table_id)

        base_id: Optional[str] = None
        try:
            from app.models.table import Table
            table = Table.query.get(table_id)
            if table:
                base_id = str(table.base_id)
        except Exception:
            pass
        cls._TABLE_CONTEXT_CACHE[table_id] = (
            now + cls._TABLE_CONTEXT_TTL_SECONDS, base_id, context
        )
        return context

    @classmethod
    def invalidate_table_context_cache(
        cls,
        table_id: Optional[str] = None,
        base_id: Optional[str] = None
    ) -> None:
        """
        失效整列数据上下文缓存。

        记录/字段/表变更后必须调用：给定 table_id 时清除该表自身及同 Base 全部
        缓存条目（其他表的上下文可能整列引用了本表数据）；给定 base_id 时按 Base 清。
        """
        target_base: Optional[str] = str(base_id) if base_id else None
        if table_id and not target_base:
            try:
                from app.models.table import Table
                table = Table.query.get(str(table_id))
                target_base = str(table.base_id) if table else None
            except Exception:
                target_base = None

        keys_to_delete: List[str] = []
        for key, (_expiry, cached_base, _ctx) in cls._TABLE_CONTEXT_CACHE.items():
            if target_base and cached_base and str(cached_base) == target_base:
                keys_to_delete.append(key)
            elif table_id and key == str(table_id):
                keys_to_delete.append(key)
        for key in keys_to_delete:
            cls._TABLE_CONTEXT_CACHE.pop(key, None)

    @classmethod
    def _build_table_context(
        cls,
        table_id: str
    ) -> Optional[Dict[str, Dict[str, List[Any]]]]:
        """
        查询本表全量记录并构建整列数据上下文（P2 支持同 Base 跨表引用）

        构建顺序：
        1. 本表自身（key 为本表表名小写）
        2. 扫描本表所有公式中 [表].[字段] 引用的目标表名，
           在同一 Base 内按表名匹配（大小写不敏感），命中则加载其全表列数据

        未命中的目标表（不存在/跨 Base/引用自身之外的表名）不注入上下文，
        求值时整列引用退化为 None，与前端行为对齐。

        Returns:
            {表名小写: {字段名: [按记录顺序的整列值]}}
        """
        from app.models.table import Table

        table = Table.query.get(table_id)
        if not table:
            return None

        fields = Field.query.filter_by(table_id=table_id).all()
        records = cls._get_table_records(table_id)
        context: Dict[str, Dict[str, List[Any]]] = {
            str(table.name).lower(): cls._build_columns(fields, records)
        }

        # P2：同 Base 跨表引用——扫描公式中引用的目标表名并加载其列数据
        target_names = cls._extract_column_ref_table_names(fields)
        target_names.discard(str(table.name).lower())
        if target_names:
            base_tables = Table.query.filter_by(base_id=table.base_id).all()
            for candidate in base_tables:
                name_key = str(candidate.name).lower()
                if name_key not in target_names or name_key in context:
                    continue
                t_fields = Field.query.filter_by(table_id=candidate.id).all()
                t_records = cls._get_table_records(candidate.id)
                context[name_key] = cls._build_columns(t_fields, t_records)

        return context

    @staticmethod
    def _get_table_records(table_id: str) -> List['Record']:
        from app.models.record import Record

        return Record.query.filter_by(table_id=table_id, is_deleted=False).all()

    @staticmethod
    def _build_columns(
        fields: List['Field'],
        records: List['Record'],
    ) -> Dict[str, List[Any]]:
        """
        由字段列表与全表记录构建列数据 {字段名: [整列值]}

        记录 values 以 field_id 为键，须先建立字段名 → field_id 映射再取值；
        公式/查找等计算型字段的值不落 values，整列取值为 None（引用时退化为 0/空）。
        """
        field_key_by_name = {f.name: str(f.id) for f in fields}
        columns: Dict[str, List[Any]] = {f.name: [] for f in fields}
        for record in records:
            values = record.values or {}
            for f in fields:
                columns[f.name].append(values.get(field_key_by_name[f.name]))
        return columns

    @staticmethod
    def _datetime_to_millis(dt: Optional[datetime]) -> Optional[int]:
        """datetime → 毫秒时间戳（与前端系统字段取值形态一致）；naive 视为 UTC"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)

    @classmethod
    def _build_formula_context(
        cls,
        all_fields: List['Field'],
        values: Dict[str, Any],
        record: Optional[Any] = None,
        compute_ctx: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        构建以字段名为 key 的公式上下文（公式引擎用字段名引用）

        record.values 以 field_id 为键，须映射为字段名；系统维护字段
        （创建人/创建时间/更新人/更新时间/最后修改人）的值不落 values，
        从记录元数据补充注入，与前端取值形态一致：
        用户字段为用户 ID 字符串，时间字段为毫秒时间戳。

        compute_ctx: 可选 RecordComputeContext（B1+B2 联合优化）。传入后，
        lookup 值从 ctx.get_lookup_value 取（与 records.py 循环共享预加载
        + 去重缓存），不再重新执行 LookupService.compute_lookup_value。
        """
        field_id_to_name = {str(f.id): f.name for f in all_fields}

        context: Dict[str, Any] = {}
        for field_id, value in (values or {}).items():
            field_name = field_id_to_name.get(str(field_id))
            if field_name:
                context[field_name] = value

        if record is None:
            return context

        # 系统维护字段（创建人/创建时间/更新人/更新时间/最后修改人）从元数据注入
        meta_by_type = {
            FieldType.CREATED_BY.value: str(record.created_by) if record.created_by else None,
            FieldType.UPDATED_BY.value: str(record.updated_by) if record.updated_by else None,
            FieldType.LAST_MODIFIED_BY.value: str(record.updated_by) if record.updated_by else None,
            FieldType.CREATED_TIME.value: cls._datetime_to_millis(record.created_at),
            FieldType.UPDATED_TIME.value: cls._datetime_to_millis(record.updated_at),
        }
        for f in all_fields:
            if f.type in meta_by_type:
                context[f.name] = meta_by_type[f.type]

        # 查找字段值不落 record.values（实时计算），公式引用时现算注入：
        # 先求查找字段结果再计算公式，保证 {查找字段} 参与运算取到真实值
        # B2 优化：有 compute_ctx 时走 ctx 共享缓存，不再重复查 DB（消灭 P0-2 双算）
        from app.services.lookup_service import LookupService

        for f in all_fields:
            if f.type == FieldType.LOOKUP.value:
                try:
                    if compute_ctx is not None:
                        context[f.name] = compute_ctx.get_lookup_value(record, f)
                    else:
                        context[f.name] = LookupService.compute_lookup_value(record, f)
                except Exception:
                    context[f.name] = None

        return context

    @classmethod
    def _extract_column_ref_table_names(cls, fields: List['Field']) -> Set[str]:
        """扫描公式字段中 [表].[字段] 引用的目标表名集合（表名小写）"""
        names: Set[str] = set()
        for f in fields:
            formula = (f.config or {}).get('formula', '') or (f.options or {}).get('formula', '')
            if not formula:
                continue
            for m in cls._COLUMN_REF_RE.finditer(formula):
                names.add(str(m.group(1)).strip().lower())
        return names
