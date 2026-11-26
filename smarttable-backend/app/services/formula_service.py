# Auto-split skeleton

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

from .formula_service_errors import FormulaError
from .formula_service_parser import FormulaParser, _ASTParser
from .formula_service_evaluator import FormulaEvaluator
from .formula_service_helpers import _flatten_values, _CURRENCY_CHARS, _to_number, _flatten_numbers
from .formula_service_functions_part1 import fn_abs, fn_round, fn_ceiling, fn_floor, fn_power, fn_sqrt, fn_mod, fn_sum, fn_avg, fn_max, fn_min, fn_ln, fn_log, fn_exp, fn_pi, fn_e, fn_rand, fn_randbetween, fn_concat, fn_upper, fn_lower, fn_len, fn_trim, fn_left, fn_right, fn_mid, fn_replace, fn_substitute, fn_find, fn_rept, fn_text, fn_value, fn_now, fn_today, fn_year, fn_month, fn_day, fn_hour, fn_minute, fn_second, fn_weekday, fn_dateadd, _parse_date_value, fn_datediff, fn_datetime_format, fn_fromunixtime, fn_unixtimestamp
from .formula_service_functions_part2 import fn_if, fn_ifs, fn_switch, fn_and, fn_or, fn_not, fn_xor, fn_isblank, fn_iserror, fn_isnumber, fn_istext, fn_isdate, fn_blank, fn_na, fn_error, fn_count, fn_counta, _match_criteria, fn_filter, fn_countif, fn_sumif, fn_averageif, fn_iferror, fn_countblank, fn_stdev, fn_var, fn_median, fn_mode, fn_rank, fn_unique
from .formula_service_group01 import FormulaServiceGroup01Mixin
from .formula_service_group02 import FormulaServiceGroup02Mixin

class FormulaService(FormulaServiceGroup01Mixin, FormulaServiceGroup02Mixin):
    """FormulaService — 主类"""

    """
    公式计算服务类（主入口）
    
    提供记录级别的公式计算、批量重算、缓存等功能
    """

    _parser = FormulaParser()

    _COLUMN_REF_RE = re.compile(r'\[([^\[\]{}]+)\]\s*\.\s*\[([^\[\]{}]+)\]')

    _TABLE_CONTEXT_CACHE: Dict[str, Tuple[float, Optional[str], Optional[Dict[str, Dict[str, List[Any]]]]]] = {}

    _TABLE_CONTEXT_TTL_SECONDS: float = 10.0



# === 反向注入：把主类注入到所有 group mixin 模块 ===
from app.services._inject import inject_main_class
inject_main_class(FormulaService, 'formula_service_group01', 'formula_service_group02', 'field_service_group03')
