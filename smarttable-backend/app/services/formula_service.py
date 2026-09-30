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
from app.models.field import Field


class FormulaError(Exception):
    """公式计算错误"""
    pass


class FormulaParser:
    """
    公式解析器
    
    将公式字符串解析为可执行的 AST（抽象语法树）
    支持的语法：
    - 字段引用: {field_name} 或 {field_id}
    - 函数调用: FUNC(arg1, arg2, ...)
    - 算术运算: +, -, *, /, ^
    - 比较运算: =, <>, >, <, >=, <=
    - 逻辑运算: AND, OR, NOT
    - 字符串: "text" 或 'text'
    - 数字: 123, 12.34
    - 布尔: TRUE, FALSE
    - 空值: BLANK()
    """
    
    TOKEN_PATTERNS = [
        ('WHITESPACE', r'\s+'),
        ('NUMBER', r'-?\d+\.?\d*'),
        ("STRING", r'"[^"]*"|\'[^\']*\''),
        # 整列引用 [表名].[字段名]（整体匹配，避免内部被拆分）
        ('COLUMN_REF', r'\[[^\[\]{}]+\]\s*\.\s*\[[^\[\]{}]+\]'),
        ('FIELD_REF', r'\{[^}]+\}'),
        # CurrentValue（统计函数惰性条件中的当前元素，大小写不敏感）
        ('CURRENT_VALUE', r'(?i:CURRENTVALUE)\b'),
        ('FUNCTION', r'[A-Z_][A-Z0-9_]*(?=\s*\()'),
        ('IDENTIFIER', r'[A-Z_][A-Z0-9_]*'),
        ('LPAREN', r'\('),
        ('RPAREN', r'\)'),
        ('COMMA', r','),
        ('OPERATOR', r'[+\-*/^<>=!&|]+'),
    ]
    
    def __init__(self):
        self._compiled_patterns = [
            (name, re.compile(pattern))
            for name, pattern in self.TOKEN_PATTERNS
        ]
    
    def tokenize(self, formula: str) -> List[Tuple[str, str]]:
        """
        词法分析，将公式字符串转换为 token 列表
        
        Args:
            formula: 公式字符串
            
        Returns:
            token 列表 [(type, value), ...]
        """
        tokens = []
        pos = 0
        
        while pos < len(formula):
            match = None
            
            for name, pattern in self._compiled_patterns:
                match = pattern.match(formula, pos)
                if match:
                    if name != 'WHITESPACE':
                        tokens.append((name, match.group()))
                    pos = match.end()
                    break
            
            if not match:
                raise FormulaError(f"无法解析的字符: '{formula[pos]}' (位置 {pos})")
        
        return tokens
    
    def parse(self, formula: str) -> Dict[str, Any]:
        """
        解析公式为 AST
        
        Args:
            formula: 公式字符串
            
        Returns:
            AST 字典
        """
        tokens = self.tokenize(formula)
        
        if not tokens:
            raise FormulaError("公式不能为空")
        
        parser = _ASTParser(tokens)
        ast = parser.parse_expression()
        
        if not parser.is_at_end():
            raise FormulaError(f"公式末尾有多余内容")
        
        return ast


