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

@FormulaEvaluator.register('ABS')
def fn_abs(args: List[Any]) -> Union[int, float]:
    """绝对值（字符串数字自动归一化，数字字段可能存字符串形态脏数据）"""
    n = _to_number(args[0])
    return abs(n) if n is not None else None

@FormulaEvaluator.register('ROUND')
def fn_round(args: List[Any]) -> float:
    """四舍五入（参数自动数值归一化）"""
    val = _to_number(args[0])
    digits = _to_number(args[1]) if len(args) > 1 else 0
    digits = int(digits) if digits is not None else 0
    return round(val, digits) if val is not None else None

@FormulaEvaluator.register('CEILING')
def fn_ceiling(args: List[Any]) -> int:
    """向上取整（参数自动数值归一化）"""
    val = _to_number(args[0])
    return math.ceil(val) if val is not None else None

@FormulaEvaluator.register('FLOOR')
def fn_floor(args: List[Any]) -> int:
    """向下取整（参数自动数值归一化）"""
    val = _to_number(args[0])
    return math.floor(val) if val is not None else None

@FormulaEvaluator.register('POWER')
def fn_power(args: List[Any]) -> float:
    """幂运算（参数自动数值归一化）"""
    base = _to_number(args[0])
    exp = _to_number(args[1])
    return base ** exp if base is not None and exp is not None else None

@FormulaEvaluator.register('SQRT')
def fn_sqrt(args: List[Any]) -> float:
    """平方根（参数自动数值归一化）"""
    val = _to_number(args[0])
    if val is None:
        return None
    if val < 0:
        raise FormulaError("SQRT 的参数必须非负")
    return math.sqrt(val)

@FormulaEvaluator.register('MOD')
def fn_mod(args: List[Any]) -> float:
    """取模（参数自动数值归一化）"""
    a = _to_number(args[0])
    b = _to_number(args[1])
    if a is None or b is None:
        return None
    if b == 0:
        raise FormulaError("MOD 除数不能为零")
    return a % b

@FormulaEvaluator.register('SUM')
def fn_sum(args: List[Any]) -> Optional[float]:
    """求和（支持整列数组参数，字符串数字自动归一化）"""
    values = _flatten_numbers(args)
    return sum(values) if values else 0

@FormulaEvaluator.register('AVG')
def fn_avg(args: List[Any]) -> Optional[float]:
    """平均值（支持整列数组参数，字符串数字自动归一化）"""
    values = _flatten_numbers(args)
    return sum(values) / len(values) if values else None

@FormulaEvaluator.register('MAX')
def fn_max(args: List[Any]) -> Any:
    """最大值（支持整列数组参数，字符串数字自动归一化）"""
    values = _flatten_numbers(args)
    return max(values) if values else None

@FormulaEvaluator.register('MIN')
def fn_min(args: List[Any]) -> Any:
    """最小值（支持整列数组参数，字符串数字自动归一化）"""
    values = _flatten_numbers(args)
    return min(values) if values else None

@FormulaEvaluator.register('LN')
def fn_ln(args: List[Any]) -> float:
    """自然对数（参数自动数值归一化）"""
    val = _to_number(args[0])
    if val is None:
        return None
    if val <= 0:
        raise FormulaError("LN 参数必须大于零")
    return math.log(val)

@FormulaEvaluator.register('LOG')
def fn_log(args: List[Any]) -> float:
    """对数（参数自动数值归一化）"""
    val = _to_number(args[0])
    base = _to_number(args[1]) if len(args) > 1 and args[1] is not None else 10
    base = base if base is not None else 10
    if val is None:
        return None
    if val <= 0 or base <= 0 or base == 1:
        raise FormulaError("LOG 参数无效")
    return math.log(val, base)

@FormulaEvaluator.register('EXP')
def fn_exp(args: List[Any]) -> float:
    """e 的幂（参数自动数值归一化）"""
    val = _to_number(args[0])
    return math.exp(val) if val is not None else None

@FormulaEvaluator.register('PI')
def fn_pi(args: List[Any]) -> float:
    """圆周率 π"""
    return math.pi

@FormulaEvaluator.register('E')
def fn_e(args: List[Any]) -> float:
    """自然常数 e"""
    return math.e

@FormulaEvaluator.register('RAND')
def fn_rand(args: List[Any]) -> float:
    """随机数 [0, 1)"""
    import random
    return random.random()

