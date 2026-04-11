"""
导入导出路由模块
处理数据导入导出请求，支持 Excel、CSV、JSON 格式
"""
import io
from flask import Blueprint, request, g, send_file, current_app

from app.services.import_export_service import ImportExportService
from app.services.base_service import BaseService
from app.models.base import MemberRole
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
def preview_import():
    """
    预览导入数据（不实际导入）
    
    请求参数:
        - file: 文件（Excel 或 CSV）
        - table_id: 目标表格 ID
        - field_mapping: 字段映射 JSON 字符串 {列名: field_id}
        - file_type: 文件类型（excel/csv，可选，自动检测）
        
    返回:
        预览数据和验证结果
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
def import_data():
    """
    执行数据导入
    
    请求参数:
        - file: 文件（Excel 或 CSV）
        - table_id: 目标表格 ID
        - field_mapping: 字段映射 JSON 字符串 {列名: field_id}
        - file_type: 文件类型（excel/csv，可选）
        
    返回:
        导入任务 ID 和结果
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
def import_json():
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
def analyze_import_file():
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
def export_data():
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
    user_id = g.current_user_id
    
    data = request.get_json() or {}
    
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


@import_export_bp.route('/export/excel', methods=['POST'])
@jwt_required
def export_excel():
    """导出为 Excel 格式（便捷接口）"""
    data = request.get_json() or {}
    data['format'] = 'excel'
    request._cached_json = data
    return export_data()


@import_export_bp.route('/export/csv', methods=['POST'])
@jwt_required
def export_csv():
    """导出为 CSV 格式（便捷接口）"""
    data = request.get_json() or {}
    data['format'] = 'csv'
    request._cached_json = data
    return export_data()


@import_export_bp.route('/export/json', methods=['POST'])
@jwt_required
def export_json():
    """导出为 JSON 格式（便捷接口）"""
    data = request.get_json() or {}
    data['format'] = 'json'
    request._cached_json = data
    return export_data()


# ==================== 任务状态查询 ====================

@import_export_bp.route('/import/<task_id>', methods=['GET'])
@jwt_required
def get_import_task(task_id):
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


# ==================== 辅助权限检查方法 ====================

# BaseService.check_permission_for_table 已在 base_service.py 中实现
