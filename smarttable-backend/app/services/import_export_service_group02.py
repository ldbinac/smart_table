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

class ImportExportServiceGroup02Mixin:
    """Mixin auto-split"""
    
    """导入导出服务类"""
    
    _tasks: Dict[str, Dict[str, Any]] = {}
    
    MAX_IMPORT_ROWS = 10000
    
    BATCH_SIZE = 500
    
    
    @staticmethod
    def _format_link_export_value(linked_ids: Any, field: Field,
                                  record_cache: Dict[str, Any],
                                  field_cache: Dict[str, Any]) -> str:
        """
        格式化关联记录字段的导出值：将关联记录 ID 解析为显示名称，多值以逗号分隔。
    
        Args:
            linked_ids: 关联记录 ID 列表（或单个 ID）
            field: 关联字段对象
            record_cache: {记录ID: Record} 预取缓存
            field_cache: {字段ID: Field} 缓存（供显示值解析复用）
        """
        from app.services.link_service import LinkService
    
        if not linked_ids:
            return ''
        if not isinstance(linked_ids, list):
            linked_ids = [linked_ids]
    
        display_values = []
        fallback_values = []
        for rid in linked_ids:
            rid = str(rid)
            target = record_cache.get(rid)
            if target is None:
                # 关联记录已被删除等情况下，退化为显示 ID
                fallback_values.append(rid)
            else:
                display_values.append(
                    LinkService._get_link_display_value(target, str(field.id), field_cache)
                )
        # 兜底值若与已解析的显示名重复（例如历史导入残留的显示文本），
        # 不再重复输出，避免导出「苹果, 苹果」。
        resolved = set(display_values)
        for value in dict.fromkeys(fallback_values):
            if value not in resolved:
                display_values.append(value)
        return ', '.join(display_values)
    
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
            raise ImportError('install_pandas_pip_install_pandas_openpyxl')
    
        # 获取表格和字段
        table, fields, records, data = cls._prepare_export_data(table_id, record_ids, field_ids)
    
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
        table, fields, records, data = cls._prepare_export_data(table_id, record_ids, field_ids)
    
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
        table, fields, records, data = cls._prepare_export_data(table_id, record_ids, field_ids)
    
        # 补充记录级元信息（与 Excel/CSV 区分，JSON 需要保留 id 与时间戳）
        for i, record in enumerate(records):
            row = {'id': str(record.id)}
            row.update(data[i])
            row['created_at'] = record.created_at.isoformat()
            row['updated_at'] = record.updated_at.isoformat()
            data[i] = row
    
        output = io.BytesIO()
        output.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))
        output.seek(0)
    
        filename = f"{table.name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    
        return output.getvalue(), filename
    
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
    
        # 关联记录字段：单元格里是显示名称文本，导入后需通过按值批量匹配建立关联。
        # 不能写入 record.values，否则显示文本会被当成记录 ID，再次导出时重复。
        if field_type in (FieldType.LINK_TO_RECORD, FieldType.LINK):
            return []
    
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
                value = value.strip()
                # 明确的真值
                if value.lower() in ('true', '1', 'yes', '是', 'y', '✓', '☑', 'checked', 'on'):
                    return True
                # 明确的假值
                if value.lower() in ('false', '0', 'no', '否', 'n', '', '✗', '☐', 'unchecked', 'off'):
                    return False
                # 其他字符串视为真（非空即为真）
                return True
            if isinstance(value, (int, float)):
                # 数字：1 为真，0 为假，其他非零数字根据业务需求（这里视为真）
                return value == 1 or value == True
            return bool(value)
    
        # 单选类型
        if field_type == FieldType.SINGLE_SELECT:
            if isinstance(value, str):
                return value.strip()
            return str(value) if value is not None else None
    
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
            # 尝试解析字符串日期
            if isinstance(value, str):
                try:
                    # 尝试多种日期格式
                    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S']:
                        try:
                            dt = datetime.strptime(value.strip(), fmt)
                            return dt.strftime('%Y-%m-%d')
                        except ValueError:
                            continue
                    # 如果都解析失败，返回原值
                    return value
                except Exception:
                    return value
            return str(value) if value is not None else None
    
        # 日期时间类型
        if field_type == FieldType.DATE_TIME:
            if isinstance(value, datetime):
                # 处理 tz-naive 的 datetime（如 pandas Timestamp）
                if value.tzinfo is None:
                    return value.replace(tzinfo=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                return value.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            # 尝试解析字符串日期时间
            if isinstance(value, str):
                try:
                    # 尝试多种日期时间格式
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                        try:
                            dt = datetime.strptime(value.strip(), fmt)
                            # 将本地时间转换为 UTC ISO 格式
                            return dt.replace(tzinfo=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                        except ValueError:
                            continue
                    # 如果都解析失败，返回原值
                    return value
                except Exception:
                    return value
            return str(value) if value is not None else None
    
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
    
        # AI 字段：多选输出类型存储选项名称数组（如 ["工作", "生活"]），
        # 同样转为逗号分隔；单选/文本/数字输出为标量原样返回（修复导出异常）
        if field_type == FieldType.AI:
            if isinstance(value, list):
                return ', '.join(str(v) for v in value)
            return value
    
        # 附件类型
        if field_type == FieldType.ATTACHMENT and isinstance(value, list):
            return f'[{len(value)} 个附件]'
    
        # 兜底：其余类型的列表值转逗号分隔（openpyxl 不支持列表单元格）
        if isinstance(value, list):
            return ', '.join(str(v) for v in value)
    
        # 日期时间类型：将 UTC ISO 格式转换为本地时区格式
        if field_type == FieldType.DATE_TIME and isinstance(value, str):
            try:
                # 解析 UTC 时间
                if value.endswith('Z'):
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                elif 'T' in value:
                    dt = datetime.fromisoformat(value)
                else:
                    return value
                # 转换为本地时区（系统本地时区）
                local_dt = dt.astimezone()
                return local_dt.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                return value
    
        return value
    
    @staticmethod
    def detect_field_type(sample_values: List[Any], column_name: str = '') -> Dict[str, Any]:
        """
        根据样本数据智能识别字段类型
    
        参数:
            sample_values: 样本数据列表
            column_name: 列名（用于辅助判断）
    
        返回:
            包含建议类型和置信度的字典
        """
        if not sample_values:
            return {'type': 'single_line_text', 'confidence': 0.5}
    
        # 过滤掉None和空值
        values = [v for v in sample_values if v is not None and str(v).strip() != '']
        if not values:
            return {'type': 'single_line_text', 'confidence': 0.5}
    
        total = len(values)
    
        # 检查是否为布尔值
        bool_patterns = ['是', '否', 'true', 'false', 'yes', 'no', '1', '0', 'y', 'n', 'on', 'off']
        bool_count = sum(1 for v in values if str(v).lower().strip() in bool_patterns)
        if bool_count / total >= 0.8:
            return {'type': 'checkbox', 'confidence': 0.9}
    
        # 检查是否为日期
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # 2024-01-01
            r'^\d{4}/\d{2}/\d{2}$',  # 2024/01/01
            r'^\d{2}-\d{2}-\d{4}$',  # 01-01-2024
            r'^\d{2}/\d{2}/\d{4}$',  # 01/01/2024
            r'^\d{4}年\d{2}月\d{2}日$',  # 2024年01月01日
        ]
        date_count = 0
        for v in values:
            v_str = str(v).strip()
            if any(re.match(pattern, v_str) for pattern in date_patterns):
                date_count += 1
        if date_count / total >= 0.8:
            return {'type': 'date', 'confidence': 0.9}
    
        # 检查是否为日期时间
        datetime_patterns = [
            r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}',
            r'^\d{4}/\d{2}/\d{2}[T ]\d{2}:\d{2}:\d{2}',
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            r'^\d{4}/\d{2}/\d{2} \d{2}:\d{2}$',
        ]
        datetime_count = 0
        for v in values:
            v_str = str(v).strip()
            if any(re.match(pattern, v_str) for pattern in datetime_patterns):
                datetime_count += 1
        if datetime_count / total >= 0.8:
            return {'type': 'date_time', 'confidence': 0.9}
    
        # 检查是否为邮箱
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        email_count = sum(1 for v in values if re.match(email_pattern, str(v).strip()))
        if email_count / total >= 0.8:
            return {'type': 'email', 'confidence': 0.95}
    
        # 检查是否为URL
        url_pattern = r'^https?://[^\s<>"{}|\\^`\[\]]+$'
        url_count = sum(1 for v in values if re.match(url_pattern, str(v).strip()))
        if url_count / total >= 0.8:
            return {'type': 'url', 'confidence': 0.95}
    
        # 检查是否为电话号码
        phone_patterns = [
            r'^1[3-9]\d{9}$',  # 中国大陆手机号
            r'^\d{3,4}-\d{7,8}$',  # 座机号
            r'^\+86[\s-]?1[3-9]\d{9}$',  # +86手机号
            r'^\(\d{3,4}\)\d{7,8}$',  # (区号)号码
        ]
        phone_count = 0
        for v in values:
            v_str = re.sub(r'[\s-]', '', str(v).strip())
            if any(re.match(pattern, v_str) for pattern in phone_patterns):
                phone_count += 1
        if phone_count / total >= 0.8:
            return {'type': 'phone', 'confidence': 0.9}
    
        # 检查是否为数字
        number_count = 0
        for v in values:
            try:
                float(str(v).replace(',', '').strip())
                number_count += 1
            except (ValueError, TypeError):
                pass
        if number_count / total >= 0.9:
            # 检查是否为整数
            int_count = 0
            for v in values:
                try:
                    v_str = str(v).replace(',', '').strip()
                    if float(v_str) == int(float(v_str)):
                        int_count += 1
                except (ValueError, TypeError):
                    pass
            if int_count / total >= 0.9:
                return {'type': 'number', 'confidence': 0.9, 'is_integer': True}
            return {'type': 'number', 'confidence': 0.9}
    
        # 检查是否为多选（包含逗号或分号分隔的值）
        multi_select_count = 0
        for v in values:
            v_str = str(v).strip()
            if ',' in v_str or '，' in v_str or ';' in v_str:
                multi_select_count += 1
        if multi_select_count / total >= 0.5:
            return {'type': 'multi_select', 'confidence': 0.7}
    
        # 检查文本长度
        avg_length = sum(len(str(v)) for v in values) / total
        if avg_length > 100:
            return {'type': 'long_text', 'confidence': 0.8}
    
        # 检查是否为单选（唯一值较少）
        unique_values = set(str(v).strip() for v in values)
        if len(unique_values) <= 10 and len(unique_values) / total < 0.5:
            return {'type': 'single_select', 'confidence': 0.7}
    
        # 默认返回单行文本类型
        return {'type': 'single_line_text', 'confidence': 0.6}
    
    @classmethod
    def analyze_excel_for_table(cls, file: BinaryIO) -> Dict[str, Any]:
        """
        分析Excel文件，用于创建数据表
    
        参数:
            file: Excel文件对象
    
        返回:
            文件结构信息和字段建议
        """
        if not HAS_PANDAS:
            raise ImportError('install_pandas_pip_install_pandas_openpyxl')
    
        # 读取Excel文件
        try:
            df = pd.read_excel(file)
        except Exception as e:
            raise ValueError(translate('excel_read_failed_short', str(e)))
    
        if len(df) == 0:
            raise ValueError('excel_file_empty_contains_no_data_rows')
    
        # 分析列
        columns = []
        for col in df.columns:
            sample_values = df[col].dropna().head(5).tolist()
            detected = cls.detect_field_type(sample_values, str(col))
    
            columns.append({
                'name': str(col),
                'source_column': str(col),
                'suggested_type': detected['type'],
                'confidence': detected['confidence'],
                'sample_values': [str(v) for v in sample_values[:3]],
                'is_primary_candidate': len(columns) == 0  # 第一列作为主字段候选
            })
    
        return {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': columns,
            'sheet_name': 'Sheet1'
        }
    
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
            raise ImportError('install_pandas_pip_install_pandas_openpyxl')
    
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
            raise ValueError('unsupported_file_type')
    
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
    
