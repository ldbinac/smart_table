"""
查找字段（LOOKUP）后端服务单元测试

覆盖范围（参照 checklist.md「后端：单元测试」）：
- SubTask 5.1: 配置校验各场景（LookupService.validate_config）
- SubTask 5.2: 7 种过滤操作符求值（LookupService._evaluate_condition）
- SubTask 5.3: AND/OR 连接的多个条件求值（LookupService._filter_source_records）
- SubTask 5.4: 8 种计算方式聚合（LookupService._apply_aggregation）
- SubTask 5.5: 字段格式化（LookupService._format_value）
- SubTask 5.6: 端到端 compute_lookup_value 多表场景
"""
import pytest

from app.extensions import db
from app.models import Base, Record, Table
from app.models.field import Field, FieldType
from app.models.lookup import (
    LookupAggregationType,
    LookupFieldFormat,
    LookupFilterOperator,
)
from app.services.lookup_service import LookupService


# ----------------------------------------------------------------------
# 辅助函数（仅用于纯逻辑测试，不入库）
# ----------------------------------------------------------------------

def _make_record(values):
    """创建内存中的 Record 对象（不入库）"""
    record = Record()
    record.values = values
    return record


def _make_field(field_type='single_line_text'):
    """创建内存中的 Field 对象（不入库）"""
    field = Field()
    field.type = field_type
    return field


def _make_source_fields_map(field_id='src_field_1', field_type='single_line_text'):
    """创建源表字段映射（单字段）"""
    return {field_id: _make_field(field_type)}


# ======================================================================
# SubTask 5.1: 配置校验
# ======================================================================