@FormulaEvaluator.register('RANDBETWEEN')
def fn_randbetween(args: List[Any]) -> int:
    """指定范围内的随机整数（参数自动数值归一化）"""
    lo = _to_number(args[0])
    hi = _to_number(args[1])
    if lo is None or hi is None:
        return None
    import random
    return random.randint(int(lo), int(hi))

@FormulaEvaluator.register('CONCAT')
def fn_concat(args: List[Any]) -> str:
    """拼接文本"""
    parts = [str(v) if v is not None else '' for v in args]
    return ''.join(parts)

@FormulaEvaluator.register('UPPER')
def fn_upper(args: List[Any]) -> str:
    """转大写"""
    val = args[0]
    return val.upper() if isinstance(val, str) else str(val).upper()

@FormulaEvaluator.register('LOWER')
def fn_lower(args: List[Any]) -> str:
    """转小写"""
    val = args[0]
    return val.lower() if isinstance(val, str) else str(val).lower()

@FormulaEvaluator.register('LEN')
def fn_len(args: List[Any]) -> int:
    """文本长度"""
    val = args[0]
    return len(str(val)) if val is not None else 0

@FormulaEvaluator.register('TRIM')
def fn_trim(args: List[Any]) -> str:
    """去除首尾空白"""
    val = args[0]
    return str(val).strip() if val is not None else ''

@FormulaEvaluator.register('LEFT')
def fn_left(args: List[Any]) -> str:
    """左侧 N 个字符"""
    text = str(args[0]) if args[0] is not None else ''
    n = int(args[1])
    return text[:n]

@FormulaEvaluator.register('RIGHT')
def fn_right(args: List[Any]) -> str:
    """右侧 N 个字符"""
    text = str(args[0]) if args[0] is not None else ''
    n = int(args[1])
    return text[-n:] if n > 0 else ''

@FormulaEvaluator.register('MID')
def fn_mid(args: List[Any]) -> str:
    """从中间提取子串"""
    text = str(args[0]) if args[0] is not None else ''
    start = int(args[1]) - 1
    length = int(args[2])
    return text[start:start + length]

@FormulaEvaluator.register('REPLACE')
def fn_replace(args: List[Any]) -> str:
    """替换文本"""
    text = str(args[0]) if args[0] is not None else ''
    start = int(args[1]) - 1
    length = int(args[2])
    new_text = str(args[3])
    return text[:start] + new_text + text[start + length:]

@FormulaEvaluator.register('SUBSTITUTE')
def fn_substitute(args: List[Any]) -> str:
    """替换子串"""
    text = str(args[0]) if args[0] is not None else ''
    old_str = str(args[1])
    new_str = str(args[2])
    instance_num = int(args[3]) if len(args) > 3 else 0
    
    if instance_num > 0:
        count = 0
        result = []
        i = 0
        while i < len(text):
            if text[i:i+len(old_str)] == old_str:
                count += 1
                if count == instance_num:
                    result.append(new_str)
                    i += len(old_str)
                    continue
            result.append(text[i])
            i += 1
        return ''.join(result)
    
    return text.replace(old_str, new_str)

@FormulaEvaluator.register('FIND')
def fn_find(args: List[Any]) -> Optional[int]:
    """查找子串位置（FIND(搜索文本, 被搜索文本, [起始位置]）"""
    search = str(args[0])
    text = str(args[1]) if args[1] is not None else ''
    start_pos = int(args[2]) - 1 if len(args) > 2 else 0
    
    idx = text.find(search, start_pos)
    return idx + 1 if idx >= 0 else None

@FormulaEvaluator.register('REPT')
def fn_rept(args: List[Any]) -> str:
    """重复文本"""
    text = str(args[0]) if args[0] is not None else ''
    count = int(args[1])
    return text * count

@FormulaEvaluator.register('TEXT')
def fn_text(args: List[Any]) -> str:
    """格式化数字为文本"""
    val = args[0]
    fmt = args[1] if len(args) > 1 else '#'
    
    if val is None:
        return ''
    
    if isinstance(fmt, str):
        if fmt.lower() == '0%':
            return f"{val:.0%}"
        elif fmt.lower() == '0.00%':
            return f"{val:.2%}"
        elif ',' in fmt and '.' in fmt:
            decimals = len(fmt.split('.')[1].replace('%', ''))
            formatted = f"{val:,.{decimals}f}"
            return formatted
        elif '.' in fmt:
            decimals = len(fmt.split('.')[1].replace('%', ''))
            return f"{val:.{decimals}f}"
        elif ',' in fmt:
            return f"{val:,.0f}"
    
    return str(val)

