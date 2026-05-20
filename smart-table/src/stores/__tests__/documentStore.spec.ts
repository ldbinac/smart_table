/**
 * documentStore 测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useDocumentStore } from '../documentStore';
import { documentApiService } from '@/services/api/documentApiService';

vi.mock('@/services/api/documentApiService');
vi.mock('@/db/schema');

describe('documentStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  const mockDocument = {
    id: 'doc-1',
    baseId: 'base-1',
    name: '测试文档',
    content: '{"ops":[]}',
    contentFormat: 'delta' as const,
    order: 0,
    isPinned: false,
    createdAt: Date.now(),
    updatedAt: Date.now()
  };

  it('should initialize with correct default state', () => {
    const store = useDocumentStore();
    expect(store.documents).toEqual([]);
    expect(store.currentDocument).toBeNull();
    expect(store.loading).toBe(false);
  });

  it('should fetch documents for a base', async () => {
    const store = useDocumentStore();
    (documentApiService.getList as any).mockResolvedValue({
      items: [mockDocument],
      total: 1
    });

    await store.fetchDocuments('base-1');

    expect(documentApiService.getList).toHaveBeenCalledWith('base-1');
    expect(store.documents).toEqual([mockDocument]);
  });

  it('should fetch single document detail', async () => {
    const store = useDocumentStore();
    (documentApiService.getById as any).mockResolvedValue(mockDocument);

    const result = await store.fetchDocumentDetail('doc-1');

    expect(documentApiService.getById).toHaveBeenCalledWith('doc-1');
    expect(store.currentDocument).toEqual(mockDocument);
    expect(result).toEqual(mockDocument);
  });

  it('should create document', async () => {
    const store = useDocumentStore();
    (documentApiService.create as any).mockResolvedValue(mockDocument);

    const result = await store.createDocument('base-1', {
      name: '新文档',
      content: '{"ops":[]}'
    });

    expect(documentApiService.create).toHaveBeenCalledWith('base-1', {
      name: '新文档',
      content: '{"ops":[]}'
    });
    expect(result).toEqual(mockDocument);
    expect(store.documents.length).toBeGreaterThan(0);
  });

  it('should update document', async () => {
    const store = useDocumentStore();
    store.documents = [mockDocument];
    const updatedDoc = { ...mockDocument, name: '更新的文档' };
    (documentApiService.update as any).mockResolvedValue(updatedDoc);

    const result = await store.updateDocument('doc-1', { name: '更新的文档' });

    expect(documentApiService.update).toHaveBeenCalledWith('doc-1', { name: '更新的文档' });
    expect(result).toEqual(updatedDoc);
  });
});
