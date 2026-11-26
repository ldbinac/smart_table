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

# Cross-import: 装饰器和辅助函数分布在其他子文件
from .formula_service_evaluator import FormulaEvaluator
from .formula_service_helpers import _to_number, _flatten_values, _flatten_numbers, _CURRENCY_CHARS
from .formula_service_errors import FormulaError

@FormulaEvaluator.register('IF')
def fn_if(args: List[Any]) -> Any:
    """条件判断"""
    condition = args[0]
    true_val = args[1] if len(args) > 1 else None
    false_val = args[2] if len(args) > 2 else None
    
    if condition is None:
        return false_val
    return true_val if condition else false_val

@FormulaEvaluator.register('IFS')
def fn_ifs(args: List[Any]) -> Any:
    """多条件判断

    参数个数为奇数时，最后一个参数视为「默认兜底值」，
    即当所有条件/值对都不满足时返回该默认值（与前端引擎保持一致）。
    """
    has_default = len(args) % 2 != 0
    pair_count = len(args) - 1 if has_default else len(args)

    for i in range(0, pair_count, 2):
        condition = args[i]
        value = args[i + 1]
        if condition is not None and condition:
            return value

    if has_default:
        return args[-1]

    return None

@FormulaEvaluator.register('SWITCH')
def fn_switch(args: List[Any]) -> Any:
    """多条件匹配"""
    if len(args) < 3:
        raise FormulaError("SWITCH 至少需要 3 个参数")
    
    expression = args[0]
    default_value = None
    
    i = 1
    while i < len(args) - 1:
        if args[i] in ('DEFAULT', 'default', '__DEFAULT__'):
            default_value = args[i + 1]
            i += 2
            continue
        
        if expression == args[i]:
            return args[i + 1]
        i += 2
    
    return default_value

@FormulaEvaluator.register('AND')
def fn_and(args: List[Any]) -> bool:
    """逻辑与"""
    for val in args:
        if val is None or not val:
            return False
    return True

@FormulaEvaluator.register('OR')
def fn_or(args: List[Any]) -> bool:
    """逻辑或"""
    for val in args:
        if val is not None and val:
            return True
    return False

@FormulaEvaluator.register('NOT')
def fn_not(args: List[Any]) -> bool:
    """逻辑非"""
    val = args[0]
    return not val if val is not None else None

@FormulaEvaluator.register('XOR')
def fn_xor(args: List[Any]) -> bool:
    """异或"""
    if len(args) < 2:
        return not args[0] if args[0] is not None else None
    result = bool(args[0]) if args[0] is not None else False
    for val in args[1:]:
        result ^= bool(val) if val is not None else False
    return result

@FormulaEvaluator.register('ISBLANK')
def fn_isblank(args: List[Any]) -> bool:
    """判断是否为空"""
    val = args[0]
    return val is None or val == '' or (isinstance(val, list) and len(val) == 0)

@FormulaEvaluator.register('ISERROR')
def fn_iserror(args: List[Any]) -> bool:
    """判断是否为错误值"""
    val = args[0]
    return isinstance(val, (FormulaError, Exception))

@FormulaEvaluator.register('ISNUMBER')
def fn_isnumber(args: List[Any]) -> bool:
    """判断是否为数字"""
    val = args[0]
    if val is None:
        return False
    return isinstance(val, (int, float)) and not isinstance(val, bool)

@FormulaEvaluator.register('ISTEXT')
def fn_istext(args: List[Any]) -> bool:
    """判断是否为文本"""
    val = args[0]
    return isinstance(val, str)

@FormulaEvaluator.register('ISDATE')
def fn_isdate(args: List[Any]) -> bool:
    """判断是否为日期"""
    val = args[0]
    if isinstance(val, (datetime, date)):
        return True
    if isinstance(val, str):
        for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'):
            try:
                datetime.strptime(val, fmt)
                return True
            except ValueError:
                continue
    return False

@FormulaEvaluator.register('BLANK')
def fn_blank(args: List[Any]) -> None:
    """返回空值"""
    return None

@FormulaEvaluator.register('NA')
def fn_na(args: List[Any]) -> FormulaError:
    """返回 N/A 错误"""
    return FormulaError("#N/A")

@FormulaEvaluator.register('ERROR')
def fn_error(args: List[Any]) -> FormulaError:
    """返回自定义错误"""
    msg = str(args[0]) if args else "ERROR"
    return FormulaError(msg)

@FormulaEvaluator.register('COUNT')
def fn_count(args: List[Any]) -> int:
    """计数（仅数字，支持整列数组参数，字符串数字计入）"""
    return len(_flatten_numbers(args, include_bool=False))

@FormulaEvaluator.register('COUNTA')
def fn_counta(args: List[Any]) -> int:
    """计数（非空，支持整列数组参数）"""
    count = 0
    for val in _flatten_values(args):
        if val is not None and val != '':
            count += 1
    return count