class TestLookupValidateConfig:
    """LookupService.validate_config 各场景测试"""

    @pytest.fixture
    def lookup_data(self, app, db_session, test_user):
        """创建配置校验所需的多表多字段数据：两个 base、三个 table、若干 field"""
        # base1 包含当前表和源表
        base1 = Base(
            name='Base1', description='测试库1',
            icon='table', color='#6366f1', owner_id=test_user.id,
        )
        db.session.add(base1)
        db.session.commit()

        current_table = Table(base_id=base1.id, name='当前表', order=0)
        source_table = Table(base_id=base1.id, name='源表', order=1)
        db.session.add_all([current_table, source_table])
        db.session.commit()

        # base2 包含另一个库的表（用于跨库校验测试）
        base2 = Base(
            name='Base2', description='测试库2',
            icon='table', color='#6366f1', owner_id=test_user.id,
        )
        db.session.add(base2)
        db.session.commit()

        other_base_table = Table(base_id=base2.id, name='其他库表', order=0)
        db.session.add(other_base_table)
        db.session.commit()

        # 源表字段
        src_text_field = Field(
            table_id=source_table.id, name='分类',
            type=FieldType.SINGLE_LINE_TEXT.value, order=0,
        )
        src_number_field = Field(
            table_id=source_table.id, name='金额',
            type=FieldType.NUMBER.value, order=1,
        )
        src_date_field = Field(
            table_id=source_table.id, name='日期',
            type=FieldType.DATE.value, order=2,
        )
        db.session.add_all([src_text_field, src_number_field, src_date_field])

        # 当前表字段
        cur_text_field = Field(
            table_id=current_table.id, name='分类',
            type=FieldType.SINGLE_LINE_TEXT.value, order=0,
        )
        db.session.add(cur_text_field)

        db.session.commit()
        for obj in [src_text_field, src_number_field, src_date_field, cur_text_field]:
            db.session.refresh(obj)

        return {
            'current_table': current_table,
            'source_table': source_table,
            'other_base_table': other_base_table,
            'src_text_field': src_text_field,
            'src_number_field': src_number_field,
            'src_date_field': src_date_field,
            'cur_text_field': cur_text_field,
        }

    def _base_config(self, data):
        """构建一份合法的基础配置，后续用例在此基础上修改"""
        return {
            'sourceTableId': str(data['source_table'].id),
            'targetFieldId': str(data['src_text_field'].id),
            'filterConditions': [
                {
                    'fieldId': str(data['src_text_field'].id),
                    'operator': LookupFilterOperator.EQUAL.value,
                    'valueType': 'field',
                    'valueFieldId': str(data['cur_text_field'].id),
                }
            ],
            'filterConjunction': 'and',
            'aggregationType': LookupAggregationType.ORIGINAL.value,
        }

    def test_missing_source_table_id(self, app, lookup_data):
        """缺少 sourceTableId → 失败"""
        config = self._base_config(lookup_data)
        del config['sourceTableId']
        ok, err = LookupService.validate_config(
            config, str(lookup_data['current_table'].id)
        )
        assert ok is False
        assert err is not None

    def test_source_table_equals_current(self, app, lookup_data):
        """sourceTableId 等于当前表 → 失败（不能引用当前数据表）"""
        config = self._base_config(lookup_data)
        config['sourceTableId'] = str(lookup_data['current_table'].id)
        ok, err = LookupService.validate_config(
            config, str(lookup_data['current_table'].id)
        )
        assert ok is False
        assert '不能引用当前数据表' in err

    def test_source_table_in_different_base(self, app, lookup_data):
        """sourceTableId 与当前表不在同一 base → 失败"""
        config = self._base_config(lookup_data)
        config['sourceTableId'] = str(lookup_data['other_base_table'].id)
        ok, err = LookupService.validate_config(
            config, str(lookup_data['current_table'].id)
        )
        assert ok is False
        assert '同一个多维表格' in err

    def test_missing_target_field_id(self, app, lookup_data):
        """缺少 targetFieldId → 失败"""
        config = self._base_config(lookup_data)
        del config['targetFieldId']
        ok, err = LookupService.validate_config(
            config, str(lookup_data['current_table'].id)
        )
        assert ok is False
        assert err is not None

    def test_target_field_not_in_source_table(self, app, lookup_data):
        """targetFieldId 不属于源表 → 失败"""
        config = self._base_config(lookup_data)
        config['targetFieldId'] = str(lookup_data['cur_text_field'].id)
        ok, err = LookupService.validate_config(
            config, str(lookup_data['current_table'].id)
        )
        assert ok is False
        assert '引用字段必须属于源数据表' in err

    def test_too_many_filter_conditions(self, app, lookup_data):
        """filterConditions 超过 5 个 → 失败"""
        config = self._base_config(lookup_data)
        cond = dict(config['filterConditions'][0])
        config['filterConditions'] = [dict(cond) for _ in range(6)]
        ok, err = LookupService.validate_config(
            config, str(lookup_data['current_table'].id)
        )
        assert ok is False
        assert '最多支持 5 个查找条件' in err

    def test_condition_field_not_in_source_table(self, app, lookup_data):
        """条件的 fieldId 不属于源表 → 失败"""
        config = self._base_config(lookup_data)
        config['filterConditions'][0]['fieldId'] = str(lookup_data['cur_text_field'].id)
        ok, err = LookupService.validate_config(
            config, str(lookup_data['current_table'].id)
        )
        assert ok is False
        assert '过滤条件字段必须属于源数据表' in err

    def test_condition_invalid_operator(self, app, lookup_data):
        """条件的 operator 非法 → 失败"""
        config = self._base_config(lookup_data)
        config['filterConditions'][0]['operator'] = 'invalid_operator'
        ok, err = LookupService.validate_config(
            config, str(lookup_data['current_table'].id)
        )
        assert ok is False
        assert '操作符不合法' in err

    def test_is_empty_no_value_needed(self, app, lookup_data):
        """条件 is_empty 时不需要 value → 成功"""
        config = self._base_config(lookup_data)
        config['filterConditions'][0] = {
            'fieldId': str(lookup_data['src_text_field'].id),
            'operator': LookupFilterOperator.IS_EMPTY.value,
        }
        ok, err = LookupService.validate_config(
            config, str(lookup_data['current_table'].id)
        )
        assert ok is True, f'合法配置不应失败: {err}'

    def test_value_type_field_missing_value_field_id(self, app, lookup_data):
        """valueType=field 但缺 valueFieldId → 失败"""
        config = self._base_config(lookup_data)
        cond = config['filterConditions'][0]
        del cond['valueFieldId']
        ok, err = LookupService.validate_config(
            config, str(lookup_data['current_table'].id)
        )
        assert ok is False
        assert '值字段必须属于当前表' in err

    def test_value_type_custom_missing_value_custom(self, app, lookup_data):
        """valueType=custom 但缺 valueCustom → 失败"""
        config = self._base_config(lookup_data)
        cond = config['filterConditions'][0]
        cond['valueType'] = 'custom'
        del cond['valueFieldId']
        # 不设置 valueCustom
        ok, err = LookupService.validate_config(
            config, str(lookup_data['current_table'].id)
        )
        assert ok is False
        assert '自定义值不能为空' in err

    def test_invalid_aggregation_type(self, app, lookup_data):
        """aggregationType 非法 → 失败"""
        config = self._base_config(lookup_data)
        config['aggregationType'] = 'invalid_agg'
        ok, err = LookupService.validate_config(
            config, str(lookup_data['current_table'].id)
        )
        assert ok is False
        assert '计算方式不合法' in err

    def test_field_format_incompatible_with_aggregation(self, app, lookup_data):
        """fieldFormat 与 aggregationType 不兼容（distinct_count + date）→ 失败"""
        config = self._base_config(lookup_data)
        config['aggregationType'] = LookupAggregationType.DISTINCT_COUNT.value
        config['fieldFormat'] = LookupFieldFormat.DATE.value
        ok, err = LookupService.validate_config(
            config, str(lookup_data['current_table'].id)
        )
        assert ok is False
        assert '字段格式与计算方式不兼容' in err

    def test_full_valid_config(self, app, lookup_data):
        """完整合法配置 → 成功"""
        config = self._base_config(lookup_data)
        ok, err = LookupService.validate_config(
            config, str(lookup_data['current_table'].id)
        )
        assert ok is True, f'合法配置不应失败: {err}'
        assert err is None


