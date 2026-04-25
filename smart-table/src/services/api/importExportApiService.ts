/**
 * 导入导出 API 服务
 */
import { apiClient } from '@/api/client';
import type { ImportPreview, ImportResult, ExportOptions, TaskStatus } from '@/api/types';

export const analyzeImportFile = async (file: File): Promise<ImportPreview> => {
  const formData = new FormData();
  formData.append('file', file);

  return apiClient.upload('/import/analyze', formData) as Promise<ImportPreview>;
};

export const previewCSVImport = async (
  file: File,
  tableId: string
): Promise<ImportPreview> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('table_id', tableId);
  formData.append('preview_only', 'true');

  return apiClient.upload('/import/csv', formData) as Promise<ImportPreview>;
};

export const importFromCSV = async (
  file: File,
  tableId: string,
  fieldMapping?: Record<string, string>,
  skipFirstRow?: boolean
): Promise<ImportResult> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('table_id', tableId);
  if (skipFirstRow) formData.append('skip_first_row', 'true');
  if (fieldMapping) {
    Object.entries(fieldMapping).forEach(([k, v]) => {
      formData.append(`field_mapping[${k}]`, v);
    });
  }

  return apiClient.upload('/import/csv', formData) as Promise<ImportResult>;
};

export const importFromExcel = async (
  file: File,
  tableId: string,
  fieldMapping?: Record<string, string>,
  skipFirstRow?: boolean
): Promise<ImportResult> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('table_id', tableId);
  if (skipFirstRow) formData.append('skip_first_row', 'true');
  if (fieldMapping) {
    Object.entries(fieldMapping).forEach(([k, v]) => {
      formData.append(`field_mapping[${k}]`, v);
    });
  }

  return apiClient.upload('/import/excel', formData) as Promise<ImportResult>;
};

export const importFromJSON = async (
  data: unknown[],
  tableId: string,
  previewOnly?: boolean
): Promise<ImportResult | ImportPreview> => {
  if (previewOnly) {
    return apiClient.post<ImportPreview>('/import/json', {
      data,
      table_id: tableId,
      preview_only: true
    });
  }
  return apiClient.post<ImportResult>('/import/json', {
    data,
    table_id: tableId
  });
};

export const exportData = async (options: ExportOptions): Promise<Blob | unknown> => {
  if (options.format === 'json') {
    return apiClient.post<unknown>('/export', options);
  }
  const response = await apiClient.raw().post('/export', options, { responseType: 'blob' });
  return response.data as Blob;
};

export const getImportTaskStatus = async (taskId: string): Promise<TaskStatus> => {
  return apiClient.get<TaskStatus>(`/import/${taskId}`);
};

export const getExportTaskStatus = async (taskId: string): Promise<TaskStatus> => {
  return apiClient.get<TaskStatus>(`/export/tasks/${taskId}`);
};

// Excel导入创建数据表相关接口
export interface ExcelColumnAnalysis {
  name: string;
  source_column: string;
  suggested_type: string;
  confidence: number;
  sample_values: string[];
  is_primary_candidate: boolean;
}

export interface ExcelAnalysisResult {
  total_rows: number;
  total_columns: number;
  columns: ExcelColumnAnalysis[];
  sheet_name: string;
  file_key: string;
  original_filename: string;
}

export interface FieldConfig {
  source_column: string;
  name: string;
  type: string;
  is_primary: boolean;
  included: boolean;
}

export interface CreateTableFromExcelRequest {
  base_id: string;
  table_name: string;
  description?: string;
  file_key: string;
  fields: FieldConfig[];
  import_data: boolean;
}

export interface CreateTableFromExcelResult {
  table_id: string;
  table_name: string;
  created_fields_count: number;
  imported_rows: number;
  failed_rows: number;
  task_id?: string;
}

export const analyzeExcelForTable = async (file: File): Promise<{
  success: boolean;
  data?: ExcelAnalysisResult;
  message?: string;
}> => {
  const formData = new FormData();
  formData.append('file', file);

  // 使用 raw() 获取原始响应，以便获取完整的响应结构
  const response = await apiClient.raw().post('/import/excel/analyze', formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  
  const result = response.data as {
    success: boolean;
    data?: ExcelAnalysisResult;
    message?: string;
  };
  
  return result;
};

export const createTableFromExcel = async (
  params: CreateTableFromExcelRequest
): Promise<{
  success: boolean;
  data?: CreateTableFromExcelResult;
  message?: string;
}> => {
  // 使用 raw() 获取原始响应，以便获取完整的响应结构
  const response = await apiClient.raw().post('/import/excel/create-table', params);
  
  const result = response.data as {
    success: boolean;
    data?: CreateTableFromExcelResult;
    message?: string;
  };
  
  return result;
};

export const importExportApiService = {
  analyzeImportFile,
  previewCSVImport,
  importFromCSV,
  importFromExcel,
  importFromJSON,
  exportData,
  getImportTaskStatus,
  getExportTaskStatus,
  analyzeExcelForTable,
  createTableFromExcel
};

export default importExportApiService;
