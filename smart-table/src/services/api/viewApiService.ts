/**
 * View API 服务
 */
import { apiClient } from '@/api/client';
import type { View, ViewType, PaginatedData, PaginationParams } from '@/api/types';

export const getViews = async (tableId: string): Promise<View[]> => {
  return apiClient.get<View[]>(`/tables/${tableId}/views`);
};

export const getView = async (id: string): Promise<View> => {
  return apiClient.get<View>(`/views/${id}`);
};

export const createView = async (tableId: string, data: Partial<View>): Promise<View> => {
  return apiClient.post<View>(`/tables/${tableId}/views`, { ...data, table_id: tableId });
};

export const updateView = async (id: string, data: Partial<View>): Promise<View> => {
  return apiClient.put<View>(`/views/${id}`, data);
};

export const deleteView = async (id: string): Promise<void> => {
  await apiClient.delete<void>(`/views/${id}`);
};

export const duplicateView = async (id: string, name?: string): Promise<View> => {
  return apiClient.post<View>(`/views/${id}/duplicate`, name ? { name } : undefined);
};

export const setDefaultView = async (tableId: string, viewId: string): Promise<View> => {
  return apiClient.put<View>(`/tables/${tableId}/views/${viewId}/set-default`);
};

export const reorderViews = async (
  tableId: string,
  viewOrders: Array<{ id: string; order: number }>
): Promise<View[]> => {
  return apiClient.put<View[]>(`/tables/${tableId}/views/reorder`, { view_orders: viewOrders });
};

export const getViewTypes = async (): Promise<Array<{ type: ViewType; name: string; description: string; icon: string }>> => {
  return apiClient.get<Array<{ type: ViewType; name: string; description: string; icon: string }>>('/views/types');
};

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
};

export default viewApiService;