# ======================================================================
# SubTask 5.2: 7 种过滤操作符求值
# ======================================================================

class TestLookupEvaluateCondition:
    """LookupService._evaluate_condition 7 种操作符测试

    每个需要值的操作符都测试 valueType='field' 和 'custom' 两种来源。
    is_empty / is_not_empty 无需值，不区分来源。
    """

    FIELD_ID = 'src_field_1'
    CURRENT_FIELD_ID = 'cur_field_1'

    def _build_condition(self, operator, value_type='custom',
                         value_custom=None, value_field_id=None):
        """构造过滤条件字典"""
        cond = {'fieldId': self.FIELD_ID, 'operator': operator}
        if operator in (LookupFilterOperator.IS_EMPTY.value,
                        LookupFilterOperator.IS_NOT_EMPTY.value):
            return cond
        cond['valueType'] = value_type
        if value_type == 'field':
            cond['valueFieldId'] = value_field_id or self.CURRENT_FIELD_ID
        else:
            cond['valueCustom'] = value_custom
        return cond

    def _eval(self, field_value, condition, current_value=None,
              field_type='single_line_text'):
        """调用 _evaluate_condition 的辅助方法"""
        record = _make_record({self.FIELD_ID: field_value})
        current_record = (
            _make_record({self.CURRENT_FIELD_ID: current_value})
            if current_value is not None else None
        )
        source_fields_map = _make_source_fields_map(
            field_id=self.FIELD_ID, field_type=field_type
        )
        return LookupService._evaluate_condition(
            record, condition, current_record, source_fields_map
        )

    # --- equal ---
    def test_equal_string_custom(self, app):
        """equal: 字符串相等（custom 值）"""
        cond = self._build_condition(
            LookupFilterOperator.EQUAL.value, value_custom='hello'
        )
        assert self._eval('hello', cond) is True

    def test_equal_string_field(self, app):
        """equal: 字符串相等（field 值，从当前记录取值）"""
        cond = self._build_condition(
            LookupFilterOperator.EQUAL.value, value_type='field'
        )
        assert self._eval('hello', cond, current_value='hello') is True

    def test_equal_number(self, app):
        """equal: 数字相等"""
        cond = self._build_condition(
            LookupFilterOperator.EQUAL.value, value_custom=42
        )
        assert self._eval(42, cond) is True

    def test_equal_array_contains(self, app):
        """equal: 数组中包含比较值"""
        cond = self._build_condition(
            LookupFilterOperator.EQUAL.value, value_custom='b'
        )
        assert self._eval(['a', 'b', 'c'], cond) is True

    # --- not_equal ---
    def test_not_equal_string_custom(self, app):
        """not_equal: 字符串不等（custom 值）"""
        cond = self._build_condition(
            LookupFilterOperator.NOT_EQUAL.value, value_custom='world'
        )
        assert self._eval('hello', cond) is True

    def test_not_equal_string_field(self, app):
        """not_equal: 字符串不等（field 值）"""
        cond = self._build_condition(
            LookupFilterOperator.NOT_EQUAL.value, value_type='field'
        )
        assert self._eval('hello', cond, current_value='world') is True

    def test_not_equal_array_not_contains(self, app):
        """not_equal: 数组中所有元素都不等于比较值"""
        cond = self._build_condition(
            LookupFilterOperator.NOT_EQUAL.value, value_custom='d'
        )
        assert self._eval(['a', 'b', 'c'], cond) is True

    # --- contains ---
    def test_contains_text_custom(self, app):
        """contains: 文本子串包含（custom 值）"""
        cond = self._build_condition(
            LookupFilterOperator.CONTAINS.value, value_custom='world'
        )
        assert self._eval('hello world', cond) is True

    def test_contains_text_field(self, app):
        """contains: 文本子串包含（field 值）"""
        cond = self._build_condition(
            LookupFilterOperator.CONTAINS.value, value_type='field'
        )
        assert self._eval('hello world', cond, current_value='world') is True

    def test_contains_array(self, app):
        """contains: 数组包含元素"""
        cond = self._build_condition(
            LookupFilterOperator.CONTAINS.value, value_custom='a'
        )
        assert self._eval(['a', 'b', 'c'], cond) is True

    # --- is_empty ---
    def test_is_empty_none(self, app):
        """is_empty: None 值为空"""
        cond = self._build_condition(LookupFilterOperator.IS_EMPTY.value)
        assert self._eval(None, cond) is True

    def test_is_empty_string(self, app):
        """is_empty: 空字符串为空"""
        cond = self._build_condition(LookupFilterOperator.IS_EMPTY.value)
        assert self._eval('', cond) is True

    def test_is_empty_list(self, app):
        """is_empty: 空数组为空"""
        cond = self._build_condition(LookupFilterOperator.IS_EMPTY.value)
        assert self._eval([], cond) is True

    def test_is_empty_dict(self, app):
        """is_empty: 空对象为空"""
        cond = self._build_condition(LookupFilterOperator.IS_EMPTY.value)
        assert self._eval({}, cond) is True

    # --- is_not_empty ---
    def test_is_not_empty_string(self, app):
        """is_not_empty: 非空字符串"""
        cond = self._build_condition(LookupFilterOperator.IS_NOT_EMPTY.value)
        assert self._eval('hello', cond) is True

    def test_is_not_empty_list(self, app):
        """is_not_empty: 非空数组"""
        cond = self._build_condition(LookupFilterOperator.IS_NOT_EMPTY.value)
        assert self._eval([1], cond) is True

    def test_is_not_empty_empty_returns_false(self, app):
        """is_not_empty: 空值返回 False"""
        cond = self._build_condition(LookupFilterOperator.IS_NOT_EMPTY.value)
        assert self._eval('', cond) is False

    # --- before ---
    def test_before_custom(self, app):
        """before: 日期字符串早于（custom 值）"""
        cond = self._build_condition(
            LookupFilterOperator.BEFORE.value, value_custom='2025-02-01'
        )
        assert self._eval('2025-01-01', cond) is True

    def test_before_field(self, app):
        """before: 日期字符串早于（field 值）"""
        cond = self._build_condition(
            LookupFilterOperator.BEFORE.value, value_type='field'
        )
        assert self._eval('2025-01-01', cond, current_value='2025-02-01') is True

    def test_before_not_earlier(self, app):
        """before: 不早于 → False"""
        cond = self._build_condition(
            LookupFilterOperator.BEFORE.value, value_custom='2025-01-01'
        )
        assert self._eval('2025-02-01', cond) is False

    # --- after ---
    def test_after_custom(self, app):
        """after: 日期字符串晚于（custom 值）"""
        cond = self._build_condition(
            LookupFilterOperator.AFTER.value, value_custom='2025-02-01'
        )
        assert self._eval('2025-03-01', cond) is True

    def test_after_field(self, app):
        """after: 日期字符串晚于（field 值）"""
        cond = self._build_condition(
            LookupFilterOperator.AFTER.value, value_type='field'
        )
        assert self._eval('2025-03-01', cond, current_value='2025-02-01') is True

    def test_after_not_later(self, app):
        """after: 不晚于 → False"""
        cond = self._build_condition(
            LookupFilterOperator.AFTER.value, value_custom='2025-03-01'
        )
        assert self._eval('2025-02-01', cond) is False