@FormulaEvaluator.register('VALUE')
def fn_value(args: List[Any]) -> Optional[float]:
    """将文本转为数字（复用 _to_number：剥离货币符号/千分位；非数字返回 None）"""
    return _to_number(args[0])

@FormulaEvaluator.register('NOW')
def fn_now(args: List[Any]) -> datetime:
    """当前日期时间"""
    return datetime.now(timezone.utc)

@FormulaEvaluator.register('TODAY')
def fn_today(args: List[Any]) -> date:
    """当前日期"""
    return date.today()

@FormulaEvaluator.register('YEAR')
def fn_year(args: List[Any]) -> Optional[int]:
    """获取年份"""
    val = args[0]
    if val is None:
        return None
    dt = _parse_date_value(val)
    return dt.year if dt else None

@FormulaEvaluator.register('MONTH')
def fn_month(args: List[Any]) -> Optional[int]:
    """获取月份"""
    val = args[0]
    if val is None:
        return None
    dt = _parse_date_value(val)
    return dt.month if dt else None

@FormulaEvaluator.register('DAY')
def fn_day(args: List[Any]) -> Optional[int]:
    """获取日期"""
    val = args[0]
    if val is None:
        return None
    dt = _parse_date_value(val)
    return dt.day if dt else None

@FormulaEvaluator.register('HOUR')
def fn_hour(args: List[Any]) -> Optional[int]:
    """获取小时"""
    val = args[0]
    if val is None:
        return None
    dt = _parse_date_value(val)
    return dt.hour if dt else None

@FormulaEvaluator.register('MINUTE')
def fn_minute(args: List[Any]) -> Optional[int]:
    """获取分钟"""
    val = args[0]
    if val is None:
        return None
    dt = _parse_date_value(val)
    return dt.minute if dt else None

@FormulaEvaluator.register('SECOND')
def fn_second(args: List[Any]) -> Optional[int]:
    """获取秒"""
    val = args[0]
    if val is None:
        return None
    dt = _parse_date_value(val)
    return dt.second if dt else None

@FormulaEvaluator.register('WEEKDAY')
def fn_weekday(args: List[Any]) -> Optional[int]:
    """获取星期几 (1=周一, 7=周日)"""
    val = args[0]
    if val is None:
        return None
    dt = _parse_date_value(val)
    if dt:
        wd = dt.weekday()
        return wd + 1
    return None

@FormulaEvaluator.register('DATEADD')
def fn_dateadd(args: List[Any]) -> datetime:
    """日期加法

    语法：DATEADD(date, amount, unit)
    示例：DATEADD(TODAY(), 7, "D") 表示今天往后 7 天
    """
    start_date = _parse_date_value(args[0])
    amount = int(args[1]) if len(args) > 1 else 0
    raw_unit = str(args[2]).strip() if len(args) > 2 else 'days'
    unit_lower = raw_unit.lower()

    if start_date is None:
        return None

    # 先按原始大小写匹配（M=月，m=分），再按小写匹配
    unit_map = {
        # 月/分钟需区分大小写
        'M': 'months',
        'm': 'minutes',
        # 小写通用别名
        'years': 'years',
        'year': 'years',
        'y': 'years',
        'months': 'months',
        'month': 'months',
        'weeks': 'weeks',
        'week': 'weeks',
        'w': 'weeks',
        'days': 'days',
        'day': 'days',
        'd': 'days',
        'hours': 'hours',
        'hour': 'hours',
        'h': 'hours',
        'minutes': 'minutes',
        'minute': 'minutes',
        'seconds': 'seconds',
        'second': 'seconds',
        's': 'seconds'
    }

    target_unit = unit_map.get(raw_unit) or unit_map.get(unit_lower, 'days')
    kwargs = {target_unit: amount}
    from dateutil.relativedelta import relativedelta
    return start_date + relativedelta(**kwargs)

