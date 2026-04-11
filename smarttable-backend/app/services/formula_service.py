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
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
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
        ('FIELD_REF', r'\{[^}]+\}'),
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
    
    def __init__(self, context: Dict[str, Any]):
        """
        初始化求值器
        
        Args:
            context: 计算上下文，包含字段名到值的映射
        """
        self.context = context
    
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
    
    def _eval_function(self, node: Dict[str, Any]) -> Any:
        """求值函数调用"""
        func_name = node['name'].upper()
        
        if func_name not in self.FUNCTIONS:
            raise FormulaError(f"未知函数: {func_name}")
        
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

@FormulaEvaluator.register('SUM')
def fn_sum(args: List[Any]) -> Optional[float]:
    """求和"""
    values = [v for v in args if v is not None]
    return sum(values) if values else 0

@FormulaEvaluator.register('AVG')
def fn_avg(args: List[Any]) -> Optional[float]:
    """平均值"""
    values = [float(v) for v in args if v is not None]
    return sum(values) / len(values) if values else None

@FormulaEvaluator.register('MAX')
def fn_max(args: List[Any]) -> Any:
    """最大值"""
    values = [v for v in args if v is not None]
    return max(values) if values else None

@FormulaEvaluator.register('MIN')
def fn_min(args: List[Any]) -> Any:
    """最小值"""
    values = [v for v in args if v is not None]
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
    return datetime.utcnow()

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
    if isinstance(val, datetime):
        return val.year
    if isinstance(val, date):
        return val.year
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
            return dt.year
        except ValueError:
            pass
    return None

@FormulaEvaluator.register('MONTH')
def fn_month(args: List[Any]) -> Optional[int]:
    """获取月份"""
    val = args[0]
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.month
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
            return dt.month
        except ValueError:
            pass
    return None

@FormulaEvaluator.register('DAY')
def fn_day(args: List[Any]) -> Optional[int]:
    """获取日期"""
    val = args[0]
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.day
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
            return dt.day
        except ValueError:
            pass
    return None

@FormulaEvaluator.register('HOUR')
def fn_hour(args: List[Any]) -> Optional[int]:
    """获取小时"""
    val = args[0]
    if isinstance(val, datetime):
        return val.hour
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
            return dt.hour
        except ValueError:
            pass
    return None

@FormulaEvaluator.register('MINUTE')
def fn_minute(args: List[Any]) -> Optional[int]:
    """获取分钟"""
    val = args[0]
    if isinstance(val, datetime):
        return val.minute
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
            return dt.minute
        except ValueError:
            pass
    return None

@FormulaEvaluator.register('SECOND')
def fn_second(args: List[Any]) -> Optional[int]:
    """获取秒"""
    val = args[0]
    if isinstance(val, datetime):
        return val.second
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
            return dt.second
        except ValueError:
            pass
    return None

@FormulaEvaluator.register('WEEKDAY')
def fn_weekday(args: List[Any]) -> Optional[int]:
    """获取星期几 (1=周一, 7=周日)"""
    val = args[0]
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        wd = val.weekday()
        return wd + 1
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
            return dt.weekday() + 1
        except ValueError:
            pass
    return None

@FormulaEvaluator.register('DATEADD')
def fn_dateadd(args: List[Any]) -> datetime:
    """日期加法"""
    start_date = args[0]
    unit = str(args[1]).lower() if len(args) > 1 else 'days'
    amount = int(args[2]) if len(args) > 2 else 0
    
    if start_date is None:
        return None
    
    if isinstance(start_date, str):
        try:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise FormulaError("无效的日期格式")
    
    unit_map = {
        'years': 'years',
        'months': 'months',
        'weeks': 'weeks',
        'days': 'days',
        'hours': 'hours',
        'minutes': 'minutes',
        'seconds': 'seconds'
    }
    
    kwargs = {unit_map.get(unit, 'days'): amount}
    from dateutil.relativedelta import relativedelta
    return start_date + relativedelta(**kwargs)

@FormulaEvaluator.register('DATEDIFF')
def fn_datediff(args: List[Any]) -> int:
    """日期差"""
    start_date = args[0]
    end_date = args[1]
    unit = str(args[2]).lower() if len(args) > 2 else 'days'
    
    if start_date is None or end_date is None:
        return None
    
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    
    delta = end_date - start_date
    
    unit_map = {
        'days': delta.days,
        'hours': int(delta.total_seconds() / 3600),
        'minutes': int(delta.total_seconds() / 60),
        'seconds': int(delta.total_seconds()),
        'weeks': int(delta.days / 7),
        'months': (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month),
        'years': end_date.year - start_date.year,
    }
    
    return unit_map.get(unit, delta.days)

@FormulaEvaluator.register('DATETIME_FORMAT')
def fn_datetime_format(args: List[Any]) -> str:
    """格式化日期时间"""
    val = args[0]
    fmt = args[1] if len(args) > 1 else '%Y-%m-%d %H:%M:%S'
    
    if val is None:
        return ''
    
    if isinstance(val, str):
        try:
            val = datetime.fromisoformat(val.replace('Z', '+00:00'))
        except ValueError:
            return str(val)
    
    if isinstance(val, (datetime, date)):
        return val.strftime(str(fmt))
    
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
    """多条件判断"""
    if len(args) % 2 != 0:
        raise FormulaError("IFS 需要偶数个参数（条件/值对）")
    
    for i in range(0, len(args), 2):
        condition = args[i]
        value = args[i + 1]
        if condition is not None and condition:
            return value
    
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
    """计数（仅数字）"""
    count = 0
    for val in args:
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            count += 1
    return count

