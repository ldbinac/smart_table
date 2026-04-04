"""
公式引擎单元测试
覆盖公式解析器、求值器、69+ 内置函数、FormulaService 主入口
"""
import pytest
from datetime import datetime, date, timedelta
from app.services.formula_service import (
    FormulaService,
    FormulaParser,
    FormulaEvaluator,
    FormulaError,
)


class TestFormulaParser:
    """公式解析器测试"""
    
    def setup_method(self):
        self.parser = FormulaParser()
    
    def test_parse_number(self):
        """解析数字字面量"""
        ast = self.parser.parse('42')
        assert ast['type'] == 'number'
        assert ast['value'] == 42
    
    def test_parse_float(self):
        """解析浮点数字面量"""
        ast = self.parser.parse('3.14')
        assert ast['type'] == 'number'
        assert abs(ast['value'] - 3.14) < 0.001
    
    def test_parse_negative_number(self):
        """解析负数（NUMBER 正则包含可选负号前缀）"""
        ast = self.parser.parse('-10')
        assert ast['type'] == 'number'
        assert ast['value'] == -10
    
    def test_parse_string(self):
        """解析字符串字面量"""
        ast = self.parser.parse('"hello"')
        assert ast['type'] == 'string'
        assert ast['value'] == 'hello'
    
    def test_parse_field_ref(self):
        """解析字段引用"""
        ast = self.parser.parse('{price}')
        assert ast['type'] == 'field_ref'
        assert ast['name'] == 'price'
    
    def test_parse_function_call(self):
        """解析函数调用"""
        ast = self.parser.parse('SUM({a}, {b})')
        assert ast['type'] == 'function_call'
        assert ast['name'] == 'SUM'
        assert len(ast['arguments']) == 2
    
    def test_parse_binary_op_add(self):
        """解析加法运算"""
        ast = self.parser.parse('{a} + {b}')
        assert ast['type'] == 'binary_op'
        assert ast['operator'] == '+'
    
    def test_parse_binary_op_multiply(self):
        """解析乘法运算（优先级高于加法）"""
        ast = self.parser.parse('{a} + {b} * {c}')
        assert ast['operator'] == '+'
        assert ast['right']['operator'] == '*'
    
    def test_parse_comparison_eq(self):
        """解析等于比较"""
        ast = self.parser.parse('{a} = {b}')
        assert ast['type'] == 'comparison'
        assert ast['operator'] == '='
    
    def test_parse_comparison_neq(self):
        """解析不等于比较"""
        ast = self.parser.parse('{a} <> {b}')
        assert ast['type'] == 'comparison'
        assert ast['operator'] == '<>'
    
    def test_parse_nested_parens(self):
        """解析嵌套括号"""
        ast = self.parser.parse('({a} + {b}) * 2')
        assert ast['type'] == 'binary_op'
        assert ast['operator'] == '*'
        assert ast['left']['type'] == 'binary_op'
    
    def test_parse_boolean_true(self):
        """解析布尔常量 TRUE"""
        ast = self.parser.parse('TRUE')
        assert ast['type'] == 'boolean'
        assert ast['value'] is True
    
    def test_parse_boolean_false(self):
        """解析布尔常量 FALSE"""
        ast = self.parser.parse('FALSE')
        assert ast['type'] == 'boolean'
        assert ast['value'] is False
    
    def test_parse_blank(self):
        """解析 BLANK()（零参数函数）"""
        ast = self.parser.parse('BLANK()')
        assert ast['type'] == 'function_call'
        assert ast['name'] == 'BLANK'
    
    def test_parse_complex_formula(self):
        """解析复杂公式：IF({status}="done", {score}*1.2, {score})"""
        ast = self.parser.parse('IF({status}="done", {score}*1.2, {score})')
        assert ast['type'] == 'function_call'
        assert ast['name'] == 'IF'
        assert len(ast['arguments']) == 3
    
    def test_parse_empty_formula_raises_error(self):
        """空公式应报错"""
        with pytest.raises(FormulaError):
            self.parser.parse('')
        
        with pytest.raises(FormulaError):
            self.parser.parse('   ')
    
    def test_parse_invalid_char_raises_error(self):
        """非法字符应报错"""
        with pytest.raises(FormulaError):
            self.parser.parse('@invalid')