# ======================================================================
# SubTask 5.3: AND/OR 连接的多个条件求值
# ======================================================================

class TestLookupFilterSourceRecords:
    """LookupService._filter_source_records AND/OR 连接测试"""

    FIELD_ID = 'src_field_1'

    def _make_records(self, field_values):
        """批量创建源表记录"""
        return [_make_record({self.FIELD_ID: v}) for v in field_values]

    def _make_condition(self, operator, value_custom=None):
        """构造 custom 值条件"""
        return {
            'fieldId': self.FIELD_ID,
            'operator': operator,
            'valueType': 'custom',
            'valueCustom': value_custom,
        }

    def test_no_conditions_returns_all(self, app):
        """无条件 → 返回全部记录"""
        records = self._make_records(['a', 'b', 'c'])
        source_fields_map = _make_source_fields_map(field_id=self.FIELD_ID)
        result = LookupService._filter_source_records(
            records, [], 'and', None, source_fields_map
        )
        assert len(result) == 3

    def test_and_conjunction(self, app):
        """AND 连接：仅返回同时满足两个条件的记录"""
        records = self._make_records(['apple', 'banana', 'cherry'])
        cond1 = self._make_condition(
            LookupFilterOperator.CONTAINS.value, value_custom='a'
        )
        cond2 = self._make_condition(
            LookupFilterOperator.NOT_EQUAL.value, value_custom='apple'
        )
        source_fields_map = _make_source_fields_map(field_id=self.FIELD_ID)
        result = LookupService._filter_source_records(
            records, [cond1, cond2], 'and', None, source_fields_map
        )
        # 含 'a' 且 不等于 'apple'：banana（含 a 且不等于 apple）
        assert len(result) == 1
        assert result[0].values[self.FIELD_ID] == 'banana'

    def test_or_conjunction(self, app):
        """OR 连接：返回满足任一条件的记录"""
        records = self._make_records(['apple', 'banana', 'cherry'])
        cond1 = self._make_condition(
            LookupFilterOperator.EQUAL.value, value_custom='apple'
        )
        cond2 = self._make_condition(
            LookupFilterOperator.EQUAL.value, value_custom='cherry'
        )
        source_fields_map = _make_source_fields_map(field_id=self.FIELD_ID)
        result = LookupService._filter_source_records(
            records, [cond1, cond2], 'or', None, source_fields_map
        )
        assert len(result) == 2
        values = [r.values[self.FIELD_ID] for r in result]
        assert 'apple' in values
        assert 'cherry' in values


