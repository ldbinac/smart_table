"""
记录服务模块
"""
from typing import List, Optional, Dict, Any
import uuid

from app.extensions import db
from app.models.record import Record


class RecordService:
    """记录服务类"""
    
    @staticmethod
    def get_table_records(table_id: str, page: int = 1, 
                         per_page: int = 20) -> tuple:
        """
        获取表格下的记录列表
        
        Args:
            table_id: 表格 ID
            page: 页码
            per_page: 每页数量
            
        Returns:
            (记录列表, 总数量)
        """
        query = Record.query.filter_by(table_id=table_id)
        total = query.count()
        records = query.order_by(Record.created_at.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        return records, total
    
    @staticmethod
    def create_record(table_id: str, values: Dict[str, Any],
                     created_by: str = None) -> Record:
        """
        创建记录
        
        Args:
            table_id: 表格 ID
            values: 字段值字典
            created_by: 创建者 ID
            
        Returns:
            创建的记录对象
        """
        record = Record(
            table_id=table_id,
            values=values or {},
            created_by=created_by,
            updated_by=created_by
        )
        
        db.session.add(record)
        db.session.commit()
        
        return record
    
    @staticmethod
    def get_record_by_id(record_id: str) -> Optional[Record]:
        """
        根据 ID 获取记录
        
        Args:
            record_id: 记录 ID
            
        Returns:
            记录对象或 None
        """
        return Record.query.get(record_id)
    
    @staticmethod
    def update_record(record: Record, values: Dict[str, Any] = None,
                     updated_by: str = None) -> Record:
        """
        更新记录
        
        Args:
            record: 记录对象
            values: 更新的字段值
            updated_by: 更新者 ID
            
        Returns:
            更新后的记录对象
        """
        if values:
            # 合并新值到现有值
            # 创建新的字典对象，确保 SQLAlchemy 检测到变化
            current_values = dict(record.values) if record.values else {}
            current_values.update(values)
            # 直接赋值新字典对象，SQLAlchemy 会检测到变化
            record.values = current_values
        
        if updated_by:
            record.updated_by = updated_by
        
        # 刷新对象以确保获取最新的数据库状态
        db.session.flush()
        db.session.commit()
        return record
    
    @staticmethod
    def delete_record(record: Record) -> bool:
        """
        删除记录
        
        Args:
            record: 记录对象
            
        Returns:
            是否成功
        """
        try:
            db.session.delete(record)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def search_records(table_id: str, query: str, 
                      field_ids: List[str] = None) -> List[Record]:
        """
        搜索记录
        
        Args:
            table_id: 表格 ID
            query: 搜索关键词
            field_ids: 要搜索的字段 ID 列表
            
        Returns:
            记录列表
        """
        # 简化实现，实际应该使用全文搜索
        records = Record.query.filter_by(table_id=table_id).all()
        
        results = []
        query_lower = query.lower()
        
        for record in records:
            values = record.values or {}
            for field_id, value in values.items():
                if field_ids and field_id not in field_ids:
                    continue
                if value and query_lower in str(value).lower():
                    results.append(record)
                    break
        
        return results
