/**
 * 文档状态管理
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { documentApiService } from '@/services/api/documentApiService';
import { db } from '@/db/schema';
import type { Document, DocumentCreateRequest, DocumentUpdateRequest } from '@/types/document';

function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

function convertSnakeToCamel<T extends Record<string, unknown>>(obj: Record<string, unknown>): T {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    const camelKey = snakeToCamel(key);
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      result[camelKey] = convertSnakeToCamel(value as Record<string, unknown>);
    } else {
      result[camelKey] = value;
    }
  }
  return result as T;
}

export const useDocumentStore = defineStore('document', () => {
  const documents = ref<Document[]>([]);
  const currentDocument = ref<Document | null>(null);
  const loading = ref(false); // 文档列表加载状态
  const loadingDocumentDetail = ref(false); // 单个文档详情加载状态
  const error = ref<string | null>(null);
  const lastLoadedBaseId = ref<string | null>(null); // 记录最后加载的 baseId，防止重复调用

  const documentCount = computed(() => documents.value.length);
  const canCreateMore = computed(() => documents.value.length < 10);
  const currentDocumentId = computed(() => currentDocument.value?.id);

  async function fetchDocuments(baseId: string, force = false) {
    // 如果正在加载，或者已经加载过相同的 baseId 且不是强制刷新，跳过重复请求
    if (loading.value || (!force && lastLoadedBaseId.value === baseId)) {
      return;
    }
    
    loading.value = true;
    error.value = null;
    try {
      const { items } = await documentApiService.getList(baseId);
      documents.value = items.map(item => convertSnakeToCamel<Document>(item));
      lastLoadedBaseId.value = baseId; // 更新最后加载的 baseId
      await db.documents.bulkPut(documents.value.map(doc => ({
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
    const convertedDoc = convertSnakeToCamel<Document>(doc);
    documents.value.push(convertedDoc);
    currentDocument.value = convertedDoc;
    await db.documents.put({
      ...convertedDoc,
      createdAt: new Date(convertedDoc.createdAt).getTime(),
      updatedAt: new Date(convertedDoc.updatedAt).getTime()
    });
    return convertedDoc;
  }

  async function updateDocument(docId: string, data: DocumentUpdateRequest) {
    const updated = await documentApiService.update(docId, data);
    const convertedUpdated = convertSnakeToCamel<Document>(updated);
    const index = documents.value.findIndex(d => d.id === docId);
    if (index !== -1) documents.value[index] = convertedUpdated;
    if (currentDocument.value?.id === docId) currentDocument.value = convertedUpdated;
    await db.documents.put({
      ...convertedUpdated,
      createdAt: new Date(convertedUpdated.createdAt).getTime(),
      updatedAt: new Date(convertedUpdated.updatedAt).getTime()
    });
    return convertedUpdated;
  }

  async function deleteDocument(docId: string) {
    await documentApiService.delete(docId);
    documents.value = documents.value.filter(d => d.id !== docId);
    await db.documents.delete(docId);
  }

  async function fetchDocumentDetail(docId: string) {
    loadingDocumentDetail.value = true;
    try {
      const doc = await documentApiService.getById(docId);
      const convertedDoc = convertSnakeToCamel<Document>(doc);
      currentDocument.value = convertedDoc;
      return convertedDoc;
    } finally {
      loadingDocumentDetail.value = false;
    }
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
    documents, currentDocument, loading, loadingDocumentDetail, error,
    documentCount, canCreateMore, currentDocumentId,
    fetchDocuments, createDocument, updateDocument, deleteDocument, fetchDocumentDetail, exportPdf
  };
});
