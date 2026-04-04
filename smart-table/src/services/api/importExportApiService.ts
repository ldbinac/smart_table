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
  return apiClient.get<TaskStatus>(`/import/tasks/${taskId}`);
};

export const getExportTaskStatus = async (taskId: string): Promise<TaskStatus> => {
  return apiClient.get<TaskStatus>(`/export/tasks/${taskId}`);
};

export const importExportApiService = {
  analyzeImportFile,
  previewCSVImport,
  importFromCSV,
  importFromExcel,
  importFromJSON,
  exportData,
  getImportTaskStatus,
  getExportTaskStatus
};

export default importExportApiService;