@FormulaEvaluator.register('COUNTA')
def fn_counta(args: List[Any]) -> int:
    """计数（非空）"""
    count = 0
    for val in args:
        if val is not None and val != '':
            count += 1
    return count

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
    values = [float(v) for v in args if v is not None and isinstance(v, (int, float))]
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)

@FormulaEvaluator.register('VAR')
def fn_var(args: List[Any]) -> Optional[float]:
    """方差"""
    values = [float(v) for v in args if v is not None and isinstance(v, (int, float))]
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / (len(values) - 1)

@FormulaEvaluator.register('MEDIAN')
def fn_median(args: List[Any]) -> Optional[float]:
    """中位数"""
    values = sorted([float(v) for v in args if v is not None and isinstance(v, (int, float))])
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
    values = [v for v in args if v is not None and isinstance(v, (int, float))]
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
    value = args[0]
    all_values = [v for v in args[1:] if v is not None and isinstance(v, (int, float))]
    
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
    
    @classmethod
    def evaluate_formula(
        cls,
        formula: str,
        context: Dict[str, Any],
        use_cache: bool = True
    ) -> Any:
        """
        计算单个公式表达式（任务 29.1）
        
        Args:
            formula: 公式字符串，如 "{price} * {quantity}"
            context: 字段上下文，如 {"price": 100, "quantity": 5}
            use_cache: 是否使用缓存
            
        Returns:
            计算结果
            
        Raises:
            FormulaError: 公式语法或执行错误
        """
        if not formula or not formula.strip():
            return None
        
        cache_key = None
        if use_cache:
            cache_key = cls._build_cache_key(formula, context)
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            ast = cls._parser.parse(formula)
            evaluator = FormulaEvaluator(context)
            result = evaluator.evaluate(ast)
            
            if cache_key:
                cache.set(cache_key, result, timeout=300)
            
            return result
            
        except FormulaError:
            raise
        except Exception as e:
            raise FormulaError(f"公式计算失败: {str(e)}")
    
    @classmethod
    def compute_record_formulas(
        cls,
        table_id: str,
        values: Dict[str, Any],
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        计算记录中所有公式的值（任务 30.1）
        
        在记录保存时调用，自动计算所有公式字段并返回结果
        
        Args:
            table_id: 表格 ID
            values: 记录的原始字段值字典 {field_name_or_id: value}
            user_id: 操作用户 ID（可选，用于审计）
            
        Returns:
            公式字段计算结果字典 {field_name: computed_value}
        """
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
        
        results = {}
        
        for field in formula_fields:
            formula_config = field.config or {}
            formula_expr = formula_config.get('formula', '')
            
            if not formula_expr:
                continue
            
            try:
                result = cls.evaluate_formula(formula_expr, values)
                results[field.name] = result
                
                if field.config is None:
                    field.config = {}
                field.config['_last_computed'] = {
                    'result': cls._serialize_result(result),
                    'computed_at': datetime.utcnow().isoformat(),
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
                            use_cache=False
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
                {'name': 'DATEADD', 'desc': '日期加法', 'syntax': 'DATEADD(date, unit, amount)'},
                {'name': 'DATEDIFF', 'desc': '日期差', 'syntax': 'DATEDIFF(start, end, unit)'},
                {'name': 'DATETIME_FORMAT', 'desc': '格式化日期', 'syntax': 'DATETIME_FORMAT(date, format)'},
                {'name': 'FROMUNIXTIME', 'desc': '时间戳转日期', 'syntax': 'FROMUNIXTIME(timestamp)'},
                {'name': 'UNIXTIMESTAMP', 'desc': '日期转时间戳', 'syntax': 'UNIXTIMESTAMP(date)'},
            ],
            '逻辑': [
                {'name': 'IF', 'desc': '条件判断', 'syntax': 'IF(condition, true_value, false_value)'},
                {'name': 'IFS', 'desc': '多条件判断', 'syntax': 'IFS(cond1, val1, cond2, val2, ...)'},
                {'name': 'SWITCH', 'desc': '多值匹配', 'syntax': 'SWITCH(expr, val1, res1, ..., DEFAULT, default)'},
                {'name': 'AND', 'desc': '逻辑与', 'syntax': 'AND(cond1, cond2, ...)'},
                {'name': 'OR', 'desc': '逻辑或', 'syntax': 'OR(cond1, cond2, ...)'},
                {'name': 'NOT', 'desc': '逻辑非', 'syntax': 'NOT(condition)'},
                {'name': 'XOR', 'desc': '异或', 'syntax': 'XOR(cond1, cond2)'},
                {'name': 'ISBLANK', 'desc': '判断是否为空', 'syntax': 'ISBLANK(value)'},
                {'name': 'ISERROR', 'desc': '判断是否为错误', 'syntax': 'ISERROR(value)'},
                {'name': 'ISNUMBER', 'desc': '判断是否为数字', 'syntax': 'ISNUMBER(value)'},
                {'name': 'ISTEXT', 'desc': '判断是否为文本', 'syntax': 'ISTEXT(value)'},
                {'name': 'ISDATE', 'desc': '判断是否为日期', 'syntax': 'ISDATE(value)'},
                {'name': 'BLANK', 'desc': '返回空值', 'syntax': 'BLANK()'},
            ],
            '统计': [
                {'name': 'COUNT', 'desc': '计数(数字)', 'syntax': 'COUNT(value1, value2, ...)'},
                {'name': 'COUNTA', 'desc': '计数(非空)', 'syntax': 'COUNTA(value1, value2, ...)'},
                {'name': 'COUNTBLANK', 'desc': '计数(空值)', 'syntax': 'COUNTBLANK(value1, value2, ...)'},
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
