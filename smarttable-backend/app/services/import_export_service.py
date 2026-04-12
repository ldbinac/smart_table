"""
导入导出服务模块
处理 Excel、CSV、JSON 格式的数据导入导出
支持预览导入数据和批量处理
"""
import io
import json
import uuid
from typing import List, Optional, Dict, Any, Tuple, BinaryIO
from datetime import datetime
from enum import Enum as PyEnum

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    pd = None
    HAS_PANDAS = False

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


class ImportExportService:
    """导入导出服务类"""
    
    # 内存存储任务状态（生产环境建议使用 Redis 或数据库）
    _tasks: Dict[str, Dict[str, Any]] = {}
    
    # 最大导入行数
    MAX_IMPORT_ROWS = 10000
    
    # 批量插入大小
    BATCH_SIZE = 500
    
    @classmethod
    def _generate_task_id(cls) -> str:
        """生成任务 ID"""
        return f"task_{uuid.uuid4().hex[:16]}"
    
    @classmethod
    def _create_task(cls, task_type: str, table_id: str, user_id: str) -> str:
        """
        创建任务记录
        
        参数:
            task_type: 任务类型（import/export）
            table_id: 表格 ID
            user_id: 用户 ID
            
        返回:
            任务 ID
        """
        task_id = cls._generate_task_id()
        cls._tasks[task_id] = {
            'id': task_id,
            'type': task_type,
            'table_id': table_id,
            'user_id': user_id,
            'status': ImportStatus.PENDING.value,
            'progress': 0,
            'total': 0,
            'processed': 0,
            'success_count': 0,
            'error_count': 0,
            'errors': [],
            'result': None,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'completed_at': None
        }
        return task_id
    
    @classmethod
    def _update_task(cls, task_id: str, **kwargs):
        """更新任务状态"""
        if task_id in cls._tasks:
            cls._tasks[task_id].update(kwargs)
            cls._tasks[task_id]['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    @classmethod
    def get_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        参数:
            task_id: 任务 ID
            
        返回:
            任务信息或 None
        """
        return cls._tasks.get(task_id)
    
    # ==================== Excel 导入 ====================
    
    @classmethod
    def import_from_excel(cls, file: BinaryIO, table_id: str, 
                         field_mapping: Dict[str, str],
                         user_id: str,
                         preview_only: bool = False) -> Dict[str, Any]:
        """
        从 Excel 文件导入数据
        
        参数:
            file: Excel 文件对象
            table_id: 目标表格 ID
            field_mapping: 字段映射 {excel列名: field_id}
            user_id: 操作用户 ID
            preview_only: 是否仅预览（不实际导入）
            
        返回:
            导入结果或预览数据
        """
        try:
            if not HAS_PANDAS:
                raise ImportError('请安装 pandas: pip install pandas openpyxl')
        except ImportError:
            raise ImportError('请安装 pandas: pip install pandas openpyxl')
        
        # 读取 Excel 文件
        try:
            df = pd.read_excel(file)
        except Exception as e:
            raise ValueError(f'无法读取 Excel 文件: {str(e)}')
        
        # 检查行数限制
        if len(df) > cls.MAX_IMPORT_ROWS:
            raise ValueError(f'导入数据行数超过限制（最大 {cls.MAX_IMPORT_ROWS} 行）')
        
        # 获取表格信息
        table = Table.query.get(table_id)
        if not table:
            raise ValueError('表格不存在')
        
        # 获取字段信息
        fields = {str(f.id): f for f in table.fields.all()}
        
        # 转换数据
        records_data = []
        errors = []
        
        for idx, row in df.iterrows():
            row_num = idx + 2  # Excel 行号（从 2 开始，1 是表头）
            record_values = {}
            
            for excel_col, field_id in field_mapping.items():
                if excel_col not in df.columns:
                    continue
                
                if field_id not in fields:
                    continue
                
                field = fields[field_id]
                value = row.get(excel_col)
                
                # 数据类型转换
                converted_value = cls._convert_value(value, field)
                
                # 验证字段值
                is_valid, error_msg = field.validate_value(converted_value)
                if not is_valid:
                    errors.append({
                        'row': row_num,
                        'column': excel_col,
                        'field': field.name,
                        'error': error_msg
                    })
                else:
                    record_values[field_id] = converted_value
            
            records_data.append({
                'row': row_num,
                'values': record_values,
                'source_data': row.to_dict()
            })
        
        # 仅预览模式
        if preview_only:
            return {
                'preview': True,
                'total_rows': len(df),
                'valid_rows': len(records_data) - len(errors),
                'error_rows': len(errors),
                'sample_data': records_data[:10],  # 返回前 10 条预览
                'errors': errors[:10]  # 返回前 10 条错误
            }
        
        # 如果有错误，不执行导入
        if errors:
            return {
                'success': False,
                'message': '数据验证失败',
                'total_rows': len(df),
                'error_rows': len(errors),
                'errors': errors
            }
        
        # 创建任务
        task_id = cls._create_task('import', table_id, user_id)
        cls._update_task(task_id, status=ImportStatus.PROCESSING.value, total=len(records_data))
        
        # 执行导入
        success_count = 0
        error_count = 0
        imported_records = []
        
        try:
            for i, record_data in enumerate(records_data):
                try:
                    record = Record(
                        table_id=table_id,
                        values=record_data['values'],
                        created_by=user_id
                    )
                    db.session.add(record)
                    
                    # 批量提交
                    if (i + 1) % cls.BATCH_SIZE == 0:
                        db.session.commit()
                        imported_records.extend([r.id for r in db.session.new if isinstance(r, Record)])
                    
                    success_count += 1
                    cls._update_task(task_id, processed=i+1, success_count=success_count)
                    
                except Exception as e:
                    error_count += 1
                    cls._update_task(task_id, error_count=error_count)
            
            # 提交剩余记录
            db.session.commit()
            
            cls._update_task(
                task_id,
                status=ImportStatus.COMPLETED.value,
                progress=100,
                completed_at=datetime.now(timezone.utc).isoformat(),
                result={
                    'imported_count': success_count,
                    'error_count': error_count
                }
            )
            
            return {
                'success': True,
                'task_id': task_id,
                'imported_count': success_count,
                'error_count': error_count
            }
            
        except Exception as e:
            db.session.rollback()
            cls._update_task(
                task_id,
                status=ImportStatus.FAILED.value,
                errors=[str(e)]
            )
            raise
    
    # ==================== CSV 导入 ====================
    
    @classmethod
    def import_from_csv(cls, file: BinaryIO, table_id: str,
                       field_mapping: Dict[str, str],
                       user_id: str,
                       preview_only: bool = False,
                       encoding: str = 'utf-8',
                       delimiter: str = ',') -> Dict[str, Any]:
        """
        从 CSV 文件导入数据
        
        参数:
            file: CSV 文件对象
            table_id: 目标表格 ID
            field_mapping: 字段映射 {csv列名: field_id}
            user_id: 操作用户 ID
            preview_only: 是否仅预览
            encoding: 文件编码
            delimiter: 分隔符
            
        返回:
            导入结果或预览数据
        """
        try:
            if not HAS_PANDAS:
                raise ImportError('请安装 pandas: pip install pandas')
        except ImportError:
            raise ImportError('请安装 pandas: pip install pandas')
        
        # 读取 CSV 文件
        try:
            df = pd.read_csv(file, encoding=encoding, delimiter=delimiter)
        except UnicodeDecodeError:
            # 尝试其他编码
            file.seek(0)
            df = pd.read_csv(file, encoding='gbk', delimiter=delimiter)
        except Exception as e:
            raise ValueError(f'无法读取 CSV 文件: {str(e)}')
        
        # 复用 Excel 导入逻辑
        return cls.import_from_excel(
            io.BytesIO(df.to_excel(index=False)),
            table_id,
            field_mapping,
            user_id,
            preview_only
        )
    
    # ==================== JSON 导入 ====================
    
    @classmethod
    def import_from_json(cls, data: List[Dict[str, Any]], table_id: str,
                        field_mapping: Optional[Dict[str, str]],
                        user_id: str,
                        preview_only: bool = False) -> Dict[str, Any]:
        """
        从 JSON 数据导入
        
        参数:
            data: JSON 数据列表
            table_id: 目标表格 ID
            field_mapping: 字段映射 {json字段名: field_id}，为 None 时使用同名字段
            user_id: 操作用户 ID
            preview_only: 是否仅预览
            
        返回:
            导入结果或预览数据
        """
        # 获取表格信息
        table = Table.query.get(table_id)
        if not table:
            raise ValueError('表格不存在')
        
        # 获取字段信息
        fields = {str(f.id): f for f in table.fields.all()}
        field_name_map = {f.name: f for f in fields.values()}
        
        # 如果没有提供映射，使用同名字段匹配
        if field_mapping is None:
            field_mapping = {}
            for item in data[:1]:  # 使用第一条数据推断
                for key in item.keys():
                    if key in field_name_map:
                        field_mapping[key] = str(field_name_map[key].id)
        
        # 检查行数限制
        if len(data) > cls.MAX_IMPORT_ROWS:
            raise ValueError(f'导入数据行数超过限制（最大 {cls.MAX_IMPORT_ROWS} 行）')
        
        # 转换数据
        records_data = []
        errors = []
        
        for idx, item in enumerate(data):
            row_num = idx + 1
            record_values = {}
            
            for json_field, field_id in field_mapping.items():
                if json_field not in item:
                    continue
                
                if field_id not in fields:
                    continue
                
                field = fields[field_id]
                value = item.get(json_field)
                
                # 数据类型转换
                converted_value = cls._convert_value(value, field)
                
                # 验证字段值
                is_valid, error_msg = field.validate_value(converted_value)
                if not is_valid:
                    errors.append({
                        'row': row_num,
                        'field': json_field,
                        'error': error_msg
                    })
                else:
                    record_values[field_id] = converted_value
            
            records_data.append({
                'row': row_num,
                'values': record_values,
                'source_data': item
            })
        
        # 仅预览模式
        if preview_only:
            return {
                'preview': True,
                'total_rows': len(data),
                'valid_rows': len(records_data) - len(errors),
                'error_rows': len(errors),
                'sample_data': records_data[:10],
                'errors': errors[:10]
            }
        
        # 如果有错误，不执行导入
        if errors:
            return {
                'success': False,
                'message': '数据验证失败',
                'total_rows': len(data),
                'error_rows': len(errors),
                'errors': errors
            }
        
        # 创建任务并执行导入
        task_id = cls._create_task('import', table_id, user_id)
        cls._update_task(task_id, status=ImportStatus.PROCESSING.value, total=len(records_data))
        
        success_count = 0
        error_count = 0
        
        try:
            for i, record_data in enumerate(records_data):
                try:
                    record = Record(
                        table_id=table_id,
                        values=record_data['values'],
                        created_by=user_id
                    )
                    db.session.add(record)
                    
                    if (i + 1) % cls.BATCH_SIZE == 0:
                        db.session.commit()
                    
                    success_count += 1
                    cls._update_task(task_id, processed=i+1, success_count=success_count)
                    
                except Exception as e:
                    error_count += 1
                    cls._update_task(task_id, error_count=error_count)
            
            db.session.commit()
            
            cls._update_task(
                task_id,
                status=ImportStatus.COMPLETED.value,
                progress=100,
                completed_at=datetime.now(timezone.utc).isoformat(),
                result={'imported_count': success_count, 'error_count': error_count}
            )
            
            return {
                'success': True,
                'task_id': task_id,
                'imported_count': success_count,
                'error_count': error_count
            }
            
        except Exception as e:
            db.session.rollback()
            cls._update_task(task_id, status=ImportStatus.FAILED.value, errors=[str(e)])
            raise
    
    # ==================== 导出功能 ====================
    
    @classmethod
    def export_to_excel(cls, table_id: str, record_ids: Optional[List[str]] = None,
                       field_ids: Optional[List[str]] = None) -> Tuple[bytes, str]:
        """
        导出表格数据到 Excel
        
        参数:
            table_id: 表格 ID
            record_ids: 指定记录 ID 列表（可选，导出全部）
            field_ids: 指定字段 ID 列表（可选，导出全部）
            
        返回:
            (文件内容字节, 文件名)
        """
        if not HAS_PANDAS:
            raise ImportError('请安装 pandas: pip install pandas openpyxl')
        
        # 获取表格和字段
        table = Table.query.get(table_id)
        if not table:
            raise ValueError('表格不存在')
        
        # 获取字段
        if field_ids:
            fields = Field.query.filter(
                Field.id.in_(field_ids),
                Field.table_id == table_id
            ).order_by(Field.order).all()
        else:
            fields = table.fields.order_by(Field.order).all()
        
        # 获取记录
        query = Record.query.filter_by(table_id=table_id)
        if record_ids:
            query = query.filter(Record.id.in_(record_ids))
        records = query.all()
        
        # 准备数据
        data = []
        field_id_map = {str(f.id): f for f in fields}
        
        for record in records:
            row = {}
            for field in fields:
                value = record.values.get(str(field.id))
                row[field.name] = cls._format_export_value(value, field)
            data.append(row)
        
        # 创建 DataFrame
        df = pd.DataFrame(data)
        
        # 导出到字节流
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=table.name[:31])  # Excel 工作表名最多 31 字符
        output.seek(0)
        
        filename = f"{table.name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return output.getvalue(), filename
    
    @classmethod
    def export_to_csv(cls, table_id: str, record_ids: Optional[List[str]] = None,
                     field_ids: Optional[List[str]] = None,
                     encoding: str = 'utf-8-sig') -> Tuple[bytes, str]:
        """
        导出表格数据到 CSV
        
        参数:
            table_id: 表格 ID
            record_ids: 指定记录 ID 列表（可选）
            field_ids: 指定字段 ID 列表（可选）
            encoding: 文件编码
            
        返回:
            (文件内容字节, 文件名)
        """
        if not HAS_PANDAS:
            raise ImportError('请安装 pandas: pip install pandas')
        
        # 复用 Excel 的数据准备逻辑
        table = Table.query.get(table_id)
        if not table:
            raise ValueError('表格不存在')
        
        if field_ids:
            fields = Field.query.filter(
                Field.id.in_(field_ids),
                Field.table_id == table_id
            ).order_by(Field.order).all()
        else:
            fields = table.fields.order_by(Field.order).all()
        
        query = Record.query.filter_by(table_id=table_id)
        if record_ids:
            query = query.filter(Record.id.in_(record_ids))
        records = query.all()
        
        data = []
        for record in records:
            row = {}
            for field in fields:
                value = record.values.get(str(field.id))
                row[field.name] = cls._format_export_value(value, field)
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # 导出到字节流
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding=encoding)
        output.seek(0)
        
        filename = f"{table.name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        
        return output.getvalue(), filename
    
    @classmethod
    def export_to_json(cls, table_id: str, record_ids: Optional[List[str]] = None,
                      field_ids: Optional[List[str]] = None) -> Tuple[bytes, str]:
        """
        导出表格数据到 JSON
        
        参数:
            table_id: 表格 ID
            record_ids: 指定记录 ID 列表（可选）
            field_ids: 指定字段 ID 列表（可选）
            
        返回:
            (文件内容字节, 文件名)
        """
        table = Table.query.get(table_id)
        if not table:
            raise ValueError('表格不存在')
        
        if field_ids:
            fields = Field.query.filter(
                Field.id.in_(field_ids),
                Field.table_id == table_id
            ).order_by(Field.order).all()
        else:
            fields = table.fields.order_by(Field.order).all()
        
        query = Record.query.filter_by(table_id=table_id)
        if record_ids:
            query = query.filter(Record.id.in_(record_ids))
        records = query.all()
        
        data = []
        for record in records:
            row = {'id': str(record.id)}
            for field in fields:
                value = record.values.get(str(field.id))
                row[field.name] = cls._format_export_value(value, field)
            row['created_at'] = record.created_at.isoformat()
            row['updated_at'] = record.updated_at.isoformat()
            data.append(row)
        
        output = io.BytesIO()
        output.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))
        output.seek(0)
        
        filename = f"{table.name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        
        return output.getvalue(), filename
    
    # ==================== 辅助方法 ====================
    
    @staticmethod
    def _convert_value(value: Any, field: Field) -> Any:
        """
        转换导入值为字段所需类型

        参数:
            value: 原始值
            field: 字段对象
            
        返回:
            转换后的值
        """
        if value is None:
            return None
        
        if HAS_PANDAS and pd is not None and pd.isna(value):
            return None
        
        field_type = FieldType(field.type)
        
        # 数字类型
        if field_type in (FieldType.NUMBER, FieldType.CURRENCY, FieldType.PERCENT, FieldType.RATING):
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        # 整数类型
        if field_type == FieldType.AUTO_NUMBER:
            try:
                return int(value)
            except (ValueError, TypeError):
                return None
        
        # 布尔类型
        if field_type == FieldType.CHECKBOX:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', '是', 'y')
            return bool(value)
        
        # 多选类型
        if field_type == FieldType.MULTI_SELECT:
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                # 支持逗号分隔或 JSON 数组字符串
                try:
                    return json.loads(value)
                except:
                    return [v.strip() for v in value.split(',') if v.strip()]
            return []
        
        # 日期类型
        if field_type == FieldType.DATE:
            if isinstance(value, datetime):
                return value.strftime('%Y-%m-%d')
            return str(value)
        
        # 日期时间类型
        if field_type == FieldType.DATE_TIME:
            if isinstance(value, datetime):
                return value.isoformat()
            return str(value)
        
        # 默认转为字符串
        return str(value)
    
    @staticmethod
    def _format_export_value(value: Any, field: Field) -> Any:
        """
        格式化导出值
        
        参数:
            value: 字段值
            field: 字段对象
            
        返回:
            格式化后的值
        """
        if value is None:
            return ''
        
        field_type = FieldType(field.type)
        
        # 多选类型转为逗号分隔字符串
        if field_type == FieldType.MULTI_SELECT and isinstance(value, list):
            return ', '.join(str(v) for v in value)
        
        # 关联记录类型
        if field_type == FieldType.LINK_TO_RECORD and isinstance(value, list):
            return ', '.join(str(v) for v in value)
        
        # 附件类型
        if field_type == FieldType.ATTACHMENT and isinstance(value, list):
            return f'[{len(value)} 个附件]'
        
        return value
    
    @classmethod
    def analyze_import_file(cls, file: BinaryIO, file_type: str) -> Dict[str, Any]:
        """
        分析导入文件结构
        
        参数:
            file: 文件对象
            file_type: 文件类型（excel/csv）
            
        返回:
            文件结构信息（列名、示例数据等）
        """
        if not HAS_PANDAS:
            raise ImportError('请安装 pandas: pip install pandas openpyxl')
        
        # 读取文件
        if file_type == 'excel':
            df = pd.read_excel(file)
        elif file_type == 'csv':
            try:
                df = pd.read_csv(file)
            except UnicodeDecodeError:
                file.seek(0)
                df = pd.read_csv(file, encoding='gbk')
        else:
            raise ValueError('不支持的文件类型')
        
        # 分析列
        columns = []
        for col in df.columns:
            sample_values = df[col].dropna().head(5).tolist()
            columns.append({
                'name': str(col),
                'type': str(df[col].dtype),
                'sample_values': [str(v) for v in sample_values]
            })
        
        return {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': columns,
            'sample_rows': df.head(5).to_dict('records')
        }
