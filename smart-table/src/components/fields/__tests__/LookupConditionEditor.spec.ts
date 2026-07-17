/**
 * LookupConditionEditor 组件测试
 *
 * 重点验证 emit 事件和数据流（添加/删除条件、切换 conjunction、禁用态、is_empty 隐藏值输入）。
 * 由于 Element Plus 组件较重，这里使用 stub 隔离。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import LookupConditionEditor from '../LookupConditionEditor.vue';
import type { FieldEntity } from '@/db/schema';
import type {
  LookupFilterCondition,
  LookupFilterOperator,
} from '@/types/fields';

// mock Element Plus 图标（Delete 在模板中使用）
// 使用 importOriginal 保留其它图标导出，避免 types/fields.ts 中的图标导入失败
vi.mock('@element-plus/icons-vue', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    Delete: { template: '<span class="icon-delete" />' },
  };
});

/**
 * Element Plus 组件 stub。
 * 使用 PascalCase 键以匹配模板中的 <ElButton> 等标签（vitest 未启用 unplugin-vue-components）。
 */
const stubs = {
  ElRadioGroup: {
    template: '<div class="el-radio-group"><slot /></div>',
    props: ['modelValue', 'disabled', 'size'],
    emits: ['update:modelValue'],
  },
  ElRadioButton: {
    template: '<label class="el-radio-button"><slot /></label>',
    props: ['value'],
  },
  ElSelect: {
    template:
      '<select class="el-select" :class="$attrs.class"><slot /></select>',
    props: ['modelValue', 'disabled', 'size', 'placeholder'],
    emits: ['update:modelValue'],
  },
  ElOption: {
    template: '<option class="el-option"><slot /></option>',
    props: ['label', 'value'],
  },
  ElButton: {
    template:
      '<button class="el-button" :class="$attrs.class" :disabled="disabled ? true : undefined" @click="$emit(\'click\')"><slot /></button>',
    props: ['type', 'size', 'disabled', 'text'],
    emits: ['click'],
  },
  ElIcon: {
    template: '<i class="el-icon"><slot /></i>',
  },
  ElInputNumber: {
    template: '<div class="el-input-number"><input /></div>',
    props: ['modelValue', 'disabled', 'size', 'placeholder'],
    emits: ['update:modelValue'],
  },
  ElDatePicker: {
    template: '<input class="el-date-picker" />',
    props: [
      'modelValue',
      'disabled',
      'size',
      'type',
      'placeholder',
      'valueFormat',
    ],
    emits: ['update:modelValue'],
  },
  ElInput: {
    template: '<input class="el-input" />',
    props: ['modelValue', 'disabled', 'size', 'placeholder'],
    emits: ['update:modelValue'],
  },
};