class TestFormulaEvaluator:
    """公式求值器测试"""
    
    def _eval(self, formula, context=None):
        parser = FormulaParser()
        ast = parser.parse(formula)
        evaluator = FormulaEvaluator(context or {})
        return evaluator.evaluate(ast)
    
    def test_eval_number(self):
        """求值数字"""
        assert self._eval('42') == 42
        assert self._eval('3.14') == pytest.approx(3.14)
    
    def test_eval_string(self):
        """求值字符串"""
        assert self._eval('"hello"') == 'hello'
    
    def test_eval_field_ref(self):
        """求值字段引用"""
        assert self._eval('{price}', {'price': 100}) == 100
    
    def test_eval_add(self):
        """加法运算"""
        assert self._eval('{a} + {b}', {'a': 10, 'b': 20}) == 30
    
    def test_eval_subtract(self):
        """减法运算"""
        assert self._eval('{a} - {b}', {'a': 20, 'b': 5}) == 15
    
    def test_eval_multiply(self):
        """乘法运算"""
        assert self._eval('{a} * {b}', {'a': 6, 'b': 7}) == 42
    
    def test_eval_divide(self):
        """除法运算"""
        assert self._eval('{a} / {b}', {'a': 20, 'b': 4}) == 5.0
    
    def test_eval_divide_by_zero_raises_error(self):
        """除以零应报错"""
        with pytest.raises(FormulaError):
            self._eval('{a} / 0', {'a': 10})
    
    def test_eval_power(self):
        """幂运算"""
        assert self._eval('2 ^ 10') == 1024
    
    def test_eval_comparison_eq(self):
        """等于比较"""
        assert self._eval('{a} = {b}', {'a': 5, 'b': 5}) is True
        assert self._eval('{a} = {b}', {'a': 5, 'b': 3}) is False
    
    def test_eval_comparison_neq(self):
        """不等于比较"""
        assert self._eval('{a} <> {b}', {'a': 5, 'b': 3}) is True
    
    def test_eval_comparison_gt_lt(self):
        """大于/小于比较"""
        assert self._eval('{a} > {b}', {'a': 5, 'b': 3}) is True
        assert self._eval('{a} < {b}', {'a': 5, 'b': 3}) is False
    
    def test_eval_null_handling(self):
        """空值处理（任一操作数为 null 则结果为 null）"""
        result = self._eval('{a} + {b}', {'a': None, 'b': 10})
        assert result is None


class TestMathFunctions:
    """数学函数测试"""
    
    def _eval(self, formula, context=None):
        return FormulaService.evaluate_formula(formula, context or {}, use_cache=False)
    
    def test_sum(self):
        """SUM 求和"""
        assert self._eval('SUM(1, 2, 3, 4, 5)') == 15
        assert self._eval('SUM({a}, {b}, {c})', {'a': 10, 'b': 20, 'c': 30}) == 60
    
    def test_sum_empty(self):
        """SUM 空参数返回 0"""
        assert self._eval('SUM()') == 0
    
    def test_avg(self):
        """AVG 平均值"""
        result = self._eval('AVG(2, 4, 6)')
        assert abs(result - 4.0) < 0.001
    
    def test_max_min(self):
        """MAX/MIN 最大最小值"""
        assert self._eval('MAX(3, 1, 4, 1, 5)') == 5
        assert self._eval('MIN(3, 1, 4, 1, 5)') == 1
    
    def test_abs(self):
        """ABS 绝对值"""
        assert self._eval('ABS(-42)') == 42
        assert self._eval('ABS(42)') == 42
        assert self._eval('ABS({val})', {'val': -100}) == 100
    
    def test_round(self):
        """ROUND 四舍五入"""
        assert self._eval('ROUND(3.14159, 2)') == 3.14
        assert self._eval('ROUND(3.5)') == 4
        assert self._eval('ROUND(2.7)') == 3
    
    def test_ceiling_floor(self):
        """CEILING/FLOOR 取整"""
        assert self._eval('CEILING(3.2)') == 4
        assert self._eval('FLOOR(3.8)') == 3
    
    def test_sqrt(self):
        """SQRT 平方根"""
        result = self._eval('SQRT(16)')
        assert result == 4.0
    
    def test_sqrt_negative_raises_error(self):
        """SQRT 负数应报错"""
        with pytest.raises(FormulaError):
            self._eval('SQRT(-1)')
    
    def test_power_func(self):
        """POWER 幂运算"""
        assert self._eval('POWER(2, 10)') == 1024
    
    def test_mod(self):
        """MOD 取模"""
        assert self._eval('MOD(17, 5)') == 2
    
    def test_mod_zero_raises_error(self):
        """MOD 除零应报错"""
        with pytest.raises(FormulaError):
            self._eval('MOD(10, 0)')
    
    def test_ln_log_exp(self):
        """LN/LOG/EXP 对数指数"""
        import math
        assert abs(self._eval('EXP(0)') - 1.0) < 0.001
        assert abs(self._eval('LN(1)') - 0.0) < 0.001
        result = self._eval('LOG(100, 10)')
        assert abs(result - 2.0) < 0.001
    
    def test_pi_e(self):
        """PI/E 常量"""
        import math
        assert abs(self._eval('PI') - math.pi) < 0.0001
        assert abs(self._eval('E') - math.e) < 0.0001
    
    def test_rand_between(self):
        """RANDBETWEEN 范围随机整数"""
        for _ in range(10):
            val = self._eval('RANDBETWEEN(1, 10)')
            assert 1 <= val <= 10


