"""
字段服务模块
处理 Field 的 CRUD 操作、排序管理和类型验证
支持 22 种字段类型
"""
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import func

from app.extensions import db
from app.models.field import Field, FieldType
from app.models.table import Table
from app.models.base import MemberRole


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
    def create_field(table_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
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
            return {'success': False, 'error': '字段类型不能为空'}
        
        if field_type not in FieldService.VALID_FIELD_TYPES:
            valid_types = ', '.join(FieldService.VALID_FIELD_TYPES)
            return {'success': False, 'error': f'无效的字段类型。支持的类型: {valid_types}'}
        
        # 验证选择类型字段的选项
        if field_type in FieldService.OPTIONS_REQUIRED_TYPES:
            options = data.get('options', {})
            choices = options.get('choices', [])
            if not choices or not isinstance(choices, list):
                return {'success': False, 'error': f'{field_type} 类型字段必须提供选项列表'}
        
        # 获取当前最大 order
        max_order = db.session.query(func.max(Field.order)).filter_by(table_id=table_id).scalar()
        new_order = (max_order or 0) + 1
        
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
            config=data.get('config')
        )
        
        try:
            db.session.add(field)
            db.session.commit()
            
            return {
                'success': True,
                'field': field.to_dict()
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': f'创建字段失败: {str(e)}'}
    
    @staticmethod
    def update_field(field_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
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
            return {'success': False, 'error': '字段不存在'}
        
        # 检查是否是系统字段
        if field.is_primary and 'is_primary' in data and not data['is_primary']:
            return {'success': False, 'error': '不能取消主字段的主键状态'}
        
        # 允许更新的字段
        allowed_fields = ['name', 'description', 'is_required', 'options', 'config']
        
        # 类型字段特殊处理
        if 'type' in data:
            new_type = data['type'].strip().lower()
            if new_type != field.type:
                # 检查类型转换是否合法
                if not FieldService._is_valid_type_conversion(field.type, new_type):
                    return {'success': False, 'error': f'不能将 {field.type} 转换为 {new_type}'}
                field.type = new_type
        
        for field_name in allowed_fields:
            if field_name in data:
                setattr(field, field_name, data[field_name])
        
        # 验证选择类型字段的选项
        if field.type in FieldService.OPTIONS_REQUIRED_TYPES:
            options = field.options or {}
            choices = options.get('choices', [])
            if not choices or not isinstance(choices, list):
                return {'success': False, 'error': f'{field.type} 类型字段必须提供选项列表'}
        
        field.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return {
                'success': True,
                'field': field.to_dict()
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': f'更新字段失败: {str(e)}'}
    
    @staticmethod
    def delete_field(field_id: str) -> Dict[str, Any]:
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
            return {'success': False, 'error': '字段不存在'}
        
        # 检查是否是主字段
        if field.is_primary:
            return {'success': False, 'error': '主字段不能被删除'}
        
        # 检查是否是系统字段类型
        try:
            field_type_enum = FieldType(field.type)
            if field_type_enum in FieldService.SYSTEM_FIELD_TYPES:
                return {'success': False, 'error': f'{field.type} 是系统字段类型，不能被删除'}
        except ValueError:
            pass
        
        try:
            db.session.delete(field)
            db.session.commit()
            return {'success': True}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': f'删除字段失败: {str(e)}'}
    
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
            return {'success': False, 'error': '字段不存在'}
        
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
            return {'success': False, 'error': f'复制字段失败: {str(e)}'}
    
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
            return {'success': False, 'error': '字段不存在'}
        
        is_valid, error_msg = field.validate_value(value)
        
        if is_valid:
            return {'success': True}
        else:
            return {'success': False, 'error': error_msg}
    
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
    def _is_valid_type_conversion(from_type: str, to_type: str) -> bool:
        """
        检查字段类型转换是否合法
        
        Args:
            from_type: 原类型
            to_type: 目标类型
            
        Returns:
            是否允许转换
        """
        # 相同类型总是允许
        if from_type == to_type:
            return True
        
        # 定义允许的转换映射
        allowed_conversions = {
            FieldType.SINGLE_LINE_TEXT.value: [
                FieldType.LONG_TEXT.value,
                FieldType.RICH_TEXT.value,
                FieldType.EMAIL.value,
                FieldType.PHONE.value,
                FieldType.URL.value
            ],
            FieldType.NUMBER.value: [
                FieldType.CURRENCY.value,
                FieldType.PERCENT.value,
                FieldType.RATING.value,
                FieldType.SINGLE_LINE_TEXT.value
            ],
            FieldType.DATE.value: [
                FieldType.DATE_TIME.value,
                FieldType.SINGLE_LINE_TEXT.value
            ],
            FieldType.SINGLE_SELECT.value: [
                FieldType.MULTI_SELECT.value,
                FieldType.SINGLE_LINE_TEXT.value
            ],
            FieldType.MULTI_SELECT.value: [
                FieldType.SINGLE_SELECT.value,
                FieldType.SINGLE_LINE_TEXT.value
            ]
        }
        
        return to_type in allowed_conversions.get(from_type, [])
    
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
        from app.services.base_service import BaseService
        
        field = Field.query.get(field_id)
        if not field:
            return False
        
        # 通过表格和基础数据检查权限
        table = Table.query.get(field.table_id)
        if not table:
            return False
        
        return BaseService.check_permission(str(table.base_id), user_id, min_role)
