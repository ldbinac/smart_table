/**
 * 文档 API 服务
 */
import { apiClient } from '@/api/client';
import type { Document, DocumentCreateRequest, DocumentUpdateRequest } from '@/types/document';

function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

function convertSnakeToCamel<T>(obj: object): T {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    const camelKey = snakeToCamel(key);
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      result[camelKey] = convertSnakeToCamel(value as Record<string, unknown>);
    } else if (Array.isArray(value)) {
      result[camelKey] = value.map((item: unknown) => 
        item && typeof item === 'object' ? convertSnakeToCamel(item as Record<string, unknown>) : item
      );
    } else {
      result[camelKey] = value;
    }
  }
  return result as T;
}

export const documentApiService = {
  async getList(baseId: string): Promise<{ items: Document[]; total: number }> {
    const result = await apiClient.get<{ items: Record<string, unknown>[]; total: number }>(
      `/bases/${baseId}/documents`
    );
    return {
      ...result,
      items: result.items.map(item => convertSnakeToCamel<Document>(item)),
    };
  },

  async create(baseId: string, data: DocumentCreateRequest): Promise<Document> {
    const result = await apiClient.post<Record<string, unknown>>(
      `/bases/${baseId}/documents`,
      data
    );
    return convertSnakeToCamel<Document>(result);
  },

  async getById(docId: string): Promise<Document> {
    const result = await apiClient.get<Record<string, unknown>>(`/documents/${docId}`);
    return convertSnakeToCamel<Document>(result);
  },

  async update(docId: string, data: DocumentUpdateRequest): Promise<Document> {
    const result = await apiClient.put<Record<string, unknown>>(`/documents/${docId}`, data);
    return convertSnakeToCamel<Document>(result);
  },

  async delete(docId: string): Promise<void> {
    return apiClient.delete(`/documents/${docId}`);
  },

  async exportPdf(docId: string, exportType: 'frontend' | 'backend' = 'backend'): Promise<{ downloadUrl: string; filename: string }> {
    return apiClient.post(`/documents/${docId}/export-pdf`, { export_type: exportType });
  }
};