class TestTextFunctions:
    """文本函数测试"""
    
    def _eval(self, formula, ctx=None):
        return FormulaService.evaluate_formula(formula, ctx or {}, use_cache=False)
    
    def test_concat(self):
        """CONCAT 拼接文本"""
        assert self._eval('CONCAT("Hello", " ", "World")') == 'Hello World'
        assert self._eval('CONCAT({a}, {b})', {'a': 'foo', 'b': 'bar'}) == 'foobar'
    
    def test_upper_lower(self):
        """UPPER/LOWER 大小写转换"""
        assert self._eval('UPPER("hello")') == 'HELLO'
        assert self._eval('LOWER("HELLO")') == 'hello'
        assert self._eval('UPPER({v})', {'v': 'mixed'}) == 'MIXED'
    
    def test_len(self):
        """LEN 文本长度"""
        assert self._eval('LEN("hello")') == 5
        assert self._eval('LEN("")') == 0
    
    def test_trim(self):
        """TRIM 去除首尾空白"""
        assert self._eval('TRIM("  hello  ")') == 'hello'
    
    def test_left_right_mid(self):
        """LEFT/RIGHT/MID 子串提取"""
        assert self._eval('LEFT("Hello World", 5)') == 'Hello'
        assert self._eval('RIGHT("Hello World", 5)') == 'World'
        assert self._eval('MID("Hello World", 7, 5)') == 'World'
    
    def test_replace(self):
        """REPLACE 替换文本"""
        assert self._eval('REPLACE("Hello World", 7, 5, "Universe")') == 'Hello Universe'
    
    def test_substitute(self):
        """SUBSTITUTE 替换子串"""
        assert self._eval('SUBSTITUTE("abc abc abc", "abc", "x")') == 'x x x'
    
    def test_find(self):
        """FIND 查找子串位置"""
        assert self._eval('FIND("World", "Hello World")') == 7
        assert self._eval('FIND("xyz", "Hello World")') is None
    
    def test_rept(self):
        """REPT 重复文本"""
        assert self._eval('REPT("ab", 3)') == 'ababab'
    
    def test_text_format(self):
        """TEXT 格式化数字"""
        assert self._eval('TEXT(0.75, "0%")') == '75%'
        assert self._eval('TEXT(1234.56, "#,##0.00")') == '1,234.56'
    
    def test_value_conversion(self):
        """VALUE 文本转数字"""
        assert self._eval('VALUE("123.45")') == 123.45


class TestDateFunctions:
    """日期函数测试"""
    
    def _eval(self, formula, ctx=None):
        return FormulaService.evaluate_formula(formula, ctx or {}, use_cache=False)
    
    def test_now_today(self):
        """NOW/TODAY 当前时间"""
        now = self._eval('NOW()')
        assert isinstance(now, (datetime,))
        
        today = self._eval('TODAY()')
        assert isinstance(today, (date,))
    
    def test_year_month_day(self):
        """YEAR/MONTH/DAY 提取日期部分"""
        dt = '2025-06-15'
        assert self._eval(f'YEAR("{dt}")') == 2025
        assert self._eval(f'MONTH("{dt}")') == 6
        assert self._eval(f'DAY("{dt}")') == 15
    
    def test_hour_minute_second(self):
        """HOUR/MINUTE/SECOND 提取时间部分"""
        dt = '2025-06-15T14:30:45'
        assert self._eval(f'HOUR("{dt}")') == 14
        assert self._eval(f'MINUTE("{dt}")') == 30
        assert self._eval(f'SECOND("{dt}")') == 45
    
    def test_weekday(self):
        """WEEKDAY 星期几"""
        dt = '2025-01-06'  # Monday
        wd = self._eval(f'WEEKDAY("{dt}")')
        assert isinstance(wd, int)
        assert 1 <= wd <= 7
    
    def test_datetime_format(self):
        """DATETIME_FORMAT 格式化日期"""
        result = self._eval('DATETIME_FORMAT("2025-06-15", "%Y年%m月%d日")')
        assert '2025' in result
        assert '06' in result
        assert '15' in result


