/**
 * Record API 服务
 */
import { apiClient } from '@/api/client';
import type { Record, PaginatedData, PaginationParams } from '@/api/types';

export const getRecords = async (
  tableId: string,
  params?: PaginationParams & { search?: string; view_id?: string }
): Promise<PaginatedData<Record>> => {
  return apiClient.get<PaginatedData<Record>>(`/tables/${tableId}/records`, params as Record<string, unknown>);
};

export const getRecord = async (id: string): Promise<Record> => {
  return apiClient.get<Record>(`/records/${id}`);
};

export const createRecord = async (
  tableId: string,
  values: Record<string, unknown>
): Promise<Record> => {
  return apiClient.post<Record>(`/tables/${tableId}/records`, { values });
};

export const updateRecord = async (id: string, values: Record<string, unknown>): Promise<Record> => {
  return apiClient.put<Record>(`/records/${id}`, { values });
};

export const deleteRecord = async (id: string): Promise<void> => {
  await apiClient.delete<void>(`/records/${id}`);
};

export const batchCreateRecords = async (
  tableId: string,
  records: Array<{ values: Record<string, unknown> }>
): Promise<{ created_count: number; records: Record[] }> => {
  return apiClient.post<{ created_count: number; records: Record[] }>(
    `/tables/${tableId}/records/batch`,
    { records }
  );
};

export const batchUpdateRecords = async (
  recordIds: string[],
  values: Record<string, unknown>
): Promise<{ updated_count: number; failed_ids: string[] }> => {
  return apiClient.put<{ updated_count: number; failed_ids: string[] }>('/records/batch', {
    record_ids: recordIds,
    values
  });
};

export const batchDeleteRecords = async (
  recordIds: string[]
): Promise<{ deleted_count: number; failed_ids: string[] }> => {
  return apiClient.delete<{ deleted_count: number; failed_ids: string[] }>('/records/batch', {
    record_ids: recordIds
  } as Record<string, unknown>);
};

export const computeFormulas = async (
  tableId: string,
  values: Record<string, unknown>
): Promise<Record<string, unknown>> => {
  return apiClient.post<Record<string, unknown>>(
    `/tables/${tableId}/records/compute-formulas`,
    { values }
  );
};

export const recordApiService = {
  getRecords,
  getRecord,
  createRecord,
  updateRecord,
  deleteRecord,
  batchCreateRecords,
  batchUpdateRecords,
  batchDeleteRecords,
  computeFormulas
};

export default recordApiService;
