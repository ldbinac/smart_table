/**
 * Table API服务
 * 处理Table相关的API调用
 */

import { apiClient } from '@/api/client'
import type { Table, PaginatedData, PaginationParams } from '@/api/types'

/**
 * 获取Base下的Table列表
 */
export const getTables = async (baseId: string, params?: PaginationParams): Promise<PaginatedData<Table>> => {
  const response = await apiClient.get<PaginatedData<Table>>(`/bases/${baseId}/tables`, params as Record<string, unknown>)
  return response.data
}

/**
 * 获取单个Table
 */
export const getTable = async (id: string): Promise<Table> => {
  const response = await apiClient.get<Table>(`/tables/${id}`)
  return response.data
}

/**
 * 创建Table
 */
export const createTable = async (baseId: string, data: Partial<Table>): Promise<Table> => {
  const response = await apiClient.post<Table>('/tables', {
    base_id: baseId,
    ...data
  } as Record<string, unknown>)
  return response.data
}

/**
 * 更新Table
 */
export const updateTable = async (id: string, data: Partial<Table>): Promise<Table> => {
  const response = await apiClient.put<Table>(`/tables/${id}`, data as Record<string, unknown>)
  return response.data
}

/**
 * 删除Table
 */
export const deleteTable = async (id: string): Promise<void> => {
  await apiClient.delete(`/tables/${id}`)
}

/**
 * 复制Table
 */
export const duplicateTable = async (id: string, name?: string): Promise<Table> => {
  const response = await apiClient.post<Table>(`/tables/${id}/duplicate`, name ? { name } : undefined)
  return response.data
}

/**
 * 重新排序Tables
 */
export const reorderTables = async (baseId: string, tableOrders: { id: string; order: number }[]): Promise<Table[]> => {
  const response = await apiClient.put<Table[]>(`/bases/${baseId}/tables/reorder`, {
    table_orders: tableOrders
  })
  return response.data
}

// 导出Table服务
export const tableApiService = {
  getTables,
  getTable,
  createTable,
  updateTable,
  deleteTable,
  duplicateTable,
  reorderTables
}

export default tableApiService
