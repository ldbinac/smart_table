/**
 * SubTableToolbar 组件测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import SubTableToolbar from '../SubTableToolbar.vue';

// mock 图标，避免引入真实 SVG 组件
vi.mock('@element-plus/icons-vue', () => ({
  Plus: { name: 'Plus', template: '<span class="icon-plus" />' },
  Refresh: { name: 'Refresh', template: '<span class="icon-refresh" />' },
}));

// ElSelect 在 jsdom 测试环境中会触发 "Maximum recursive updates exceeded"，
// 参考仓库内 WorkflowNodeConfig / FieldValueInput 测试，使用原生 select 桩替换。
const ElSelectStub = {
  name: 'ElSelect',
  template:
    '<select class="el-select" :value="modelValue" @change="$emit(\'change\', $event.target.value)"><slot /></select>',
  props: ['modelValue'],
  emits: ['update:modelValue', 'change'],
};
const ElOptionStub = {
  name: 'ElOption',
  template: '<option class="el-option" :value="value">{{ label }}</option>',
  props: ['label', 'value'],
};

interface LinkField {
  fieldId: string;
  fieldName: string;
  targetTableId: string;
  relationshipType: string;
}

const singleLinkFields: LinkField[] = [
  {
    fieldId: 'f-1',
    fieldName: '关联项目',
    targetTableId: 'tbl-proj',
    relationshipType: 'many_to_many',
  },
];

const multiLinkFields: LinkField[] = [
  {
    fieldId: 'f-1',
    fieldName: '关联项目',
    targetTableId: 'tbl-proj',
    relationshipType: 'many_to_many',
  },
  {
    fieldId: 'f-2',
    fieldName: '关联任务',
    targetTableId: 'tbl-task',
    relationshipType: 'one_to_many',
  },
];

function mountToolbar(props: Record<string, any> = {}) {
  return mount(SubTableToolbar, {
    props: {
      linkFields: multiLinkFields,
      currentFieldId: 'f-1',
      readonly: false,
      hasMultipleLinkFields: true,
      ...props,
    } as any,
    global: {
      stubs: {
        ElSelect: ElSelectStub,
        ElOption: ElOptionStub,
      },
    },
  });
}

/** 按文本内容查找原生按钮 */
function findButtonByText(wrapper: ReturnType<typeof mountToolbar>, text: string) {
  return wrapper.findAll('button').find(b => b.text().includes(text));
}

describe('SubTableToolbar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('单 LINK 字段时不显示切换下拉，显示字段名', () => {
    const wrapper = mountToolbar({
      linkFields: singleLinkFields,
      currentFieldId: 'f-1',
      hasMultipleLinkFields: false,
    });

    expect(wrapper.findComponent({ name: 'ElSelect' }).exists()).toBe(false);
    expect(wrapper.find('.field-label').exists()).toBe(true);
    expect(wrapper.find('.field-label').text()).toBe('关联项目');
  });

  it('多 LINK 字段时显示切换下拉', () => {
    const wrapper = mountToolbar({
      linkFields: multiLinkFields,
      currentFieldId: 'f-1',
      hasMultipleLinkFields: true,
    });

    const select = wrapper.findComponent({ name: 'ElSelect' });
    expect(select.exists()).toBe(true);
    // 下拉应绑定当前字段 ID
    expect(select.props('modelValue')).toBe('f-1');
  });

  it('切换下拉触发 switch-field 事件', async () => {
    const wrapper = mountToolbar({
      linkFields: multiLinkFields,
      currentFieldId: 'f-1',
      hasMultipleLinkFields: true,
    });

    const select = wrapper.findComponent({ name: 'ElSelect' });
    await select.vm.$emit('change', 'f-2');

    expect(wrapper.emitted('switch-field')).toBeTruthy();
    expect(wrapper.emitted('switch-field')![0]).toEqual(['f-2']);
  });

  it('点击添加关联按钮触发 add-link 事件', async () => {
    const wrapper = mountToolbar({
      hasMultipleLinkFields: false,
    });

    const addBtn = findButtonByText(wrapper, '添加关联');
    expect(addBtn).toBeTruthy();
    await addBtn!.trigger('click');

    expect(wrapper.emitted('add-link')).toBeTruthy();
  });

  it('点击刷新按钮触发 refresh 事件', async () => {
    const wrapper = mountToolbar({
      hasMultipleLinkFields: false,
    });

    const refreshBtn = findButtonByText(wrapper, '刷新');
    expect(refreshBtn).toBeTruthy();
    await refreshBtn!.trigger('click');

    expect(wrapper.emitted('refresh')).toBeTruthy();
  });

  it('readonly 模式下添加和刷新按钮被禁用', () => {
    const wrapper = mountToolbar({
      readonly: true,
      hasMultipleLinkFields: false,
    });

    const addBtn = findButtonByText(wrapper, '添加关联');
    const refreshBtn = findButtonByText(wrapper, '刷新');

    expect(addBtn!.attributes('disabled')).toBeDefined();
    expect(refreshBtn!.attributes('disabled')).toBeDefined();
  });

  it('disabledAdd 为 true 时添加按钮被禁用（刷新可用）', () => {
    const wrapper = mountToolbar({
      disabledAdd: true,
      addDisabledReason: '一对一关系已存在关联记录',
      hasMultipleLinkFields: false,
    });

    const addBtn = findButtonByText(wrapper, '添加关联');
    const refreshBtn = findButtonByText(wrapper, '刷新');

    expect(addBtn!.attributes('disabled')).toBeDefined();
    // 刷新按钮不受 disabledAdd 影响
    expect(refreshBtn!.attributes('disabled')).toBeUndefined();
  });
});