class TestLogicFunctions:
    """逻辑函数测试"""
    
    def _eval(self, formula, ctx=None):
        return FormulaService.evaluate_formula(formula, ctx or {}, use_cache=False)
    
    def test_if_true(self):
        """IF 条件为真"""
        assert self._eval('IF(TRUE, "yes", "no")') == 'yes'
        assert self._eval('IF(1=1, "yes", "no")') == 'yes'
    
    def test_if_false(self):
        """IF 条件为假"""
        assert self._eval('IF(FALSE, "yes", "no")') == 'no'
        assert self._eval('IF(1=2, "yes", "no")') == 'no'
    
    def test_if_null_returns_false_branch(self):
        """IF 条件为 NULL 返回 false 分支"""
        assert self._eval('IF(NULL, "yes", "no")') == 'no'
    
    def test_ifs(self):
        """IFS 多条件判断"""
        assert self._eval('IFS(TRUE, "first", TRUE, "second")') == 'first'
        assert self._eval('IFS(FALSE, "a", TRUE, "b")') == 'b'
        assert self._eval('IFS(FALSE, "a", FALSE, "b")') is None
    
    def test_switch_match(self):
        """SWITCH 匹配"""
        assert self._eval('SWITCH("b", "a", 1, "b", 2, DEFAULT, 99)') == 2
    
    def test_switch_default(self):
        """SWITCH 默认值"""
        assert self._eval('SWITCH("x", "a", 1, "b", 2, DEFAULT, 99)') == 99
    
    def test_and_or_not(self):
        """AND/OR/NOT 逻辑运算"""
        assert self._eval('AND(TRUE, TRUE)') is True
        assert self._eval('AND(TRUE, FALSE)') is False
        assert self._eval('OR(FALSE, TRUE)') is True
        assert self._eval('OR(FALSE, FALSE)') is False
        assert self._eval('NOT(TRUE)') is False
        assert self._eval('NOT(FALSE)') is True
    
    def test_isblank(self):
        """ISBLANK 判断是否为空"""
        assert self._eval('ISBLANK(NULL)') is True
        assert self._eval('ISBLANK("")') is True
        assert self._eval('ISBLANK("text")') is False
        assert self._eval('ISBLANK(0)') is False
    
    def test_isnumber_istext_isdate(self):
        """ISNUMBER/ISTEXT/ISDATE 类型检查"""
        assert self._eval('ISNUMBER(42)') is True
        assert self._eval('ISNUMBER("42")') is False
        assert self._eval('ISTEXT("hello")') is True
        assert self._eval('ISTEXT(42)') is False
        assert self._eval('ISDATE("2025-01-01")') is True
        assert self._eval('ISDATE("not-date")') is False
    
    def test_xor(self):
        """XOR 异或"""
        assert self._eval('XOR(TRUE, FALSE)') is True
        assert self._eval('XOR(TRUE, TRUE)') is False


class TestStatFunctions:
    """统计函数测试"""
    
    def _eval(self, formula, ctx=None):
        return FormulaService.evaluate_formula(formula, ctx or {}, use_cache=False)
    
    def test_count(self):
        """COUNT 计数（仅数字）"""
        assert self._eval('COUNT(1, "a", 3, NULL)') == 2
    
    def test_counta(self):
        """COUNTA 计数（非空）"""
        assert self._eval('COUNTA(1, "a", "", NULL)') == 2
    
    def test_countblank(self):
        """COUNTBLANK 计数（空值）"""
        assert self._eval('COUNTBLANK(1, "", NULL, "a")') == 2
    
    def test_stdev_var(self):
        """STDEV/VAR 标准差方差"""
        import math
        stdev = self._eval('STDEV(2, 4, 4, 4, 5, 5, 7, 9)')
        assert stdev is not None
        assert stdev > 0
        
        var = self._eval('VAR(2, 4, 4, 4, 5, 5, 7, 9)')
        assert var is not None
        assert var > 0
    
    def test_median(self):
        """MEDIAN 中位数"""
        assert self._eval('MEDIAN(1, 3, 5)') == 3
        assert self._eval('MEDIAN(1, 2, 3, 4)') == 2.5
    
    def test_mode(self):
        """MODE 众数"""
        assert self._eval('MODE(1, 2, 2, 3, 3, 3)') == 3
    
    def test_rank(self):
        """RANK 排名"""
        assert self._eval('RANK(3, 1, 2, 3, 4, 5)') == 3
        assert self._eval('RANK(1, 1, 2, 3, 4, 5)') == 1
    
    def test_unique(self):
        """UNIQUE 去重"""
        result = self._eval('UNIQUE(1, 2, 2, 3, 3, 3)')
        assert set(result) == {1, 2, 3}


