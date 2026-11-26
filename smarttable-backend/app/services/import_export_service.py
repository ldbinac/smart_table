# Auto-split skeleton

"""
导入导出服务模块
处理 Excel、CSV、JSON 格式的数据导入导出
支持预览导入数据和批量处理
"""
import io
import json
import uuid
import re
from typing import List, Optional, Dict, Any, Tuple, BinaryIO
from datetime import datetime, timezone
from enum import Enum as PyEnum

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    pd = None
    HAS_PANDAS = False

from app.i18n import translate
from app.extensions import db
from app.models.table import Table
from app.models.field import Field, FieldType
from app.models.record import Record


class ImportStatus(PyEnum):
    """导入任务状态枚举"""
    PENDING = 'pending'         # 待处理
    PROCESSING = 'processing'   # 处理中
    COMPLETED = 'completed'     # 完成
    FAILED = 'failed'           # 失败
    CANCELLED = 'cancelled'     # 已取消


class ExportFormat(PyEnum):
    """导出格式枚举"""
    EXCEL = 'excel'
    CSV = 'csv'
    JSON = 'json'

from .import_export_service_group01 import ImportExportServiceGroup01Mixin
from .import_export_service_group02 import ImportExportServiceGroup02Mixin

class ImportExportService(ImportExportServiceGroup01Mixin, ImportExportServiceGroup02Mixin):
    """ImportExportService — 主类，方法在 mixin 中"""
    
    """导入导出服务类"""
    
    _tasks: Dict[str, Dict[str, Any]] = {}
    
    MAX_IMPORT_ROWS = 10000
    
    BATCH_SIZE = 500

# === 反向注入：把主类注入到所有 group mixin 模块 ===
from app.services._inject import inject_main_class
inject_main_class(ImportStatus, 'import_export_service_group01', 'import_export_service_group02')
