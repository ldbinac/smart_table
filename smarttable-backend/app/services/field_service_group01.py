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

class FieldServiceGroup01Mixin:
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
    def get_all_fields(table_id: str) -> List[Field]:
        """
        获取表格中的所有字段
    
        Args:
            table_id: 表格 ID
    
        Returns:
            字段列表（按 order 排序）
        """
        return Field.query.filter_by(table_id=table_id).order_by(Field.order.asc()).all()
    
    @staticmethod
    def get_fields_by_type(table_id: str, field_type: str) -> List[Field]:
        """
        获取表格中指定类型的字段
    
        Args:
            table_id: 表格 ID
            field_type: 字段类型
    
        Returns:
            字段列表
        """
        return Field.query.filter_by(table_id=table_id, type=field_type).all()
    
    @staticmethod
    def get_field(field_id: str) -> Optional[Field]:
        """
        获取单个字段
    
        Args:
            field_id: 字段 ID
    
        Returns:
            字段对象或 None
        """
        return Field.query.get(field_id)
    
    @staticmethod
    def _validate_formula_expression(
        table_id: str,
        formula_expr: str,
        exclude_field_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        公式字段保存校验：语法解析 + 字段引用有效性
    
        保存时当场校验，避免错误公式静默保存后在计算阶段才暴露。
        返回错误信息字符串；通过校验返回 None。
    
        Args:
            table_id: 表格 ID（用于字段引用存在性校验）
            formula_expr: 公式表达式
            exclude_field_id: 编辑时排除自身（自身旧名不算缺失引用）
        """
        formula_expr = (formula_expr or '').strip()
        if not formula_expr:
            return translate('formula_expression_required')
    
        # 语法校验：解析失败即返回具体错误（如"无法解析的字符: 'V'(位置 6)"）
        from app.services.formula_service import FormulaParser, FormulaError
        try:
            FormulaParser().parse(formula_expr)
        except FormulaError as e:
            return str(e)
    
        # 引用有效性：{字段名} 引用的本表字段必须存在（编辑时排除自身）
        import re as _re
        fields = Field.query.filter_by(table_id=table_id).all()
        existing_names = {
            f.name.strip().lower() for f in fields
            if exclude_field_id is None or str(f.id) != str(exclude_field_id)
        }
        missing = [
            name for name in _re.findall(r'\{([^{}]+)\}', formula_expr)
            if name.strip().lower() not in existing_names
        ]
        if missing:
            return translate('formula_unknown_field_reference', ', '.join(missing))
    
        return None
    
    def create_field(table_id: str, data: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """
        创建新字段
    
        支持 22 种字段类型：
        - 基础类型: single_line_text, long_text, rich_text
        - 数字类型: number, currency, percent, rating
        - 日期时间: date, date_time, duration
        - 选择类型: single_select, multi_select, checkbox
        - 关联类型: link_to_record, lookup, rollup
        - 人员类型: created_by, last_modified_by, collaborator
        - 系统时间类型: created_time, updated_time（值取自记录元数据）
        - 附件类型: attachment
        - 计算类型: formula, auto_number, barcode
        - 其他类型: email, phone, url, button
    
        Args:
            table_id: 表格 ID
            data: 创建数据，包含 name, type, options, config 等
    
        Returns:
            包含操作结果的字典
        """
        # 字段增删影响整列引用的列数据与目标字段校验
        FormulaService.invalidate_table_context_cache(table_id=str(table_id))
        # 验证字段类型
        field_type = data.get('type', '').strip().lower()
        if not field_type:
            return {'success': False, 'error': 'field_type_empty'}
    
        if field_type not in FieldService.VALID_FIELD_TYPES:
            valid_types = ', '.join(FieldService.VALID_FIELD_TYPES)
            return {'success': False, 'error': translate('invalid_field_type_supported_types', valid_types)}
    
        # 验证选择类型字段的选项
        if field_type in FieldService.OPTIONS_REQUIRED_TYPES:
            options = data.get('options', {})
            choices = options.get('choices', [])
            if not choices or not isinstance(choices, list):
                return {'success': False, 'error': translate('options_required_for_field_type', field_type)}
    
        # 查找字段配置校验
        if field_type == FieldType.LOOKUP.value:
            from app.services.lookup_service import LookupService
            config_data = data.get('config', {}) or {}
            is_valid, error_msg = LookupService.validate_config(config_data, table_id)
            if not is_valid:
                return {'success': False, 'error': error_msg}
    
        # AI 字段 ai_config 结构校验（B1）
        if field_type == FieldType.AI.value:
            is_valid, error_key = _validate_ai_options(
                (data.get('options') or {}).get('ai_config'), str(table_id))
            if not is_valid:
                return {'success': False, 'error': translate(error_key)}
    
        # 公式字段校验：语法与字段引用（保存时当场提示，避免错误公式静默保存）
        if field_type == FieldType.FORMULA.value:
            options = data.get('options', {}) or {}
            config_data = data.get('config', {}) or {}
            formula_expr = options.get('formula') or config_data.get('formula') or ''
            error_msg = FieldService._validate_formula_expression(table_id, formula_expr)
            if error_msg:
                return {'success': False, 'error': error_msg}
    
        # 验证默认值（如果提供）
        if 'defaultValue' in data or 'default_value' in data:
            default_value = data.get('defaultValue') or data.get('default_value')
            is_valid, error_msg = FieldService.validate_default_value(field_type, data.get('options'), default_value)
            if not is_valid:
                return {'success': False, 'error': error_msg}
    
        # 获取当前最大 order
        max_order = db.session.query(func.max(Field.order)).filter_by(table_id=table_id).scalar()
        new_order = (max_order or 0) + 1
    
        # 准备 config 数据，包含默认值
        config = data.get('config', {}) or {}
        default_value = data.get('defaultValue') or data.get('default_value')
        if default_value is not None:
            # 日期类型字段根据字段类型格式化默认值
            if field_type in [FieldType.DATE.value, FieldType.DATE_TIME.value]:
                default_value = _format_date_default_value(default_value, field_type)
            config['defaultValue'] = default_value
            config['defaultType'] = 'dynamic' if default_value == 'now' else 'static'
            config['updatedAt'] = datetime.now(timezone.utc).isoformat()
    
        # 创建字段
        field = Field(
            table_id=table_id,
            name=data.get('name', '未命名字段'),
            type=field_type,
            description=data.get('description'),
            order=new_order,
            is_primary=data.get('is_primary', False),
            is_required=data.get('is_required', False),
            options=data.get('options'),
            config=config if config else None
        )
    
        try:
            db.session.add(field)
            db.session.commit()
    
            try:
                from app.services.collaboration_service import CollaborationService
                CollaborationService.broadcast_if_enabled('data:field_created', str(field.table.base_id), {
                    'table_id': table_id,
                    'field': field.to_dict(),
                    'changed_by': user_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            except Exception:
                pass
    
            return {
                'success': True,
                'field': field.to_dict()
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': 'failed_create_field_try_again_later'}
    
    @staticmethod
    def update_field(field_id: str, data: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """
        更新字段
    
        Args:
            field_id: 字段 ID
            data: 更新数据
    
        Returns:
            包含操作结果的字典
        """
        field = Field.query.get(field_id)
    
        if not field:
            return {'success': False, 'error': 'field_does_not_exist'}
    
        # 字段更新（改名/公式/选项）影响整列引用的列数据
        FormulaService.invalidate_table_context_cache(table_id=str(field.table_id))
    
        # 公式字段校验：表达式变化时校验语法与字段引用
        if field.type == FieldType.FORMULA.value:
            options = data.get('options') if 'options' in data else (field.options or {})
            config_data = data.get('config') if 'config' in data else (field.config or {})
            formula_expr = (options or {}).get('formula') or (config_data or {}).get('formula') or ''
            error_msg = FieldService._validate_formula_expression(
                str(field.table_id), formula_expr, exclude_field_id=str(field.id)
            )
            if error_msg:
                return {'success': False, 'error': error_msg}
    
        # 检查是否是系统字段
        if field.is_primary and 'is_primary' in data and not data['is_primary']:
            return {'success': False, 'error': 'primary_key_status_primary_field_removed'}
    
        # 允许更新的字段
        allowed_fields = ['name', 'description', 'is_required', 'options', 'config']
    
        # AI 字段 ai_config 结构校验（B1）：类型变更为 ai、或 ai 字段更新 options 时
        _target_type = (data.get('type', '').strip().lower()
                        if 'type' in data else field.type)
        if _target_type == FieldType.AI.value and (
                'options' in data or _target_type != field.type):
            _options_data = data.get('options', field.options) or {}
            is_valid, error_key = _validate_ai_options(
                (_options_data or {}).get('ai_config'), str(field.table_id),
                current_field_id=str(field.id))  # B8：依赖链以新配置覆盖旧配置校验
            if not is_valid:
                return {'success': False, 'error': translate(error_key)}
    
        # 处理默认值更新
        if 'defaultValue' in data or 'default_value' in data:
            # 用 in 判断键是否存在，取出时不使用 `or` 兜底：
            # 否则显式传入的 0 / '' / False 等假值会被吞掉，且无法区分“清除默认值(null)”与“未传”
            default_value = data.get('defaultValue', data.get('default_value'))
            is_valid, error_msg = FieldService.validate_default_value(
                field.type, field.options, default_value
            )
            if not is_valid:
                return {'success': False, 'error': error_msg}
    
            # 日期类型字段根据字段类型格式化默认值
            if default_value is not None and field.type in [FieldType.DATE.value, FieldType.DATE_TIME.value]:
                default_value = _format_date_default_value(default_value, field.type)
    
            # 更新 config 中的默认值
            if field.config is None:
                field.config = {}
            if default_value is None:
                # 清除默认值：必须移除配置键而非写入 None，
                # 否则 get_default_value() 会命中该键返回 None，
                # 且 to_dict() 仍会输出 defaultValue，前端表现为“取消不生效”
                field.config.pop('defaultValue', None)
                field.config.pop('defaultType', None)
            else:
                field.config['defaultValue'] = default_value
                field.config['defaultType'] = 'dynamic' if default_value == 'now' else 'static'
            field.config['updatedAt'] = datetime.now(timezone.utc).isoformat()
            # 标记 config 字段为已修改，确保 SQLAlchemy 检测到变更
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(field, 'config')
    
        # 类型字段特殊处理
        if 'type' in data:
            new_type = data['type'].strip().lower()
            if new_type != field.type:
                # 1) 目标类型必须是受支持的字段类型
                if new_type not in FieldService.VALID_FIELD_TYPES:
                    return {'success': False, 'error': translate('invalid_field_type_supported_types', new_type)}
    
                old_type = field.type
                has_data = FieldService._field_has_data(field)
                verdict, reason_key, _notice = FieldService._evaluate_conversion(field, new_type, has_data)
    
                # 2) 禁止的转换：直接拒绝并说明原因
                if verdict == 'forbidden':
                    return {
                        'success': False,
                        'error': translate(reason_key, old_type, new_type),
                        'errorKey': reason_key,
                    }
    
                # 3) 有损转换：必须显式确认，避免用户在不知情的情况下丢失数据
                if verdict == 'lossy' and not data.get('confirmLossy'):
                    return {
                        'success': False,
                        'error': translate('field_type_conversion_requires_confirmation', old_type, new_type),
                        'needConfirm': True,
                        'lossy': True,
                    }
    
                # 4) 目标类型为选择类时必须先提供选项，
                #    否则后续校验失败会留下未回滚的脏会话
                if new_type in FieldService.OPTIONS_REQUIRED_TYPES:
                    pending_options = data.get('options', field.options) or {}
                    choices = pending_options.get('choices', []) if isinstance(pending_options, dict) else []
                    if not choices:
                        return {'success': False, 'error': translate('options_required_for_field_type', new_type)}
    
                # 4.5) 目标类型为引用/计算类时必须提供相应配置，确保关联关系一致
                config_ok, config_err = FieldService._validate_conversion_target_config(field, new_type, data)
                if not config_ok:
                    return {'success': False, 'error': translate(config_err), 'errorKey': config_err}
    
                # 5) 转换前值兼容性预检：存在无法承载的值则整字段拒绝，绝不静默改写
                is_compatible, incompatible_count, samples = FieldService._precheck_values(field, old_type, new_type)
                if not is_compatible:
                    return {
                        'success': False,
                        'error': translate('field_type_conversion_incompatible_values', incompatible_count),
                        'incompatibleCount': incompatible_count,
                        'samples': samples,
                    }
    
                # 6) 转换已有记录中该字段的值，避免类型变更后出现类型转换错误
                converted_count = FieldService._convert_record_values(field, old_type, new_type)
                field.type = new_type
    
                # 7) 公式冻结：当前计算结果已固化为静态值，清除公式配置
                if old_type == FieldType.FORMULA.value and field.config:
                    from sqlalchemy.orm.attributes import flag_modified
                    field.config.pop('formula', None)
                    field.config.pop('_last_computed', None)
                    flag_modified(field, 'config')
    
                logger.info(
                    f'[FieldService] 字段类型转换: field={field_id}, {old_type} -> {new_type}, '
                    f'hasData={has_data}, lossy={verdict == "lossy"}, converted={converted_count}'
                )
    
        # 处理 config 更新 - 需要特殊处理以确保 SQLAlchemy 检测到变更
        if 'config' in data:
            field.config = data['config']
            # 标记 config 字段为已修改，确保 SQLAlchemy 检测到变更
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(field, 'config')
    
        for field_name in allowed_fields:
            if field_name in data and field_name != 'config':  # config 已单独处理
                setattr(field, field_name, data[field_name])
    
        # 公式字段：确保公式表达式同时落在 options 与 config，前后端/服务端一致。
        # 前端以 options.formula 为准，服务端公式引擎（formula_service）读取 config.formula；
        # 任一侧缺失时从另一侧补齐，避免保存后公式丢失或服务端计算失败。
        if field.type == FieldType.FORMULA.value:
            from sqlalchemy.orm.attributes import flag_modified
            options = field.options or {}
            formula_expr = options.get('formula')
            if not formula_expr and field.config:
                formula_expr = field.config.get('formula')
            if formula_expr:
                if field.options is None:
                    field.options = {}
                field.options['formula'] = formula_expr
                if field.config is None:
                    field.config = {}
                field.config['formula'] = formula_expr
                flag_modified(field, 'config')
                flag_modified(field, 'options')
    
        # 验证选择类型字段的选项
        if field.type in FieldService.OPTIONS_REQUIRED_TYPES:
            options = field.options or {}
            choices = options.get('choices', [])
            if not choices or not isinstance(choices, list):
                return {'success': False, 'error': translate('options_required_for_field_type', field.type)}
    
        # 查找字段配置校验
        if field.type == FieldType.LOOKUP.value:
            from app.services.lookup_service import LookupService
            config_data = field.config or {}
            is_valid, error_msg = LookupService.validate_config(config_data, str(field.table_id))
            if not is_valid:
                return {'success': False, 'error': error_msg}
    
        field.updated_at = datetime.now(timezone.utc)
    
        try:
            db.session.commit()
    
            try:
                workflow_event_bus.publish(
                    event_type='field_changed',
                    table_id=str(field.table_id),
                    actor_id=str(user_id) if user_id else None,
                    changes=data,
                    metadata={'field_id': field_id, 'field': field.to_dict()}
                )
            except Exception as e:
                logger.error(f'[FieldService] workflow_event_bus publish (update) error: {e}')
    
            try:
                from app.services.collaboration_service import CollaborationService
                CollaborationService.broadcast_if_enabled('data:field_updated', str(field.table.base_id), {
                    'table_id': str(field.table_id),
                    'field_id': field_id,
                    'field': field.to_dict(),
                    'changed_by': user_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            except Exception:
                pass
    
            return {
                'success': True,
                'field': field.to_dict()
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': 'failed_update_field_try_again_later'}
    
    @staticmethod
    def delete_field(field_id: str, user_id: str = None) -> Dict[str, Any]:
        """
        删除字段
    
        系统字段（is_primary=True）不能被删除
    
        Args:
            field_id: 字段 ID
    
        Returns:
            包含操作结果的字典
        """
        field = Field.query.get(field_id)
        if not field:
            return {'success': False, 'error': 'field_does_not_exist'}
    
        # 字段删除影响整列引用的列数据
        FormulaService.invalidate_table_context_cache(table_id=str(field.table_id))
    
        # 检查是否是主字段
        if field.is_primary:
            return {'success': False, 'error': 'primary_field_deleted'}
    
        # 检查是否是系统字段类型
        try:
            field_type_enum = FieldType(field.type)
            if field_type_enum in FieldService.SYSTEM_FIELD_TYPES:
                return {'success': False, 'error': translate('system_field_type_cannot_delete', field.type)}
        except ValueError:
            pass
    
        saved_base_id = str(field.table.base_id)
        saved_table_id = str(field.table_id)
        saved_field_id = str(field.id)
    
        try:
            db.session.delete(field)
            db.session.commit()
    
            try:
                from app.services.collaboration_service import CollaborationService
                CollaborationService.broadcast_if_enabled('data:field_deleted', saved_base_id, {
                    'table_id': saved_table_id,
                    'field_id': saved_field_id,
                    'changed_by': user_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            except Exception:
                pass
    
            return {'success': True}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': 'failed_delete_field_try_again_later'}
    
