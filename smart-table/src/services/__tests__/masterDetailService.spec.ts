/**
 * masterDetailService 集成测试
 * 验证主从表数据服务的核心方法：API 调用、列配置构建、字段定义缓存
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { FieldType } from '@/types/fields';

// mock apiClient
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

// mock fieldService
vi.mock('@/db/services/fieldService', () => ({
  fieldService: {
    getFieldsByTable: vi.fn(),
  },
}));

// mock timezone 工具，避免依赖 pinia/adminStore
vi.mock('@/utils/timezone', () => ({
  formatDate: vi.fn((value: string | number) => `formatted-date:${value}`),
  formatDateTime: vi.fn((value: string | number) => `formatted-datetime:${value}`),
}));

import { apiClient } from '@/api/client';
import { fieldService } from '@/db/services/fieldService';
import {
  masterDetailService,
  buildSubTableColumns,
} from '@/services/masterDetailService';

describe('masterDetailService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // 清理字段定义缓存，避免测试间相互影响
    masterDetailService.fieldDefinitionCache.clear();
  });

  describe('getLinkedRecordsDetail', () => {
    it('正确调用 API 并返回数据', async () => {
      const mockResponse = {
        records: [
          {
            id: 'r1',
            values: { name: '测试记录' },
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-02T00:00:00Z',
          },
        ],
        fields: [{ id: 'f-target', name: '名称', type: 'single_line_text' }],
        total: 1,
        page: 1,
        per_page: 20,
        link_relation: {
          id: 'lr-1',
          source_table_id: 'tbl-src',
          target_table_id: 'tbl-target',
          source_field_id: 'f-link',
          target_field_id: null,
          relationship_type: 'one_to_many' as const,
          bidirectional: false,
        },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await masterDetailService.getLinkedRecordsDetail(
        'rec-1',
        'f-link'
      );

      expect(apiClient.get).toHaveBeenCalledWith(
        '/records/rec-1/links/f-link/details',
        {}
      );
      expect(result).toEqual(mockResponse);
      expect(result.records).toHaveLength(1);
      expect(result.records[0].id).toBe('r1');
    });

    it('支持分页和关键字参数', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        records: [],
        fields: [],
        total: 0,
        page: 2,
        per_page: 50,
        link_relation: {} as never,
      });

      await masterDetailService.getLinkedRecordsDetail('rec-1', 'f-link', {
        page: 2,
        per_page: 50,
        keyword: '搜索词',
      });

      expect(apiClient.get).toHaveBeenCalledWith(
        '/records/rec-1/links/f-link/details',
        { page: 2, per_page: 50, keyword: '搜索词' }
      );
    });
  });

  describe('createAndLinkRecord', () => {
    it('正确调用 API', async () => {
      const mockResponse = {
        record: {
          id: 'r-new',
          values: { name: '新记录' },
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
        link_value: {
          id: 'lv-1',
          link_relation_id: 'lr-1',
          source_record_id: 'rec-1',
          target_record_id: 'r-new',
        },
      };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const values = { name: '新记录', status: 'active' };
      const result = await masterDetailService.createAndLinkRecord(
        'rec-1',
        'f-link',
        values
      );

      expect(apiClient.post).toHaveBeenCalledWith(
        '/records/rec-1/links/f-link/records',
        { values }
      );
      expect(result).toEqual(mockResponse);
      expect(result.record.id).toBe('r-new');
      expect(result.link_value.target_record_id).toBe('r-new');
    });
  });

  describe('buildSubTableColumns', () => {
    it('对文本字段生成正确的列配置', () => {
      const fields = [
        {
          id: 'f-text',
          name: '名称',
          type: FieldType.SINGLE_LINE_TEXT,
        },
      ];

      const columns = buildSubTableColumns(fields);

      expect(columns).toHaveLength(1);
      expect(columns[0].field).toBe('f-text');
      expect(columns[0].title).toBe('名称');
      expect(columns[0].width).toBe(150);
      expect(columns[0].cellType).toBe('text');
      // 文本字段不应生成 fieldFormat
      expect(columns[0].fieldFormat).toBeUndefined();
    });

    it('对数字字段生成带 fieldFormat 的列配置', () => {
      const fields = [
        {
          id: 'f-num',
          name: '金额',
          type: FieldType.NUMBER,
          options: { precision: 2, prefix: '$', suffix: '' },
        },
      ];

      const columns = buildSubTableColumns(fields);

      expect(columns[0].fieldFormat).toBeDefined();
      expect(typeof columns[0].fieldFormat).toBe('function');

      const format = columns[0].fieldFormat;
      // 正常数值格式化：保留两位小数 + 前缀
      expect(format({ 'f-num': 123.456 })).toBe('$123.46');
      // 空值返回空字符串
      expect(format({ 'f-num': null })).toBe('');
      expect(format({ 'f-num': undefined })).toBe('');
      expect(format({ 'f-num': '' })).toBe('');
      // 非数字返回原始字符串
      expect(format({ 'f-num': 'abc' })).toBe('abc');
    });

    it('对日期字段生成带 fieldFormat 的列配置', () => {
      const fields = [
        { id: 'f-date', name: '创建日期', type: FieldType.DATE },
        { id: 'f-datetime', name: '更新时间', type: FieldType.DATE_TIME },
      ];

      const columns = buildSubTableColumns(fields);

      // DATE 字段
      expect(columns[0].fieldFormat).toBeDefined();
      expect(typeof columns[0].fieldFormat).toBe('function');
      const dateFormat = columns[0].fieldFormat;
      expect(dateFormat({ 'f-date': '2026-01-15' })).toBe(
        'formatted-date:2026-01-15'
      );
      expect(dateFormat({ 'f-date': null })).toBe('');
      expect(dateFormat({ 'f-date': '' })).toBe('');

      // DATE_TIME 字段
      expect(columns[1].fieldFormat).toBeDefined();
      const dateTimeFormat = columns[1].fieldFormat;
      expect(dateTimeFormat({ 'f-datetime': '2026-01-15 10:30:00' })).toBe(
        'formatted-datetime:2026-01-15 10:30:00'
      );
    });

    it('对 LINK 字段生成"关联 N 条"格式化', () => {
      const fields = [
        { id: 'f-link', name: '关联项目', type: FieldType.LINK },
      ];

      const columns = buildSubTableColumns(fields);

      expect(columns[0].fieldFormat).toBeDefined();
      const format = columns[0].fieldFormat;
      // 数组显示"关联 N 条"
      expect(format({ 'f-link': ['r1', 'r2', 'r3'] })).toBe('关联 3 条');
      expect(format({ 'f-link': ['r1'] })).toBe('关联 1 条');
      // 空数组返回空字符串
      expect(format({ 'f-link': [] })).toBe('');
      // null/undefined 返回空字符串
      expect(format({ 'f-link': null })).toBe('');
      expect(format({ 'f-link': undefined })).toBe('');
    });

    it('对空字段数组返回空数组', () => {
      const columns = buildSubTableColumns([]);
      expect(columns).toEqual([]);
    });
  });

  describe('getTargetTableFields', () => {
    it('从缓存获取数据（不重复请求）', async () => {
      const mockFields = [
        { id: 'f1', name: '字段1', type: FieldType.SINGLE_LINE_TEXT },
        { id: 'f2', name: '字段2', type: FieldType.NUMBER },
      ];
      vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockFields as any);

      // 第一次调用 - 应请求 fieldService 并缓存
      const result1 = await masterDetailService.getTargetTableFields('tbl-1');
      expect(result1).toEqual(mockFields);
      expect(fieldService.getFieldsByTable).toHaveBeenCalledTimes(1);
      expect(fieldService.getFieldsByTable).toHaveBeenCalledWith('tbl-1');

      // 第二次调用 - 应从缓存获取，不重复请求
      const result2 = await masterDetailService.getTargetTableFields('tbl-1');
      expect(result2).toEqual(mockFields);
      expect(fieldService.getFieldsByTable).toHaveBeenCalledTimes(1);
    });

    it('缓存失效后重新请求', async () => {
      const mockFields1 = [
        { id: 'f1', name: '字段1', type: FieldType.SINGLE_LINE_TEXT },
      ];
      const mockFields2 = [
        { id: 'f2', name: '字段2', type: FieldType.NUMBER },
      ];
      vi.mocked(fieldService.getFieldsByTable)
        .mockResolvedValueOnce(mockFields1 as any)
        .mockResolvedValueOnce(mockFields2 as any);

      // 第一次调用
      const result1 = await masterDetailService.getTargetTableFields('tbl-2');
      expect(result1).toEqual(mockFields1);
      expect(fieldService.getFieldsByTable).toHaveBeenCalledTimes(1);

      // 失效缓存
      masterDetailService.fieldDefinitionCache.invalidate('tbl-2');

      // 第二次调用 - 缓存已失效，应重新请求
      const result2 = await masterDetailService.getTargetTableFields('tbl-2');
      expect(result2).toEqual(mockFields2);
      expect(fieldService.getFieldsByTable).toHaveBeenCalledTimes(2);
    });
  });
});
