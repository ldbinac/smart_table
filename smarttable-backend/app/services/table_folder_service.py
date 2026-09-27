"""
数据表文件夹服务模块
处理 TableFolder 的 CRUD 与空文件夹删除校验
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from sqlalchemy import func

from app.extensions import db
from app.models.table_folder import TableFolder
from app.models.table import Table


class TableFolderService:
    """数据表文件夹服务类"""

    @staticmethod
    def get_folders_by_base(base_id: str) -> List[TableFolder]:
        """获取 Base 内所有文件夹（按 order 排序）"""
        return TableFolder.query.filter_by(base_id=base_id).order_by(TableFolder.order.asc()).all()

    @staticmethod
    def get_folder(folder_id: str) -> Optional[TableFolder]:
        """获取单个文件夹"""
        return TableFolder.query.get(folder_id)

    @staticmethod
    def create_folder(base_id: str, data: Dict[str, Any]) -> TableFolder:
        """
        创建文件夹

        Args:
            base_id: 所属 Base ID
            data: 创建数据（name）

        Returns:
            创建的文件夹对象
        """
        max_order = db.session.query(func.max(TableFolder.order)).filter_by(base_id=base_id).scalar()
        folder = TableFolder(
            base_id=base_id,
            name=(data.get('name') or '未命名文件夹').strip() or '未命名文件夹',
            order=(max_order or 0) + 1
        )
        db.session.add(folder)
        db.session.commit()
        return folder

    @staticmethod
    def update_folder(folder_id: str, data: Dict[str, Any]) -> Optional[TableFolder]:
        """
        更新文件夹（名称/排序）

        Args:
            folder_id: 文件夹 ID
            data: 更新数据（name/order）

        Returns:
            更新后的文件夹对象，不存在返回 None
        """
        folder = TableFolder.query.get(folder_id)
        if not folder:
            return None

        allowed_fields = ['name', 'order']
        for field in allowed_fields:
            if field in data:
                setattr(folder, field, data[field])

        folder.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return folder

    @staticmethod
    def delete_folder(folder_id: str) -> tuple[bool, str]:
        """
        删除文件夹（仅允许删除空文件夹）

        Args:
            folder_id: 文件夹 ID

        Returns:
            (是否成功, 错误码)：成功时错误码为空；文件夹非空返回 'folder_not_empty'；不存在返回 'folder_not_found'
        """
        folder = TableFolder.query.get(folder_id)
        if not folder:
            return False, 'folder_not_found'

        table_count = Table.query.filter_by(folder_id=folder_id).count()
        if table_count > 0:
            return False, 'folder_not_empty'

        db.session.delete(folder)
        db.session.commit()
        return True, ''

    @staticmethod
    def count_tables_in_folder(folder_id: str) -> int:
        """统计文件夹内的表数量"""
        return Table.query.filter_by(folder_id=folder_id).count()