class TestFormulaServiceEntryPoints:
    """FormulaService 主入口方法测试"""
    
    def test_validate_syntax_valid(self):
        """验证有效语法"""
        ok, err = FormulaService.validate_formula_syntax('{a} + {b}')
        assert ok is True
        assert err is None
    
    def test_validate_syntax_invalid(self):
        """验证无效语法"""
        ok, err = FormulaService.validate_formula_syntax('{a} + + {b}')
        assert ok is False
        assert err is not None
    
    def test_validate_empty(self):
        """验证空公式"""
        ok, err = FormulaService.validate_formula_syntax('')
        assert ok is True
        
        ok, err = FormulaService.validate_formula_syntax(None)
        assert ok is True
    
    def test_get_dependencies(self):
        """获取公式依赖字段"""
        deps = FormulaService.get_formula_dependencies('{price} * {quantity} + {tax}')
        assert 'price' in deps
        assert 'quantity' in deps
        assert 'tax' in deps
        assert len(deps) == 3
    
    def test_get_dependencies_no_refs(self):
        """无字段引用的公式"""
        deps = FormulaService.get_formula_dependencies('SUM(1, 2, 3)')
        assert len(deps) == 0
    
    def test_get_function_list(self):
        """获取函数列表"""
        funcs = FormulaService.get_function_list()
        assert len(funcs) > 50
        names = [f['name'] for f in funcs]
        assert 'SUM' in names
        assert 'IF' in names
        assert 'CONCAT' in names
        assert 'NOW' in names
    
    def test_serialize_result_none(self):
        """序列化 NULL 结果"""
        from app.services.formula_service import FormulaService as FS
        assert FS._serialize_result(None) is None
    
    def test_serialize_result_datetime(self):
        """序列化日期结果"""
        from app.services.formula_service import FormulaService as FS
        dt = datetime(2025, 6, 15, 12, 0, 0)
        result = FS._serialize_result(dt)
        assert '2025' in result
    
    def test_serialize_result_float_special(self):
        """序列化特殊浮点数"""
        from app.services.formula_service import FormulaService as FS
        assert '#ERROR' in FS._serialize_result(float('nan'))
        assert '#ERROR' in FS._serialize_result(float('inf'))
    
    def test_build_cache_key_deterministic(self):
        """缓存键确定性"""
        key1 = FormulaService._build_cache_key('{a}+{b}', {'a': 1, 'b': 2})
        key2 = FormulaService._build_cache_key('{a}+{b}', {'a': 1, 'b': 2})
        assert key1 == key2
        
        key3 = FormulaService._build_cache_key('{a}+{b}', {'a': 1, 'b': 3})
        assert key1 != key3


class TestComplexFormulas:
    """复杂组合公式测试"""
    
    def _eval(self, formula, ctx=None):
        return FormulaService.evaluate_formula(formula, ctx or {}, use_cache=False)
    
    def test_price_with_tax(self):
        """含税价格计算"""
        ctx = {'price': 100, 'tax_rate': 0.13}
        result = self._eval('{price} * (1 + {tax_rate})', ctx)
        assert abs(result - 113.0) < 0.001
    
    def test_discount_calculation(self):
        """折扣计算"""
        ctx = {'original_price': 200, 'discount_pct': 0.2}
        result = self._eval('{original_price} * (1 - {discount_pct})', ctx)
        assert abs(result - 160.0) < 0.001
    
    def test_grade_classification(self):
        """成绩等级分类"""
        ctx = {'score': 85}
        result = self._eval(
            'IFS({score}>=90, "A", {score}>=80, "B", {score}>=70, "C", DEFAULT, "D")',
            ctx
        )
        assert result == 'B'
    
    def test_full_name_concatenation(self):
        """全名拼接"""
        ctx = {'first_name': '张', 'last_name': '三'}
        result = self._eval('CONCAT({first_name}, {last_name})', ctx)
        assert result == '张三'
    
    def test_nested_if(self):
        """嵌套 IF 条件"""
        ctx = {'value': 25}
        result = self._eval(
            'IF({value}>50, "high", IF({value}>20, "medium", "low"))',
            ctx
        )
        assert result == 'medium'
    
    def test_percentage_of_total(self):
        """占总百分比"""
        ctx = {'part': 25, 'total': 200}
        result = self._eval('ROUND(({part}/{total}) * 100, 1)', ctx)
        assert abs(result - 12.5) < 0.001