# ======================================================================
# SubTask 5.4: 8 种计算方式聚合
# ======================================================================

class TestLookupApplyAggregation:
    """LookupService._apply_aggregation 8 种计算方式测试"""

    # --- original ---
    def test_original_filters_none_and_empty(self):
        """original: 返回原数组（过滤 None 和空字符串）"""
        result = LookupService._apply_aggregation(
            [1, None, 2, '', 3], LookupAggregationType.ORIGINAL.value, None
        )
        assert result == [1, 2, 3]

    def test_original_all_empty(self):
        """original: 全部为空时返回空数组"""
        result = LookupService._apply_aggregation(
            [None, None, ''], LookupAggregationType.ORIGINAL.value, None
        )
        assert result == []

    # --- distinct ---
    def test_distinct(self):
        """distinct: 去重后数组"""
        result = LookupService._apply_aggregation(
            [1, 2, 2, 3, 3, 3], LookupAggregationType.DISTINCT.value, None
        )
        assert result == [1, 2, 3]

    def test_distinct_skips_none_and_empty(self):
        """distinct: 跳过 None 和空字符串"""
        result = LookupService._apply_aggregation(
            [1, None, 2, '', 2], LookupAggregationType.DISTINCT.value, None
        )
        assert result == [1, 2]

    # --- distinct_count ---
    def test_distinct_count(self):
        """distinct_count: 去重数量"""
        result = LookupService._apply_aggregation(
            [1, 2, 2, 3], LookupAggregationType.DISTINCT_COUNT.value, None
        )
        assert result == 3

    def test_distinct_count_skips_none_and_empty(self):
        """distinct_count: 跳过 None 和空字符串"""
        result = LookupService._apply_aggregation(
            [1, None, 2, '', 2], LookupAggregationType.DISTINCT_COUNT.value, None
        )
        assert result == 2

    # --- sum ---
    def test_sum(self):
        """sum: 求和"""
        result = LookupService._apply_aggregation(
            [1, 2, 3], LookupAggregationType.SUM.value, None
        )
        assert result == 6

    def test_sum_skips_non_numbers(self):
        """sum: 跳过非数字（含 bool）"""
        result = LookupService._apply_aggregation(
            [1, 'a', 2, None, 3, True], LookupAggregationType.SUM.value, None
        )
        assert result == 6

    def test_sum_no_numbers_returns_zero(self):
        """sum: 无数字时返回 0"""
        result = LookupService._apply_aggregation(
            ['a', None, True], LookupAggregationType.SUM.value, None
        )
        assert result == 0

    # --- count ---
    def test_count(self):
        """count: 返回数量（与值无关）"""
        result = LookupService._apply_aggregation(
            [1, 'a', None, 3], LookupAggregationType.COUNT.value, None
        )
        assert result == 4

    def test_count_empty(self):
        """count: 空列表返回 0"""
        result = LookupService._apply_aggregation(
            [], LookupAggregationType.COUNT.value, None
        )
        assert result == 0

    # --- avg ---
    def test_avg(self):
        """avg: 平均值"""
        result = LookupService._apply_aggregation(
            [2, 4, 6], LookupAggregationType.AVG.value, None
        )
        assert result == 4.0

    def test_avg_skips_non_numbers(self):
        """avg: 跳过非数字"""
        result = LookupService._apply_aggregation(
            [2, 'a', 4, None, 6], LookupAggregationType.AVG.value, None
        )
        assert result == 4.0

    def test_avg_no_numbers_returns_none(self):
        """avg: 无数字时返回 None"""
        result = LookupService._apply_aggregation(
            ['a', None], LookupAggregationType.AVG.value, None
        )
        assert result is None

    # --- max ---
    def test_max_number(self):
        """max: 数字字段最大值"""
        source_field = _make_field(FieldType.NUMBER.value)
        result = LookupService._apply_aggregation(
            [1, 5, 3], LookupAggregationType.MAX.value, source_field
        )
        assert result == 5

    def test_max_date(self):
        """max: 日期字符串最大值"""
        source_field = _make_field(FieldType.DATE.value)
        result = LookupService._apply_aggregation(
            ['2025-01-01', '2025-03-01', '2025-02-01'],
            LookupAggregationType.MAX.value, source_field,
        )
        assert result == '2025-03-01'

    def test_max_string(self):
        """max: 字符串最大值（按字典序）"""
        source_field = _make_field(FieldType.SINGLE_LINE_TEXT.value)
        result = LookupService._apply_aggregation(
            ['banana', 'apple', 'cherry'],
            LookupAggregationType.MAX.value, source_field,
        )
        assert result == 'cherry'

    # --- min ---
    def test_min_number(self):
        """min: 数字字段最小值"""
        source_field = _make_field(FieldType.NUMBER.value)
        result = LookupService._apply_aggregation(
            [1, 5, 3], LookupAggregationType.MIN.value, source_field
        )
        assert result == 1

    def test_min_date(self):
        """min: 日期字符串最小值"""
        source_field = _make_field(FieldType.DATE.value)
        result = LookupService._apply_aggregation(
            ['2025-01-01', '2025-03-01', '2025-02-01'],
            LookupAggregationType.MIN.value, source_field,
        )
        assert result == '2025-01-01'

    def test_min_string(self):
        """min: 字符串最小值（按字典序）"""
        source_field = _make_field(FieldType.SINGLE_LINE_TEXT.value)
        result = LookupService._apply_aggregation(
            ['banana', 'apple', 'cherry'],
            LookupAggregationType.MIN.value, source_field,
        )
        assert result == 'apple'

    def test_min_empty_returns_none(self):
        """min: 全部为空值时返回 None"""
        source_field = _make_field(FieldType.NUMBER.value)
        result = LookupService._apply_aggregation(
            [None, ''], LookupAggregationType.MIN.value, source_field
        )
        assert result is None


