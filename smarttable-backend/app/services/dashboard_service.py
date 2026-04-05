"""
仪表盘服务模块
处理 Dashboard 和 Widget 的 CRUD 操作以及布局管理
"""
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

from app.extensions import db
from app.models.dashboard import Dashboard, DashboardWidget


class DashboardService:
    """仪表盘服务类"""
    
    @staticmethod
    def get_all_dashboards(base_id: str) -> List[Dashboard]:
        """
        获取基础数据下的所有仪表盘
        
        参数:
            base_id: 基础数据 ID
            
        返回:
            仪表盘列表
        """
        return Dashboard.query.filter_by(base_id=base_id).order_by(
            Dashboard.is_default.desc(),
            Dashboard.created_at.desc()
        ).all()
    
    @staticmethod
    def get_dashboard(dashboard_id: str) -> Optional[Dashboard]:
        """
        根据 ID 获取仪表盘
        
        参数:
            dashboard_id: 仪表盘 ID
            
        返回:
            仪表盘对象或 None
        """
        return Dashboard.query.get(dashboard_id)
    
    @staticmethod
    def create_dashboard(base_id: str, data: Dict[str, Any], user_id: str) -> Dashboard:
        """
        创建新仪表盘
        
        参数:
            base_id: 基础数据 ID
            data: 仪表盘数据，包含 name, description, layout, is_default 等
            user_id: 创建用户 ID
            
        返回:
            创建的仪表盘对象
        """
        # 如果设置为默认仪表盘，取消其他仪表盘的默认状态
        if data.get('is_default'):
            Dashboard.query.filter_by(base_id=base_id, is_default=True).update(
                {'is_default': False}
            )
        
        dashboard = Dashboard(
            base_id=base_id,
            user_id=user_id,
            name=data.get('name', '未命名仪表盘'),
            description=data.get('description'),
            is_default=data.get('is_default', False),
            layout=data.get('layout', {}),
            widgets=data.get('widgets', [])
        )
        
        db.session.add(dashboard)
        db.session.commit()
        
        return dashboard
    
    @staticmethod
    def update_dashboard(dashboard_id: str, data: Dict[str, Any]) -> Optional[Dashboard]:
        """
        更新仪表盘
        
        参数:
            dashboard_id: 仪表盘 ID
            data: 更新数据，包含 name, description, layout, is_default, widgets 等
            
        返回:
            更新后的仪表盘对象，如果不存在返回 None
        """
        dashboard = Dashboard.query.get(dashboard_id)
        if not dashboard:
            return None
        
        # 如果设置为默认仪表盘，取消其他仪表盘的默认状态
        if data.get('is_default') and not dashboard.is_default:
            Dashboard.query.filter_by(
                base_id=dashboard.base_id, 
                is_default=True
            ).update({'is_default': False})
        
        # 允许更新的字段
        allowed_fields = ['name', 'description', 'layout', 'is_default', 'widgets']
        
        # 记录更新的字段
        update_log = []
        for field in allowed_fields:
            if field in data:
                setattr(dashboard, field, data[field])
                update_log.append(field)
        
        print(f"[DashboardService] Updating dashboard {dashboard_id} with fields: {update_log}")
        if 'widgets' in data:
            print(f"[DashboardService] Widgets data: {len(data['widgets'])} widgets")
            if data['widgets']:
                print(f"[DashboardService] First widget: {data['widgets'][0] if data['widgets'] else 'None'}")
        
        dashboard.updated_at = datetime.utcnow()
        db.session.commit()
        
        return dashboard
    
    @staticmethod
    def delete_dashboard(dashboard_id: str) -> bool:
        """
        删除仪表盘（级联删除所有组件）
        
        参数:
            dashboard_id: 仪表盘 ID
            
        返回:
            是否删除成功
        """
        dashboard = Dashboard.query.get(dashboard_id)
        if not dashboard:
            return False
        
        try:
            db.session.delete(dashboard)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
    
    # ==================== Widget 管理 ====================
    
    @staticmethod
    def add_widget(dashboard_id: str, data: Dict[str, Any]) -> Optional[DashboardWidget]:
        """
        添加组件到仪表盘
        
        参数:
            dashboard_id: 仪表盘 ID
            data: 组件数据，包含 type, title, config, data_source, position 等
            
        返回:
            创建的组件对象，仪表盘不存在返回 None
        """
        dashboard = Dashboard.query.get(dashboard_id)
        if not dashboard:
            return None
        
        # 获取当前最大排序值
        max_order = db.session.query(db.func.max(DashboardWidget.order)).filter_by(
            dashboard_id=dashboard_id
        ).scalar() or 0
        
        widget = DashboardWidget(
            dashboard_id=dashboard_id,
            type=data.get('type', 'text_block'),
            title=data.get('title', '未命名组件'),
            config=data.get('config', {}),
            data_source=data.get('data_source', {}),
            position=data.get('position', {}),
            order=data.get('order', max_order + 1)
        )
        
        db.session.add(widget)
        db.session.commit()
        
        return widget
    
    @staticmethod
    def update_widget(widget_id: str, data: Dict[str, Any]) -> Optional[DashboardWidget]:
        """
        更新组件
        
        参数:
            widget_id: 组件 ID
            data: 更新数据，包含 title, config, data_source, position, order 等
            
        返回:
            更新后的组件对象，不存在返回 None
        """
        widget = DashboardWidget.query.get(widget_id)
        if not widget:
            return None
        
        # 允许更新的字段
        allowed_fields = ['title', 'config', 'data_source', 'position', 'order']
        
        for field in allowed_fields:
            if field in data:
                setattr(widget, field, data[field])
        
        widget.updated_at = datetime.utcnow()
        db.session.commit()
        
        return widget
    
    @staticmethod
    def delete_widget(widget_id: str) -> bool:
        """
        删除组件
        
        参数:
            widget_id: 组件 ID
            
        返回:
            是否删除成功
        """
        widget = DashboardWidget.query.get(widget_id)
        if not widget:
            return False
        
        try:
            db.session.delete(widget)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def get_widget(widget_id: str) -> Optional[DashboardWidget]:
        """
        根据 ID 获取组件
        
        参数:
            widget_id: 组件 ID
            
        返回:
            组件对象或 None
        """
        return DashboardWidget.query.get(widget_id)
    
    @staticmethod
    def batch_update_widgets(dashboard_id: str, widgets_data: List[Dict[str, Any]]) -> List[DashboardWidget]:
        """
        批量更新仪表盘组件
        
        参数:
            dashboard_id: 仪表盘 ID
            widgets_data: 组件数据列表，每个包含 id（可选，无则新建）和其他字段
            
        返回:
            更新后的组件列表
        """
        dashboard = Dashboard.query.get(dashboard_id)
        if not dashboard:
            return []
        
        updated_widgets = []
        
        for index, widget_data in enumerate(widgets_data):
            widget_id = widget_data.get('id')
            
            # 设置排序顺序
            widget_data['order'] = index + 1
            
            if widget_id:
                # 更新现有组件
                widget = DashboardWidget.query.get(widget_id)
                if widget and str(widget.dashboard_id) == dashboard_id:
                    allowed_fields = ['title', 'config', 'data_source', 'position', 'order']
                    for field in allowed_fields:
                        if field in widget_data:
                            setattr(widget, field, widget_data[field])
                    widget.updated_at = datetime.utcnow()
                    updated_widgets.append(widget)
            else:
                # 创建新组件
                widget = DashboardWidget(
                    dashboard_id=dashboard_id,
                    type=widget_data.get('type', 'text_block'),
                    title=widget_data.get('title', '未命名组件'),
                    config=widget_data.get('config', {}),
                    data_source=widget_data.get('data_source', {}),
                    position=widget_data.get('position', {}),
                    order=widget_data.get('order', index + 1)
                )
                db.session.add(widget)
                updated_widgets.append(widget)
        
        db.session.commit()
        return updated_widgets
    
    # ==================== 布局管理 ====================
    
    @staticmethod
    def update_layout(dashboard_id: str, layout_data: Dict[str, Any]) -> Optional[Dashboard]:
        """
        更新仪表盘布局
        
        参数:
            dashboard_id: 仪表盘 ID
            layout_data: 布局配置，包含 type, config, widgets 等
                - type: 'grid' | 'free'
                - config: 布局配置（如网格列数、间距等）
                - widgets: 组件位置信息列表
            
        返回:
            更新后的仪表盘对象，不存在返回 None
        """
        dashboard = Dashboard.query.get(dashboard_id)
        if not dashboard:
            return None
        
        # 更新布局配置
        current_layout = dashboard.layout or {}
        
        if 'type' in layout_data:
            current_layout['type'] = layout_data['type']
        
        if 'config' in layout_data:
            current_layout['config'] = layout_data['config']
        
        if 'widgets' in layout_data:
            # 更新组件位置信息
            current_layout['widgets'] = layout_data['widgets']
            
            # 同时更新数据库中的组件位置
            for widget_position in layout_data['widgets']:
                widget_id = widget_position.get('id')
                if widget_id:
                    widget = DashboardWidget.query.get(widget_id)
                    if widget and str(widget.dashboard_id) == dashboard_id:
                        widget.position = {
                            'x': widget_position.get('x', 0),
                            'y': widget_position.get('y', 0),
                            'w': widget_position.get('w', 4),
                            'h': widget_position.get('h', 4),
                            'minW': widget_position.get('minW'),
                            'minH': widget_position.get('minH'),
                            'maxW': widget_position.get('maxW'),
                            'maxH': widget_position.get('maxH')
                        }
                        widget.updated_at = datetime.utcnow()
        
        dashboard.layout = current_layout
        dashboard.updated_at = datetime.utcnow()
        db.session.commit()
        
        return dashboard
    
    @staticmethod
    def set_default_dashboard(dashboard_id: str) -> Optional[Dashboard]:
        """
        设置默认仪表盘
        
        参数:
            dashboard_id: 仪表盘 ID
            
        返回:
            更新后的仪表盘对象，不存在返回 None
        """
        dashboard = Dashboard.query.get(dashboard_id)
        if not dashboard:
            return None
        
        # 取消同基础数据下其他仪表盘的默认状态
        Dashboard.query.filter_by(
            base_id=dashboard.base_id,
            is_default=True
        ).update({'is_default': False})
        
        dashboard.is_default = True
        dashboard.updated_at = datetime.utcnow()
        db.session.commit()
        
        return dashboard
    
    @staticmethod
    def duplicate_dashboard(dashboard_id: str, user_id: str, new_name: str = None) -> Optional[Dashboard]:
        """
        复制仪表盘
        
        参数:
            dashboard_id: 源仪表盘 ID
            user_id: 新仪表盘创建用户 ID
            new_name: 新仪表盘名称，默认添加"副本"后缀
            
        返回:
            新创建的仪表盘对象，源仪表盘不存在返回 None
        """
        source_dashboard = Dashboard.query.get(dashboard_id)
        if not source_dashboard:
            return None
        
        # 复制 widgets JSON 数据
        widgets_copy = source_dashboard.widgets.copy() if source_dashboard.widgets else []
        
        # 创建新仪表盘
        new_dashboard = Dashboard(
            base_id=source_dashboard.base_id,
            user_id=user_id,
            name=new_name or f"{source_dashboard.name} 副本",
            description=source_dashboard.description,
            is_default=False,
            layout=source_dashboard.layout,
            widgets=widgets_copy
        )
        
        db.session.add(new_dashboard)
        db.session.commit()
        
        return new_dashboard
