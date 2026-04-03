"""
视图服务模块
"""
from typing import List, Optional, Dict, Any
import uuid

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
                   sorts: List[Dict] = None) -> View:
        """
        创建视图
        
        Args:
            table_id: 表格 ID
            name: 视图名称
            view_type: 视图类型
            config: 视图配置
            filters: 筛选条件
            sorts: 排序规则
            
        Returns:
            创建的视图对象
        """
        # 获取当前最大排序值
        max_order = db.session.query(db.func.max(View.order)).filter_by(table_id=table_id).scalar() or 0
        
        view = View(
            table_id=table_id,
            name=name,
            type=view_type,
            order=max_order + 1,
            config=config or {},
            filters=filters or [],
            sorts=sorts or []
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
        return View.query.get(view_id)
    
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
        allowed_fields = ['name', 'config', 'filters', 'sorts', 
                         'hidden_fields', 'field_widths', 'order', 'description']
        
        for key in allowed_fields:
            if key in kwargs:
                setattr(view, key, kwargs[key])
        
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
            sorts=view.sorts,
            hidden_fields=view.hidden_fields,
            field_widths=view.field_widths,
            order=view.order + 1
        )
        
        db.session.add(new_view)
        db.session.commit()
        
        return new_view
