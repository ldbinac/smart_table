/**
 * Field API服务
 * 处理Field相关的API调用
 */

import { apiClient } from '@/api/client'
import type { Field, FieldType, PaginatedData, PaginationParams } from '@/api/types'

/**
 * 获取Table下的Field列表
 */
export const getFields = async (tableId: string, params?: PaginationParams): Promise<PaginatedData<Field>> => {
  const response = await apiClient.get<PaginatedData<Field>>(`/tables/${tableId}/fields`, params as Record<string, unknown>)
  return response.data
}

/**
 * 获取单个Field
 */
export const getField = async (id: string): Promise<Field> => {
  const response = await apiClient.get<Field>(`/fields/${id}`)
  return response.data
}

/**
 * 创建Field
 */
export const createField = async (tableId: string, data: Partial<Field>): Promise<Field> => {
  const response = await apiClient.post<Field>(`/tables/${tableId}/fields`, data as Record<string, unknown>)
  return response.data
}

/**
 * 更新Field
 */
export const updateField = async (id: string, data: Partial<Field>): Promise<Field> => {
  const response = await apiClient.put<Field>(`/fields/${id}`, data as Record<string, unknown>)
  return response.data
}

/**
 * 删除Field
 */
export const deleteField = async (id: string): Promise<void> => {
  await apiClient.delete(`/fields/${id}`)
}

/**
 * 重新排序Fields
 */
export const reorderFields = async (tableId: string, fieldOrders: { id: string; order: number }[]): Promise<Field[]> => {
  const response = await apiClient.put<Field[]>(`/tables/${tableId}/fields/reorder`, {
    field_orders: fieldOrders
  })
  return response.data
}

/**
 * 获取支持的字段类型列表
 */
export const getFieldTypes = async (): Promise<Array<{ type: FieldType; name: string; description: string }>> => {
  const response = await apiClient.get<Array<{ type: FieldType; name: string; description: string }>>('/fields/types')
  return response.data
}

// 导出Field服务
export const fieldApiService = {
  getFields,
  getField,
  createField,
  updateField,
  deleteField,
  reorderFields,
  getFieldTypes
}

export default fieldApiService
