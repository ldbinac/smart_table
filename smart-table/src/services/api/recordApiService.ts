/**
 * Record API 服务
 */
import { apiClient } from "@/api/client";
import type { TableRecord, PaginatedData, PaginationParams } from "@/api/types";

export const getRecords = async (
  tableId: string,
  params?: PaginationParams & { search?: string; view_id?: string },
): Promise<PaginatedData<TableRecord>> => {
  try {
    const response = await apiClient.get<
      PaginatedData<TableRecord> & { data?: TableRecord[]; meta?: { pagination?: PaginatedData<TableRecord> } }
    >(`/tables/${tableId}/records`, params as Record<string, unknown>);

    // 适配后端 {success, message, data, meta} 格式
    const res = response as any;
    if (res.data && res.meta?.pagination) {
      return {
        items: res.data,
        total: res.meta.pagination.total,
        page: res.meta.pagination.page,
        per_page: res.meta.pagination.per_page,
        total_pages: res.meta.pagination.total_pages,
      };
    }

    return response as PaginatedData<TableRecord>;
  } catch (error) {
    // 401 错误时返回空列表，让前端使用本地缓存
    console.warn("[recordApiService] getRecords failed:", error);
    return {
      items: [],
      total: 0,
      page: 1,
      per_page: 100,
      total_pages: 0,
    };
  }
};

export const getRecord = async (id: string): Promise<TableRecord> => {
  return apiClient.get<TableRecord>(`/records/${id}`);
};

export const createRecord = async (
  tableId: string,
  values: Record<string, unknown>,
): Promise<TableRecord> => {
  try {
    return await apiClient.post<TableRecord>(`/tables/${tableId}/records`, {
      values,
    });
  } catch (error) {
    console.error("[recordApiService] createRecord failed:", error);
    throw error;
  }
};

export const updateRecord = async (
  id: string,
  values: Record<string, unknown>,
): Promise<TableRecord> => {
  try {
    return await apiClient.put<TableRecord>(`/records/${id}`, { values });
  } catch (error) {
    console.error("[recordApiService] updateRecord failed:", error);
    throw error;
  }
};

export const deleteRecord = async (id: string): Promise<void> => {
  try {
    await apiClient.delete<void>(`/records/${id}`);
  } catch (error) {
    console.error("[recordApiService] deleteRecord failed:", error);
    throw error;
  }
};

export const batchCreateRecords = async (
  tableId: string,
  records: Array<{ values: Record<string, unknown> }>,
): Promise<{ created_count: number; record_ids: string[] }> => {
  return apiClient.post<{ created_count: number; record_ids: string[] }>(
    `/tables/${tableId}/records/batch`,
    { records },
  );
};

export const batchUpdateRecords = async (
  recordIds: string[],
  values: Record<string, unknown>,
): Promise<{ updated_count: number; failed_ids: string[] }> => {
  return apiClient.put<{ updated_count: number; failed_ids: string[] }>(
    "/records/batch",
    {
      record_ids: recordIds,
      values,
    },
  );
};

export const batchDeleteRecords = async (
  recordIds: string[],
): Promise<{ deleted_count: number; failed_ids: string[] }> => {
  return apiClient.delete<{ deleted_count: number; failed_ids: string[] }>(
    "/records/batch",
    {
      data: { record_ids: recordIds },
      headers: {
        "Content-Type": "application/json",
      },
    } as Record<string, unknown>,
  );
};

export const computeFormulas = async (
  tableId: string,
  values: Record<string, unknown>,
): Promise<Record<string, unknown>> => {
  return apiClient.post<Record<string, unknown>>(
    `/tables/${tableId}/records/compute-formulas`,
    { values },
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
  computeFormulas,
};

export default recordApiService;
