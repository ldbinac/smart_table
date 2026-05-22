/**
 * 文档版本历史 API 服务
 */
import { apiClient } from '@/api/client';
import type { DocumentVersion, DocumentVersionListResponse } from '@/types/documentVersion';

function snakeToCamel(obj: Record<string, any>): Record<string, any> {
  if (Array.isArray(obj)) {
    return obj.map(snakeToCamel);
  }
  if (obj !== null && typeof obj === 'object') {
    return Object.keys(obj).reduce((acc, key) => {
      const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
      acc[camelKey] = snakeToCamel(obj[key]);
      return acc;
    }, {} as Record<string, any>);
  }
  return obj;
}

export const documentVersionApiService = {
  async getList(docId: string): Promise<DocumentVersionListResponse> {
    const response = await apiClient.get<{ items: any[]; total: number }>(`/documents/${docId}/versions`);
    return {
      items: response.items.map(snakeToCamel),
      total: response.total
    };
  },

  async getById(docId: string, versionId: string): Promise<DocumentVersion> {
    const response = await apiClient.get<any>(`/documents/${docId}/versions/${versionId}`);
    return snakeToCamel(response);
  },

  async restore(docId: string, versionId: string): Promise<{ document: unknown; version: DocumentVersion }> {
    const response = await apiClient.post<{ document: unknown; version: any }>(`/documents/${docId}/versions/${versionId}/restore`);
    return {
      document: response.document,
      version: snakeToCamel(response.version)
    };
  },

  async delete(docId: string, versionId: string): Promise<void> {
    return apiClient.delete(`/documents/${docId}/versions/${versionId}`);
  }
};
