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

class FormulaEvaluator:
    """
    公式求值器
    
    对 AST 进行求值，支持所有内置函数
    """
    
    FUNCTIONS = {}
    
    @classmethod
    def register(cls, name: str):
        """注册内置函数的装饰器"""
        def decorator(func):
            cls.FUNCTIONS[name.upper()] = func
            return func
        return decorator
    
    # 支持 CurrentValue 惰性条件求值的统计函数
    LAZY_STAT_FUNCS = {'FILTER', 'COUNTIF', 'SUMIF', 'AVERAGEIF'}

    def __init__(
        self,
        context: Dict[str, Any],
        table_context: Optional[Dict[str, Dict[str, List[Any]]]] = None
    ):
        """
        初始化求值器

        Args:
            context: 计算上下文，包含字段名到值的映射
            table_context: 整列引用数据上下文，{表名小写: {字段名: [整列值]}}；
                          用于 [表].[字段] 整列引用求值
        """
        self.context = context
        self.table_context = table_context or {}
        # CurrentValue 栈：惰性条件逐元素求值时压入当前元素
        self.current_value_stack: List[Any] = []
    
    def evaluate(self, node: Dict[str, Any]) -> Any:
        """
        对 AST 节点进行求值
        
        Args:
            node: AST 节点
            
        Returns:
            求值结果
        """
        node_type = node.get('type')
        
        if node_type == 'number':
            return node['value']
        
        if node_type == 'string':
            return node['value']
        
        if node_type == 'boolean':
            return node['value']
        
        if node_type == 'null':
            return None
        
        if node_type == 'field_ref':
            field_name = node['name']
            if field_name not in self.context:
                raise FormulaError(f"未找到字段: {field_name}")
            return self.context[field_name]

        if node_type == 'column_ref':
            return self._eval_column_ref(node)

        if node_type == 'current_value':
            if not self.current_value_stack:
                raise FormulaError(
                    "CurrentValue 仅可在 FILTER/COUNTIF/SUMIF/AVERAGEIF 的条件参数中使用"
                )
            return self.current_value_stack[-1]
        
        if node_type == 'binary_op':
            return self._eval_binary_op(node)
        
        if node_type == 'comparison':
            return self._eval_comparison(node)
        
        if node_type == 'unary_minus':
            val = self.evaluate(node['operand'])
            if val is None:
                return None
            return -val
        
        if node_type == 'unary_not':
            val = self.evaluate(node['operand'])
            if val is None:
                return None
            return not val
        
        if node_type == 'function_call':
            return self._eval_function(node)
        
        if node_type == 'default_keyword':
            return '__DEFAULT__'
        
        raise FormulaError(f"未知节点类型: {node_type}")
    
    def _eval_binary_op(self, node: Dict[str, Any]) -> Any:
        """求值二元运算符"""
        op = node['operator']
        left = self.evaluate(node['left'])
        right = self.evaluate(node['right'])

        if left is None or right is None:
            return None

        # 数值归一化：数字字段可能存字符串形态脏数据（'1.3'、'¥1,234.5'），
        # 字符串参与算术时先归一化为数字（与聚合函数 _to_number 一致）；
        # 无法归一化（真文本/日期对象等）时保持原类型由下方运算/异常兜底
        if isinstance(left, str) or isinstance(right, str):
            n_left, n_right = _to_number(left), _to_number(right)
            if n_left is not None and n_right is not None:
                left, right = n_left, n_right

        if op == '+':
            return left + right
        elif op == '-':
            return left - right
        elif op == '*':
            return left * right
        elif op == '/':
            if right == 0:
                raise FormulaError("除数不能为零")
            return left / right
        elif op == '^':
            return left ** right
        else:
            raise FormulaError(f"未知运算符: {op}")
    
    def _eval_comparison(self, node: Dict[str, Any]) -> bool:
        """求值比较运算符"""
        op = node['operator']
        left = self.evaluate(node['left'])
        right = self.evaluate(node['right'])
        
        # 日期/时间智能比较：当两侧任一可解析为日期时，统一归一化为 datetime 再比较，
        # 解决字段值（JSON 存储的日期字符串、datetime 对象）与 TODAY()/NOW()（date/datetime）
        # 类型不一致导致比较抛 TypeError 的问题（如 IF({结束日期}>TODAY(),'1','2') 永远异常）。
        # 同时去除时区信息（naive），避免 NOW()（UTC aware）与字段（naive）比较仍抛异常。
        if left is not None and right is not None:
            left_dt = _parse_date_value(left)
            right_dt = _parse_date_value(right)
            if left_dt is not None and right_dt is not None:
                left = left_dt.replace(tzinfo=None) if isinstance(left_dt, datetime) else left_dt
                right = right_dt.replace(tzinfo=None) if isinstance(right_dt, datetime) else right_dt
        
        if op == '=':
            return left == right
        elif op == '<>':
            return left != right
        elif op in ('>', '<', '>=', '<='):
            if left is None or right is None:
                return False
            l, r = left, right
            if not (isinstance(l, str) and isinstance(r, str)):
                # 至少一侧非字符串：尝试数值归一化（数字字段可能存字符串形态脏数据，
                # 如 '85' >= 60 原生会抛 TypeError）；两侧均可数值化则数值比较
                n_l, n_r = _to_number(l), _to_number(r)
                if n_l is not None and n_r is not None:
                    l, r = n_l, n_r
                elif isinstance(l, str) or isinstance(r, str):
                    # 真文本与数字/日期混合且无法归一化：视为不命中
                    return False
            try:
                if op == '>':
                    return l > r
                elif op == '<':
                    return l < r
                elif op == '>=':
                    return l >= r
                else:
                    return l <= r
            except TypeError:
                return False
        else:
            raise FormulaError(f"未知比较运算符: {op}")
    
    def _eval_column_ref(self, node: Dict[str, Any]) -> Optional[List[Any]]:
        """求值整列引用 [表].[字段] → 该字段全表值集合（数组）"""
        columns = self.table_context.get(str(node['table']).lower())
        if columns is None:
            # 未注入表上下文或表不存在：与前端对齐，宽容退化为 None
            return None

        field_name = str(node['field'])
        if field_name in columns:
            return columns[field_name]
        # 字段名大小写不敏感兜底
        fl = field_name.lower()
        for k, v in columns.items():
            if str(k).lower() == fl:
                return v
        return None

    @classmethod
    def _contains_current_value(cls, node: Any) -> bool:
        """递归检测 AST 子树中是否包含 current_value 节点"""
        if isinstance(node, dict):
            if node.get('type') == 'current_value':
                return True
            return any(cls._contains_current_value(v) for v in node.values())
        if isinstance(node, list):
            return any(cls._contains_current_value(v) for v in node)
        return False

    def _eval_lazy_statistical(self, func_name: str, node: Dict[str, Any]) -> Any:
        """
        惰性求值统计函数（条件参数含 CurrentValue）：
        对范围逐元素构造 CurrentValue 上下文递归求值条件，再执行过滤/聚合
        """
        range_val = self.evaluate(node['arguments'][0])
        values = range_val if isinstance(range_val, list) else [range_val]
        criteria_node = node['arguments'][1]

        matched: List[bool] = []
        for v in values:
            self.current_value_stack.append(v)
            try:
                matched.append(bool(self.evaluate(criteria_node)))
            except TypeError:
                # 脏数据兜底：数字字段以字符串形态存储（'1.3'），数值条件
                # （如 CurrentValue > 100）比较 str 与 int 抛 TypeError。
                # 将当前值归一化为数字后重试；纯文本无法归一化则视为不命中。
                normalized = _to_number(v)
                try:
                    if normalized is None:
                        matched.append(False)
                    else:
                        self.current_value_stack[-1] = normalized
                        matched.append(bool(self.evaluate(criteria_node)))
                except Exception:
                    matched.append(False)
            finally:
                self.current_value_stack.pop()

        if func_name == 'FILTER':
            return [v for v, m in zip(values, matched) if m]

        if func_name == 'COUNTIF':
            return sum(1 for m in matched if m)

        # SUMIF / AVERAGEIF：可选第三个参数为求和/平均列
        agg_values = values
        if len(node['arguments']) > 2:
            agg_val = self.evaluate(node['arguments'][2])
            agg_values = agg_val if isinstance(agg_val, list) else [agg_val]

        total = 0.0
        count = 0
        for i, m in enumerate(matched):
            if m and i < len(agg_values):
                # 数值归一化：数字字段可能以字符串形态存储（'1.3'、'¥1,234.5'）
                n = _to_number(agg_values[i])
                if n is not None:
                    total += n
                    count += 1

        if func_name == 'SUMIF':
            return total if any(matched) else None
        return total / count if count > 0 else None

    def _eval_function(self, node: Dict[str, Any]) -> Any:
        """求值函数调用"""
        func_name = node['name'].upper()

        if func_name not in self.FUNCTIONS:
            raise FormulaError(f"未知函数: {func_name}")

        # IFERROR 需要特殊处理：捕获第一个参数的求值错误
        if func_name == 'IFERROR':
            if len(node['arguments']) < 2:
                raise FormulaError("IFERROR 需要两个参数")
            try:
                value = self.evaluate(node['arguments'][0])
                if isinstance(value, Exception):
                    return self.evaluate(node['arguments'][1])
                return value
            except Exception:
                return self.evaluate(node['arguments'][1])

        # 统计函数惰性求值：条件参数含 CurrentValue 时不预先求值参数
        if (
            func_name in self.LAZY_STAT_FUNCS
            and len(node['arguments']) >= 2
            and self._contains_current_value(node['arguments'][1])
        ):
            try:
                return self._eval_lazy_statistical(func_name, node)
            except FormulaError:
                raise
            except Exception as e:
                raise FormulaError(f"函数 {func_name} 执行错误: {str(e)}")

        args = [self.evaluate(arg) for arg in node['arguments']]

        try:
            return self.FUNCTIONS[func_name](args)
        except Exception as e:
            raise FormulaError(f"函数 {func_name} 执行错误: {str(e)}")
