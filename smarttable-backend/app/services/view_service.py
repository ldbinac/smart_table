"""
视图服务模块
"""
from typing import List, Optional, Dict, Any
import uuid

from sqlalchemy.orm.attributes import flag_modified

from app.extensions import db
from app.models.view import View, ViewType


class ViewService:
    """视图服务类"""
    
    @staticmethod
    def get_table_views(table_id: str) -> List[View]:
        """
        获取表格下的所有视图
        
        Args:
            table_id: 表格 ID
            
        Returns:
            视图列表
        """
        return View.query.filter_by(table_id=table_id).order_by(View.order).all()
    
    @staticmethod
    def create_view(table_id: str, name: str, view_type: str = 'grid',
                   config: Dict[str, Any] = None, 
                   filters: List[Dict] = None,
                   sorts: List[Dict] = None,
                   group_bys: List[str] = None) -> View:
        """
        创建视图
        
        Args:
            table_id: 表格 ID
            name: 视图名称
            view_type: 视图类型
            config: 视图配置
            filters: 筛选条件
            sorts: 排序规则
            group_bys: 分组字段列表
            
        Returns:
            创建的视图对象
        """
        # 获取当前最大排序值
        max_order = db.session.query(db.func.max(View.order)).filter_by(table_id=table_id).scalar() or 0
        
        # 将字符串类型转换为 ViewType 枚举的 value 值（字符串）
        try:
            view_type_value = ViewType(view_type).value
        except ValueError:
            # 如果是无效的类型，使用默认的 table
            view_type_value = ViewType.TABLE.value
        
        # 构建 group_config
        group_config = {}
        if group_bys:
            group_config['group_bys'] = group_bys
        
        view = View(
            table_id=table_id,
            name=name,
            type=view_type_value,  # 使用字符串值而不是枚举对象
            order=max_order + 1,
            description='',
            filters=filters or [],
            sort_config=sorts or [],
            group_config=group_config or {},
            field_visibility={}
        )
        
        db.session.add(view)
        db.session.commit()
        
        return view
    
    @staticmethod
    def get_view_by_id(view_id: str) -> Optional[View]:
        """
        根据 ID 获取视图
        
        Args:
            view_id: 视图 ID
            
        Returns:
            视图对象或 None
        """
        # 使用 filter_by 而不是 get，避免 UUID 转换问题
        return View.query.filter_by(id=view_id).first()
    
    @staticmethod
    def update_view(view: View, **kwargs) -> View:
        """
        更新视图
        
        Args:
            view: 视图对象
            **kwargs: 要更新的字段
            
        Returns:
            更新后的视图对象
        """
        # 直接映射的字段（字段名相同）
        direct_fields = ['name', 'config', 'filters', 
                        'hidden_fields', 'field_widths', 'order', 'description']
        
        for key in direct_fields:
            if key in kwargs:
                setattr(view, key, kwargs[key])
        
        # 处理排序配置 - 前端使用 sorts，数据库使用 sort_config
        if 'sorts' in kwargs:
            view.sort_config = kwargs['sorts']
            flag_modified(view, 'sort_config')
        
        # 处理分组配置 - 确保保留所有分组层级
        if 'group_bys' in kwargs:
            # 确保 group_config 是字典
            if not view.group_config or not isinstance(view.group_config, dict):
                view.group_config = {}
            # 更新 group_bys，保留其他配置
            view.group_config['group_bys'] = kwargs['group_bys']
            # 标记 group_config 为已修改（确保 SQLAlchemy 检测到变更）
            flag_modified(view, 'group_config')
        
        if 'group_config' in kwargs:
            # 如果直接提供了 group_config，合并到现有配置
            if not view.group_config or not isinstance(view.group_config, dict):
                view.group_config = {}
            # 合并配置，新配置覆盖旧配置
            view.group_config.update(kwargs['group_config'])
            # 标记 group_config 为已修改
            flag_modified(view, 'group_config')
        
        db.session.commit()
        return view
    
    @staticmethod
    def delete_view(view: View) -> bool:
        """
        删除视图
        
        Args:
            view: 视图对象
            
        Returns:
            是否成功
        """
        # 检查是否为默认视图
        if view.is_default:
            return False
        
        try:
            db.session.delete(view)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def duplicate_view(view: View, new_name: str = None) -> View:
        """
        复制视图
        
        Args:
            view: 原视图对象
            new_name: 新视图名称
            
        Returns:
            新创建的视图对象
        """
        name = new_name or f'{view.name} (复制)'
        
        new_view = View(
            table_id=view.table_id,
            name=name,
            type=view.type,
            description=view.description,
            config=view.config,
            filters=view.filters,
            sort_config=view.sort_config,  # 使用 sort_config 而不是 sorts
            group_config=view.group_config,
            field_visibility=view.field_visibility,
            hidden_fields=view.hidden_fields,
            field_widths=view.field_widths,
            order=view.order + 1
        )
        
        db.session.add(new_view)
        db.session.commit()
        
        return new_view