def _match_criteria(value: Any, criteria: Any) -> bool:
    """根据条件字符串判断值是否匹配（支持 >, <, >=, <=, <> 及等于）"""
    if criteria is None:
        return False
    crit = str(criteria)
    # 数值条件先归一化：数字字段可能以字符串形态存储（'1.3'、'¥1,234.5'）
    if crit.startswith('>='):
        n = _to_number(value)
        return n is not None and n >= float(crit[2:])
    if crit.startswith('<='):
        n = _to_number(value)
        return n is not None and n <= float(crit[2:])
    if crit.startswith('<>'):
        return str(value) != crit[2:]
    if crit.startswith('>'):
        n = _to_number(value)
        return n is not None and n > float(crit[1:])
    if crit.startswith('<'):
        n = _to_number(value)
        return n is not None and n < float(crit[1:])
    if crit.startswith('='):
        return str(value) == crit[1:]
    return str(value) == crit

@FormulaEvaluator.register('FILTER')
def fn_filter(args: List[Any]) -> List[Any]:
    """条件筛选（条件含 CurrentValue 时走惰性求值分支）"""
    if len(args) < 2:
        raise FormulaError("FILTER 需要至少两个参数")
    values = args[0] if isinstance(args[0], list) else [args[0]]
    return [v for v in values if _match_criteria(v, args[1])]

@FormulaEvaluator.register('COUNTIF')
def fn_countif(args: List[Any]) -> int:
    """条件计数"""
    if len(args) < 2:
        raise FormulaError("COUNTIF 需要至少两个参数")
    values = args[0] if isinstance(args[0], list) else [args[0]]
    criteria = args[1]
    return sum(1 for v in values if _match_criteria(v, criteria))

@FormulaEvaluator.register('SUMIF')
def fn_sumif(args: List[Any]) -> Optional[float]:
    """条件求和"""
    if len(args) < 2:
        raise FormulaError("SUMIF 需要至少两个参数")
    values = args[0] if isinstance(args[0], list) else [args[0]]
    criteria = args[1]
    sum_range = args[2] if len(args) > 2 else values
    if not isinstance(sum_range, list):
        sum_range = [sum_range]

    total = 0.0
    matched = False
    for i, v in enumerate(values):
        if _match_criteria(v, criteria):
            matched = True
            if i < len(sum_range):
                # 数值归一化：数字字段可能以字符串形态存储
                sv = _to_number(sum_range[i])
                if sv is not None:
                    total += sv
    return total if matched else None

@FormulaEvaluator.register('AVERAGEIF')
def fn_averageif(args: List[Any]) -> Optional[float]:
    """条件平均值"""
    if len(args) < 2:
        raise FormulaError("AVERAGEIF 需要至少两个参数")
    values = args[0] if isinstance(args[0], list) else [args[0]]
    criteria = args[1]
    avg_range = args[2] if len(args) > 2 else values
    if not isinstance(avg_range, list):
        avg_range = [avg_range]

    total = 0.0
    count = 0
    for i, v in enumerate(values):
        if _match_criteria(v, criteria):
            if i < len(avg_range):
                # 数值归一化：数字字段可能以字符串形态存储
                av = _to_number(avg_range[i])
                if av is not None:
                    total += av
                    count += 1
    return total / count if count > 0 else None

@FormulaEvaluator.register('IFERROR')
def fn_iferror(args: List[Any]) -> Any:
    """错误处理（实际错误捕获在 _eval_function 中处理）"""
    if len(args) < 2:
        raise FormulaError("IFERROR 需要两个参数")
    # 正常执行到此说明第一个参数未抛出异常
    return args[0]

@FormulaEvaluator.register('COUNTBLANK')
def fn_countblank(args: List[Any]) -> int:
    """计数（空值）"""
    count = 0
    for val in args:
        if val is None or val == '':
            count += 1
    return count

@FormulaEvaluator.register('STDEV')
def fn_stdev(args: List[Any]) -> Optional[float]:
    """标准差"""
    values = _flatten_numbers(args)
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)

@FormulaEvaluator.register('VAR')
def fn_var(args: List[Any]) -> Optional[float]:
    """方差"""
    values = _flatten_numbers(args)
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / (len(values) - 1)

@FormulaEvaluator.register('MEDIAN')
def fn_median(args: List[Any]) -> Optional[float]:
    """中位数"""
    values = sorted(_flatten_numbers(args))
    if not values:
        return None
    n = len(values)
    mid = n // 2
    if n % 2 == 1:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2

@FormulaEvaluator.register('MODE')
def fn_mode(args: List[Any]) -> Optional[float]:
    """众数"""
    values = _flatten_numbers(args)
    if not values:
        return None

    counts = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1

    max_count = max(counts.values())
    modes = [k for k, v in counts.items() if v == max_count]

    return modes[0] if len(modes) == 1 else None

@FormulaEvaluator.register('RANK')
def fn_rank(args: List[Any]) -> int:
    """排名（值越小排名越靠前）"""
    value = _to_number(args[0]) if args else None
    all_values = _flatten_numbers(args[1:] if len(args) > 1 else [])

    if value is None or not all_values:
        return None

    lower_or_equal = sum(1 for v in all_values if v < value)
    return lower_or_equal + 1

@FormulaEvaluator.register('UNIQUE')
def fn_unique(args: List[Any]) -> List[Any]:
    """去重（展平嵌套数组后去重，与前端 flattenValues 语义一致）"""
    seen = set()
    result = []
    for val in _flatten_values(args):
        key = json.dumps(val, sort_keys=True, default=str) if not isinstance(val, (str, int, float, bool, type(None))) else val
        if key not in seen:
            seen.add(key)
            result.append(val)
    return result
