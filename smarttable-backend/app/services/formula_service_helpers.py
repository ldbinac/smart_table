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

def _flatten_values(args: List[Any]) -> List[Any]:
    """递归展开嵌套数组（整列引用 [表].[字段] 与函数返回的数组作为参数传递）"""
    result: List[Any] = []
    for v in args:
        if isinstance(v, list):
            result.extend(_flatten_values(v))
        else:
            result.append(v)
    return result

_CURRENCY_CHARS = '¥$€£, '

def _to_number(v: Any) -> Optional[float]:
    """数值归一化：数字原样；字符串数字（剥离货币符号/千分位逗号）转 float；其余跳过。

    数字字段历史数据可能以字符串形态存储（如 '1.3'、'1,234.5'），聚合时须归一化。
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        s = v.strip().strip(_CURRENCY_CHARS).replace(',', '')
        try:
            return float(s)
        except ValueError:
            return None
    return None

def _flatten_numbers(args: List[Any], include_bool: bool = True) -> List[float]:
    """展开嵌套数组并归一化为数值列表；无法转数字的元素（含空值）跳过"""
    result: List[float] = []
    for v in _flatten_values(args):
        if isinstance(v, bool) and not include_bool:
            continue
        n = _to_number(v)
        if n is not None:
            result.append(n)
    return result
