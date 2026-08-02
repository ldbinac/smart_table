/**
 * useMasterDetail 组合式函数测试
 * 验证 LINK 字段检测、插件实例创建、字段切换、状态清理等核心逻辑
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { FieldType } from '@/types/fields';

// mock masterDetailService
vi.mock('@/services/masterDetailService', () => ({
  masterDetailService: {
    getLinkedRecordsDetail: vi.fn(),
    createAndLinkRecord: vi.fn(),
    buildSubTableColumns: vi.fn(() => []),
    getTargetTableFields: vi.fn(),
    fieldDefinitionCache: {
      get: vi.fn(),
      set: vi.fn(),
      invalidate: vi.fn(),
      clear: vi.fn(),
    },
  },
}));

// mock linkApiService
vi.mock('@/services/api/linkApiService', () => ({
  linkApiService: {
    invalidateCacheByPattern: vi.fn(),
  },
}));

// mock vtable-plugins
vi.mock('@visactor/vtable-plugins', () => ({
  MasterDetailPlugin: vi.fn().mockImplementation(() => ({
    setRecordChildren: vi.fn(),
    name: 'Master Detail Plugin',
  })),
}));

import { useMasterDetail } from '@/composables/useMasterDetail';
import { masterDetailService } from '@/services/masterDetailService';
import { MasterDetailPlugin } from '@visactor/vtable-plugins';

describe('useMasterDetail', () => {
  let composable: ReturnType<typeof useMasterDetail>;

  beforeEach(() => {
    vi.clearAllMocks();
    composable = useMasterDetail({ readonly: false });
  });

  describe('detectLinkFields', () => {
    it('正确检测 LINK 类型字段', () => {
      const fields = [
        { id: 'f1', name: '名称', type: FieldType.SINGLE_LINE_TEXT },
        {
          id: 'f2',
          name: '关联项目',
          type: FieldType.LINK,
          options: {
            linkedTableId: 'tbl-proj',
            relationshipType: 'many_to_many',
          },
        },
      ];

      composable.detectLinkFields(fields);

      expect(composable.linkFields.value).toHaveLength(1);
      expect(composable.linkFields.value[0]).toEqual({
        fieldId: 'f2',
        fieldName: '关联项目',
        targetTableId: 'tbl-proj',
        relationshipType: 'many_to_many',
      });
      // 首次自动选中第一个 LINK 字段
      expect(composable.currentLinkFieldId.value).toBe('f2');
    });

    it('过滤掉没有 targetTableId 的字段', () => {
      const fields = [
        {
          id: 'f1',
          name: '关联无目标',
          type: FieldType.LINK,
          options: {},
        },
        {
          id: 'f2',
          name: '关联有目标',
          type: FieldType.LINK,
          options: { linkedTableId: 'tbl-2' },
        },
      ];

      composable.detectLinkFields(fields);

      expect(composable.linkFields.value).toHaveLength(1);
      expect(composable.linkFields.value[0].fieldId).toBe('f2');
      expect(composable.linkFields.value[0].targetTableId).toBe('tbl-2');
    });

    it('无 LINK 字段时 linkFields 为空', () => {
      const fields = [
        { id: 'f1', name: '名称', type: FieldType.SINGLE_LINE_TEXT },
        { id: 'f2', name: '数量', type: FieldType.NUMBER },
      ];

      composable.detectLinkFields(fields);

      expect(composable.linkFields.value).toHaveLength(0);
      expect(composable.currentLinkFieldId.value).toBeNull();
    });
  });

  describe('hasLinkFields', () => {
    it('在有 LINK 字段时为 true', () => {
      composable.detectLinkFields([
        {
          id: 'f1',
          name: '关联',
          type: FieldType.LINK,
          options: { linkedTableId: 'tbl-1' },
        },
      ]);
      expect(composable.hasLinkFields.value).toBe(true);
    });

    it('在无 LINK 字段时为 false', () => {
      composable.detectLinkFields([
        { id: 'f1', name: '名称', type: FieldType.SINGLE_LINE_TEXT },
      ]);
      expect(composable.hasLinkFields.value).toBe(false);
    });
  });

  describe('hasMultipleLinkFields', () => {
    it('在有 2+ LINK 字段时为 true', () => {
      composable.detectLinkFields([
        {
          id: 'f1',
          name: '关联1',
          type: FieldType.LINK,
          options: { linkedTableId: 'tbl-1' },
        },
        {
          id: 'f2',
          name: '关联2',
          type: FieldType.LINK,
          options: { linkedTableId: 'tbl-2' },
        },
      ]);
      expect(composable.hasMultipleLinkFields.value).toBe(true);
    });

    it('在有 1 个 LINK 字段时为 false', () => {
      composable.detectLinkFields([
        {
          id: 'f1',
          name: '关联1',
          type: FieldType.LINK,
          options: { linkedTableId: 'tbl-1' },
        },
      ]);
      expect(composable.hasMultipleLinkFields.value).toBe(false);
    });
  });

  describe('createPluginInstance', () => {
    it('在无 LINK 字段时返回 null', () => {
      composable.detectLinkFields([
        { id: 'f1', name: '名称', type: FieldType.SINGLE_LINE_TEXT },
      ]);

      const plugin = composable.createPluginInstance();

      expect(plugin).toBeNull();
      expect(MasterDetailPlugin).not.toHaveBeenCalled();
    });

    it('在有 LINK 字段时返回插件实例', () => {
      composable.detectLinkFields([
        {
          id: 'f1',
          name: '关联',
          type: FieldType.LINK,
          options: { linkedTableId: 'tbl-1' },
        },
      ]);

      const plugin = composable.createPluginInstance();

      expect(plugin).not.toBeNull();
      expect(MasterDetailPlugin).toHaveBeenCalledTimes(1);
      // 插件实例应被保存到响应式状态
      expect(composable.masterDetailPlugin.value).not.toBeNull();
    });
  });

  describe('switchLinkField', () => {
    it('切换当前字段', async () => {
      vi.mocked(masterDetailService.getTargetTableFields).mockResolvedValue([]);

      composable.detectLinkFields([
        {
          id: 'f1',
          name: '关联1',
          type: FieldType.LINK,
          options: { linkedTableId: 'tbl-1' },
        },
        {
          id: 'f2',
          name: '关联2',
          type: FieldType.LINK,
          options: { linkedTableId: 'tbl-2' },
        },
      ]);

      // 初始选中第一个字段
      expect(composable.currentLinkFieldId.value).toBe('f1');

      // 切换到第二个字段
      await composable.switchLinkField('f2');

      expect(composable.currentLinkFieldId.value).toBe('f2');
      // preloadColumns 应请求新字段对应目标表的字段定义
      expect(masterDetailService.getTargetTableFields).toHaveBeenCalledWith(
        'tbl-2'
      );
      expect(masterDetailService.buildSubTableColumns).toHaveBeenCalled();
    });
  });

  describe('dispose', () => {
    it('清理所有状态', () => {
      // 先填充状态
      composable.detectLinkFields([
        {
          id: 'f1',
          name: '关联',
          type: FieldType.LINK,
          options: { linkedTableId: 'tbl-1' },
        },
      ]);
      composable.createPluginInstance();

      // 验证状态已填充
      expect(composable.linkFields.value).toHaveLength(1);
      expect(composable.masterDetailPlugin.value).not.toBeNull();
      expect(composable.currentLinkFieldId.value).toBe('f1');

      // 执行清理
      composable.dispose();

      // 验证所有状态已清空
      expect(composable.linkFields.value).toHaveLength(0);
      expect(composable.masterDetailPlugin.value).toBeNull();
      expect(composable.currentLinkFieldId.value).toBeNull();
    });
  });
});
