/**
 * Field API 服务
 */
import { apiClient } from '@/api/client';
import type { Field, FieldType, FieldPermissionResponse, FieldPermissionUpdateRequest } from '@/api/types';
import type { FieldPermissionConfig } from '@/types/fields';

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

/**
 * 获取当前用户在表中所有字段的权限
 * GET /tables/${tableId}/field-permissions
 */
export const getFieldPermissions = async (tableId: string): Promise<FieldPermissionResponse> => {
  return apiClient.get<FieldPermissionResponse>(`/tables/${tableId}/field-permissions`);
};

/**
 * 更新字段权限配置（仅 admin/owner 可调用）
 * PUT /fields/${fieldId}/permissions
 */
export const updateFieldPermissions = async (
  fieldId: string,
  permissions: FieldPermissionConfig
): Promise<{ permissions: FieldPermissionConfig }> => {
  return apiClient.put<{ permissions: FieldPermissionConfig }>(
    `/fields/${fieldId}/permissions`,
    { permissions } as FieldPermissionUpdateRequest
  );
};

export const fieldApiService = {
  getFields,
  getField,
  createField,
  updateField,
  deleteField,
  reorderFields,
  getFieldTypes,
  getFieldPermissions,
  updateFieldPermissions
};

export default fieldApiService;
