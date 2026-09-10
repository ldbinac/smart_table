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


class FieldService:
    """字段服务类"""
    
    # 系统字段类型（自动创建，不能删除）
    SYSTEM_FIELD_TYPES = [
        FieldType.CREATED_BY,
        FieldType.LAST_MODIFIED_BY,
        FieldType.AUTO_NUMBER
    ]
    
    # 需要选项的字段类型
    OPTIONS_REQUIRED_TYPES = [
        FieldType.SINGLE_SELECT.value,
        FieldType.MULTI_SELECT.value
    ]
    
    # 所有支持的字段类型
    VALID_FIELD_TYPES = [ft.value for ft in FieldType]

    # ==================== 字段类型转换规则（已创建字段调整字段类型） ====================

    # 文本类字段类型
    TEXT_TYPES = [
        FieldType.SINGLE_LINE_TEXT.value,
        FieldType.LONG_TEXT.value,
        FieldType.RICH_TEXT.value,
    ]

    # 数值族字段类型（数值保留，仅展示格式变化）
    NUMERIC_TYPES = [
        FieldType.NUMBER.value,
        FieldType.CURRENCY.value,
        FieldType.PERCENT.value,
        FieldType.RATING.value,
        FieldType.DURATION.value,
    ]

    # 日期族字段类型
    DATE_TYPES = [
        FieldType.DATE.value,
        FieldType.DATE_TIME.value,
    ]

    # 系统维护的系统字段类型（值由系统写入，不允许转换）
    CONVERT_SYSTEM_TYPES = [
        FieldType.CREATED_BY.value,
        FieldType.LAST_MODIFIED_BY.value,
        FieldType.AUTO_NUMBER.value,
    ]

    # 双向禁止转换的类型：系统类型 + 引用/计算类型（值依赖跨表配置或系统维护）
    CONVERT_FORBIDDEN_TYPES = CONVERT_SYSTEM_TYPES + [
        FieldType.LINK_TO_RECORD.value,
        FieldType.LINK.value,
        FieldType.LOOKUP.value,
        FieldType.ROLLUP.value,
        FieldType.BUTTON.value,
    ]

    # 禁止作为转换目标的类型：公式需要表达式，语义上属于新增计算字段
    CONVERT_FORBIDDEN_TARGET_TYPES = [
        FieldType.FORMULA.value,
    ]

    # 字段已有数据时允许的无损转换白表
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

    # 文本类字段可转换为地理位置（文本承载为地址串），统一补充目标类型
    _geolocation_target = FieldType.GEOLOCATION.value
    for _src in TEXT_TYPES + [FieldType.EMAIL.value, FieldType.PHONE.value,
                              FieldType.URL.value, FieldType.BARCODE.value]:
        if _src != _geolocation_target:
            LOSSLESS_CONVERSIONS.setdefault(_src, [])
            if _geolocation_target not in LOSSLESS_CONVERSIONS[_src]:
                LOSSLESS_CONVERSIONS[_src].append(_geolocation_target)

    # 字段已有数据时允许的有损转换白表（全局唯一例外：日期时间转日期，丢弃时间部分）
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
        - 附件类型: attachment
        - 计算类型: formula, auto_number, barcode
        - 其他类型: email, phone, url, button
        
        Args:
            table_id: 表格 ID
            data: 创建数据，包含 name, type, options, config 等
            
        Returns:
            包含操作结果的字典
        """
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
        
        # 检查是否是系统字段
        if field.is_primary and 'is_primary' in data and not data['is_primary']:
            return {'success': False, 'error': 'primary_key_status_primary_field_removed'}
        
        # 允许更新的字段
        allowed_fields = ['name', 'description', 'is_required', 'options', 'config']
        
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
        （auto_number / created_by / last_modified_by）无需额外配置。
        返回 (是否合法, 错误 i18n key)。
        """
        if new_type in (FieldType.LINK_TO_RECORD.value, FieldType.LINK.value, FieldType.ROLLUP.value):
            config = data.get('config') or {}
            linked_table_id = config.get('linkedTableId') or config.get('linked_table_id')
            if not linked_table_id:
                return False, 'field_configuration_missing_linked_table_id'

        if new_type == FieldType.FORMULA.value:
            config = data.get('config') or {}
            formula = config.get('formula')
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
