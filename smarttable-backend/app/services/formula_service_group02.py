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

class FormulaServiceGroup02Mixin:
    """group02 mixin"""

    _parser = FormulaParser()

    _COLUMN_REF_RE = re.compile(r'\[([^\[\]{}]+)\]\s*\.\s*\[([^\[\]{}]+)\]')

    _TABLE_CONTEXT_CACHE: Dict[str, Tuple[float, Optional[str], Optional[Dict[str, Dict[str, List[Any]]]]]] = {}

    _TABLE_CONTEXT_TTL_SECONDS: float = 10.0


    @classmethod
    def compute_record_formulas(
        cls,
        table_id: str,
        values: Dict[str, Any],
        user_id: str = None,
        formula_fields: List[Field] = None,
        table_context: Optional[Dict[str, Dict[str, List[Any]]]] = None,
        record: Optional[Any] = None,
        all_fields: Optional[List[Field]] = None,
        compute_ctx: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        计算记录中所有公式的值（任务 30.1）

        在记录保存时调用，自动计算所有公式字段并返回结果

        Args:
            table_id: 表格 ID
            values: 记录的原始字段值字典 {field_name_or_id: value}
            user_id: 操作用户 ID（可选，用于审计）
            formula_fields: 可选的预查询公式字段列表，避免重复数据库查询
            table_context: 可选的整列引用数据上下文；未提供时若公式含
                          [表].[字段] 引用则自动查询本表全量数据构建
            record: 可选的记录 ORM 对象；传入时公式可引用系统维护字段
                   （创建人/创建时间/更新人/更新时间，值取自记录元数据）
            all_fields: 可选的预查询全部字段列表（B2 优化：避免每条记录重复 SELECT * FROM fields）
            compute_ctx: 可选的 RecordComputeContext（B1+B2 联合优化：让 lookup 值
                         与 records.py 循环共用同一份预加载数据 + 去重缓存）

        Returns:
            公式字段计算结果字典 {field_name: computed_value}
        """
        if formula_fields is None:
            from app.models.table import Table

            table = Table.query.get(table_id)
            if not table:
                raise FormulaError(f"表格不存在: {table_id}")

            formula_fields = Field.query.filter_by(
                table_id=table_id,
                type='formula'
            ).all()

        if not formula_fields:
            return {}

        # 含整列引用的公式需要全表数据；调用方未提供时按需构建
        if table_context is None:
            table_context = cls.build_table_context_for_fields(
                table_id, formula_fields
            )

        # 获取表格所有字段，构建以字段名为 key 的上下文
        # （公式引擎用字段名引用；系统维护字段从记录元数据补充）
        # B2 优化：all_fields 已预取 → 直接用，避免每条记录 1 次 SELECT * FROM fields
        if all_fields is None:
            all_fields = Field.query.filter_by(table_id=table_id).all()
        context_by_name = cls._build_formula_context(
            all_fields, values, record=record, compute_ctx=compute_ctx
        )

        results = {}

        for field in formula_fields:
            formula_config = field.config or {}
            formula_expr = formula_config.get('formula', '')

            if not formula_expr:
                continue

            try:
                result = cls.evaluate_formula(
                    formula_expr,
                    context_by_name,
                    table_context=table_context
                )
                # 序列化结果，确保 datetime 对象转为 ISO 字符串
                results[field.name] = cls._serialize_result(result)
                
                if field.config is None:
                    field.config = {}
                field.config['_last_computed'] = {
                    'result': cls._serialize_result(result),
                    'computed_at': datetime.now(timezone.utc).isoformat(),
                    'user_id': str(user_id) if user_id else None
                }
                
            except FormulaError as e:
                results[field.name] = f"#ERROR: {str(e)}"
        
        return results

    @classmethod
    def batch_recalculate(
        cls,
        table_id: str,
        field_ids: List[str] = None,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        批量重新计算表格中的公式值（任务 30.2）
        
        当字段配置变更时调用，批量更新受影响的记录
        
        Args:
            table_id: 表格 ID
            field_ids: 要重算的字段 ID 列表（None 表示全部公式字段）
            batch_size: 每批处理的记录数量
            
        Returns:
            统计信息字典
            {
                'total_records': 总记录数,
                'processed': 已处理数量,
                'errors': 错误数量,
                'fields_updated': 更新的字段列表
            }
        """
        from app.models.table import Table
        from app.models.record import Record
        
        table = Table.query.get(table_id)
        if not table:
            raise FormulaError(f"表格不存在: {table_id}")
        
        query = Field.query.filter_by(
            table_id=table_id,
            type='formula'
        )
        
        if field_ids:
            query = query.filter(Field.id.in_(field_ids))
        
        formula_fields = query.all()
        
        if not formula_fields:
            return {
                'total_records': 0,
                'processed': 0,
                'errors': 0,
                'fields_updated': []
            }
        
        total_records = Record.query.filter_by(
            table_id=table_id,
            is_deleted=False
        ).count()

        # 整列引用公式需要全表数据上下文（构建一次，循环内复用）
        table_context = cls.build_table_context_for_fields(
            table_id, formula_fields
        )

        processed = 0
        errors = 0
        updated_fields = []

        # 构建字段名上下文所需的全部字段（含系统字段元数据注入）
        all_fields = Field.query.filter_by(table_id=table_id).all()

        offset = 0
        while offset < total_records:
            records = Record.query.filter_by(
                table_id=table_id,
                is_deleted=False
            ).offset(offset).limit(batch_size).all()

            for record in records:
                # 以字段名为 key 的上下文（公式引擎用字段名引用；
                # 系统维护字段从记录元数据补充）
                context_by_name = cls._build_formula_context(
                    all_fields, record.values or {}, record=record
                )

                for field in formula_fields:
                    formula_expr = (field.config or {}).get('formula', '')

                    if not formula_expr:
                        continue

                    try:
                        result = cls.evaluate_formula(
                            formula_expr,
                            context_by_name,
                            use_cache=False,
                            table_context=table_context
                        )
                        
                        if record.values is None:
                            record.values = {}
                        
                        record.values[field.name] = cls._serialize_result(result)
                        
                        if field.id not in updated_fields:
                            updated_fields.append(field.id)
                            
                    except FormulaError:
                        errors += 1
                
                processed += 1
            
            db.session.commit()
            offset += batch_size
        
        cls.invalidate_table_cache(table_id)
        
        return {
            'total_records': total_records,
            'processed': processed,
            'errors': errors,
            'fields_updated': updated_fields
        }

    @classmethod
    def invalidate_table_cache(cls, table_id: str) -> None:
        """
        使指定表格的公式缓存失效（任务 30.3）
        
        当数据变更后调用此方法清除相关缓存
        
        Args:
            table_id: 表格 ID
        """
        pattern = f"formula:{table_id}:*"
        try:
            keys_to_delete = []
            for key in cache.cache._client.scan_iter(match=pattern):
                keys_to_delete.append(key)
            if keys_to_delete:
                cache.cache._client.delete(*keys_to_delete)
        except Exception:
            pass

    @classmethod
    def validate_formula_syntax(cls, formula: str) -> Tuple[bool, Optional[str]]:
        """
        验证公式语法是否正确
        
        Args:
            formula: 公式字符串
            
        Returns:
            (是否有效, 错误信息)
        """
        if not formula or not formula.strip():
            return True, None
        
        try:
            cls._parser.parse(formula)
            return True, None
        except FormulaError as e:
            return False, str(e)

    @classmethod
    def get_formula_dependencies(cls, formula: str) -> List[str]:
        """
        获取公式依赖的字段列表
        
        Args:
            formula: 公式字符串
            
        Returns:
            依赖的字段名称列表
        """
        if not formula or not formula.strip():
            return []
        
        dependencies = []
        pattern = r'\{([^}]+)\}'
        
        for match in re.finditer(pattern, formula):
            dep = match.group(1)
            if dep not in dependencies:
                dependencies.append(dep)
        
        return dependencies

    @classmethod
    def get_function_list(cls) -> List[Dict[str, Any]]:
        """
        获取所有可用函数的列表及说明
        
        Returns:
            函数信息列表
        """
        function_info = {
            '数学': [
                {'name': 'SUM', 'desc': '求和', 'syntax': 'SUM(value1, value2, ...)'},
                {'name': 'AVG', 'desc': '平均值', 'syntax': 'AVG(value1, value2, ...)'},
                {'name': 'MAX', 'desc': '最大值', 'syntax': 'MAX(value1, value2, ...)'},
                {'name': 'MIN', 'desc': '最小值', 'syntax': 'MIN(value1, value2, ...)'},
                {'name': 'ROUND', 'desc': '四舍五入', 'syntax': 'ROUND(value, digits)'},
                {'name': 'ABS', 'desc': '绝对值', 'syntax': 'ABS(value)'},
                {'name': 'CEILING', 'desc': '向上取整', 'syntax': 'CEILING(value)'},
                {'name': 'FLOOR', 'desc': '向下取整', 'syntax': 'FLOOR(value)'},
                {'name': 'POWER', 'desc': '幂运算', 'syntax': 'POWER(base, exponent)'},
                {'name': 'SQRT', 'desc': '平方根', 'syntax': 'SQRT(value)'},
                {'name': 'MOD', 'desc': '取模', 'syntax': 'MOD(a, b)'},
                {'name': 'LN', 'desc': '自然对数', 'syntax': 'LN(value)'},
                {'name': 'LOG', 'desc': '对数', 'syntax': 'LOG(value, base)'},
                {'name': 'EXP', 'desc': 'e的幂', 'syntax': 'EXP(value)'},
                {'name': 'PI', 'desc': '圆周率', 'syntax': 'PI()'},
                {'name': 'E', 'desc': '自然常数', 'syntax': 'E()'},
                {'name': 'RAND', 'desc': '随机数[0,1)', 'syntax': 'RAND()'},
                {'name': 'RANDBETWEEN', 'desc': '范围随机整数', 'syntax': 'RANDBETWEEN(min, max)'},
            ],
            '文本': [
                {'name': 'CONCAT', 'desc': '拼接文本', 'syntax': 'CONCAT(text1, text2, ...)'},
                {'name': 'UPPER', 'desc': '转大写', 'syntax': 'UPPER(text)'},
                {'name': 'LOWER', 'desc': '转小写', 'syntax': 'LOWER(text)'},
                {'name': 'LEN', 'desc': '文本长度', 'syntax': 'LEN(text)'},
                {'name': 'TRIM', 'desc': '去除首尾空白', 'syntax': 'TRIM(text)'},
                {'name': 'LEFT', 'desc': '左侧N字符', 'syntax': 'LEFT(text, n)'},
                {'name': 'RIGHT', 'desc': '右侧N字符', 'syntax': 'RIGHT(text, n)'},
                {'name': 'MID', 'desc': '中间截取', 'syntax': 'MID(text, start, length)'},
                {'name': 'REPLACE', 'desc': '替换文本', 'syntax': 'REPLACE(text, start, length, new_text)'},
                {'name': 'SUBSTITUTE', 'desc': '替换子串', 'syntax': 'SUBSTITUTE(text, old, new, instance)'},
                {'name': 'FIND', 'desc': '查找子串', 'syntax': 'FIND(search_text, text, start)'},
                {'name': 'REPT', 'desc': '重复文本', 'syntax': 'REPT(text, count)'},
                {'name': 'TEXT', 'desc': '格式化为文本', 'syntax': 'TEXT(value, format)'},
                {'name': 'VALUE', 'desc': '文本转数字', 'syntax': 'VALUE(text)'},
            ],
            '日期': [
                {'name': 'NOW', 'desc': '当前日期时间', 'syntax': 'NOW()'},
                {'name': 'TODAY', 'desc': '当前日期', 'syntax': 'TODAY()'},
                {'name': 'YEAR', 'desc': '获取年份', 'syntax': 'YEAR(date)'},
                {'name': 'MONTH', 'desc': '获取月份', 'syntax': 'MONTH(date)'},
                {'name': 'DAY', 'desc': '获取日', 'syntax': 'DAY(date)'},
                {'name': 'HOUR', 'desc': '获取小时', 'syntax': 'HOUR(datetime)'},
                {'name': 'MINUTE', 'desc': '获取分钟', 'syntax': 'MINUTE(datetime)'},
                {'name': 'SECOND', 'desc': '获取秒', 'syntax': 'SECOND(datetime)'},
                {'name': 'WEEKDAY', 'desc': '获取星期几', 'syntax': 'WEEKDAY(date)'},
                {'name': 'DATEADD', 'desc': '日期加法', 'syntax': 'DATEADD(date, amount, unit)'},
                {'name': 'DATEDIF', 'desc': '日期差（DATEDIFF 别名）', 'syntax': 'DATEDIF(start, end, unit)'},
                {'name': 'DATEDIFF', 'desc': '日期差（DATEDIF 别名）', 'syntax': 'DATEDIFF(start, end, unit)'},
                {'name': 'DATETIME_FORMAT', 'desc': '格式化日期', 'syntax': 'DATETIME_FORMAT(date, format)'},
                {'name': 'FROMUNIXTIME', 'desc': '时间戳转日期', 'syntax': 'FROMUNIXTIME(timestamp)'},
                {'name': 'UNIXTIMESTAMP', 'desc': '日期转时间戳', 'syntax': 'UNIXTIMESTAMP(date)'}
            ],
            '逻辑': [
                {'name': 'IF', 'desc': '条件判断', 'syntax': 'IF(condition, true_value, false_value)'},
                {'name': 'IFS', 'desc': '多条件判断', 'syntax': 'IFS(cond1, val1, cond2, val2, ...)'},
                {'name': 'SWITCH', 'desc': '多值匹配', 'syntax': 'SWITCH(expr, val1, res1, ..., DEFAULT, default)'},
                {'name': 'AND', 'desc': '逻辑与', 'syntax': 'AND(cond1, cond2, ...)'},
                {'name': 'OR', 'desc': '逻辑或', 'syntax': 'OR(cond1, cond2, ...)'},
                {'name': 'NOT', 'desc': '逻辑非', 'syntax': 'NOT(condition)'},
                {'name': 'XOR', 'desc': '异或', 'syntax': 'XOR(cond1, cond2)'},
                {'name': 'IFERROR', 'desc': '错误处理', 'syntax': 'IFERROR(value, value_if_error)'},
                {'name': 'ISBLANK', 'desc': '判断是否为空', 'syntax': 'ISBLANK(value)'},
                {'name': 'ISERROR', 'desc': '判断是否为错误', 'syntax': 'ISERROR(value)'},
                {'name': 'ISNUMBER', 'desc': '判断是否为数字', 'syntax': 'ISNUMBER(value)'},
                {'name': 'ISTEXT', 'desc': '判断是否为文本', 'syntax': 'ISTEXT(value)'},
                {'name': 'ISDATE', 'desc': '判断是否为日期', 'syntax': 'ISDATE(value)'},
                {'name': 'BLANK', 'desc': '返回空值', 'syntax': 'BLANK()'},
                {'name': 'NA', 'desc': '返回 N/A 错误', 'syntax': 'NA()'},
                {'name': 'ERROR', 'desc': '返回自定义错误', 'syntax': 'ERROR(message)'},
            ],
            '统计': [
                {'name': 'COUNT', 'desc': '计数(数字)', 'syntax': 'COUNT(value1, value2, ...)'},
                {'name': 'COUNTA', 'desc': '计数(非空)', 'syntax': 'COUNTA(value1, value2, ...)'},
                {'name': 'COUNTBLANK', 'desc': '计数(空值)', 'syntax': 'COUNTBLANK(value1, value2, ...)'},
                {'name': 'COUNTIF', 'desc': '条件计数', 'syntax': 'COUNTIF(range, criteria)'},
                {'name': 'SUMIF', 'desc': '条件求和', 'syntax': 'SUMIF(range, criteria, [sum_range])'},
                {'name': 'AVERAGEIF', 'desc': '条件平均值', 'syntax': 'AVERAGEIF(range, criteria, [avg_range])'},
                {'name': 'STDEV', 'desc': '标准差', 'syntax': 'STDEV(value1, value2, ...)'},
                {'name': 'VAR', 'desc': '方差', 'syntax': 'VAR(value1, value2, ...)'},
                {'name': 'MEDIAN', 'desc': '中位数', 'syntax': 'MEDIAN(value1, value2, ...)'},
                {'name': 'MODE', 'desc': '众数', 'syntax': 'MODE(value1, value2, ...)'},
                {'name': 'RANK', 'desc': '排名', 'syntax': 'RANK(value, value1, value2, ...)'},
                {'name': 'UNIQUE', 'desc': '去重', 'syntax': 'UNIQUE(value1, value2, ...)'},
            ]
        }
        
        result = []
        for category, funcs in function_info.items():
            result.extend(funcs)
        
        return result

    @staticmethod
    def _build_cache_key(formula: str, context: Dict[str, Any]) -> str:
        """构建缓存键"""
        content = json.dumps({
            'formula': formula,
            'context': context
        }, sort_keys=True, default=str)
        
        hash_value = hashlib.md5(content.encode()).hexdigest()
        return f"formula:{hash_value}"

    @staticmethod
    def _serialize_result(result: Any) -> Any:
        """序列化计算结果以便存储"""
        if result is None:
            return None
        if isinstance(result, datetime):
            return result.isoformat()
        if isinstance(result, date):
            return result.isoformat()
        if isinstance(result, (list, dict)):
            return json.dumps(result, default=str)
        if isinstance(result, bool):
            return result
        if isinstance(result, float):
            if result != result:
                return "#ERROR: NaN"
            if abs(result) == float('inf'):
                return "#ERROR: Infinity"
            return round(result, 10)
        return result
