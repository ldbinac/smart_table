/**
 * Field API 服务
 */
import { apiClient } from '@/api/client';
import type { Field, FieldType } from '@/api/types';

export const getFields = async (tableId: string): Promise<Field[]> => {
  return apiClient.get<Field[]>(`/tables/${tableId}/fields`);
};

export const getField = async (id: string): Promise<Field> => {
  return apiClient.get<Field>(`/fields/${id}`);
};

export const createField = async (tableId: string, data: Partial<Field>): Promise<Field> => {
  return apiClient.post<Field>(`/tables/${tableId}/fields`, { ...data, table_id: tableId });
};

export const updateField = async (id: string, data: Partial<Field>): Promise<Field> => {
  return apiClient.put<Field>(`/fields/${id}`, data);
};

export const deleteField = async (id: string): Promise<void> => {
  await apiClient.delete<void>(`/fields/${id}`);
};

export const reorderFields = async (
  tableId: string,
  fieldOrders: Array<{ field_id: string; order: number }>
): Promise<Field[]> => {
  return apiClient.post<Field[]>('/fields/reorder', {
    table_id: tableId,
    orders: fieldOrders
  });
};

export const getFieldTypes = async (): Promise<Array<{
  type: FieldType
  name: string
  description: string
}>> => {
  return apiClient.get<Array<{ type: FieldType; name: string; description: string }>>('/fields/types');
};

export const fieldApiService = {
  getFields,
  getField,
  createField,
  updateField,
  deleteField,
  reorderFields,
  getFieldTypes
};

export default fieldApiService;
