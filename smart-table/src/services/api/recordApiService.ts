/**
 * Record API 服务
 */
import { apiClient } from '@/api/client';
import type { Record, PaginatedData, PaginationParams } from '@/api/types';

export const getRecords = async (
  tableId: string,
  params?: PaginationParams & { search?: string; view_id?: string }
): Promise<PaginatedData<Record>> => {
  try {
    return await apiClient.get<PaginatedData<Record>>(`/tables/${tableId}/records`, params as Record<string, unknown>);
  } catch (error) {
    // 401 错误时返回空列表，让前端使用本地缓存
    console.warn('[recordApiService] getRecords failed:', error);
    return {
      data: [],
      total: 0,
      page: 1,
      per_page: 100,
      total_pages: 0,
    };
  }
};

export const getRecord = async (id: string): Promise<Record> => {
  return apiClient.get<Record>(`/records/${id}`);
};

export const createRecord = async (
  tableId: string,
  values: Record<string, unknown>
): Promise<Record> => {
  try {
    return await apiClient.post<Record>(`/tables/${tableId}/records`, { values });
  } catch (error) {
    console.error('[recordApiService] createRecord failed:', error);
    throw error;
  }
};

export const updateRecord = async (id: string, values: Record<string, unknown>): Promise<Record> => {
  try {
    return await apiClient.put<Record>(`/records/${id}`, { values });
  } catch (error) {
    console.error('[recordApiService] updateRecord failed:', error);
    throw error;
  }
};

export const deleteRecord = async (id: string): Promise<void> => {
  try {
    await apiClient.delete<void>(`/records/${id}`);
  } catch (error) {
    console.error('[recordApiService] deleteRecord failed:', error);
    throw error;
  }
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
