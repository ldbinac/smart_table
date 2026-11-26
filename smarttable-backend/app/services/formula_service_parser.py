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
        # 函数名大小写不敏感（value(...) 与 VALUE(...) 等价，parser 求值时统一 upper）
        ('FUNCTION', r'(?i:[A-Z_][A-Z0-9_]*)(?=\s*\()'),
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

        # 全角符号归一化：全角括号/逗号常由中文输入法误输入，统一转半角后解析
        formula = formula.replace('（', '(').replace('）', ')').replace('，', ',')

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