def _parse_date_value(value: Any) -> Optional[datetime]:
    """将字符串、毫秒时间戳或 datetime/date 解析为 datetime

    统一返回"无时区(naive)"的 datetime，避免 NOW()（UTC aware）与字段值
    （naive）在比较/相减时出现 aware/naive 类型冲突而抛 TypeError。
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        # 去除时区信息，统一为 naive，便于与无时区日期值进行运算/比较
        return value.replace(tzinfo=None) if value.tzinfo is not None else value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None

        # 支持 YYYYMMDD 格式（如 MID 返回的 "19900307"）
        # 必须在数字时间戳检查之前，因为 8 位数字字符串也会通过 isdigit 检查
        if re.match(r'^\d{8}$', trimmed):
            try:
                return datetime.strptime(trimmed, '%Y%m%d')
            except ValueError:
                pass

        # 尝试解析为数字时间戳（其他函数嵌套返回的序列化时间戳字符串）
        # 只有超过 8 位（如 13 位毫秒时间戳）才尝试，避免与 YYYYMMDD 混淆
        if trimmed.isdigit() and len(trimmed) > 8:
            try:
                ts = int(trimmed)
                return datetime.fromtimestamp(ts / 1000)
            except (ValueError, OSError, OverflowError):
                pass

        # 尝试标准 ISO 格式
        try:
            parsed = datetime.fromisoformat(trimmed.replace('Z', '+00:00'))
            # 去除时区信息，统一为 naive（如带 Z 的 UTC 时间）
            return parsed.replace(tzinfo=None) if parsed.tzinfo is not None else parsed
        except ValueError:
            pass

        # 尝试常见日期格式
        for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
            try:
                return datetime.strptime(trimmed, fmt)
            except ValueError:
                continue

        return None

    if isinstance(value, (int, float)):
        # 毫秒时间戳（前端及日期字段常用）
        try:
            return datetime.fromtimestamp(value / 1000)
        except (ValueError, OSError, OverflowError):
            return None
    return None

@FormulaEvaluator.register('DATEDIFF')
@FormulaEvaluator.register('DATEDIF')
def fn_datediff(args: List[Any]) -> int:
    """日期差（DATEDIF / DATEDIFF）"""
    start_date = _parse_date_value(args[0])
    end_date = _parse_date_value(args[1])
    raw_unit = str(args[2]).strip() if len(args) > 2 else 'days'
    unit_lower = raw_unit.lower()

    if start_date is None or end_date is None:
        return None

    delta = end_date - start_date

    # 先按原始大小写匹配（M=月，m=分），再按小写匹配
    unit_map = {
        'M': 'months',
        'm': 'minutes',
        'days': 'days',
        'day': 'days',
        'd': 'days',
        'hours': 'hours',
        'hour': 'hours',
        'h': 'hours',
        'minutes': 'minutes',
        'minute': 'minutes',
        'seconds': 'seconds',
        'second': 'seconds',
        's': 'seconds',
        'weeks': 'weeks',
        'week': 'weeks',
        'w': 'weeks',
        'months': 'months',
        'month': 'months',
        'years': 'years',
        'year': 'years',
        'y': 'years'
    }

    unit = unit_map.get(raw_unit) or unit_map.get(unit_lower, 'days')

    result_map = {
        'days': delta.days,
        'hours': int(delta.total_seconds() / 3600),
        'minutes': int(delta.total_seconds() / 60),
        'seconds': int(delta.total_seconds()),
        'weeks': int(delta.days / 7),
        'months': (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month),
        'years': end_date.year - start_date.year,
    }

    return result_map.get(unit, delta.days)

@FormulaEvaluator.register('DATETIME_FORMAT')
def fn_datetime_format(args: List[Any]) -> str:
    """格式化日期时间"""
    val = args[0]
    fmt = args[1] if len(args) > 1 else '%Y-%m-%d %H:%M:%S'
    
    if val is None:
        return ''
    
    # 使用 _parse_date_value 统一解析，支持更多格式
    parsed = _parse_date_value(val)
    if parsed is not None:
        return parsed.strftime(str(fmt))
    
    return str(val)

@FormulaEvaluator.register('FROMUNIXTIME')
def fn_fromunixtime(args: List[Any]) -> datetime:
    """Unix 时间戳转日期时间"""
    ts = args[0]
    if ts is None:
        return None
    return datetime.utcfromtimestamp(int(ts))

@FormulaEvaluator.register('UNIXTIMESTAMP')
def fn_unixtimestamp(args: List[Any]) -> int:
    """日期时间转 Unix 时间戳"""
    val = args[0]
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, datetime):
        return int(val.timestamp())
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except ValueError:
            pass
    return None
