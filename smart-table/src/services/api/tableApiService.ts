/**
 * Table API 服务
 */
import { apiClient } from '@/api/client';
import type { Table } from '@/api/types';

export interface CreateTableOptions {
  name?: string;
  description?: string;
  primary_field_name?: string;
  create_default_fields?: boolean;
}

export const getTables = async (baseId: string): Promise<Table[]> => {
  return apiClient.get<Table[]>(`/bases/${baseId}/tables`);
};

export const getTable = async (id: string): Promise<Table> => {
  return apiClient.get<Table>(`/tables/${id}`);
};

export const createTable = async (
  baseId: string, 
  data: CreateTableOptions
): Promise<Table> => {
  return apiClient.post<Table>(`/bases/${baseId}/tables`, data);
};

export const updateTable = async (id: string, data: Partial<Table>): Promise<Table> => {
  return apiClient.put<Table>(`/tables/${id}`, data);
};

export const deleteTable = async (id: string): Promise<void> => {
  await apiClient.delete<void>(`/tables/${id}`);
};

export const duplicateTable = async (id: string, data?: { name?: string }): Promise<Table> => {
  return apiClient.post<Table>(`/tables/${id}/duplicate`, data || {});
};

export const reorderTables = async (
  baseId: string,
  tableOrders: Array<{ id: string; order: number }>
): Promise<Table[]> => {
  return apiClient.put<Table[]>(`/bases/${baseId}/tables/reorder`, { table_orders: tableOrders });
};

export const tableApiService = {
  getTables,
  getTable,
  createTable,
  updateTable,
  deleteTable,
  duplicateTable,
  reorderTables
};

export default tableApiService;
