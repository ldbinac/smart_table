/**
 * lookupApiService 单元测试
 *
 * 验证三个 API 方法调用正确的 URL、HTTP 方法与请求体。
 * apiClient 已统一封装响应解包，这里仅校验调用参数。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  createLookupField,
  updateLookupField,
  previewLookupValue,
  lookupApiService,
} from '../lookupApiService';
import { apiClient } from '@/api/client';
import type { LookupFieldConfig } from '@/types/fields';

// mock apiClient，避免真实网络请求
vi.mock('@/api/client', () => ({
  apiClient: {
    post: vi.fn(),
    put: vi.fn(),
    get: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn(),
  },
}));

function buildConfig(override: Partial<LookupFieldConfig> = {}): LookupFieldConfig {
  return {
    sourceTableId: 'src-table-1',
    targetFieldId: 'src-field-1',
    filterConditions: [],
    filterConjunction: 'and',
    aggregationType: 'sum',
    fieldFormat: { type: 'number' },
    ...override,
  };
}

describe('lookupApiService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('createLookupField', () => {
    it('应调用 POST /tables/{tableId}/fields/lookup', async () => {
      const mockResponse = { id: 'field-1', table_id: 'table-1', name: '查找1', type: 'lookup' };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse as any);

      const config = buildConfig();
      const result = await createLookupField('table-1', {
        name: '查找1',
        config,
      });

      expect(apiClient.post).toHaveBeenCalledWith(
        '/tables/table-1/fields/lookup',
        { name: '查找1', config },
      );
      expect(apiClient.post).toHaveBeenCalledTimes(1);
      expect(result).toEqual(mockResponse);
    });

    it('应支持 description 字段', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ id: 'field-1' } as any);

      const config = buildConfig();
      await createLookupField('table-1', {
        name: '查找字段',
        description: '描述信息',
        config,
      });

      expect(apiClient.post).toHaveBeenCalledWith(
        '/tables/table-1/fields/lookup',
        { name: '查找字段', description: '描述信息', config },
      );
    });

    it('应将不同 tableId 拼入 URL', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ id: 'field-2' } as any);
      await createLookupField('tbl-abc', { name: '查找2', config: buildConfig() });

      expect(apiClient.post).toHaveBeenCalledWith(
        '/tables/tbl-abc/fields/lookup',
        expect.objectContaining({ name: '查找2' }),
      );
    });
  });

  describe('updateLookupField', () => {
    it('应调用 PUT /fields/{fieldId}/lookup', async () => {
      const mockResponse = { id: 'field-1', name: '更新后', type: 'lookup' };
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse as any);

      const config = buildConfig({ aggregationType: 'count' });
      const result = await updateLookupField('field-1', {
        name: '更新后',
        config,
      });

      expect(apiClient.put).toHaveBeenCalledWith('/fields/field-1/lookup', {
        name: '更新后',
        config,
      });
      expect(apiClient.put).toHaveBeenCalledTimes(1);
      expect(result).toEqual(mockResponse);
    });

    it('应支持仅传 config 不传 name', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({ id: 'field-1' } as any);

      const config = buildConfig();
      await updateLookupField('field-1', { config });

      expect(apiClient.put).toHaveBeenCalledWith('/fields/field-1/lookup', {
        config,
      });
    });

    it('应将不同 fieldId 拼入 URL', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({ id: 'fld-xyz' } as any);
      await updateLookupField('fld-xyz', { config: buildConfig() });

      expect(apiClient.put).toHaveBeenCalledWith(
        '/fields/fld-xyz/lookup',
        expect.objectContaining({ config: expect.any(Object) }),
      );
    });
  });

  describe('previewLookupValue', () => {
    it('应调用 POST /fields/{fieldId}/lookup/preview', async () => {
      const mockResponse = { value: [1, 2, 3] };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse as any);

      const result = await previewLookupValue('field-1', {
        record_id: 'record-1',
      });

      expect(apiClient.post).toHaveBeenCalledWith(
        '/fields/field-1/lookup/preview',
        { record_id: 'record-1' },
      );
      expect(apiClient.post).toHaveBeenCalledTimes(1);
      expect(result).toEqual(mockResponse);
    });

    it('应支持附带 config 进行预览', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ value: 60 } as any);

      const config = buildConfig({ aggregationType: 'sum' });
      await previewLookupValue('field-1', {
        record_id: 'rec-1',
        config,
      });

      expect(apiClient.post).toHaveBeenCalledWith(
        '/fields/field-1/lookup/preview',
        { record_id: 'rec-1', config },
      );
    });

    it('应将不同 fieldId 拼入 URL', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ value: null } as any);
      await previewLookupValue('fld-preview', { record_id: 'r1' });

      expect(apiClient.post).toHaveBeenCalledWith(
        '/fields/fld-preview/lookup/preview',
        { record_id: 'r1' },
      );
    });
  });

  describe('lookupApiService 聚合对象', () => {
    it('应导出三个方法', () => {
      expect(typeof lookupApiService.createLookupField).toBe('function');
      expect(typeof lookupApiService.updateLookupField).toBe('function');
      expect(typeof lookupApiService.previewLookupValue).toBe('function');
    });

    it('通过聚合对象调用 createLookupField 应走相同路径', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ id: 'f1' } as any);
      await lookupApiService.createLookupField('t1', {
        name: 'n',
        config: buildConfig(),
      });
      expect(apiClient.post).toHaveBeenCalledWith(
        '/tables/t1/fields/lookup',
        expect.objectContaining({ name: 'n' }),
      );
    });
  });
});
