import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';


import WorkflowTriggerConfig from '../WorkflowTriggerConfig.vue';
import { FilterOperator } from '@/types/filters';

vi.mock('@/components/fields/FieldValueInput.vue', () => ({
  default: {
    name: 'FieldValueInput',
    template: '<div class="field-value-input-mock"><slot /></div>',
    props: ['field', 'modelValue', 'placeholder', 'disabled'],
    emits: ['update:modelValue'],
  },
}));

vi.mock('@element-plus/icons-vue', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@element-plus/icons-vue')>();
  return {
    ...actual,
    Delete: { template: '<span class="icon-delete" />' },
    Plus: { template: '<span class="icon-plus" />' },
  };
});

describe('WorkflowTriggerConfig', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockTrigger = {
    id: 'trigger-1',
    workflow_id: 'wf-1',
    trigger_type: 'record_created' as const,
    filter_config: {},
    field_ids: [],
  };

  const mockFields = [
    { id: 'field-1', name: '标题', type: 'single_line_text' },
    { id: 'field-2', name: '状态', type: 'single_select' },
  ];

  function mountTriggerConfig(overrideProps: any = {}) {
    return mount(WorkflowTriggerConfig, {
      props: {
        trigger: overrideProps.trigger ?? mockTrigger,
        fields: overrideProps.fields ?? mockFields,
        readonly: overrideProps.readonly ?? false,
      },
      global: {
        stubs: {
          'el-form': { template: '<form class="el-form"><slot /></form>' },
          'el-form-item': { template: '<div class="el-form-item"><slot /></div>' },
          'el-select': {
            template: '<div class="el-select"><slot /></div>',
            props: ['modelValue'],
            emits: ['change', 'update:modelValue'],
          },
          'el-option': {
            template: '<div class="el-option"><slot /></div>',
            props: ['label', 'value'],
          },
          'el-radio-group': { template: '<div class="el-radio-group"><slot /></div>', props: ['modelValue'] },
          'el-radio-button': { template: '<span class="el-radio-button"><slot /></span>', props: ['label'] },
          'el-button': {
            template: '<button class="el-button" :class="$props.class" @click="$emit(\'click\')"><slot /></button>',
            props: ['type', 'icon', 'text', 'circle', 'link', 'size', 'class'],
            emits: ['click'],
          },
          'el-icon': { template: '<i class="el-icon"><slot /></i>' },
          'el-divider': { template: '<hr class="el-divider" />' },
        },
      },
    });
  }

  it('应该正确渲染触发器配置', () => {
    const wrapper = mountTriggerConfig();
    expect(wrapper.exists()).toBe(true);
    expect(wrapper.find('.workflow-trigger-config').exists()).toBe(true);
  });

  it('debug: 点击添加按钮后应渲染条件行', async () => {
    const wrapper = mountTriggerConfig();
    await flushPromises();
    const addButton = wrapper.find('.conditions-list .el-button');
    await addButton.trigger('click');
    await flushPromises();
    console.log('emitted events:', Object.keys(wrapper.emitted()));
    console.log('emitted update:trigger:', wrapper.emitted('update:trigger'));
  });

  it('有可用字段时添加过滤条件应该新增条件并触发 update:trigger 事件', async () => {
    const wrapper = mountTriggerConfig();
    await flushPromises();

    const addButton = wrapper.findAll('.conditions-list .el-button').find((btn) =>
      btn.text().includes('添加过滤条件')
    );
    expect(addButton).toBeTruthy();
    await addButton!.trigger('click');
    await flushPromises();

    const emitted = wrapper.emitted('update:trigger') as any[][];
    expect(emitted).toBeTruthy();
    const lastTrigger = emitted[emitted.length - 1][0];
    expect(lastTrigger.filter_config.conditions).toHaveLength(1);
    expect(lastTrigger.filter_config.conditions[0]).toMatchObject({
      field_id: mockFields[0].id,
      operator: FilterOperator.EQUALS,
      value: undefined,
    });
  });

  it('没有可用字段时添加过滤条件不应新增条件且不触发 update:trigger 事件', async () => {
    const wrapper = mountTriggerConfig({ fields: [] });
    await flushPromises();

    const addButton = wrapper.findAll('.conditions-list .el-button').find((btn) =>
      btn.text().includes('添加过滤条件')
    );
    expect(addButton).toBeTruthy();
    await addButton!.trigger('click');
    await flushPromises();

    expect(wrapper.emitted('update:trigger')).toBeFalsy();
    expect(wrapper.findAll('.condition-row').length).toBe(0);
  });

  it('字段选择变更时应更新操作符和值', async () => {
    const wrapper = mountTriggerConfig({
      trigger: {
        ...mockTrigger,
        filter_config: {
          conditions: [
            { field_id: mockFields[0].id, operator: FilterOperator.EQUALS, value: 'foo' },
          ],
        },
      },
    });
    await flushPromises();

    const fieldSelect = wrapper.findAll('.condition-row .el-select')[0];
    await fieldSelect.find('select').setValue(mockFields[1].id);
    await fieldSelect.find('select').trigger('change');
    await flushPromises();

    const emitted = wrapper.emitted('update:trigger') as any[][];
    expect(emitted).toBeTruthy();
    const lastTrigger = emitted[emitted.length - 1][0];
    expect(lastTrigger.filter_config.conditions[0]).toMatchObject({
      field_id: mockFields[1].id,
      value: undefined,
    });
  });

  it('删除过滤条件应更新条件列表', async () => {
    const wrapper = mountTriggerConfig({
      trigger: {
        ...mockTrigger,
        filter_config: {
          conditions: [
            { field_id: mockFields[0].id, operator: FilterOperator.EQUALS, value: 'foo' },
            { field_id: mockFields[1].id, operator: FilterOperator.EQUALS, value: 'bar' },
          ],
        },
      },
    });
    await flushPromises();

    const deleteButtons = wrapper.findAll('.condition-row .el-button');
    expect(deleteButtons.length).toBe(2);
    await deleteButtons[0].trigger('click');
    await flushPromises();

    const emitted = wrapper.emitted('update:trigger') as any[][];
    expect(emitted).toBeTruthy();
    const lastTrigger = emitted[emitted.length - 1][0];
    expect(lastTrigger.filter_config.conditions).toHaveLength(1);
    expect(lastTrigger.filter_config.conditions[0].field_id).toBe(mockFields[1].id);
  });
});
