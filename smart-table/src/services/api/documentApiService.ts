/**
 * 文档 API 服务
 */
import axios from 'axios';
import type { Document, DocumentCreateRequest, DocumentUpdateRequest } from '@/types/document';

const API_BASE = '/api';

export const documentApiService = {
  async getList(baseId: string): Promise<{ items: Document[]; total: number }> {
    const res = await axios.get(`${API_BASE}/bases/${baseId}/documents`);
    return res.data.data;
  },

  async create(baseId: string, data: DocumentCreateRequest): Promise<Document> {
    const res = await axios.post(`${API_BASE}/bases/${baseId}/documents`, data);
    return res.data.data;
  },

  async getById(docId: string): Promise<Document> {
    const res = await axios.get(`${API_BASE}/documents/${docId}`);
    return res.data.data;
  },

  async update(docId: string, data: DocumentUpdateRequest): Promise<Document> {
    const res = await axios.put(`${API_BASE}/documents/${docId}`, data);
    return res.data.data;
  },

  async delete(docId: string): Promise<void> {
    await axios.delete(`${API_BASE}/documents/${docId}`);
  },

  async exportPdf(docId: string, exportType: 'frontend' | 'backend' = 'backend'): Promise<{ downloadUrl: string; filename: string }> {
    const res = await axios.post(`${API_BASE}/documents/${docId}/export-pdf`, { export_type: exportType });
    return res.data.data;
  }
};