describe('LookupConditionEditor', () => {
  const sourceTableFields: FieldEntity[] = [
    {
      id: 'src-field-1',
      tableId: 'src-table-1',
      name: '源字段1',
      type: 'single_line_text',
      isPrimary: false,
      isSystem: false,
      isRequired: false,
      isVisible: true,
      order: 0,
      createdAt: 0,
      updatedAt: 0,
    },
    {
      id: 'src-field-2',
      tableId: 'src-table-1',
      name: '金额',
      type: 'number',
      isPrimary: false,
      isSystem: false,
      isRequired: false,
      isVisible: true,
      order: 1,
      createdAt: 0,
      updatedAt: 0,
    },
  ];

  const currentTableFields: FieldEntity[] = [
    {
      id: 'cur-field-1',
      tableId: 'cur-table-1',
      name: '当前表字段1',
      type: 'single_line_text',
      isPrimary: false,
      isSystem: false,
      isRequired: false,
      isVisible: true,
      order: 0,
      createdAt: 0,
      updatedAt: 0,
    },
  ];

  function makeCondition(
    override: Partial<LookupFilterCondition> = {},
  ): LookupFilterCondition {
    return {
      fieldId: 'src-field-1',
      operator: 'equal',
      valueType: 'custom',
      valueCustom: '',
      ...override,
    };
  }

  function mountEditor(overrideProps: {
    conditions?: LookupFilterCondition[];
    conjunction?: 'and' | 'or';
    disabled?: boolean;
  } = {}) {
    return mount(LookupConditionEditor, {
      props: {
        conditions: overrideProps.conditions ?? [],
        conjunction: overrideProps.conjunction ?? 'and',
        sourceTableFields,
        currentTableFields,
        disabled: overrideProps.disabled ?? false,
      },
      global: { stubs },
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('点击"添加条件"按钮应 emit update:conditions 包含 1 个新条件', async () => {
    const wrapper = mountEditor({ conditions: [] });
    await wrapper.find('.add-button').trigger('click');

    const emitted = wrapper.emitted('update:conditions');
    expect(emitted).toBeTruthy();
    expect(emitted!.length).toBe(1);

    const emittedConditions = emitted![0][0] as LookupFilterCondition[];
    expect(emittedConditions).toHaveLength(1);
    // 新条件默认使用源表第一个字段、equal 操作符、自定义值类型
    expect(emittedConditions[0]).toMatchObject({
      fieldId: 'src-field-1',
      operator: 'equal',
      valueType: 'custom',
      valueCustom: '',
    });
  });

  it('点击删除按钮应 emit update:conditions 为空数组', async () => {
    const wrapper = mountEditor({
      conditions: [makeCondition()],
    });
    const deleteBtn = wrapper.find('.condition-delete-btn');
    expect(deleteBtn.exists()).toBe(true);

    await deleteBtn.trigger('click');

    const emitted = wrapper.emitted('update:conditions');
    expect(emitted).toBeTruthy();
    expect(emitted![0][0]).toEqual([]);
  });

  it('切换 conjunction 应 emit update:conjunction 为新值', async () => {
    const wrapper = mountEditor({ conjunction: 'and' });
    // 直接在 ElRadioGroup stub 上触发 update:modelValue 事件
    // 使用 CSS 选择器定位 stub 的根元素来获取组件实例
    const radioGroup = wrapper.findComponent('.el-radio-group');
    expect(radioGroup.exists()).toBe(true);
    radioGroup.vm.$emit('update:modelValue', 'or');
    await wrapper.vm.$nextTick();

    const emitted = wrapper.emitted('update:conjunction');
    expect(emitted).toBeTruthy();
    expect(emitted![0][0]).toBe('or');
  });

  it('条件数量达到 5 个时添加按钮应禁用', () => {
    const conditions = Array.from({ length: 5 }, (_, i) =>
      makeCondition({ fieldId: `src-field-${(i % 2) + 1}` }),
    );
    const wrapper = mountEditor({ conditions });

    const addButton = wrapper.find('.add-button');
    expect(addButton.exists()).toBe(true);
    expect(addButton.attributes('disabled')).toBeDefined();
  });

  it('条件数量未达 5 个时添加按钮应可用', () => {
    const wrapper = mountEditor({
      conditions: [makeCondition(), makeCondition()],
    });
    const addButton = wrapper.find('.add-button');
    expect(addButton.attributes('disabled')).toBeUndefined();
  });

  it('is_empty 操作符应隐藏值输入控件', () => {
    const wrapper = mountEditor({
      conditions: [
        makeCondition({ operator: 'is_empty' as LookupFilterOperator }),
      ],
    });
    // 值类型下拉与值输入容器都不应存在
    expect(wrapper.find('.condition-value-type-select').exists()).toBe(false);
    expect(wrapper.find('.condition-value-input').exists()).toBe(false);
  });

  it('is_not_empty 操作符同样应隐藏值输入控件', () => {
    const wrapper = mountEditor({
      conditions: [
        makeCondition({ operator: 'is_not_empty' as LookupFilterOperator }),
      ],
    });
    expect(wrapper.find('.condition-value-type-select').exists()).toBe(false);
    expect(wrapper.find('.condition-value-input').exists()).toBe(false);
  });

  it('equal 操作符应显示值输入控件', () => {
    const wrapper = mountEditor({
      conditions: [makeCondition({ operator: 'equal' })],
    });
    expect(wrapper.find('.condition-value-type-select').exists()).toBe(true);
    expect(wrapper.find('.condition-value-input').exists()).toBe(true);
  });

  it('disabled 状态下添加按钮应禁用', () => {
    const wrapper = mountEditor({ conditions: [], disabled: true });
    const addButton = wrapper.find('.add-button');
    expect(addButton.attributes('disabled')).toBeDefined();
  });
});
