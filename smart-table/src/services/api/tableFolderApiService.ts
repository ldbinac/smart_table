/**
 * Table Folder API 服务（数据表文件夹）
 */
import { apiClient } from '@/api/client';

export interface TableFolderData {
  id: string;
  base_id: string;
  name: string;
  order: number;
  created_at: string;
  updated_at: string;
}

export const getTableFolders = async (baseId: string): Promise<TableFolderData[]> => {
  return apiClient.get<TableFolderData[]>(`/bases/${baseId}/table-folders`);
};

export const createTableFolder = async (
  baseId: string,
  data: { name: string }
): Promise<TableFolderData> => {
  return apiClient.post<TableFolderData>(`/bases/${baseId}/table-folders`, data);
};

export const updateTableFolder = async (
  id: string,
  data: { name?: string; order?: number }
): Promise<TableFolderData> => {
  return apiClient.put<TableFolderData>(`/table-folders/${id}`, data);
};

export const deleteTableFolder = async (id: string): Promise<void> => {
  await apiClient.delete<void>(`/table-folders/${id}`);
};

export const tableFolderApiService = {
  getTableFolders,
  createTableFolder,
  updateTableFolder,
  deleteTableFolder,
};

export default tableFolderApiService;
