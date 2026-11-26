"""
字段服务模块
处理 Field 的 CRUD 操作、排序管理和类型验证
支持 22 种字段类型
"""
import logging
import re
from typing import List, Optional, Dict, Any, Tuple
import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import func

from app.extensions import db
from app.models.field import Field, FieldType
from app.models.record import Record
from app.models.table import Table
from app.models.base import MemberRole
from app.services.base_service import BaseService
from app.services.formula_service import FormulaService
from app.i18n import translate
from app.services.workflow_event_bus import workflow_event_bus
import logging


logger = logging.getLogger(__name__)


def _format_date_default_value(default_value: str, field_type: str) -> str:
    """
    根据字段类型（date 或 date_time）格式化默认值

    Args:
        default_value: 原始默认值（ISO 8601 格式或 YYYY-MM-DD 格式）
        field_type: 字段类型（'date' 或 'date_time'）

    Returns:
        格式化后的日期字符串
    """
    if default_value is None or default_value == 'now':
        return default_value

    # 根据字段类型决定格式
    is_date_time = field_type == FieldType.DATE_TIME.value

    try:
        # 解析日期时间
        if 'T' in default_value:
            # ISO 8601 格式: 2026-04-12T00:00:00.000Z 或 2026-04-12T00:00:00+00:00
            dt = datetime.fromisoformat(default_value.replace('Z', '+00:00'))
        else:
            # 已经是 YYYY-MM-DD 或 YYYY-MM-DD HH:mm:ss 格式
            if len(default_value) <= 10:
                dt = datetime.strptime(default_value, '%Y-%m-%d')
            else:
                dt = datetime.strptime(default_value, '%Y-%m-%d %H:%M:%S')

        # 根据字段类型格式化
        if is_date_time:
            # 保留 UTC ISO 格式（如 2026-05-10T16:16:40Z）
            return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            return dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        # 如果解析失败，返回原始值
        return default_value


def _validate_ai_options(ai_config, table_id, current_field_id=None):
    """AI 字段 options.ai_config 校验（B1/B8；延迟导入避免 services.ai 循环依赖）"""
    try:
        from app.services.ai.ai_field_service import validate_ai_config
    except ImportError:
        validate_ai_config = None
    return validate_ai_config(ai_config, table_id, current_field_id)

