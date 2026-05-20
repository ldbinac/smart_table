/**
 * 文档状态管理
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { documentApiService } from '@/services/api/documentApiService';
import { db } from '@/db/schema';
import type { Document, DocumentCreateRequest, DocumentUpdateRequest } from '@/types/document';

export const useDocumentStore = defineStore('document', () => {
  const documents = ref<Document[]>([]);
  const currentDocument = ref<Document | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const documentCount = computed(() => documents.value.length);
  const canCreateMore = computed(() => documents.value.length < 10);
  const currentDocumentId = computed(() => currentDocument.value?.id);

  async function fetchDocuments(baseId: string) {
    loading.value = true;
    error.value = null;
    try {
      const { items } = await documentApiService.getList(baseId);
      documents.value = items;
      await db.documents.bulkPut(items.map(doc => ({
        ...doc,
        createdAt: new Date(doc.createdAt).getTime(),
        updatedAt: new Date(doc.updatedAt).getTime()
      })));
    } catch (e) {
      error.value = e instanceof Error ? e.message : '获取文档失败';
      const cached = await db.documents.where('baseId').equals(baseId).toArray();
      documents.value = cached;
    } finally {
      loading.value = false;
    }
  }

  async function createDocument(baseId: string, data: DocumentCreateRequest) {
    const doc = await documentApiService.create(baseId, data);
    documents.value.push(doc);
    await db.documents.put({
      ...doc,
      createdAt: new Date(doc.createdAt).getTime(),
      updatedAt: new Date(doc.updatedAt).getTime()
    });
    return doc;
  }

  async function updateDocument(docId: string, data: DocumentUpdateRequest) {
    const updated = await documentApiService.update(docId, data);
    const index = documents.value.findIndex(d => d.id === docId);
    if (index !== -1) documents.value[index] = updated;
    if (currentDocument.value?.id === docId) currentDocument.value = updated;
    await db.documents.put({
      ...updated,
      createdAt: new Date(updated.createdAt).getTime(),
      updatedAt: new Date(updated.updatedAt).getTime()
    });
    return updated;
  }

  async function deleteDocument(docId: string) {
    await documentApiService.delete(docId);
    documents.value = documents.value.filter(d => d.id !== docId);
    await db.documents.delete(docId);
  }

  async function fetchDocumentDetail(docId: string) {
    const doc = await documentApiService.getById(docId);
    currentDocument.value = doc;
    return doc;
  }

  async function exportPdf(docId: string, mode: 'frontend' | 'backend' = 'frontend') {
    // 先获取文档内容
    const doc = await documentApiService.getById(docId);
    if (mode === 'frontend') {
      // 前端导出
      const { exportPdfFrontend } = await import('@/utils/export/pdfExport');
      await exportPdfFrontend(doc.name, doc.content);
      return { filename: `${doc.name}.pdf` };
    } else {
      // 后端导出
      try {
        const response = await documentApiService.exportPdf(docId);
        return response;
      } catch {
        // 后端不可用时回退到前端
        const { exportPdfFrontend } = await import('@/utils/export/pdfExport');
        await exportPdfFrontend(doc.name, doc.content);
        return { filename: `${doc.name}.pdf` };
      }
    }
  }

  return {
    documents, currentDocument, loading, error,
    documentCount, canCreateMore, currentDocumentId,
    fetchDocuments, createDocument, updateDocument, deleteDocument, fetchDocumentDetail, exportPdf
  };
});
