/**
 * Field API 服务
 */
import { apiClient } from '@/api/client';
import type { Field, FieldType } from '@/api/types';
import type { ConvertibleTypeItem, ConvertibleTypesResult } from '@/types/fields';

export const getFields = async (tableId: string, shareToken?: string): Promise<Field[]> => {
  const params = shareToken ? { share_token: shareToken } : undefined;
  return apiClient.get<Field[]>(`/tables/${tableId}/fields`, params);
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

/**
 * 获取字段可转换的目标类型清单
 * 用于字段配置面板启用/禁用类型选项，并提示有损转换与影响告知
 */
export const getConvertibleTypes = async (id: string): Promise<ConvertibleTypesResult> => {
  return apiClient.get<ConvertibleTypesResult>(`/fields/${id}/convertible-types`);
};

export const fieldApiService = {
  getFields,
  getField,
  createField,
  updateField,
  deleteField,
  reorderFields,
  getFieldTypes,
  getConvertibleTypes
};

export default fieldApiService;
