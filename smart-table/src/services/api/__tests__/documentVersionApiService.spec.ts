/**
 * documentVersionApiService 测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { documentVersionApiService } from '../documentVersionApiService';
import { apiClient } from '@/api/client';

vi.mock('@/api/client');

describe('documentVersionApiService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockVersionsRaw = [
    {
      id: 'v1',
      document_id: 'doc-1',
      name: '版本 1',
      content: '{"ops":[{"insert":"test"}]}',
      content_format: 'delta',
      version_number: 1,
      change_summary: '创建文档',
      created_by: 'user-1',
      created_at: new Date().toISOString()
    }
  ];

  const mockVersionsCamel = [
    {
      id: 'v1',
      documentId: 'doc-1',
      name: '版本 1',
      content: '{"ops":[{"insert":"test"}]}',
      contentFormat: 'delta',
      versionNumber: 1,
      changeSummary: '创建文档',
      createdBy: 'user-1',
      createdAt: mockVersionsRaw[0].created_at
    }
  ];

  it('should fetch versions list for a document', async () => {
    (apiClient.get as any).mockResolvedValue({ items: mockVersionsRaw, total: 1 });
    const result = await documentVersionApiService.getList('doc-1');
    expect(apiClient.get).toHaveBeenCalledWith('/documents/doc-1/versions');
    expect(result).toEqual({ items: mockVersionsCamel, total: 1 });
  });

  it('should get a specific version by id', async () => {
    (apiClient.get as any).mockResolvedValue(mockVersionsRaw[0]);
    const result = await documentVersionApiService.getById('doc-1', 'v1');
    expect(apiClient.get).toHaveBeenCalledWith('/documents/doc-1/versions/v1');
    expect(result).toEqual(mockVersionsCamel[0]);
  });

  it('should restore a version', async () => {
    const restoreResponseRaw = { document: { id: 'doc-1' }, version: mockVersionsRaw[0] };
    const restoreResponseExpected = { document: { id: 'doc-1' }, version: mockVersionsCamel[0] };
    (apiClient.post as any).mockResolvedValue(restoreResponseRaw);
    const result = await documentVersionApiService.restore('doc-1', 'v1');
    expect(apiClient.post).toHaveBeenCalledWith('/documents/doc-1/versions/v1/restore');
    expect(result).toEqual(restoreResponseExpected);
  });

  it('should delete a version', async () => {
    (apiClient.delete as any).mockResolvedValue(undefined);
    await documentVersionApiService.delete('doc-1', 'v1');
    expect(apiClient.delete).toHaveBeenCalledWith('/documents/doc-1/versions/v1');
  });
});