# ======================================================================
# SubTask 5.5: 字段格式化
# ======================================================================

class TestLookupFormatValue:
    """LookupService._format_value 字段格式化测试"""

    def test_number_format_with_precision(self):
        """number 格式 + precision=2 → "60.00" """
        result = LookupService._format_value(
            60,
            {'fieldFormat': LookupFieldFormat.NUMBER.value, 'precision': 2},
            None,
        )
        assert result == '60.00'

    def test_currency_format_with_symbol_and_precision(self):
        """currency 格式 + currencySymbol="¥" + precision=2 → "¥60.00" """
        result = LookupService._format_value(
            60,
            {
                'fieldFormat': LookupFieldFormat.CURRENCY.value,
                'currencySymbol': '¥',
                'precision': 2,
            },
            None,
        )
        assert result == '¥60.00'

    def test_date_format_with_date_format(self):
        """date 格式 + dateFormat="YYYY-MM-DD" → "2025-05-01" """
        result = LookupService._format_value(
            '2025-05-01',
            {'fieldFormat': LookupFieldFormat.DATE.value, 'dateFormat': 'YYYY-MM-DD'},
            None,
        )
        assert result == '2025-05-01'

    def test_format_none_value(self):
        """None 值直接返回 None"""
        result = LookupService._format_value(
            None,
            {'fieldFormat': LookupFieldFormat.NUMBER.value, 'precision': 2},
            None,
        )
        assert result is None