class FieldServiceGroup02Mixin:
    """Mixin auto-split"""
    
    """字段服务类"""
    
    SYSTEM_FIELD_TYPES = [
        FieldType.AUTO_NUMBER
    ]
    
    OPTIONS_REQUIRED_TYPES = [
        FieldType.SINGLE_SELECT.value,
        FieldType.MULTI_SELECT.value
    ]
    
    VALID_FIELD_TYPES = [ft.value for ft in FieldType]
    
    TEXT_TYPES = [
        FieldType.SINGLE_LINE_TEXT.value,
        FieldType.LONG_TEXT.value,
        FieldType.RICH_TEXT.value,
    ]
    
    NUMERIC_TYPES = [
        FieldType.NUMBER.value,
        FieldType.CURRENCY.value,
        FieldType.PERCENT.value,
        FieldType.RATING.value,
        FieldType.DURATION.value,
    ]
    
    DATE_TYPES = [
        FieldType.DATE.value,
        FieldType.DATE_TIME.value,
    ]
    
    CONVERT_SYSTEM_TYPES = [
        FieldType.CREATED_BY.value,
        FieldType.CREATED_TIME.value,
        FieldType.UPDATED_BY.value,
        FieldType.UPDATED_TIME.value,
        FieldType.LAST_MODIFIED_BY.value,
        FieldType.AUTO_NUMBER.value,
    ]
    
    CONVERT_FORBIDDEN_TYPES = CONVERT_SYSTEM_TYPES + [
        FieldType.LINK_TO_RECORD.value,
        FieldType.LINK.value,
        FieldType.LOOKUP.value,
        FieldType.ROLLUP.value,
        FieldType.BUTTON.value,
    ]
    
    CONVERT_FORBIDDEN_TARGET_TYPES = [
        FieldType.FORMULA.value,
        FieldType.AI.value,
    ]
    
    LOSSLESS_CONVERSIONS = {
        # 文本升级（单行 -> 多行/富文本）
        FieldType.SINGLE_LINE_TEXT.value: [
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        FieldType.LONG_TEXT.value: [
            FieldType.RICH_TEXT.value,
        ],
        # 选择类：单选转多选无损；转文本保留选项 ID
        FieldType.SINGLE_SELECT.value: [
            FieldType.MULTI_SELECT.value,
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        FieldType.MULTI_SELECT.value: [
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        # 文本格式类转文本类
        FieldType.EMAIL.value: list(TEXT_TYPES),
        FieldType.PHONE.value: list(TEXT_TYPES),
        FieldType.URL.value: list(TEXT_TYPES),
        FieldType.BARCODE.value: list(TEXT_TYPES),
        # 文本类 <-> 地理位置：文本直接承载为地址串，地理对象转文本按层级拼接
        FieldType.GEOLOCATION.value: list(TEXT_TYPES),
        # 数值族互转 + 转文本类
        FieldType.NUMBER.value: [
            FieldType.CURRENCY.value,
            FieldType.PERCENT.value,
            FieldType.RATING.value,
            FieldType.DURATION.value,
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        FieldType.CURRENCY.value: [
            FieldType.NUMBER.value,
            FieldType.PERCENT.value,
            FieldType.RATING.value,
            FieldType.DURATION.value,
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        FieldType.PERCENT.value: [
            FieldType.NUMBER.value,
            FieldType.CURRENCY.value,
            FieldType.RATING.value,
            FieldType.DURATION.value,
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        FieldType.RATING.value: [
            FieldType.NUMBER.value,
            FieldType.CURRENCY.value,
            FieldType.PERCENT.value,
            FieldType.DURATION.value,
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        FieldType.DURATION.value: [
            FieldType.NUMBER.value,
            FieldType.CURRENCY.value,
            FieldType.PERCENT.value,
            FieldType.RATING.value,
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        # 日期族互转 + 转文本类
        FieldType.DATE.value: [
            FieldType.DATE_TIME.value,
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        FieldType.DATE_TIME.value: [
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
        ],
        # 成员转文本类（保留成员 ID）
        FieldType.COLLABORATOR.value: list(TEXT_TYPES),
        # 公式冻结：转为常规值类型，实际能否承载由值兼容性预检判定
        FieldType.FORMULA.value: [
            FieldType.SINGLE_LINE_TEXT.value,
            FieldType.LONG_TEXT.value,
            FieldType.RICH_TEXT.value,
            FieldType.NUMBER.value,
            FieldType.CURRENCY.value,
            FieldType.PERCENT.value,
            FieldType.RATING.value,
            FieldType.DURATION.value,
            FieldType.DATE.value,
            FieldType.DATE_TIME.value,
        ],
    }
    
    _geolocation_target = FieldType.GEOLOCATION.value
    
    LOSSLESS_CONVERSIONS[FieldType.AI.value] = list(TEXT_TYPES)
    
    LOSSY_CONVERSIONS = {
        FieldType.DATE_TIME.value: [
            FieldType.DATE.value,
        ],
    }
    
    
    @staticmethod
    def reorder_fields(table_id: str, field_orders: List[Dict[str, Any]]) -> bool:
        """
        批量重新排序字段
    
        Args:
            table_id: 表格 ID
            field_orders: 排序列表，每个元素包含 field_id 和 order
                例如：[{'field_id': 'xxx', 'order': 0}, {'field_id': 'yyy', 'order': 1}]
    
        Returns:
            是否排序成功
        """
        try:
            for item in field_orders:
                field_id = item.get('field_id')
                new_order = item.get('order')
    
                if field_id is None or new_order is None:
                    continue
    
                field = Field.query.filter_by(
                    id=field_id,
                    table_id=table_id
                ).first()
    
                if field:
                    field.order = new_order
    
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def duplicate_field(field_id: str, new_name: str = None) -> Dict[str, Any]:
        """
        复制字段
    
        Args:
            field_id: 源字段 ID
            new_name: 新字段名称（可选）
    
        Returns:
            包含操作结果的字典
        """
        source_field = Field.query.get(field_id)
        if not source_field:
            return {'success': False, 'error': 'field_does_not_exist'}
    
        # 获取当前最大 order
        max_order = db.session.query(func.max(Field.order)).filter_by(
            table_id=source_field.table_id
        ).scalar()
        new_order = (max_order or 0) + 1
    
        # 创建新字段
        new_field = Field(
            table_id=source_field.table_id,
            name=new_name or f"{source_field.name} 副本",
            type=source_field.type,
            description=source_field.description,
            order=new_order,
            is_primary=False,  # 复制的字段不能是主字段
            is_required=source_field.is_required,
            options=source_field.options,
            config=source_field.config
        )
    
        try:
            db.session.add(new_field)
            db.session.commit()
    
            return {
                'success': True,
                'field': new_field.to_dict()
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': 'failed_copy_field_try_again_later'}
    
    @staticmethod
    def validate_field_value(field_id: str, value: Any) -> Dict[str, Any]:
        """
        验证字段值
    
        Args:
            field_id: 字段 ID
            value: 待验证的值
    
        Returns:
            包含验证结果的字典
        """
        field = Field.query.get(field_id)
        if not field:
            return {'success': False, 'error': 'field_does_not_exist'}
    
        is_valid, error_msg = field.validate_value(value)
    
        if is_valid:
            return {'success': True}
        else:
            return {'success': False, 'error': error_msg}
    
    @staticmethod
    def validate_default_value(field_type: str, options: Optional[Dict[str, Any]], value: Any) -> tuple[bool, Optional[str]]:
        """
        验证默认值是否合法
    
        Args:
            field_type: 字段类型
            options: 字段选项（用于验证选择类型）
            value: 待验证的默认值
    
        Returns:
            (是否有效，错误信息)
        """
        # None 值总是有效的（表示没有默认值）
        if value is None:
            return True, None
    
        # 签字字段不支持默认值
        if field_type == FieldType.SIGNATURE.value:
            return False, translate('field_type_no_default_value', field_type)
    
        # 特殊处理动态默认值
        if value == 'now':
            if field_type in [FieldType.DATE.value, FieldType.DATE_TIME.value]:
                return True, None
            else:
                return False, translate('field_type_no_dynamic_default', field_type)
    
        # 根据字段类型验证默认值
        if field_type in [FieldType.SINGLE_LINE_TEXT.value, FieldType.LONG_TEXT.value, 
                         FieldType.RICH_TEXT.value, FieldType.EMAIL.value, 
                         FieldType.PHONE.value, FieldType.URL.value]:
            if not isinstance(value, str):
                return False, translate('field_default_value_must_be_string', field_type)
    
        elif field_type in [FieldType.NUMBER.value, FieldType.CURRENCY.value, 
                           FieldType.PERCENT.value, FieldType.RATING.value, 
                           FieldType.DURATION.value]:
            if not isinstance(value, (int, float)):
                return False, translate('field_default_value_must_be_number', field_type)
    
        elif field_type in [FieldType.DATE.value, FieldType.DATE_TIME.value]:
            if not isinstance(value, str):
                return False, translate('field_default_value_must_be_date_string', field_type)
            # 验证日期格式
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return False, translate('field_default_value_must_be_valid_date_format', field_type)
    
        elif field_type == FieldType.CHECKBOX.value:
            if not isinstance(value, bool):
                return False, translate('field_default_value_must_be_boolean', field_type)
    
        elif field_type == FieldType.SINGLE_SELECT.value:
            # 单选默认值应该是选项 ID（字符串）
            if not isinstance(value, str):
                return False, translate('field_default_value_must_be_option_id', field_type)
            # 验证选项是否存在
            if options and isinstance(options, dict):
                choices = options.get('choices', [])
                if not any(choice.get('id') == value for choice in choices):
                    return False, translate('field_default_value_option_not_exist', field_type)
    
        elif field_type == FieldType.MULTI_SELECT.value:
            # 多选默认值应该是选项 ID 数组
            if not isinstance(value, list):
                return False, translate('field_default_value_must_be_option_id_array', field_type)
            # 验证所有选项是否存在
            if options and isinstance(options, dict):
                choices = options.get('choices', [])
                for option_id in value:
                    if not any(choice.get('id') == option_id for choice in choices):
                        return False, translate('field_default_value_contains_nonexistent_options', field_type)
    
        elif field_type in [FieldType.LINK_TO_RECORD.value, FieldType.LINK.value,
                           FieldType.COLLABORATOR.value, FieldType.ATTACHMENT.value]:
            # 这些类型默认值应该是数组
            if not isinstance(value, list):
                return False, translate('field_default_value_must_be_array', field_type)
    
        elif field_type == FieldType.GEOLOCATION.value:
            # 地理位置默认值应该是结构化对象
            if not isinstance(value, dict):
                return False, translate('field_default_value_must_be_object', field_type)
    
        return True, None
    
    @staticmethod
    def get_field_type_info(field_type: str) -> Dict[str, Any]:
        """
        获取字段类型信息
    
        Args:
            field_type: 字段类型
    
        Returns:
            字段类型信息字典
        """
        type_info = {
            FieldType.SINGLE_LINE_TEXT.value: {
                'name': '单行文本',
                'icon': 'text',
                'description': '单行文本输入',
                'configurable': ['default_value', 'placeholder']
            },
            FieldType.LONG_TEXT.value: {
                'name': '多行文本',
                'icon': 'align-left',
                'description': '多行文本输入',
                'configurable': ['default_value', 'placeholder', 'max_length']
            },
            FieldType.RICH_TEXT.value: {
                'name': '富文本',
                'icon': 'file-text',
                'description': '富文本编辑器',
                'configurable': ['default_value']
            },
            FieldType.NUMBER.value: {
                'name': '数字',
                'icon': 'hash',
                'description': '数值输入',
                'configurable': ['default_value', 'precision', 'min', 'max', 'format']
            },
            FieldType.CURRENCY.value: {
                'name': '货币',
                'icon': 'dollar-sign',
                'description': '货币金额',
                'configurable': ['default_value', 'currency_symbol', 'precision']
            },
            FieldType.PERCENT.value: {
                'name': '百分比',
                'icon': 'percent',
                'description': '百分比值',
                'configurable': ['default_value', 'precision']
            },
            FieldType.RATING.value: {
                'name': '评分',
                'icon': 'star',
                'description': '星级评分',
                'configurable': ['max_rating', 'icon']
            },
            FieldType.DATE.value: {
                'name': '日期',
                'icon': 'calendar',
                'description': '日期选择',
                'configurable': ['default_value', 'format', 'include_time']
            },
            FieldType.DATE_TIME.value: {
                'name': '日期时间',
                'icon': 'clock',
                'description': '日期时间选择',
                'configurable': ['default_value', 'format', 'time_zone']
            },
            FieldType.DURATION.value: {
                'name': '时长',
                'icon': 'watch',
                'description': '时间时长',
                'configurable': ['format']
            },
            FieldType.SINGLE_SELECT.value: {
                'name': '单选',
                'icon': 'circle',
                'description': '单选下拉框',
                'configurable': ['choices', 'default_value', 'allow_add']
            },
            FieldType.MULTI_SELECT.value: {
                'name': '多选',
                'icon': 'check-square',
                'description': '多选下拉框',
                'configurable': ['choices', 'default_value', 'allow_add']
            },
            FieldType.CHECKBOX.value: {
                'name': '复选框',
                'icon': 'check',
                'description': '布尔值复选框',
                'configurable': ['default_value']
            },
            FieldType.LINK_TO_RECORD.value: {
                'name': '关联记录',
                'icon': 'link',
                'description': '关联到其他表格的记录',
                'configurable': ['linked_table_id', 'allow_multiple']
            },
            FieldType.LINK.value: {
                'name': '关联记录',
                'icon': 'link',
                'description': '关联到其他表格的记录',
                'configurable': ['linked_table_id', 'allow_multiple']
            },
            FieldType.LOOKUP.value: {
                'name': '查找引用',
                'icon': 'search',
                'description': '引用关联记录的字段值',
                'configurable': ['linked_field_id', 'rollup_function']
            },
            FieldType.ROLLUP.value: {
                'name': '汇总',
                'icon': 'layers',
                'description': '汇总关联记录的值',
                'configurable': ['linked_field_id', 'function']
            },
            FieldType.CREATED_BY.value: {
                'name': '创建者',
                'icon': 'user-plus',
                'description': '自动记录创建者',
                'configurable': [],
                'system': True
            },
            FieldType.LAST_MODIFIED_BY.value: {
                'name': '最后修改者',
                'icon': 'edit',
                'description': '自动记录最后修改者',
                'configurable': [],
                'system': True
            },
            FieldType.COLLABORATOR.value: {
                'name': '协作者',
                'icon': 'users',
                'description': '选择协作者',
                'configurable': ['allow_multiple', 'restrict_to_base_members']
            },
            FieldType.ATTACHMENT.value: {
                'name': '附件',
                'icon': 'paperclip',
                'description': '文件附件',
                'configurable': ['max_files', 'allowed_types', 'max_size']
            },
            FieldType.FORMULA.value: {
                'name': '公式',
                'icon': 'function',
                'description': '计算公式',
                'configurable': ['formula', 'format', 'precision']
            },
            FieldType.AUTO_NUMBER.value: {
                'name': '自动编号',
                'icon': 'hash',
                'description': '自动递增编号',
                'configurable': ['prefix', 'suffix', 'start_number'],
                'system': True
            },
            FieldType.BARCODE.value: {
                'name': '条形码',
                'icon': 'maximize',
                'description': '条形码/二维码',
                'configurable': ['format']
            },
            FieldType.EMAIL.value: {
                'name': '邮箱',
                'icon': 'mail',
                'description': '邮箱地址',
                'configurable': ['default_value', 'placeholder']
            },
            FieldType.PHONE.value: {
                'name': '电话',
                'icon': 'phone',
                'description': '电话号码',
                'configurable': ['default_value', 'format', 'country_code']
            },
            FieldType.URL.value: {
                'name': 'URL',
                'icon': 'globe',
                'description': '网址链接',
                'configurable': ['default_value', 'placeholder']
            },
            FieldType.BUTTON.value: {
                'name': '按钮',
                'icon': 'mouse-pointer',
                'description': '可点击按钮',
                'configurable': ['label', 'action', 'style']
            },
            FieldType.GEOLOCATION.value: {
                'name': '地理位置',
                'icon': 'map-pin',
                'description': '省份/城市/区县/国家和地区/经纬度/地图选点',
                'configurable': ['geo_format', 'geo_language', 'default_value']
            },
            FieldType.SIGNATURE.value: {
                'name': '签字',
                'icon': 'edit-pen',
                'description': '手写签字或输入签字，以 PNG 图片格式存储',
                'configurable': []
            }
        }
    
        return type_info.get(field_type, {
            'name': field_type,
            'icon': 'help-circle',
            'description': '未知类型',
            'configurable': []
        })
    
    @staticmethod
    def get_all_field_types() -> List[Dict[str, Any]]:
        """
        获取所有支持的字段类型信息
    
        Returns:
            字段类型信息列表
        """
        return [
            FieldService.get_field_type_info(ft.value)
            for ft in FieldType
        ]
    
    @staticmethod
    def _to_text(value: Any) -> str:
        """将值转为文本：列表以逗号分隔并保留原始 ID（不解析为名称，避免有损转换）。"""
        if isinstance(value, list):
            return ', '.join(FieldService._to_text(item) for item in value)
        if isinstance(value, dict):
            # 地理位置对象：按层级拼接为可读地址串
            if 'province' in value or 'city' in value or 'district' in value \
                    or 'country' in value or 'region' in value \
                    or 'lng' in value or 'lat' in value or 'address' in value:
                return FieldService._format_geo_text(value)
            return str(value.get('id') or value.get('name') or '')
        return str(value)
    
    @staticmethod
    def _format_geo_text(value: Any) -> str:
        """将地理位置对象格式化为地址文本串（用于展示与文本转换）。"""
        if not isinstance(value, dict):
            return str(value) if value is not None else ''
        # 经纬度优先展示坐标
        if ('lng' in value or 'lat' in value) and (value.get('lng') or value.get('lat')):
            lng = value.get('lng')
            lat = value.get('lat')
            return f'{lng}, {lat}'
        # 国家和地区
        if value.get('country') or value.get('region'):
            parts = [p for p in [value.get('region'), value.get('country')] if p]
            if parts:
                return ' / '.join(parts)
        # 省/市/区及详情
        parts = [value.get('province'), value.get('city'), value.get('district')]
        parts = [p for p in parts if p]
        if value.get('detail'):
            parts.append(value['detail'])
        if parts:
            return ' / '.join(parts)
        if value.get('address'):
            return str(value['address'])
        return ''
    
    @staticmethod
    def _to_number(value: Any) -> Any:
        """将值转为数值；无法解析时返回原值，交由预检拒绝。"""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            text = value.strip()
            try:
                number = float(text)
            except (TypeError, ValueError):
                return value
            return int(number) if number.is_integer() and '.' not in text else number
        return value
    
    @staticmethod
    def _convert_value_for_type(value: Any, from_type: str, to_type: str) -> Any:
        """
        将字段值从旧类型转换为新类型（纯函数，不查库，便于单测）
    
        Args:
            value: 原值
            from_type: 原类型
            to_type: 目标类型
    
        Returns:
            转换后的值
        """
        if value is None:
            return None
        if from_type == to_type:
            return value
    
        # 公式：结果由公式实时计算得出，按目标类型族承载
        if from_type == FieldType.FORMULA.value:
            if to_type in FieldService.TEXT_TYPES:
                return FieldService._to_text(value)
            if to_type in FieldService.NUMERIC_TYPES:
                return FieldService._to_number(value)
            if to_type in FieldService.DATE_TYPES:
                return value if isinstance(value, str) else FieldService._to_text(value)
            return value
    
        # 转文本类：原值转字符串（引用型保留原始 ID）
        if to_type in FieldService.TEXT_TYPES:
            return FieldService._to_text(value)
    
        # 单选转多选：单值包装为数组，无损
        if from_type == FieldType.SINGLE_SELECT.value and to_type == FieldType.MULTI_SELECT.value:
            return [value] if value is not None else []
    
        # 数值族互转：数值原样保留，仅展示格式变化
        if from_type in FieldService.NUMERIC_TYPES and to_type in FieldService.NUMERIC_TYPES:
            return value
    
        # 日期转日期时间：补全时间部分，无损
        if from_type == FieldType.DATE.value and to_type == FieldType.DATE_TIME.value:
            if isinstance(value, str) and 'T' not in value:
                return f"{value.strip()}T00:00:00Z"
            return value
    
        # 日期时间转日期：截取日期部分（有损，全局唯一放行的有损转换）
        if from_type == FieldType.DATE_TIME.value and to_type == FieldType.DATE.value:
            if isinstance(value, str):
                matched = re.match(r'^(\d{4}-\d{2}-\d{2})', value.strip())
                if matched:
                    return matched.group(1)
            return value
    
        # 其他转数值族：尽量数值化，无法解析时保留原值，由预检拒绝
        if to_type in FieldService.NUMERIC_TYPES:
            return FieldService._to_number(value)
    
        # 其他转日期族：字符串原样保留，由预检校验格式
        if to_type in FieldService.DATE_TYPES and isinstance(value, str):
            return value
    
        # 地理位置 <-> 文本类：文本承载为地址串，地理对象按层级拼接
        if to_type == FieldType.GEOLOCATION.value:
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                return {'address': value}
            return {'address': FieldService._to_text(value)}
        if from_type == FieldType.GEOLOCATION.value and to_type in FieldService.TEXT_TYPES:
            return FieldService._format_geo_text(value)
    
        return value
    
