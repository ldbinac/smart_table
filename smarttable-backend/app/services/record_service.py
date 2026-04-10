"""
记录服务模块
"""
from typing import List, Optional, Dict, Any
import uuid

from app.extensions import db
from app.models.record import Record
from app.models.field import Field
from app.models.record_history import RecordHistory, HistoryAction
from app.services.field_service import FieldService


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
        
        创建记录时会自动应用字段的默认值（如果字段有配置默认值且提供的 values 中没有该字段）
        
        Args:
            table_id: 表格 ID
            values: 字段值字典
            created_by: 创建者 ID
            
        Returns:
            创建的记录对象
        """
        from datetime import datetime
        
        # 获取所有字段并应用默认值
        fields = FieldService.get_all_fields(table_id)
        
        # 从提供的 values 开始
        final_values = dict(values) if values else {}
        
        # 对每个有默认值的字段，如果没有提供值，则应用默认值
        for field in fields:
            field_id = str(field.id)
            if field_id not in final_values:
                default_value = field.get_default_value()
                # 只应用非 None 的默认值
                if default_value is not None:
                    # 特殊处理动态日期默认值 'now'
                    if default_value == 'now':
                        if field.type == 'date_time':
                            final_values[field_id] = datetime.utcnow().isoformat()
                        else:
                            # 仅日期格式
                            final_values[field_id] = datetime.utcnow().strftime('%Y-%m-%d')
                    else:
                        final_values[field_id] = default_value
        
        record = Record(
            table_id=table_id,
            values=final_values,
            created_by=created_by,
            updated_by=created_by
        )

        db.session.add(record)
        db.session.flush()  # 获取 record.id

        # 创建变更历史记录
        # 确保 ID 是 UUID 对象
        record_id = record.id if isinstance(record.id, uuid.UUID) else uuid.UUID(str(record.id))
        tbl_id = uuid.UUID(table_id) if isinstance(table_id, str) else table_id
        # created_by 可能是 UUID 对象或字符串
        if created_by:
            changer_id = created_by if isinstance(created_by, uuid.UUID) else uuid.UUID(str(created_by))
        else:
            changer_id = None
        
        history = RecordHistory.create_history(
            record_id=record_id,
            table_id=tbl_id,
            action=HistoryAction.CREATE,
            changed_by=changer_id,
            changes=None,  # 创建操作没有变更对比
            snapshot=final_values  # 保存创建时的数据快照
        )
        db.session.add(history)

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
        # 保存旧值用于历史记录
        old_values = dict(record.values) if record.values else {}
        changes = []

        if values:
            # 计算变更的字段
            for field_id, new_value in values.items():
                old_value = old_values.get(field_id)
                # 只有当值真正发生变化时才记录
                if old_value != new_value:
                    changes.append({
                        'field_id': field_id,
                        'old_value': old_value,
                        'new_value': new_value
                    })

            # 合并新值到现有值
            # 创建新的字典对象，确保 SQLAlchemy 检测到变化
            current_values = dict(old_values)
            current_values.update(values)
            # 直接赋值新字典对象，SQLAlchemy 会检测到变化
            record.values = current_values

        if updated_by:
            record.updated_by = updated_by

        # 如果有变更，创建历史记录
        if changes:
            # 确保 ID 是 UUID 对象
            record_id = record.id if isinstance(record.id, uuid.UUID) else uuid.UUID(str(record.id))
            table_id = record.table_id if isinstance(record.table_id, uuid.UUID) else uuid.UUID(str(record.table_id))
            # changed_by 可能是 UUID 对象或字符串
            if updated_by:
                changed_by = updated_by if isinstance(updated_by, uuid.UUID) else uuid.UUID(str(updated_by))
            else:
                changed_by = None
            
            history = RecordHistory.create_history(
                record_id=record_id,
                table_id=table_id,
                action=HistoryAction.UPDATE,
                changed_by=changed_by,
                changes=changes,
                snapshot=dict(record.values)  # 保存更新后的快照
            )
            db.session.add(history)

        # 刷新对象以确保获取最新的数据库状态
        db.session.flush()
        db.session.commit()
        return record
    
    @staticmethod
    def delete_record(record: Record, deleted_by: str = None) -> bool:
        """
        删除记录

        Args:
            record: 记录对象
            deleted_by: 删除者 ID

        Returns:
            是否成功
        """
        try:
            # 保存删除前的数据快照
            snapshot = dict(record.values) if record.values else {}

            # 创建删除历史记录
            # 确保 ID 是 UUID 对象
            record_id = record.id if isinstance(record.id, uuid.UUID) else uuid.UUID(str(record.id))
            table_id = record.table_id if isinstance(record.table_id, uuid.UUID) else uuid.UUID(str(record.table_id))
            # deleted_by 可能是 UUID 对象或字符串
            if deleted_by:
                changer_id = deleted_by if isinstance(deleted_by, uuid.UUID) else uuid.UUID(str(deleted_by))
            else:
                changer_id = None
            
            history = RecordHistory.create_history(
                record_id=record_id,
                table_id=table_id,
                action=HistoryAction.DELETE,
                changed_by=changer_id,
                changes=None,  # 删除操作没有字段变更对比
                snapshot=snapshot  # 保存删除前的完整数据
            )
            db.session.add(history)

            # 清理关联数据
            from app.services.link_service import LinkService
            LinkService.delete_record_links(str(record_id))

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
