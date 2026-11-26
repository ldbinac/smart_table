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

class ImportExportServiceGroup01Mixin:
    """Mixin auto-split"""
    
    """导入导出服务类"""
    
    _tasks: Dict[str, Dict[str, Any]] = {}
    
    MAX_IMPORT_ROWS = 10000
    
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
                raise ImportError('install_pandas_pip_install_pandas_openpyxl')
        except ImportError:
            raise ImportError('install_pandas_pip_install_pandas_openpyxl')
    
        # 读取 Excel 文件
        try:
            df = pd.read_excel(file)
        except Exception as e:
            raise ValueError(translate('excel_read_failed', str(e)))
    
        # 检查行数限制
        if len(df) > cls.MAX_IMPORT_ROWS:
            raise ValueError(translate('import_rows_exceed_limit', cls.MAX_IMPORT_ROWS))
    
        # 获取表格信息
        table = Table.query.get(table_id)
        if not table:
            raise ValueError('table_does_not_exist')
    
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
                'message': 'data_validation_failed',
                'total_rows': len(df),
                'error_rows': len(errors),
                'errors': errors
            }
    
        # 创建任务
        task_id = cls._create_task('import', table_id, user_id)
        cls._update_task(task_id, status=ImportStatus.PROCESSING.value, total=len(records_data))
    
        # 执行导入（使用 savepoint 保证数据一致性）
        success_count = 0
        error_count = 0
        imported_record_ids = []
        batch_records = []
    
        try:
            for i, record_data in enumerate(records_data):
                try:
                    record = Record(
                        table_id=table_id,
                        values=record_data['values'],
                        created_by=user_id
                    )
                    db.session.add(record)
                    batch_records.append(record)
    
                    success_count += 1
    
                    if (i + 1) % cls.BATCH_SIZE == 0:
                        savepoint = db.session.begin_nested()
                        try:
                            db.session.flush()
                            record_ids = [str(r.id) for r in batch_records]
                            db.session.commit()
                            imported_record_ids.extend(record_ids)
                            batch_records = []
                        except Exception as batch_err:
                            savepoint.rollback()
                            error_count += len(batch_records)
                            success_count -= len(batch_records)
                            batch_records = []
                            cls._update_task(task_id, error_count=error_count)
    
                    cls._update_task(task_id, processed=i+1, success_count=success_count)
    
                except Exception as e:
                    error_count += 1
                    cls._update_task(task_id, error_count=error_count)
    
            if batch_records:
                savepoint = db.session.begin_nested()
                try:
                    db.session.flush()
                    record_ids = [str(r.id) for r in batch_records]
                    db.session.commit()
                    imported_record_ids.extend(record_ids)
                except Exception as batch_err:
                    savepoint.rollback()
                    error_count += len(batch_records)
                    success_count -= len(batch_records)
    
            cls._update_task(
                task_id,
                status=ImportStatus.COMPLETED.value,
                progress=100,
                completed_at=datetime.now(timezone.utc).isoformat(),
                result={
                    'imported_count': success_count,
                    'error_count': error_count,
                    'imported_record_ids': imported_record_ids
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
            raise ValueError(translate('csv_read_failed', str(e)))
    
        # 复用 Excel 导入逻辑
        return cls.import_from_excel(
            io.BytesIO(df.to_excel(index=False)),
            table_id,
            field_mapping,
            user_id,
            preview_only
        )
    
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
            raise ValueError('table_does_not_exist')
    
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
            raise ValueError(translate('import_rows_exceed_limit', cls.MAX_IMPORT_ROWS))
    
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
                'message': 'data_validation_failed',
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
    
    @staticmethod
    def _is_link_type(field) -> bool:
        """判断字段是否为关联记录类型（兼容 link / link_to_record 两种存储值）"""
        try:
            # FieldType 是普通 Enum，成员与 .value 字符串不相等，必须显式取 value，
            # 否则关联字段的导出格式化逻辑会被整体跳过，导出成记录 ID 列表。
            ft = FieldType(field.type).value
        except (ValueError, TypeError, AttributeError):
            ft = str(getattr(field, 'type', field))
        return ft in (FieldType.LINK_TO_RECORD.value, FieldType.LINK.value)
    
    @staticmethod
    def _is_record_id(value: Any) -> bool:
        """判断值是否为合法的记录 ID（项目统一使用 UUID）"""
        try:
            uuid.UUID(str(value))
            return True
        except (ValueError, TypeError, AttributeError):
            return False
    
    @classmethod
    def _prepare_export_data(cls, table_id: str,
                             record_ids: Optional[List[str]] = None,
                             field_ids: Optional[List[str]] = None
                             ) -> Tuple[Any, List[Field], List[Record], List[Dict[str, Any]]]:
        """
        准备导出数据（Excel/CSV/JSON 共用）。
    
        针对关联记录字段做两件事：
        1. 从权威的 LinkValue 表批量获取关联记录 ID，保证一对多主从关系下
           主表字段能导出全部关联的（而非仅 record.values 中可能缺失/被覆盖的一条）；
        2. 将关联记录 ID 解析为关联字段配置的显示名称（displayFieldId），
           避免直接导出关联表记录 ID。
    
        返回:
            (table, fields, records, data)
            - data: 与 records 同序，元素为 {字段名: 已格式化值}
        """
        from app.services.link_service import LinkService
    
        table = Table.query.get(table_id)
        if not table:
            raise ValueError('table_does_not_exist')
    
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
    
        # 关联字段：收集每条记录在「关联字段」上的全部关联记录 ID。
        # 以界面展示所用的 record.values 为主来源（与前端一致），再与权威的 LinkValue 表
        # （batch_get_record_link_ids，可覆盖反向双向关联）合并去重，避免漏导/漏显。
        link_fields = [f for f in fields if cls._is_link_type(f)]
        link_map: Dict[str, Dict[str, List[str]]] = {}
        record_cache: Dict[str, Any] = {}
        field_cache: Dict[str, Any] = {}
    
        link_id_collections: Dict[Tuple[str, str], List[str]] = {}
    
        if link_fields and records:
            all_record_ids = [str(r.id) for r in records]
            try:
                link_map = LinkService.batch_get_record_link_ids(all_record_ids)
            except Exception as e:
                try:
                    from flask import current_app as _ca
                    _ca.logger.error(f'[ImportExport] 批量获取关联记录失败: {e}')
                except Exception:
                    pass
                link_map = {}
    
            # 合并两个来源的关联 ID，record.values 优先（与前端展示一致）
            all_target_ids: set = set()
            for record in records:
                rec_id = str(record.id)
                for field in link_fields:
                    fid = str(field.id)
                    ids: set = set()
                    # 主来源：record.values 中存储的关联记录 ID 列表。
                    # 统一转成字符串并过滤非法 ID：历史导入会把「苹果, 苹果」这类
                    # 显示文本写进 values，混进来会与解析出的显示名重复导出。
                    raw = record.values.get(fid)
                    if raw:
                        candidates = raw if isinstance(raw, list) else [raw]
                        ids.update(
                            str(v) for v in candidates if cls._is_record_id(v)
                        )
                    # 补充来源：LinkValue 表（含双向反向关联，可能不在 record.values 中）
                    lm_ids = (link_map.get(rec_id) or {}).get(fid)
                    if lm_ids:
                        ids.update(str(v) for v in lm_ids)
                    if ids:
                        link_id_collections[(rec_id, fid)] = list(ids)
                        all_target_ids.update(ids)
    
            # 预取全部目标记录，用于把关联记录 ID 解析为显示名称
            if all_target_ids:
                targets = Record.query.filter(Record.id.in_(list(all_target_ids))).all()
                record_cache = {str(t.id): t for t in targets}
    
        data: List[Dict[str, Any]] = []
        for record in records:
            row: Dict[str, Any] = {}
            rec_id = str(record.id)
            for field in fields:
                if cls._is_link_type(field):
                    linked_ids = link_id_collections.get((rec_id, str(field.id)), [])
                    row[field.name] = cls._format_link_export_value(
                        linked_ids, field, record_cache, field_cache
                    )
                else:
                    value = record.values.get(str(field.id))
                    row[field.name] = cls._format_export_value(value, field)
            data.append(row)
    
        return table, fields, records, data
    