class _ASTParser:
    """内部 AST 解析器"""
    
    def __init__(self, tokens: List[Tuple[str, str]]):
        self.tokens = tokens
        self.pos = 0
    
    def is_at_end(self) -> bool:
        return self.pos >= len(self.tokens)
    
    def peek(self) -> Optional[Tuple[str, str]]:
        if self.is_at_end():
            return None
        return self.tokens[self.pos]
    
    def advance(self) -> Tuple[str, str]:
        token = self.tokens[self.pos]
        self.pos += 1
        return token
    
    def expect(self, token_type: str) -> Tuple[str, str]:
        token = self.peek()
        if token is None or token[0] != token_type:
            expected = token_type
            actual = token[0] if token else 'EOF'
            raise FormulaError(f"期望 {expected}，但得到 {actual}")
        return self.advance()
    
    def parse_expression(self) -> Dict[str, Any]:
        """解析表达式（逻辑或）"""
        left = self.parse_comparison()
        
        while True:
            token = self.peek()
            if token and token[1] in ('OR', '|'):
                self.advance()
                right = self.parse_comparison()
                left = {'type': 'binary_op', 'operator': 'OR', 'left': left, 'right': right}
            else:
                break
        
        return left
    
    def parse_comparison(self) -> Dict[str, Any]:
        """解析比较表达式"""
        left = self.parse_additive()
        
        while True:
            token = self.peek()
            if token and token[1] in ('=', '<>', '>', '<', '>=', '<='):
                op = self.advance()[1]
                right = self.parse_additive()
                left = {'type': 'comparison', 'operator': op, 'left': left, 'right': right}
            else:
                break
        
        return left
    
    def parse_additive(self) -> Dict[str, Any]:
        """解析加减法"""
        left = self.parse_multiplicative()
        
        while True:
            token = self.peek()
            if token and token[1] in ('+', '-'):
                op = self.advance()[1]
                right = self.parse_multiplicative()
                left = {'type': 'binary_op', 'operator': op, 'left': left, 'right': right}
            else:
                break
        
        return left
    
    def parse_multiplicative(self) -> Dict[str, Any]:
        """解析乘除法"""
        left = self.parse_power()
        
        while True:
            token = self.peek()
            if token and token[1] in ('*', '/'):
                op = self.advance()[1]
                right = self.parse_power()
                left = {'type': 'binary_op', 'operator': op, 'left': left, 'right': right}
            else:
                break
        
        return left
    
    def parse_power(self) -> Dict[str, Any]:
        """解析幂运算"""
        base = self.parse_unary()
        
        token = self.peek()
        if token and token[1] == '^':
            self.advance()
            exp = self.parse_unary()
            base = {'type': 'binary_op', 'operator': '^', 'left': base, 'right': exp}
        
        return base
    
    def parse_unary(self) -> Dict[str, Any]:
        """解析一元运算符"""
        token = self.peek()
        
        if token and token[1] == '-':
            self.advance()
            operand = self.parse_primary()
            return {'type': 'unary_minus', 'operand': operand}
        
        if token and token[1] in ('NOT', '!'):
            self.advance()
            operand = self.parse_primary()
            return {'type': 'unary_not', 'operand': operand}
        
        return self.parse_primary()
    
    def parse_primary(self) -> Dict[str, Any]:
        """解析基本表达式"""
        token = self.peek()

        if token is None:
            raise FormulaError("表达式不完整")

        # 整列引用 [表名].[字段名]
        if token[0] == 'COLUMN_REF':
            ref = self.advance()[1]
            m = re.match(r'^\[([^\[\]{}]+)\]\s*\.\s*\[([^\[\]{}]+)\]$', ref)
            if not m:
                raise FormulaError(f"无效的整列引用: {ref}")
            return {
                'type': 'column_ref',
                'table': m.group(1).strip(),
                'field': m.group(2).strip(),
            }

        # CurrentValue（惰性条件中的当前元素）
        if token[0] == 'CURRENT_VALUE':
            self.advance()
            return {'type': 'current_value'}

        # 数字字面量
        if token[0] == 'NUMBER':
            value = self.advance()[1]
            if '.' in value:
                return {'type': 'number', 'value': float(value)}
            return {'type': 'number', 'value': int(value)}
        
        # 字符串字面量
        if token[0] == 'STRING':
            value = self.advance()[1][1:-1]
            return {'type': 'string', 'value': value}
        
        # 字段引用
        if token[0] == 'FIELD_REF':
            ref = self.advance()[1]
            field_name = ref[1:-1]
            return {'type': 'field_ref', 'name': field_name}
        
        # 零参数函数（PI/E 等）和特殊关键字（DEFAULT）
        if token[0] == 'IDENTIFIER':
            name = token[1].upper()
            zero_arg_funcs = {'PI', 'E', 'RAND', 'TODAY', 'NOW', 'BLANK'}
            
            if name in zero_arg_funcs:
                self.advance()
                return {'type': 'function_call', 'name': name, 'arguments': []}
            
            if name == 'DEFAULT':
                self.advance()
                return {'type': 'default_keyword', 'value': 'DEFAULT'}
            
        # 布尔常量
        if token[0] == 'IDENTIFIER' and token[1] in ('TRUE', 'FALSE'):
            value = self.advance()[1] == 'TRUE'
            return {'type': 'boolean', 'value': value}
        
        # NULL / BLANK (fallback)
        if token[0] == 'IDENTIFIER' and token[1] in ('NULL',):
            self.advance()
            return {'type': 'null'}
        
        # 函数调用
        if token[0] == 'FUNCTION':
            func_name = self.advance()[1].upper()
            self.expect('LPAREN')
            
            args = []
            if self.peek() and self.peek()[0] != 'RPAREN':
                args.append(self.parse_expression())
                
                while self.peek() and self.peek()[0] == 'COMMA':
                    self.advance()
                    args.append(self.parse_expression())
            
            self.expect('RPAREN')
            return {'type': 'function_call', 'name': func_name, 'arguments': args}
        
        # 括号表达式
        if token[0] == 'LPAREN':
            self.advance()
            expr = self.parse_expression()
            self.expect('RPAREN')
            return expr
        
        raise FormulaError(f"意外的 token: {token}")


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
        elif op == '>':
            return left > right if left is not None and right is not None else False
        elif op == '<':
            return left < right if left is not None and right is not None else False
        elif op == '>=':
            return left >= right if left is not None and right is not None else False
        elif op == '<=':
            return left <= right if left is not None and right is not None else False
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


# ==================== 数学函数注册 ====================

