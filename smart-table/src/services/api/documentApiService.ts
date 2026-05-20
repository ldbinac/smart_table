/**
 * 文档 API 服务
 */
import { apiClient } from '@/api/client';
import type { Document, DocumentCreateRequest, DocumentUpdateRequest } from '@/types/document';

export const documentApiService = {
  async getList(baseId: string): Promise<{ items: Document[]; total: number }> {
    return apiClient.get(`/bases/${baseId}/documents`);
  },

  async create(baseId: string, data: DocumentCreateRequest): Promise<Document> {
    return apiClient.post(`/bases/${baseId}/documents`, data);
  },

  async getById(docId: string): Promise<Document> {
    return apiClient.get(`/documents/${docId}`);
  },

  async update(docId: string, data: DocumentUpdateRequest): Promise<Document> {
    return apiClient.put(`/documents/${docId}`, data);
  },

  async delete(docId: string): Promise<void> {
    return apiClient.delete(`/documents/${docId}`);
  },

  async exportPdf(docId: string, exportType: 'frontend' | 'backend' = 'backend'): Promise<{ downloadUrl: string; filename: string }> {
    return apiClient.post(`/documents/${docId}/export-pdf`, { export_type: exportType });
  }
};
