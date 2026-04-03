/**
 * Record API服务
 * 处理Record相关的API调用
 */

import { apiClient } from '@/api/client'
import type { Record, PaginatedData, PaginationParams } from '@/api/types'

/**
 * 获取Table下的Record列表
 */
export const getRecords = async (
  tableId: string, 
  params?: PaginationParams & { search?: string; view_id?: string }
): Promise<PaginatedData<Record>> => {
  const response = await apiClient.get<PaginatedData<Record>>(`/tables/${tableId}/records`, params as Record<string, unknown>)
  return response.data
}

/**
 * 获取单个Record
 */
export const getRecord = async (id: string): Promise<Record> => {
  const response = await apiClient.get<Record>(`/records/${id}`)
  return response.data
}

/**
 * 创建Record
 */
export const createRecord = async (tableId: string, values: Record<string, unknown>): Promise<Record> => {
  const response = await apiClient.post<Record>(`/tables/${tableId}/records`, { values })
  return response.data
}

/**
 * 更新Record
 */
export const updateRecord = async (id: string, values: Record<string, unknown>): Promise<Record> => {
  const response = await apiClient.put<Record>(`/records/${id}`, { values })
  return response.data
}

/**
 * 删除Record
 */
export const deleteRecord = async (id: string): Promise<void> => {
  await apiClient.delete(`/records/${id}`)
}

/**
 * 批量创建Records
 */
export const batchCreateRecords = async (tableId: string, records: Array<{ values: Record<string, unknown> }>): Promise<{ created_count: number; records: Record[] }> => {
  const response = await apiClient.post<{ created_count: number; records: Record[] }>(`/tables/${tableId}/records/batch`, {
    records
  })
  return response.data
}

/**
 * 批量更新Records
 */
export const batchUpdateRecords = async (recordIds: string[], values: Record<string, unknown>): Promise<{ updated_count: number; failed_ids: string[] }> => {
  const response = await apiClient.put<{ updated_count: number; failed_ids: string[] }>('/records/batch', {
    record_ids: recordIds,
    values
  })
  return response.data
}

/**
 * 批量删除Records
 */
export const batchDeleteRecords = async (recordIds: string[]): Promise<{ deleted_count: number; failed_ids: string[] }> => {
  const response = await apiClient.delete<{ deleted_count: number; failed_ids: string[] }>('/records/batch', {
    record_ids: recordIds
  } as Record<string, unknown>)
  return response.data
}

/**
 * 计算公式值
 */
export const computeFormulas = async (recordId: string, previewValues?: Record<string, unknown>): Promise<Record<string, unknown>> => {
  const response = await apiClient.post<Record<string, unknown>>(`/records/${recordId}/compute`, {
    preview_values: previewValues
  })
  return response.data
}

// 导出Record服务
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
}

export default recordApiService
