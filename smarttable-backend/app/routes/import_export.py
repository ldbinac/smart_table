"""
导入导出路由模块
处理数据导入导出请求，支持 Excel、CSV、JSON 格式
"""
import io
import os
import uuid
from typing import Dict, Optional
from flask import Blueprint, request, g, send_file, current_app

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    pd = None
    HAS_PANDAS = False

from app.services.import_export_service import ImportExportService
from app.services.base_service import BaseService
from app.models.base import MemberRole
from app.extensions import db
from app.utils.decorators import jwt_required
from app.utils.response import (
    success_response, error_response, not_found_response,
    forbidden_response
)

import_export_bp = Blueprint('import_export', __name__)
# 禁用严格斜杠，允许带或不带斜杠的URL
import_export_bp.strict_slashes = False


# ==================== 导入功能 ====================

@import_export_bp.route('/import/preview', methods=['POST'])
@jwt_required
def preview_import() -> tuple:
    """
    预览导入数据（不实际导入）
    ---
    tags:
      - Import/Export
    security:
      - Bearer: []
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: 文件（Excel 或 CSV）
      - name: table_id
        in: formData
        type: string
        required: true
        description: 目标表格 ID
      - name: field_mapping
        in: formData
        type: string
        description: "字段映射 JSON 字符串 {列名: field_id}"
      - name: file_type
        in: formData
        type: string
        enum: ['excel', 'csv']
        description: 文件类型（可选，自动检测）
    responses:
      200:
        description: 预览数据和验证结果
    """
    user_id = g.current_user_id
    
    # 检查文件
    if 'file' not in request.files:
        return error_response('请选择要导入的文件', code=400)
    
    file = request.files['file']
    if file.filename == '':
        return error_response('文件名不能为空', code=400)
    
    # 获取参数
    table_id = request.form.get('table_id') or request.args.get('table_id')
    field_mapping_str = request.form.get('field_mapping') or request.args.get('field_mapping', '{}')
    file_type = request.form.get('file_type') or request.args.get('file_type')
    
    if not table_id:
        return error_response('请指定目标表格 ID', code=400)
    
    # 检查权限
    if not BaseService.check_permission_for_table(table_id, user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限导入数据到此表格')
    
    # 解析字段映射
    try:
        import json
        field_mapping = json.loads(field_mapping_str)
    except json.JSONDecodeError:
        return error_response('字段映射格式无效', code=400)
    
    # 自动检测文件类型
    if not file_type:
        filename = file.filename.lower()
        if filename.endswith(('.xlsx', '.xls')):
            file_type = 'excel'
        elif filename.endswith('.csv'):
            file_type = 'csv'
        else:
            return error_response('不支持的文件类型，请上传 Excel 或 CSV 文件', code=400)
    
    try:
        if file_type == 'excel':
            result = ImportExportService.import_from_excel(
                file=file,
                table_id=table_id,
                field_mapping=field_mapping,
                user_id=user_id,
                preview_only=True
            )
        elif file_type == 'csv':
            result = ImportExportService.import_from_csv(
                file=file,
                table_id=table_id,
                field_mapping=field_mapping,
                user_id=user_id,
                preview_only=True
            )
        else:
            return error_response('不支持的文件类型', code=400)
        
        return success_response(
            data=result,
            message='导入预览成功'
        )
        
    except ValueError as e:
        return error_response(str(e), code=400)
    except ImportError as e:
        return error_response(str(e), code=500)
    except Exception as e:
        current_app.logger.error(f'导入预览失败: {str(e)}')
        return error_response('导入预览失败，请稍后重试', code=500)


@import_export_bp.route('/import', methods=['POST'])
@jwt_required
def import_data() -> tuple:
    """
    执行数据导入
    ---
    tags:
      - Import/Export
    security:
      - Bearer: []
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: 文件（Excel 或 CSV）
      - name: table_id
        in: formData
        type: string
        required: true
        description: 目标表格 ID
      - name: field_mapping
        in: formData
        type: string
        description: "字段映射 JSON 字符串 {列名: field_id}"
      - name: file_type
        in: formData
        type: string
        enum: ['excel', 'csv']
        description: 文件类型（可选，自动检测）
    responses:
      200:
        description: 导入任务 ID 和结果
    """
    user_id = g.current_user_id
    
    # 检查文件
    if 'file' not in request.files:
        return error_response('请选择要导入的文件', code=400)
    
    file = request.files['file']
    if file.filename == '':
        return error_response('文件名不能为空', code=400)
    
    # 获取参数
    table_id = request.form.get('table_id') or request.args.get('table_id')
    field_mapping_str = request.form.get('field_mapping') or request.args.get('field_mapping', '{}')
    file_type = request.form.get('file_type') or request.args.get('file_type')
    
    if not table_id:
        return error_response('请指定目标表格 ID', code=400)
    
    # 检查权限
    if not BaseService.check_permission_for_table(table_id, user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限导入数据到此表格')
    
    # 解析字段映射
    try:
        import json
        field_mapping = json.loads(field_mapping_str)
    except json.JSONDecodeError:
        return error_response('字段映射格式无效', code=400)
    
    # 自动检测文件类型
    if not file_type:
        filename = file.filename.lower()
        if filename.endswith(('.xlsx', '.xls')):
            file_type = 'excel'
        elif filename.endswith('.csv'):
            file_type = 'csv'
        else:
            return error_response('不支持的文件类型，请上传 Excel 或 CSV 文件', code=400)
    
    try:
        if file_type == 'excel':
            result = ImportExportService.import_from_excel(
                file=file,
                table_id=table_id,
                field_mapping=field_mapping,
                user_id=user_id,
                preview_only=False
            )
        elif file_type == 'csv':
            result = ImportExportService.import_from_csv(
                file=file,
                table_id=table_id,
                field_mapping=field_mapping,
                user_id=user_id,
                preview_only=False
            )
        else:
            return error_response('不支持的文件类型', code=400)
        
        if result.get('success'):
            return success_response(
                data=result,
                message='数据导入成功',
                code=201
            )
        else:
            return error_response(
                result.get('message', '导入失败'),
                code=400,
                details=result.get('errors', [])
            )
        
    except ValueError as e:
        return error_response(str(e), code=400)
    except ImportError as e:
        return error_response(str(e), code=500)
    except Exception as e:
        current_app.logger.error(f'数据导入失败: {str(e)}')
        return error_response('数据导入失败，请稍后重试', code=500)


@import_export_bp.route('/import/json', methods=['POST'])
@jwt_required
def import_json() -> tuple:
    """
    从 JSON 数据导入
    
    请求体:
        - table_id: 目标表格 ID
        - data: JSON 数据数组
        - field_mapping: 字段映射（可选，默认按名称匹配）
        - preview_only: 是否仅预览（可选，默认false）
        
    返回:
        导入结果或预览数据
    """
    user_id = g.current_user_id
    
    data = request.get_json() or {}
    
    table_id = data.get('table_id')
    json_data = data.get('data')
    field_mapping = data.get('field_mapping')
    preview_only = data.get('preview_only', False)
    
    if not table_id:
        return error_response('请指定目标表格 ID', code=400)
    
    if not json_data or not isinstance(json_data, list):
        return error_response('请提供有效的 JSON 数据数组', code=400)
    
    # 检查权限
    if not BaseService.check_permission_for_table(table_id, user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限导入数据到此表格')
    
    try:
        result = ImportExportService.import_from_json(
            data=json_data,
            table_id=table_id,
            field_mapping=field_mapping,
            user_id=user_id,
            preview_only=preview_only
        )
        
        if preview_only:
            return success_response(
                data=result,
                message='导入预览成功'
            )
        
        if result.get('success'):
            return success_response(
                data=result,
                message='数据导入成功',
                code=201
            )
        else:
            return error_response(
                result.get('message', '导入失败'),
                code=400,
                details=result.get('errors', [])
            )
        
    except ValueError as e:
        return error_response(str(e), code=400)
    except Exception as e:
        current_app.logger.error(f'JSON 导入失败: {str(e)}')
        return error_response('数据导入失败，请稍后重试', code=500)


@import_export_bp.route('/import/analyze', methods=['POST'])
@jwt_required
def analyze_import_file() -> tuple:
    """
    分析导入文件结构
    
    请求参数:
        - file: 文件（Excel 或 CSV）
        - file_type: 文件类型（excel/csv，可选）
        
    返回:
        文件结构信息（列名、示例数据等）
    """
    # 检查文件
    if 'file' not in request.files:
        return error_response('请选择要分析的文件', code=400)
    
    file = request.files['file']
    if file.filename == '':
        return error_response('文件名不能为空', code=400)
    
    file_type = request.form.get('file_type') or request.args.get('file_type')
    
    # 自动检测文件类型
    if not file_type:
        filename = file.filename.lower()
        if filename.endswith(('.xlsx', '.xls')):
            file_type = 'excel'
        elif filename.endswith('.csv'):
            file_type = 'csv'
        else:
            return error_response('不支持的文件类型', code=400)
    
    try:
        result = ImportExportService.analyze_import_file(file, file_type)
        return success_response(
            data=result,
            message='文件分析成功'
        )
    except ValueError as e:
        return error_response(str(e), code=400)
    except ImportError as e:
        return error_response(str(e), code=500)
    except Exception as e:
        current_app.logger.error(f'文件分析失败: {str(e)}')
        return error_response('文件分析失败', code=500)


# ==================== 导出功能 ====================

@import_export_bp.route('/export', methods=['POST'])
@jwt_required
def export_data() -> tuple:
    """
    导出表格数据
    
    请求体:
        - table_id: 表格 ID（必填）
        - format: 导出格式（excel/csv/json，默认excel）
        - record_ids: 指定记录 ID 列表（可选，导出全部）
        - field_ids: 指定字段 ID 列表（可选，导出全部）
        
    返回:
        文件下载
    """
    data = request.get_json() or {}
    return _do_export(data)


@import_export_bp.route('/export/excel', methods=['POST'])
@jwt_required
def export_excel() -> tuple:
    """导出为 Excel 格式（便捷接口）"""
    data = request.get_json() or {}
    data['format'] = 'excel'
    return _do_export(data)


@import_export_bp.route('/export/csv', methods=['POST'])
@jwt_required
def export_csv() -> tuple:
    """导出为 CSV 格式（便捷接口）"""
    data = request.get_json() or {}
    data['format'] = 'csv'
    return _do_export(data)


@import_export_bp.route('/export/json', methods=['POST'])
@jwt_required
def export_json() -> tuple:
    """导出为 JSON 格式（便捷接口）"""
    data = request.get_json() or {}
    data['format'] = 'json'
    return _do_export(data)


def _do_export(data: dict) -> tuple:
    """
    内部导出实现，接收已解析的参数字典
    
    Args:
        data: 包含 table_id, format, record_ids, field_ids 等参数的字典
    """
    user_id = g.current_user_id
    
    table_id = data.get('table_id')
    export_format = data.get('format', 'excel').lower()
    record_ids = data.get('record_ids')
    field_ids = data.get('field_ids')
    
    if not table_id:
        return error_response('请指定表格 ID', code=400)
    
    # 检查权限
    if not BaseService.check_permission_for_table(table_id, user_id, MemberRole.VIEWER):
        return forbidden_response('您没有权限导出此表格数据')
    
    try:
        if export_format == 'excel':
            file_content, filename = ImportExportService.export_to_excel(
                table_id=table_id,
                record_ids=record_ids,
                field_ids=field_ids
            )
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif export_format == 'csv':
            file_content, filename = ImportExportService.export_to_csv(
                table_id=table_id,
                record_ids=record_ids,
                field_ids=field_ids
            )
            mimetype = 'text/csv'
        elif export_format == 'json':
            file_content, filename = ImportExportService.export_to_json(
                table_id=table_id,
                record_ids=record_ids,
                field_ids=field_ids
            )
            mimetype = 'application/json'
        else:
            return error_response('不支持的导出格式', code=400)
        
        return send_file(
            io.BytesIO(file_content),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        
    except ValueError as e:
        return error_response(str(e), code=400)
    except ImportError as e:
        return error_response(str(e), code=500)
    except Exception as e:
        current_app.logger.error(f'数据导出失败: {str(e)}')
        return error_response('数据导出失败，请稍后重试', code=500)


# ==================== 任务状态查询 ====================

@import_export_bp.route('/import/<task_id>', methods=['GET'])
@jwt_required
def get_import_task(task_id) -> tuple:
    """
    获取导入任务状态
    
    参数:
        task_id: 任务 ID
        
    返回:
        任务状态和进度
    """
    task = ImportExportService.get_task(task_id)
    
    if not task:
        return not_found_response('任务')
    
    # 检查权限（只能查看自己的任务）
    if task.get('user_id') != g.current_user_id:
        return forbidden_response('您没有权限查看此任务')
    
    return success_response(
        data=task,
        message='获取任务状态成功'
    )


# ==================== Excel导入创建数据表功能 ====================

@import_export_bp.route('/import/excel/analyze', methods=['POST'])
@jwt_required
def analyze_excel_for_table() -> tuple:
    """
    分析Excel文件，用于创建数据表
    ---
    tags:
      - Import/Export
    security:
      - Bearer: []
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: Excel文件(.xlsx或.xls)
    responses:
      200:
        description: 文件结构信息和字段建议
    """
    # 检查文件
    if 'file' not in request.files:
        return error_response('请选择要上传的文件', code=400)
    
    file = request.files['file']
    if file.filename == '':
        return error_response('文件名不能为空', code=400)
    
    # 验证文件类型
    filename = file.filename.lower()
    if not filename.endswith(('.xlsx', '.xls')):
        return error_response('请上传Excel文件(.xlsx或.xls格式)', code=400)
    
    try:
        # 保存临时文件
        file_key = _save_temp_file(file)
        
        # 重新读取文件进行分析
        file.seek(0)
        result = ImportExportService.analyze_excel_for_table(file)
        result['file_key'] = file_key
        result['original_filename'] = file.filename
        
        return success_response(
            data=result,
            message='文件分析成功'
        )
    except ValueError as e:
        return error_response(str(e), code=400)
    except ImportError as e:
        return error_response(str(e), code=500)
    except Exception as e:
        current_app.logger.error(f'文件分析失败: {str(e)}')
        return error_response('文件分析失败，请稍后重试', code=500)


@import_export_bp.route('/import/excel/create-table', methods=['POST'])
@jwt_required
def create_table_from_excel() -> tuple:
    """
    从Excel文件创建数据表
    ---
    tags:
      - Import/Export
    security:
      - Bearer: []
    consumes:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            base_id:
              type: string
              description: Base ID
            table_name:
              type: string
              description: 数据表名称
            file_key:
              type: string
              description: 临时文件标识
            fields:
              type: array
              description: 字段配置
            import_data:
              type: boolean
              description: 是否同时导入数据
    responses:
      200:
        description: 创建结果
    """
    from app.services.table_service import TableService
    from app.services.field_service import FieldService
    from app.models.base import MemberRole
    
    user_id = g.current_user_id
    data = request.get_json() or {}
    
    # 验证参数
    base_id = data.get('base_id')
    table_name = data.get('table_name')
    file_key = data.get('file_key')
    fields_config = data.get('fields', [])
    import_data = data.get('import_data', False)
    
    if not base_id:
        return error_response('请指定Base ID', code=400)
    
    if not table_name:
        return error_response('请输入数据表名称', code=400)
    
    if not file_key:
        return error_response('请提供文件标识', code=400)
    
    if not fields_config:
        return error_response('请至少选择一个字段', code=400)
    
    # 检查权限
    if not BaseService.check_permission(base_id, user_id, MemberRole.EDITOR):
        return forbidden_response('您没有权限在此Base中创建数据表')
    
    # 获取临时文件路径
    temp_file_path = _get_temp_file_path(file_key)
    if not temp_file_path or not os.path.exists(temp_file_path):
        return error_response('文件已过期，请重新上传', code=400)
    
    # 检查 pandas 是否可用
    if not HAS_PANDAS or pd is None:
        return error_response('请安装 pandas: pip install pandas openpyxl', code=500)
    
    try:
        # 读取Excel文件
        df = pd.read_excel(temp_file_path)
        
        # 创建数据表（不自动创建默认字段，导入逻辑会自行创建字段）
        table = TableService.create_table(
            base_id=base_id,
            data={
                'name': table_name,
                'description': data.get('description', '')
            },
            create_default_fields=False
        )
        
        if not table:
            return error_response('创建数据表失败', code=500)
        
        created_fields = []
        field_mapping = {}  # source_column -> field_id
        primary_field_id = None  # 记录主字段 ID
        
        # 字段类型映射：前端类型 -> 后端类型
        field_type_mapping = {
            'single_line_text': 'single_line_text',
            'long_text': 'long_text',
            'rich_text': 'rich_text',
            'number': 'number',
            'date': 'date',
            'date_time': 'date_time',
            'email': 'email',
            'phone': 'phone',
            'url': 'url',
            'checkbox': 'checkbox',
            'single_select': 'single_select',
            'multi_select': 'multi_select'
        }
        
        # 创建字段
        for idx, field_conf in enumerate(fields_config):
            if not field_conf.get('included', True):
                continue
                
            field_name = field_conf.get('name', field_conf.get('source_column', f'字段{idx+1}'))
            frontend_type = field_conf.get('type', 'single_line_text')
            field_type = field_type_mapping.get(frontend_type, frontend_type)
            source_column = field_conf.get('source_column')
            is_primary = field_conf.get('is_primary', False)
            
            # 准备字段配置
            field_config = {
                'name': field_name,
                'type': field_type,
                'description': field_conf.get('description', ''),
                'is_primary': is_primary,
                'order': idx
            }
            
            # 添加类型特定的配置
            if field_type in ['single_select', 'multi_select']:
                # 从数据中推断选项
                if source_column and source_column in df.columns:
                    # 获取该列的所有非空值
                    column_values = df[source_column].dropna()
                    
                    # 收集所有选项值
                    all_options = []
                    if field_type == 'multi_select':
                        # 多选字段：对每个值按逗号分割，去空格，收集所有子项
                        for value in column_values:
                            if isinstance(value, str):
                                # 按逗号分割，去除前后空格
                                split_values = [v.strip() for v in value.split(',')]
                                all_options.extend(split_values)
                            else:
                                all_options.append(str(value))
                    else:
                        # 单选字段：直接使用值
                        all_options = [str(v) for v in column_values]
                    
                    # 去重并限制最多20个选项
                    unique_values = []
                    seen = set()
                    for opt in all_options:
                        if opt and opt not in seen:
                            unique_values.append(opt)
                            seen.add(opt)
                            if len(unique_values) >= 20:
                                break
                    
                    choices = [{'name': v, 'color': _get_option_color(i)} 
                              for i, v in enumerate(unique_values)]
                    # 选项需要包装在 choices 数组中
                    field_config['options'] = {'choices': choices}
            
            try:
                field_result = FieldService.create_field(
                    table_id=str(table.id),
                    data=field_config
                )
                if field_result.get('success') and field_result.get('field'):
                    field_data = field_result['field']
                    created_fields.append(field_data)
                    if source_column:
                        field_mapping[source_column] = field_data.get('id', '')
                    
                    # 记录主字段 ID
                    if is_primary or (primary_field_id is None and idx == 0):
                        primary_field_id = field_data.get('id')
                else:
                    current_app.logger.error(f'创建字段失败: {field_result.get("error", "未知错误")}')
            except Exception as e:
                current_app.logger.error(f'创建字段失败: {str(e)}')
                continue
        
        # 更新表格的主字段 ID
        if primary_field_id:
            table.primary_field_id = primary_field_id
            db.session.commit()
            current_app.logger.info(
                f'[import_export] 设置表格 {table.id} 的主字段: {primary_field_id}'
            )
        
        result = {
            'table_id': str(table.id),
            'table_name': table.name,
            'created_fields_count': len(created_fields),
            'imported_rows': 0,
            'failed_rows': 0
        }
        
        # 如果选择了导入数据
        if import_data and field_mapping:
            import_result = ImportExportService.import_from_excel(
                file=open(temp_file_path, 'rb'),
                table_id=str(table.id),
                field_mapping=field_mapping,
                user_id=user_id,
                preview_only=False
            )
            
            if import_result.get('success'):
                result['imported_rows'] = import_result.get('imported_count', 0)
                result['failed_rows'] = import_result.get('error_count', 0)
                result['task_id'] = import_result.get('task_id')
        
        # 清理临时文件
        try:
            os.remove(temp_file_path)
        except:
            pass
        
        return success_response(
            data=result,
            message='数据表创建成功',
            code=201
        )
        
    except Exception as e:
        current_app.logger.error(f'从Excel创建表失败: {str(e)}')
        return error_response(f'创建失败: {str(e)}', code=500)


# ==================== 临时文件存储 ====================

# 临时文件存储字典
_temp_files: Dict[str, str] = {}


def _save_temp_file(file) -> str:
    """保存文件到临时目录，返回文件标识"""
    temp_dir = current_app.config.get('TEMP_DIR', '/tmp')
    os.makedirs(temp_dir, exist_ok=True)
    
    file_key = f"excel_{uuid.uuid4().hex[:16]}"
    file_path = os.path.join(temp_dir, f"{file_key}_{file.filename}")
    
    file.save(file_path)
    _temp_files[file_key] = file_path
    
    return file_key


def _get_temp_file_path(file_key: str) -> Optional[str]:
    """获取临时文件路径"""
    return _temp_files.get(file_key)


def _get_option_color(index: int) -> str:
    """获取选项颜色"""
    colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', 
              '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc']
    return colors[index % len(colors)]


# ==================== 辅助权限检查方法 ====================

# BaseService.check_permission_for_table 已在 base_service.py 中实现
