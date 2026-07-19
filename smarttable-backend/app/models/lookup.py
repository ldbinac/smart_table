"""
查找字段（LOOKUP）相关枚举模型模块

参照飞书查找引用字段，定义：
- LookupFilterOperator：过滤条件操作符（7 种）
- LookupAggregationType：聚合计算方式（8 种）
- LookupFieldFormat：字段格式（3 种）
"""
import enum


class LookupFilterOperator(enum.Enum):
    """查找字段过滤条件操作符"""
    EQUAL = 'equal'
    NOT_EQUAL = 'not_equal'
    CONTAINS = 'contains'
    IS_EMPTY = 'is_empty'
    IS_NOT_EMPTY = 'is_not_empty'
    BEFORE = 'before'
    AFTER = 'after'


class LookupAggregationType(enum.Enum):
    """查找字段聚合计算方式"""
    ORIGINAL = 'original'
    DISTINCT = 'distinct'
    DISTINCT_COUNT = 'distinct_count'
    SUM = 'sum'
    COUNT = 'count'
    AVG = 'avg'
    MAX = 'max'
    MIN = 'min'


class LookupFieldFormat(enum.Enum):
    """查找字段格式"""
    NUMBER = 'number'
    DATE = 'date'
    CURRENCY = 'currency'
