/**
 * LookupField 组件测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { nextTick } from 'vue';
import LookupField from '../LookupField.vue';
import type { FieldEntity } from '@/db/schema';
import type { LookupFieldConfig } from '@/types/fields';

// mock fieldService，避免触发真实的 IndexedDB / API 调用
vi.mock('@/db/services/fieldService', () => ({
  fieldService: {
    getFieldsByTable: vi.fn().mockResolvedValue([]),
  },
}));

import { fieldService } from '@/db/services/fieldService';

describe('LookupField', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (fieldService.getFieldsByTable as any).mockResolvedValue([]);
  });

  /** 构造一个可用的 FieldEntity（lookup 类型） */
  function buildField(configOverride: Partial<LookupFieldConfig> = {}): FieldEntity {
    return {
      id: 'field-lookup-1',
      tableId: 'table-1',
      name: '查找字段',
      type: 'lookup',
      config: {
        sourceTableId: 'src-table-1',
        targetFieldId: 'src-field-1',
        filterConditions: [],
        filterConjunction: 'and',
        aggregationType: 'original',
        fieldFormat: { type: 'number' },
        ...configOverride,
      } as LookupFieldConfig,
      isPrimary: false,
      isSystem: false,
      isRequired: false,
      isVisible: true,
      order: 0,
      createdAt: 0,
      updatedAt: 0,
    };
  }

  function mountLookup(modelValue: unknown, field: FieldEntity) {
    return mount(LookupField, {
      props: {
        modelValue,
        field,
      },
    });
  }

  it('original 模式应将数组渲染为逗号分隔字符串', () => {
    const field = buildField({ aggregationType: 'original' });
    const wrapper = mountLookup(['a', 'b', 'c'], field);
    // original/distinct 模式采用结构化渲染（lookup-item + lookup-separator）
    // 拼接后的可见文本应等价于 "a, b, c"
    expect(wrapper.find('.lookup-empty').exists()).toBe(false);
    expect(wrapper.find('.lookup-field').text()).toBe('a, b, c');
  });

  it('sum 模式应渲染数字（后端已格式化）', () => {
    const field = buildField({
      aggregationType: 'sum',
      fieldFormat: { type: 'number', precision: 0 },
    });
    const wrapper = mountLookup(60, field);
    expect(wrapper.find('.lookup-value').text()).toBe('60');
  });

  it('空值（null）应显示 "-"', () => {
    const field = buildField({ aggregationType: 'original' });
    const wrapper = mountLookup(null, field);
    expect(wrapper.find('.lookup-empty').text()).toBe('-');
    expect(wrapper.find('.lookup-value').exists()).toBe(false);
  });

  it('空数组应显示 "-"', () => {
    const field = buildField({ aggregationType: 'original' });
    const wrapper = mountLookup([], field);
    expect(wrapper.find('.lookup-empty').text()).toBe('-');
    expect(wrapper.find('.lookup-value').exists()).toBe(false);
  });

  it('货币格式应正确显示货币符号', () => {
    const field = buildField({
      aggregationType: 'sum',
      fieldFormat: { type: 'currency', precision: 2, currencySymbol: '¥' },
    });
    const wrapper = mountLookup(60, field);
    expect(wrapper.find('.lookup-value').text()).toBe('¥60.00');
  });

  it('空字符串应显示 "-"', () => {
    const field = buildField({ aggregationType: 'original' });
    const wrapper = mountLookup('', field);
    expect(wrapper.find('.lookup-empty').text()).toBe('-');
  });

  it('original 模式渲染包含对象的数组时取 name 字段', () => {
    const field = buildField({ aggregationType: 'original' });
    const wrapper = mountLookup(
      [
        { id: 'u1', name: '张三' },
        { id: 'u2', name: '李四' },
      ],
      field,
    );
    expect(wrapper.find('.lookup-field').text()).toBe('张三, 李四');
  });

  // ====================================================================
  // SubTask 13.1 / 13.2 / 13.3：按源字段类型渲染（彩色标签 / 头像 / 缩略图）
  // ====================================================================
  describe('源字段类型渲染（original/distinct 模式）', () => {
    /** 构造源字段（FieldEntity） */
    function buildSourceField(
      type: string,
      options: Record<string, unknown> = {},
    ): FieldEntity {
      return {
        id: 'src-field-1',
        tableId: 'src-table-1',
        name: '源字段',
        type,
        options,
        isPrimary: false,
        isSystem: false,
        isRequired: false,
        isVisible: true,
        order: 0,
        createdAt: 0,
        updatedAt: 0,
      };
    }

    /** 挂载并等待 sourceField 异步加载完成 */
    async function mountLookupAsync(modelValue: unknown, field: FieldEntity) {
      const wrapper = mountLookup(modelValue, field);
      await flushPromises();
      await nextTick();
      return wrapper;
    }

    it('single_select 应按选项 ID 渲染为带颜色的标签', async () => {
      const sourceField = buildSourceField('single_select', {
        choices: [
          { id: 'opt-1', name: '待办', color: '#909399' },
          { id: 'opt-2', name: '进行中', color: '#E6A23C' },
          { id: 'opt-3', name: '已完成', color: '#67C23A' },
        ],
      });
      (fieldService.getFieldsByTable as any).mockResolvedValue([sourceField]);

      const field = buildField({ aggregationType: 'original' });
      const wrapper = await mountLookupAsync(['opt-2'], field);

      const tags = wrapper.findAll('.lookup-tag');
      expect(tags.length).toBe(1);
      expect(tags[0].text()).toBe('进行中');
      // jsdom 会将 #E6A23C 规范化为 rgb(230, 162, 60)
      const style = tags[0].attributes('style') || '';
      expect(style).toMatch(/rgba?\(230,\s*162,\s*60/);
    });

    it('single_select 应按选项名称匹配（兜底）渲染为带颜色的标签', async () => {
      const sourceField = buildSourceField('single_select', {
        choices: [
          { id: 'opt-1', name: '待办', color: '#909399' },
          { id: 'opt-2', name: '进行中', color: '#E6A23C' },
        ],
      });
      (fieldService.getFieldsByTable as any).mockResolvedValue([sourceField]);

      const field = buildField({ aggregationType: 'original' });
      const wrapper = await mountLookupAsync(['进行中'], field);

      const tags = wrapper.findAll('.lookup-tag');
      expect(tags.length).toBe(1);
      expect(tags[0].text()).toBe('进行中');
      expect(tags[0].attributes('style') || '').toMatch(
        /rgba?\(230,\s*162,\s*60/,
      );
    });

    it('multi_select 应将数组每个元素渲染为带颜色的标签', async () => {
      const sourceField = buildSourceField('multi_select', {
        choices: [
          { id: 'opt-a', name: '红', color: '#F56C6C' },
          { id: 'opt-b', name: '绿', color: '#67C23A' },
          { id: 'opt-c', name: '蓝', color: '#409EFF' },
        ],
      });
      (fieldService.getFieldsByTable as any).mockResolvedValue([sourceField]);

      const field = buildField({ aggregationType: 'original' });
      const wrapper = await mountLookupAsync(['opt-a', 'opt-c'], field);

      const tags = wrapper.findAll('.lookup-tag');
      expect(tags.length).toBe(2);
      expect(tags[0].text()).toBe('红');
      expect(tags[1].text()).toBe('蓝');
      // #F56C6C -> rgb(245, 108, 108)；#409EFF -> rgb(64, 158, 255)
      expect(tags[0].attributes('style') || '').toMatch(
        /rgba?\(245,\s*108,\s*108/,
      );
      expect(tags[1].attributes('style') || '').toMatch(
        /rgba?\(64,\s*158,\s*255/,
      );
    });

    it('single_select 未匹配选项时仍渲染文本', async () => {
      const sourceField = buildSourceField('single_select', {
        choices: [{ id: 'opt-1', name: '待办', color: '#909399' }],
      });
      (fieldService.getFieldsByTable as any).mockResolvedValue([sourceField]);

      const field = buildField({ aggregationType: 'original' });
      const wrapper = await mountLookupAsync(['未知选项'], field);

      // 找不到 choice 时回退为文本渲染
      expect(wrapper.find('.lookup-tag').exists()).toBe(false);
      expect(wrapper.find('.lookup-text').text()).toBe('未知选项');
    });

    it('collaborator 应渲染头像 + 名称', async () => {
      const sourceField = buildSourceField('collaborator');
      (fieldService.getFieldsByTable as any).mockResolvedValue([sourceField]);

      const field = buildField({ aggregationType: 'original' });
      const wrapper = await mountLookupAsync(
        [{ id: 'u1', name: '张三', avatar: 'https://example.com/a.png' }],
        field,
      );

      const avatar = wrapper.find('.lookup-avatar');
      expect(avatar.exists()).toBe(true);
      expect(avatar.find('.lookup-avatar-name').text()).toBe('张三');
      const img = avatar.find('img.lookup-avatar-img');
      expect(img.exists()).toBe(true);
      expect(img.attributes('src')).toBe('https://example.com/a.png');
    });

    it('member 在缺失 avatar 时仍渲染名称（无 img）', async () => {
      const sourceField = buildSourceField('member');
      (fieldService.getFieldsByTable as any).mockResolvedValue([sourceField]);

      const field = buildField({ aggregationType: 'original' });
      const wrapper = await mountLookupAsync(
        [{ id: 'u1', name: '李四' }],
        field,
      );

      const avatar = wrapper.find('.lookup-avatar');
      expect(avatar.exists()).toBe(true);
      expect(avatar.find('.lookup-avatar-name').text()).toBe('李四');
      expect(avatar.find('img.lookup-avatar-img').exists()).toBe(false);
    });

    it('created_by / last_modified_by 也按成员类型渲染', async () => {
      const sourceField = buildSourceField('created_by');
      (fieldService.getFieldsByTable as any).mockResolvedValue([sourceField]);

      const field = buildField({ aggregationType: 'original' });
      const wrapper = await mountLookupAsync(
        [{ id: 'u2', name: '王五', avatar: 'https://example.com/b.png' }],
        field,
      );

      expect(wrapper.find('.lookup-avatar').exists()).toBe(true);
      expect(wrapper.find('.lookup-avatar-name').text()).toBe('王五');
      expect(wrapper.find('img.lookup-avatar-img').attributes('src')).toBe(
        'https://example.com/b.png',
      );
    });

    it('attachment 应渲染缩略图 + 名称', async () => {
      const sourceField = buildSourceField('attachment');
      (fieldService.getFieldsByTable as any).mockResolvedValue([sourceField]);

      const field = buildField({ aggregationType: 'original' });
      const wrapper = await mountLookupAsync(
        [
          {
            id: 'file-1',
            url: 'https://example.com/file.pdf',
            name: '文档.pdf',
            thumbnailUrl: 'https://example.com/thumb.png',
          },
        ],
        field,
      );

      const image = wrapper.find('.lookup-image');
      expect(image.exists()).toBe(true);
      expect(image.find('.lookup-image-name').text()).toBe('文档.pdf');
      const img = image.find('img.lookup-thumb');
      expect(img.exists()).toBe(true);
      expect(img.attributes('src')).toBe('https://example.com/thumb.png');
    });

    it('attachment 缺少 thumbnailUrl 时回退使用 url', async () => {
      const sourceField = buildSourceField('attachment');
      (fieldService.getFieldsByTable as any).mockResolvedValue([sourceField]);

      const field = buildField({ aggregationType: 'original' });
      const wrapper = await mountLookupAsync(
        [
          {
            id: 'file-2',
            url: 'https://example.com/full.png',
            name: '图片.png',
          },
        ],
        field,
      );

      const img = wrapper.find('img.lookup-thumb');
      expect(img.exists()).toBe(true);
      expect(img.attributes('src')).toBe('https://example.com/full.png');
      expect(wrapper.find('.lookup-image-name').text()).toBe('图片.png');
    });

    it('attachment 同时缺少 url 与 thumbnailUrl 时仅渲染名称', async () => {
      const sourceField = buildSourceField('attachment');
      (fieldService.getFieldsByTable as any).mockResolvedValue([sourceField]);

      const field = buildField({ aggregationType: 'original' });
      const wrapper = await mountLookupAsync(
        [{ id: 'file-3', name: '无图附件' }],
        field,
      );

      expect(wrapper.find('img.lookup-thumb').exists()).toBe(false);
      expect(wrapper.find('.lookup-image-name').text()).toBe('无图附件');
    });

    it('distinct 模式同样支持彩色标签渲染', async () => {
      const sourceField = buildSourceField('single_select', {
        choices: [
          { id: 's1', name: '高', color: '#F56C6C' },
          { id: 's2', name: '低', color: '#67C23A' },
        ],
      });
      (fieldService.getFieldsByTable as any).mockResolvedValue([sourceField]);

      const field = buildField({ aggregationType: 'distinct' });
      const wrapper = await mountLookupAsync(['s1', 's2'], field);

      const tags = wrapper.findAll('.lookup-tag');
      expect(tags.length).toBe(2);
      expect(tags[0].text()).toBe('高');
      expect(tags[1].text()).toBe('低');
    });

    it('多选项之间应有分隔符', async () => {
      const sourceField = buildSourceField('multi_select', {
        choices: [
          { id: 'x1', name: '甲', color: '#F56C6C' },
          { id: 'x2', name: '乙', color: '#67C23A' },
        ],
      });
      (fieldService.getFieldsByTable as any).mockResolvedValue([sourceField]);

      const field = buildField({ aggregationType: 'original' });
      const wrapper = await mountLookupAsync(['x1', 'x2'], field);

      const separators = wrapper.findAll('.lookup-separator');
      // 第一项后面有分隔符，最后一项没有
      expect(separators.length).toBe(1);
    });
  });
});