@FormulaEvaluator.register('ABS')
def fn_abs(args: List[Any]) -> Union[int, float]:
    """绝对值"""
    val = args[0]
    return abs(val) if val is not None else None

@FormulaEvaluator.register('ROUND')
def fn_round(args: List[Any]) -> float:
    """四舍五入"""
    val = args[0]
    digits = int(args[1]) if len(args) > 1 else 0
    return round(val, digits) if val is not None else None

@FormulaEvaluator.register('CEILING')
def fn_ceiling(args: List[Any]) -> int:
    """向上取整"""
    val = args[0]
    return math.ceil(val) if val is not None else None

@FormulaEvaluator.register('FLOOR')
def fn_floor(args: List[Any]) -> int:
    """向下取整"""
    val = args[0]
    return math.floor(val) if val is not None else None

@FormulaEvaluator.register('POWER')
def fn_power(args: List[Any]) -> float:
    """幂运算"""
    base = args[0]
    exp = args[1]
    return base ** exp if base is not None and exp is not None else None

@FormulaEvaluator.register('SQRT')
def fn_sqrt(args: List[Any]) -> float:
    """平方根"""
    val = args[0]
    if val is None:
        return None
    if val < 0:
        raise FormulaError("SQRT 的参数必须非负")
    return math.sqrt(val)

@FormulaEvaluator.register('MOD')
def fn_mod(args: List[Any]) -> float:
    """取模"""
    a = args[0]
    b = args[1]
    if a is None or b is None:
        return None
    if b == 0:
        raise FormulaError("MOD 除数不能为零")
    return a % b

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
    """自然对数"""
    val = args[0]
    if val is None:
        return None
    if val <= 0:
        raise FormulaError("LN 参数必须大于零")
    return math.log(val)

@FormulaEvaluator.register('LOG')
def fn_log(args: List[Any]) -> float:
    """对数"""
    val = args[0]
    base = args[1] if len(args) > 1 else 10
    if val is None:
        return None
    if val <= 0 or base <= 0 or base == 1:
        raise FormulaError("LOG 参数无效")
    return math.log(val, base)

@FormulaEvaluator.register('EXP')
def fn_exp(args: List[Any]) -> float:
    """e 的幂"""
    val = args[0]
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
    """指定范围内的随机整数"""
    lo = int(args[0])
    hi = int(args[1])
    import random
    return random.randint(lo, hi)


# ==================== 文本函数注册 ====================

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
    """将文本转为数字"""
    val = args[0]
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            return float(val)
        cleaned = str(val).replace(',', '').replace(' ', '')
        return float(cleaned)
    except (ValueError, TypeError):
        raise FormulaError(f"无法将 '{val}' 转换为数字")


# ==================== 日期函数注册 ====================

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


# ==================== 逻辑函数注册 ====================

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


# ==================== 统计函数注册 ====================

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
    """去重"""
    seen = set()
    result = []
    for val in args:
        key = json.dumps(val, sort_keys=True, default=str) if not isinstance(val, (str, int, float, bool, type(None))) else val
        if key not in seen:
            seen.add(key)
            result.append(val)
    return result


class FormulaService:
    """
    公式计算服务类（主入口）
    
    提供记录级别的公式计算、批量重算、缓存等功能
    """
    
    _parser = FormulaParser()

    # 整列引用 [表].[字段] 检测（用于判断是否需要表数据上下文与禁用缓存）
    _COLUMN_REF_RE = re.compile(r'\[([^\[\]{}]+)\]\s*\.\s*\[([^\[\]{}]+)\]')

    # 整列数据上下文的进程内缓存：{table_id: (过期时间戳, base_id, context)}
    # TTL 兜底 + 记录/字段/表写路径主动失效（invalidate_table_context_cache）
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

    @classmethod
    def compute_record_formulas(
        cls,
        table_id: str,
        values: Dict[str, Any],
        user_id: str = None,
        formula_fields: List[Field] = None,
        table_context: Optional[Dict[str, Dict[str, List[Any]]]] = None
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

        # 获取表格所有字段，用于构建字段名到值的映射
        all_fields = Field.query.filter_by(table_id=table_id).all()
        field_id_to_name = {str(f.id): f.name for f in all_fields}

        # 构建以字段名为 key 的上下文（公式引擎用字段名引用）
        context_by_name = {}
        for field_id, value in values.items():
            field_name = field_id_to_name.get(str(field_id))
            if field_name:
                context_by_name[field_name] = value

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

        offset = 0
        while offset < total_records:
            records = Record.query.filter_by(
                table_id=table_id,
                is_deleted=False
            ).offset(offset).limit(batch_size).all()

            for record in records:
                values = record.values or {}

                for field in formula_fields:
                    formula_expr = (field.config or {}).get('formula', '')

                    if not formula_expr:
                        continue

                    try:
                        result = cls.evaluate_formula(
                            formula_expr,
                            values,
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
