/**
 * 文档版本历史 API 服务
 */
import { apiClient } from '@/api/client';
import type { DocumentVersion, DocumentVersionListResponse } from '@/types/documentVersion';

export const documentVersionApiService = {
  async getList(docId: string): Promise<DocumentVersionListResponse> {
    return apiClient.get<DocumentVersionListResponse>(`/documents/${docId}/versions`);
  },

  async getById(docId: string, versionId: string): Promise<DocumentVersion> {
    return apiClient.get<DocumentVersion>(`/documents/${docId}/versions/${versionId}`);
  },

  async restore(docId: string, versionId: string): Promise<{ document: unknown; version: DocumentVersion }> {
    return apiClient.post(`/documents/${docId}/versions/${versionId}/restore`);
  },

  async delete(docId: string, versionId: string): Promise<void> {
    return apiClient.delete(`/documents/${docId}/versions/${versionId}`);
  }
};
