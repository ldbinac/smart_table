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

class FieldServiceGroup03Mixin:
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
    def _value_fits_type(value: Any, to_type: str) -> bool:
        """判断单个值能否被目标类型承载（用于转换前预检）。"""
        if value is None:
            return True
        if to_type in FieldService.TEXT_TYPES:
            return isinstance(value, (str, int, float, bool))
        if to_type in FieldService.NUMERIC_TYPES:
            if isinstance(value, bool):
                return False
            if isinstance(value, (int, float)):
                return True
            if isinstance(value, str):
                try:
                    float(value)
                    return True
                except (TypeError, ValueError):
                    return False
            return False
        if to_type in FieldService.DATE_TYPES:
            return isinstance(value, str) and bool(re.match(r'^\d{4}-\d{2}-\d{2}', value.strip()))
        if to_type == FieldType.EMAIL.value:
            return isinstance(value, str) and (value.strip() == '' or '@' in value)
        if to_type in (FieldType.URL.value, FieldType.PHONE.value, FieldType.BARCODE.value):
            return isinstance(value, str)
        if to_type == FieldType.GEOLOCATION.value:
            return isinstance(value, dict)
        return True
    
    @staticmethod
    def _field_value_keys(field: Field, from_type: str) -> List[str]:
        """返回字段可能存储值的键。
    
        普通字段以字段 ID 为键；公式字段历史批量重算结果曾以字段名为键，需同时兼容。
        """
        keys = [str(field.id)]
        if from_type == FieldType.FORMULA.value and field.name:
            keys.append(field.name)
        return keys
    
    @staticmethod
    def _field_has_data(field: Field) -> bool:
        """判定字段是否已产生数据。
    
        采用分批遍历 + 命中即返回，避免大表全量加载。
        空值口径：None / '' / [] 视为无数据；0 / False 属于有效业务值，视为有数据。
        """
        keys = FieldService._field_value_keys(field, field.type)
        query = Record.query.filter_by(table_id=field.table_id)
        for record in query.yield_per(500):
            values = record.values or {}
            for key in keys:
                value = values.get(key)
                if value is None or value == '' or value == []:
                    continue
                return True
        return False
    
    @staticmethod
    def _compute_formula_value(
        field: Field, record: Record, field_id_to_name: Dict[str, str] = None
    ) -> Any:
        """实时计算公式字段在某条记录上的结果。
    
        公式值不落存储（读取时实时计算），因此预检与冻结都需要实时求值。
        为避免逐条查表，字段 ID -> 字段名映射由调用方一次性预取后传入。
        """
        from app.services.formula_service import FormulaService
    
        formula_expr = (field.config or {}).get('formula', '')
        if not formula_expr:
            return None
    
        if field_id_to_name is None:
            all_fields = Field.query.filter_by(table_id=field.table_id).all()
            field_id_to_name = {str(f.id): f.name for f in all_fields}
    
        context_by_name = {}
        for field_id, value in (record.values or {}).items():
            field_name = field_id_to_name.get(str(field_id))
            if field_name:
                context_by_name[field_name] = value
    
        try:
            result = FormulaService.evaluate_formula(formula_expr, context_by_name)
            return FormulaService._serialize_result(result)
        except Exception as e:
            logger.warning(f'[FieldService] 公式求值失败，跳过该记录: field={field.id}, error={e}')
            return None
    
    @staticmethod
    def _precheck_values(field: Field, from_type: str, to_type: str) -> Tuple[bool, int, List[str]]:
        """转换前值兼容性预检：校验已有值转换后能否被目标类型承载。
    
        存在不兼容值时整字段拒绝，返回不兼容数量与样例，绝不静默改写或置空。
    
        Returns:
            (是否全部兼容, 不兼容数量, 不兼容值样例)
        """
        incompatible_count = 0
        samples: List[str] = []
        field_id_to_name = None
        if from_type == FieldType.FORMULA.value:
            all_fields = Field.query.filter_by(table_id=field.table_id).all()
            field_id_to_name = {str(f.id): f.name for f in all_fields}
    
        for record in Record.query.filter_by(table_id=field.table_id).yield_per(500):
            if from_type == FieldType.FORMULA.value:
                old_value = FieldService._compute_formula_value(field, record, field_id_to_name)
            else:
                old_value = None
                values = record.values or {}
                for key in FieldService._field_value_keys(field, from_type):
                    if key in values:
                        old_value = values[key]
                        break
    
            if old_value is None or old_value == '' or old_value == []:
                continue
    
            new_value = FieldService._convert_value_for_type(old_value, from_type, to_type)
            if not FieldService._value_fits_type(new_value, to_type):
                incompatible_count += 1
                if len(samples) < 5:
                    samples.append(str(new_value)[:100])
    
        return incompatible_count == 0, incompatible_count, samples
    
    @staticmethod
    def _convert_record_values(field: Field, from_type: str, to_type: str) -> int:
        """转换表格中已有记录该字段的值，返回实际转换的记录数。
    
        分批加载避免大表内存压力；公式字段会将当前计算结果冻结为静态值写入字段 ID 键。
        """
        from sqlalchemy.orm.attributes import flag_modified
    
        field_id = str(field.id)
        keys = FieldService._field_value_keys(field, from_type)
        field_id_to_name = None
        if from_type == FieldType.FORMULA.value:
            all_fields = Field.query.filter_by(table_id=field.table_id).all()
            field_id_to_name = {str(f.id): f.name for f in all_fields}
    
        converted_count = 0
        for record in Record.query.filter_by(table_id=field.table_id).yield_per(500):
            if record.values is None:
                record.values = {}
            values = record.values
    
            # 公式冻结：实时计算结果并固化为静态值
            if from_type == FieldType.FORMULA.value:
                old_value = FieldService._compute_formula_value(field, record, field_id_to_name)
                new_value = FieldService._convert_value_for_type(old_value, from_type, to_type)
                if new_value is None:
                    continue
                values[field_id] = new_value
                flag_modified(record, 'values')
                converted_count += 1
                continue
    
            source_key = None
            old_value = None
            for key in keys:
                if key in values:
                    old_value = values[key]
                    source_key = key
                    break
            if source_key is None:
                continue
    
            new_value = FieldService._convert_value_for_type(old_value, from_type, to_type)
            # 值未变化且键已是规范键时无需写入
            if new_value == old_value and source_key == field_id:
                continue
    
            # 公式历史结果曾以字段名为键，转换时迁移到规范键，避免残留脏值
            if source_key != field_id:
                values.pop(source_key, None)
            values[field_id] = new_value
            flag_modified(record, 'values')
            converted_count += 1
    
        return converted_count
    
    @staticmethod
    def _is_valid_type_conversion(from_type: str, to_type: str, has_data: bool = True,
                                  is_primary: bool = False) -> str:
        """
        检查字段类型转换是否可行
    
        Args:
            from_type: 原类型
            to_type: 目标类型
            has_data: 该字段是否已产生数据
            is_primary: 是否为记录主字段
    
        Returns:
            'allowed' 直接放行 | 'lossy' 有损且需二次确认 | 'forbidden' 禁止转换
        """
        # 相同类型总是允许
        if from_type == to_type:
            return 'allowed'
    
        # 主字段为自动编号且已有数据时，允许降级为文本类（单行/多行/富文本）。
        # 自动编号值为整数，转为文本无损，且主字段作为记录标题保持可用；
        # 反向（主字段文本有数据转自动编号）保持禁止，见 _evaluate_conversion。
        if is_primary and from_type == FieldType.AUTO_NUMBER.value and to_type in FieldService.TEXT_TYPES:
            return 'allowed'
    
        # 字段尚无任何数据：允许自由转换到任意类型（含系统/引用/公式类型）。
        # 目标类型所需的选项与配置由 update_field 在转换时负责校验并补齐，保证一致性。
        if not has_data:
            return 'allowed'
    
        # 文本类字段（单行/多行/富文本）已有数据时，不得转换为电话/邮箱/链接：
        # 既有文本值往往不符合目标类型的格式校验，转换后会产生非法数据。
        if from_type in FieldService.TEXT_TYPES and to_type in (
                FieldType.PHONE.value, FieldType.EMAIL.value, FieldType.URL.value):
            return 'forbidden'
    
        # 系统类型与引用/计算类型双向禁止
        if from_type in FieldService.CONVERT_FORBIDDEN_TYPES:
            return 'forbidden'
        if to_type in FieldService.CONVERT_FORBIDDEN_TYPES:
            return 'forbidden'
    
        # 不允许转换为公式类型
        if to_type in FieldService.CONVERT_FORBIDDEN_TARGET_TYPES:
            return 'forbidden'
    
        # 已有数据：仅放行无损转换，以及唯一放行的有损例外
        if to_type in FieldService.LOSSLESS_CONVERSIONS.get(from_type, []):
            return 'allowed'
        if to_type in FieldService.LOSSY_CONVERSIONS.get(from_type, []):
            return 'lossy'
    
        return 'forbidden'
    
    @staticmethod
    def _validate_conversion_target_config(field: Field, new_type: str, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """空字段转换为需要配置的类型时，校验目标类型所需的配置，确保转换后字段一致。
    
        仅校验「必须提供配置才能成立」的类型；普通类型及系统自维护类型
        （auto_number / created_by / created_time / updated_by / updated_time / last_modified_by）无需额外配置。
        返回 (是否合法, 错误 i18n key)。
        """
        if new_type in (FieldType.LINK_TO_RECORD.value, FieldType.LINK.value, FieldType.ROLLUP.value):
            config = data.get('config') or {}
            linked_table_id = config.get('linkedTableId') or config.get('linked_table_id')
            if not linked_table_id:
                return False, 'field_configuration_missing_linked_table_id'
    
        if new_type == FieldType.FORMULA.value:
            # 公式表达式可能位于 config.formula（服务端约定）或 options.formula（前端约定），
            # 二者任一存在即视为已提供，避免前端只下发 options 时被误判为缺失。
            config = data.get('config') or {}
            formula = config.get('formula')
            if not formula:
                options = data.get('options') or {}
                formula = options.get('formula')
            if not formula or not str(formula).strip():
                return False, 'field_configuration_missing_formula'
    
        if new_type == FieldType.LOOKUP.value:
            from app.services.lookup_service import LookupService
            config = data.get('config') or {}
            is_valid, error_msg = LookupService.validate_config(config, str(field.table_id))
            if not is_valid:
                return False, error_msg
    
        return True, None
    
    @staticmethod
    def _evaluate_conversion(field: Field, to_type: str, has_data: bool) -> Tuple[str, str, str]:
        """综合字段自身限制评估转换结果。
    
        Returns:
            (verdict, 禁止原因 i18n key, 告知文案 i18n key)
        """
        from_type = field.type
        if from_type == to_type:
            return 'allowed', '', ''
    
        # 主字段值用作记录标题：已有数据时仅允许在文本类之间转换；
        # 尚无数据时允许转换为任意类型（空字段转换安全，且可转为自动编号等）
        if field.is_primary and has_data and to_type not in FieldService.TEXT_TYPES:
            return 'forbidden', 'field_type_conversion_primary_text_only', ''
    
        verdict = FieldService._is_valid_type_conversion(from_type, to_type, has_data, field.is_primary)
        if verdict == 'forbidden':
            if from_type in FieldService.CONVERT_SYSTEM_TYPES or to_type in FieldService.CONVERT_SYSTEM_TYPES:
                reason = 'field_type_conversion_blocked_system_type'
            elif from_type in FieldService.CONVERT_FORBIDDEN_TYPES or to_type in FieldService.CONVERT_FORBIDDEN_TYPES:
                reason = 'field_type_conversion_blocked_reference_type'
            elif to_type in FieldService.CONVERT_FORBIDDEN_TARGET_TYPES:
                reason = 'field_type_conversion_blocked_target_formula'
            elif from_type in FieldService.TEXT_TYPES and to_type in (
                    FieldType.PHONE.value, FieldType.EMAIL.value, FieldType.URL.value):
                reason = 'field_type_conversion_text_to_contact_blocked'
            else:
                reason = 'field_type_conversion_blocked_lossy'
            return verdict, reason, ''
    
        # 数据无损但行为发生变化的转换，需明确告知用户
        notice = ''
        if verdict == 'lossy':
            notice = 'field_type_conversion_lossy_datetime_to_date'
        elif from_type == FieldType.FORMULA.value:
            notice = 'field_type_conversion_notice_formula_freeze'
        elif from_type == FieldType.COLLABORATOR.value and to_type in FieldService.TEXT_TYPES:
            notice = 'field_type_conversion_notice_keep_member_id'
        elif from_type in (FieldType.SINGLE_SELECT.value, FieldType.MULTI_SELECT.value) \
                and to_type in FieldService.TEXT_TYPES:
            notice = 'field_type_conversion_notice_keep_option_id'
    
        return verdict, '', notice
    
    @staticmethod
    def get_convertible_types(field: Field) -> Dict[str, Any]:
        """获取该字段可转换的目标类型清单，供前端启用/禁用选项并展示告知。
    
        Returns:
            {'hasData': bool, 'allowed': [{'type','lossy','notice'}], 'blocked': [{'type','reason'}]}
        """
        has_data = FieldService._field_has_data(field)
        allowed: List[Dict[str, Any]] = []
        blocked: List[Dict[str, Any]] = []
    
        for field_type in FieldType:
            # link 是前端关联类型别名，与 link_to_record 属同一能力，不重复展示
            if field_type is FieldType.LINK:
                continue
            to_type = field_type.value
            verdict, reason_key, notice_key = FieldService._evaluate_conversion(field, to_type, has_data)
            if verdict == 'forbidden':
                blocked.append({'type': to_type, 'reason': translate(reason_key)})
            else:
                allowed.append({
                    'type': to_type,
                    'lossy': verdict == 'lossy',
                    'notice': translate(notice_key) if notice_key else '',
                })
    
        return {'hasData': has_data, 'allowed': allowed, 'blocked': blocked}
    
    @staticmethod
    def check_permission(field_id: str, user_id: str, 
                         min_role: MemberRole = MemberRole.VIEWER) -> bool:
        """
        检查用户对字段的权限
    
        Args:
            field_id: 字段 ID
            user_id: 用户 ID
            min_role: 最低要求角色
    
        Returns:
            是否有权限
        """
    
        field = Field.query.get(field_id)
        if not field:
            return False
    
        # 通过表格和基础数据检查权限
        table = Table.query.get(field.table_id)
        if not table:
            return False
    
        return BaseService.check_permission(str(table.base_id), user_id, min_role)
    
