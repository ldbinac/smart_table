/**
 * View API服务
 * 处理View相关的API调用
 */

import { apiClient } from '@/api/client'
import type { View, ViewType, PaginatedData, PaginationParams } from '@/api/types'

/**
 * 获取Table下的View列表
 */
export const getViews = async (tableId: string, params?: PaginationParams): Promise<PaginatedData<View>> => {
  const response = await apiClient.get<PaginatedData<View>>(`/tables/${tableId}/views`, params as Record<string, unknown>)
  return response.data
}

/**
 * 获取单个View
 */
export const getView = async (id: string): Promise<View> => {
  const response = await apiClient.get<View>(`/views/${id}`)
  return response.data
}

/**
 * 创建View
 */
export const createView = async (tableId: string, data: Partial<View>): Promise<View> => {
  const response = await apiClient.post<View>(`/tables/${tableId}/views`, data as Record<string, unknown>)
  return response.data
}

/**
 * 更新View
 */
export const updateView = async (id: string, data: Partial<View>): Promise<View> => {
  const response = await apiClient.put<View>(`/views/${id}`, data as Record<string, unknown>)
  return response.data
}

/**
 * 删除View
 */
export const deleteView = async (id: string): Promise<void> => {
  await apiClient.delete(`/views/${id}`)
}

/**
 * 复制View
 */
export const duplicateView = async (id: string, name?: string): Promise<View> => {
  const response = await apiClient.post<View>(`/views/${id}/duplicate`, name ? { name } : undefined)
  return response.data
}

/**
 * 设置默认View
 */
export const setDefaultView = async (id: string): Promise<View> => {
  const response = await apiClient.post<View>(`/views/${id}/set-default`)
  return response.data
}

/**
 * 重新排序Views
 */
export const reorderViews = async (tableId: string, viewOrders: { id: string; order: number }[]): Promise<View[]> => {
  const response = await apiClient.put<View[]>(`/tables/${tableId}/views/reorder`, {
    view_orders: viewOrders
  })
  return response.data
}

/**
 * 获取支持的视图类型列表
 */
export const getViewTypes = async (): Promise<Array<{ type: ViewType; name: string; description: string; icon: string }>> => {
  const response = await apiClient.get<Array<{ type: ViewType; name: string; description: string; icon: string }>>('/views/types')
  return response.data
}

// 导出View服务
export const viewApiService = {
  getViews,
  getView,
  createView,
  updateView,
  deleteView,
  duplicateView,
  setDefaultView,
  reorderViews,
  getViewTypes
}

export default viewApiService