# ======================================================================
# SubTask 5.6: 端到端 compute_lookup_value
# ======================================================================

class TestLookupComputeValue:
    """LookupService.compute_lookup_value 端到端多表场景测试"""

    @pytest.fixture
    def two_tables_data(self, app, db_session, test_user):
        """创建两个表（A 当前表、B 源表）及字段、记录，并在表 A 上创建 LOOKUP 字段"""
        base = Base(
            name='查找测试库', description='端到端测试',
            icon='table', color='#6366f1', owner_id=test_user.id,
        )
        db.session.add(base)
        db.session.commit()

        # 表 A（当前表）和表 B（源表）在同一 base 下
        table_a = Table(base_id=base.id, name='表A', order=0)
        table_b = Table(base_id=base.id, name='表B', order=1)
        db.session.add_all([table_a, table_b])
        db.session.commit()

        # 表 A 字段：分类
        a_category_field = Field(
            table_id=table_a.id, name='分类',
            type=FieldType.SINGLE_LINE_TEXT.value, order=0,
        )
        db.session.add(a_category_field)
        db.session.commit()
        db.session.refresh(a_category_field)

        # 表 B 字段：分类、金额
        b_category_field = Field(
            table_id=table_b.id, name='分类',
            type=FieldType.SINGLE_LINE_TEXT.value, order=0,
        )
        b_amount_field = Field(
            table_id=table_b.id, name='金额',
            type=FieldType.NUMBER.value, order=1,
        )
        db.session.add_all([b_category_field, b_amount_field])
        db.session.commit()
        for f in [b_category_field, b_amount_field]:
            db.session.refresh(f)

        # 表 A 记录：分类 = "项目"
        record_a = Record(
            table_id=table_a.id,
            values={str(a_category_field.id): '项目'},
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db.session.add(record_a)

        # 表 B 三条记录
        record_b1 = Record(
            table_id=table_b.id,
            values={str(b_category_field.id): '项目', str(b_amount_field.id): 100},
            created_by=test_user.id, updated_by=test_user.id,
        )
        record_b2 = Record(
            table_id=table_b.id,
            values={str(b_category_field.id): '项目', str(b_amount_field.id): 200},
            created_by=test_user.id, updated_by=test_user.id,
        )
        record_b3 = Record(
            table_id=table_b.id,
            values={str(b_category_field.id): '其他', str(b_amount_field.id): 50},
            created_by=test_user.id, updated_by=test_user.id,
        )
        db.session.add_all([record_b1, record_b2, record_b3])
        db.session.commit()
        db.session.refresh(record_a)

        # 在表 A 上创建 LOOKUP 字段（sum 聚合）
        lookup_field = Field(
            table_id=table_a.id, name='查找金额',
            type=FieldType.LOOKUP.value, order=1,
            config={
                'sourceTableId': str(table_b.id),
                'targetFieldId': str(b_amount_field.id),
                'filterConditions': [
                    {
                        'fieldId': str(b_category_field.id),
                        'operator': LookupFilterOperator.EQUAL.value,
                        'valueType': 'field',
                        'valueFieldId': str(a_category_field.id),
                    }
                ],
                'filterConjunction': 'and',
                'aggregationType': LookupAggregationType.SUM.value,
            },
        )
        db.session.add(lookup_field)
        db.session.commit()
        db.session.refresh(lookup_field)

        return {
            'table_a': table_a,
            'table_b': table_b,
            'a_category_field': a_category_field,
            'b_category_field': b_category_field,
            'b_amount_field': b_amount_field,
            'record_a': record_a,
            'lookup_field': lookup_field,
        }

    def test_compute_lookup_value_sum(self, app, two_tables_data):
        """端到端：按分类匹配并求和 → 300"""
        data = two_tables_data
        result = LookupService.compute_lookup_value(
            data['record_a'], data['lookup_field']
        )
        assert result == 300

    def test_compute_lookup_value_original(self, app, two_tables_data):
        """端到端：original 模式返回过滤后的金额数组 [100, 200]"""
        data = two_tables_data
        lookup_field = data['lookup_field']
        # 切换为 original 聚合
        lookup_field.config = {
            'sourceTableId': str(data['table_b'].id),
            'targetFieldId': str(data['b_amount_field'].id),
            'filterConditions': [
                {
                    'fieldId': str(data['b_category_field'].id),
                    'operator': LookupFilterOperator.EQUAL.value,
                    'valueType': 'field',
                    'valueFieldId': str(data['a_category_field'].id),
                }
            ],
            'filterConjunction': 'and',
            'aggregationType': LookupAggregationType.ORIGINAL.value,
        }
        result = LookupService.compute_lookup_value(
            data['record_a'], lookup_field
        )
        assert result == [100, 200]
