"""
表格服务模块
处理 Table 的 CRUD 操作和排序管理
"""
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

from sqlalchemy import func

from app.extensions import db
from app.models.table import Table
from app.models.field import Field, FieldType
from app.models.view import View, ViewType
from app.models.base import Base, MemberRole
from app.services.base_service import BaseService


class TableService:
    """表格服务类"""
    
    @staticmethod
    def get_all_tables(base_id: str) -> List[Table]:
        """
        获取基础数据中的所有表格
        
        Args:
            base_id: 基础数据 ID
            
        Returns:
            表格列表（按 order 排序）
        """
        return Table.query.filter_by(base_id=base_id).order_by(Table.order.asc()).all()
    
    @staticmethod
    def get_table(table_id: str) -> Optional[Table]:
        """
        获取单个表格
        
        Args:
            table_id: 表格 ID
            
        Returns:
            表格对象或 None
        """
        return Table.query.get(table_id)
    
    @staticmethod
    def get_table_by_id(table_id: str) -> Optional[Table]:
        """get_table 的别名，供路由层调用"""
        return TableService.get_table(table_id)
    
    @staticmethod
    def create_table(base_id: str, data: Dict[str, Any]) -> Table:
        """
        创建新表格
        
        创建表格时会自动创建默认字段：
        - 主字段（单行文本）
        - 创建时间字段
        - 更新时间字段
        
        Args:
            base_id: 基础数据 ID
            data: 创建数据，包含 name, description 等
            
        Returns:
            创建的表格对象
        """
        # 获取当前最大 order
        max_order = db.session.query(func.max(Table.order)).filter_by(base_id=base_id).scalar()
        new_order = (max_order or 0) + 1
        
        # 创建表格
        table = Table(
            base_id=base_id,
            name=data.get('name', '未命名表格'),
            description=data.get('description'),
            order=new_order
        )
        
        db.session.add(table)
        db.session.flush()  # 获取 table.id
        
        # 创建默认字段
        # 1. 主字段（名称字段）
        # primary_field = Field(
        #     table_id=table.id,
        #     name=data.get('primary_field_name', '名称'),
        #     type=FieldType.SINGLE_LINE_TEXT.value,
        #     order=0,
        #     is_primary=True,
        #     is_required=True
        # )
        # db.session.add(primary_field)
        # db.session.flush()
        
        # # 设置主字段
        # table.primary_field_id = primary_field.id
        
        # # 2. 创建时间字段
        # created_at_field = Field(
        #     table_id=table.id,
        #     name='创建时间',
        #     type=FieldType.DATE_TIME.value,
        #     order=1,
        #     is_required=False,
        #     config={'auto_fill': 'created_at'}
        # )
        # db.session.add(created_at_field)
        
        # # 3. 更新时间字段
        # updated_at_field = Field(
        #     table_id=table.id,
        #     name='更新时间',
        #     type=FieldType.DATE_TIME.value,
        #     order=2,
        #     is_required=False,
        #     config={'auto_fill': 'updated_at'}
        # )
        # db.session.add(updated_at_field)
        
        # 4. 创建默认的表格视图
        default_view = View(
            table_id=table.id,
            name='表格视图',
            type=ViewType.TABLE.value,  # 表格视图
            description='默认表格视图',
            order=0,
            is_default=True,
            is_public=True,
            filters=[],
            sort_config=[],
            group_config={},
            field_visibility={}
        )
        db.session.add(default_view)
        
        db.session.commit()
        
        return table
    
    @staticmethod
    def update_table(table_id: str, data: Dict[str, Any]) -> Optional[Table]:
        """
        更新表格
        
        Args:
            table_id: 表格 ID
            data: 更新数据
            
        Returns:
            更新后的表格对象，如果不存在返回 None
        """
        table = Table.query.get(table_id)
        if not table:
            return None
        
        # 允许更新的字段
        allowed_fields = ['name', 'description']
        
        for field in allowed_fields:
            if field in data:
                setattr(table, field, data[field])
        
        table.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return table
    
    @staticmethod
    def delete_table(table_id: str) -> bool:
        """
        删除表格（级联删除关联的字段、记录、视图等）
        
        Args:
            table_id: 表格 ID
            
        Returns:
            是否删除成功
        """
        table = Table.query.get(table_id)
        if not table:
            return False
        
        try:
            db.session.delete(table)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            from flask import current_app
            current_app.logger.error(f'[TableService] 删除表格失败：{table_id}, 错误：{str(e)}')
            return False
    
    @staticmethod
    def reorder_tables(base_id: str, table_orders: List[Dict[str, Any]]) -> bool:
        """
        批量重新排序表格
        
        Args:
            base_id: 基础数据 ID
            table_orders: 排序列表，每个元素包含 table_id 和 order
                例如：[{'table_id': 'xxx', 'order': 0}, {'table_id': 'yyy', 'order': 1}]
            
        Returns:
            是否排序成功
        """
        try:
            for item in table_orders:
                table_id = item.get('table_id')
                new_order = item.get('order')
                
                if table_id is None or new_order is None:
                    continue
                
                table = Table.query.filter_by(
                    id=table_id,
                    base_id=base_id
                ).first()
                
                if table:
                    table.order = new_order
            
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def duplicate_table(table_id: str, new_name: str = None) -> Optional[Table]:
        """
        复制表格（包括字段结构，不包括记录数据）
        
        Args:
            table_id: 源表格 ID
            new_name: 新表格名称（可选）
            
        Returns:
            新创建的表格对象
        """
        source_table = Table.query.get(table_id)
        if not source_table:
            return None
        
        # 获取当前最大 order
        max_order = db.session.query(func.max(Table.order)).filter_by(
            base_id=source_table.base_id
        ).scalar()
        new_order = (max_order or 0) + 1
        
        # 创建新表格
        new_table = Table(
            base_id=source_table.base_id,
            name=new_name or f"{source_table.name} 副本",
            description=source_table.description,
            order=new_order
        )
        
        db.session.add(new_table)
        db.session.flush()
        
        # 复制字段
        old_fields = Field.query.filter_by(table_id=table_id).order_by(Field.order.asc()).all()
        field_id_mapping = {}  # 旧字段ID -> 新字段ID
        
        for old_field in old_fields:
            new_field = Field(
                table_id=new_table.id,
                name=old_field.name,
                type=old_field.type,
                description=old_field.description,
                order=old_field.order,
                is_primary=old_field.is_primary,
                is_required=old_field.is_required,
                options=old_field.options,
                config=old_field.config
            )
            db.session.add(new_field)
            db.session.flush()
            
            field_id_mapping[str(old_field.id)] = str(new_field.id)
            
            # 设置主字段
            if old_field.is_primary:
                new_table.primary_field_id = new_field.id
        
        db.session.commit()
        
        return new_table
    
    @staticmethod
    def get_table_stats(table_id: str) -> Dict[str, Any]:
        """
        获取表格统计信息
        
        Args:
            table_id: 表格 ID
            
        Returns:
            统计信息字典
        """
        table = Table.query.get(table_id)
        if not table:
            return {}
        
        return {
            'record_count': table.get_record_count(),
            'field_count': table.get_field_count(),
            'view_count': table.views.count()
        }
    
    @staticmethod
    def check_permission(table_id: str, user_id: str, 
                         min_role: MemberRole = MemberRole.VIEWER) -> bool:
        """
        检查用户对表格的权限
        
        Args:
            table_id: 表格 ID
            user_id: 用户 ID
            min_role: 最低要求角色
            
        Returns:
            是否有权限
        """
        
        table = Table.query.get(table_id)
        if not table:
            return False
        
        # 通过基础数据检查权限
        return BaseService.check_permission(str(table.base_id), user_id, min_role)
