import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { nextTick } from 'vue';

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
            template: `<select
                class="el-select"
                :class="$props.class"
                :value="modelValue"
                :disabled="disabled"
                @change="$emit('update:modelValue', $event.target.value); $emit('change', $event.target.value)">
                <slot />
              </select>`,
            props: ['modelValue', 'class', 'disabled', 'multiple', 'placeholder'],
            emits: ['update:modelValue', 'change'],
          },
          'el-option': {
            template: `<option class="el-option" :value="value"><slot /></option>`,
            props: ['label', 'value'],
          },
          'el-radio-group': {
            template: `<div class="el-radio-group" :class="$props.class"><slot /></div>`,
            props: ['modelValue'],
            emits: ['update:modelValue'],
          },
          'el-radio-button': {
            template: `<label class="el-radio-button"><input type="radio" :value="label" @change="$parent?.$emit('update:modelValue', label)" /><slot /></label>`,
            props: ['label'],
          },
          'el-radio': {
            template: `<label class="el-radio"><input type="radio" :value="label" @change="$parent?.$emit('update:modelValue', label)" /><slot /></label>`,
            props: ['label'],
          },
          'el-button': {
            template: `<button class="el-button" :class="$props.class" :disabled="disabled" @click="$emit('click')"><slot /></button>`,
            props: ['type', 'icon', 'text', 'circle', 'link', 'size', 'class', 'disabled'],
            emits: ['click'],
          },
          'el-input': {
            template: `<input class="el-input" :value="modelValue" :disabled="disabled" @input="$emit('update:modelValue', $event.target.value)" />`,
            props: ['modelValue', 'disabled'],
            emits: ['update:modelValue'],
          },
          'el-input-number': {
            template: `<input class="el-input-number" type="number" :value="modelValue" :disabled="disabled" @input="$emit('update:modelValue', Number($event.target.value))" />`,
            props: ['modelValue', 'disabled'],
            emits: ['update:modelValue'],
          },
          'el-date-picker': {
            template: `<input class="el-date-picker" :value="modelValue" :disabled="disabled" @input="$emit('update:modelValue', $event.target.value)" />`,
            props: ['modelValue', 'disabled'],
            emits: ['update:modelValue'],
          },
          'el-time-picker': {
            template: `<input class="el-time-picker" :value="modelValue" :disabled="disabled" @input="$emit('update:modelValue', $event.target.value)" />`,
            props: ['modelValue', 'disabled'],
            emits: ['update:modelValue'],
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

  it('触发类型下拉框应包含指定时间选项', () => {
    const wrapper = mountTriggerConfig();
    const triggerTypeSelect = wrapper.findAll('.el-select').find((s) => s.findAll('.el-option').some((o) => (o.element as HTMLOptionElement).value === 'record_created'));
    expect(triggerTypeSelect).toBeTruthy();
    const options = triggerTypeSelect!.findAll('.el-option');
    const values = options.map((o) => (o.element as HTMLOptionElement).value);
    expect(values).toContain('specified_time');
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
    await fieldSelect.setValue(mockFields[1].id);
    await fieldSelect.trigger('change');
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

  describe('指定时间触发器', () => {
    async function setTriggerType(wrapper: any, value: string) {
      const triggerTypeSelect = wrapper.findAll('.el-select').find((s: any) =>
        s.findAll('.el-option').some((o: any) => (o.element as HTMLOptionElement).value === 'record_created')
      );
      expect(triggerTypeSelect).toBeTruthy();
      await triggerTypeSelect!.setValue(value);
      await triggerTypeSelect!.trigger('change');
      await flushPromises();
      await nextTick();
    }

    it('选择 specified_time 后隐藏监听字段和触发过滤条件区域', async () => {
      const wrapper = mountTriggerConfig({
        trigger: {
          ...mockTrigger,
          trigger_type: 'record_updated',
          field_ids: ['field-1'],
          filter_config: { conditions: [{ field_id: 'field-1', operator: FilterOperator.EQUALS, value: 'foo' }], conjunction: 'and' },
        },
      });
      await flushPromises();

      expect(wrapper.findAll('.condition-row').length).toBe(1);

      await setTriggerType(wrapper, 'specified_time');

      expect(wrapper.find('.field-ids-error').exists()).toBe(false);
      expect(wrapper.find('.filter-section').exists()).toBe(false);
      expect(wrapper.findAll('.condition-row').length).toBe(0);
    });

    it('选择 specified_time 后显示定时器配置表单', async () => {
      const wrapper = mountTriggerConfig();
      await flushPromises();

      await setTriggerType(wrapper, 'specified_time');

      expect(wrapper.find('.schedule-section').exists()).toBe(true);
      expect(wrapper.find('.schedule-start-date').exists()).toBe(true);
      expect(wrapper.find('.schedule-start-time').exists()).toBe(true);
      expect(wrapper.find('.schedule-repeat-type').exists()).toBe(true);
      expect(wrapper.find('.schedule-end-type').exists()).toBe(true);
    });

    it('从事件类型切换到 specified_time 时清空 field_ids、conditions 并初始化 schedule', async () => {
      const wrapper = mountTriggerConfig({
        trigger: {
          ...mockTrigger,
          trigger_type: 'record_updated',
          field_ids: ['field-1'],
          filter_config: { conditions: [{ field_id: 'field-1', operator: FilterOperator.EQUALS, value: 'foo' }], conjunction: 'and' },
        },
      });
      await flushPromises();

      await setTriggerType(wrapper, 'specified_time');

      const emitted = wrapper.emitted('update:trigger') as any[][];
      expect(emitted).toBeTruthy();
      const lastTrigger = emitted[emitted.length - 1][0];
      expect(lastTrigger.trigger_type).toBe('specified_time');
      expect(lastTrigger.field_ids).toEqual([]);
      expect(lastTrigger.filter_config.conditions).toEqual([]);
      expect(lastTrigger.filter_config.schedule).toMatchObject({
        repeat_type: 'no_repeat',
        custom_interval: 1,
        custom_unit: 'day',
        end_type: 'never',
      });
      expect(lastTrigger.filter_config.schedule.start_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(lastTrigger.filter_config.schedule.start_time).toBe('00:00');
    });

    it('从 specified_time 切换回事件类型时清空 schedule', async () => {
      const wrapper = mountTriggerConfig({
        trigger: {
          ...mockTrigger,
          trigger_type: 'specified_time',
          field_ids: [],
          filter_config: {
            schedule: {
              start_date: '2026-06-28',
              start_time: '23:55',
              repeat_type: 'daily',
              custom_interval: 1,
              custom_unit: 'day',
              end_type: 'never',
            },
          },
        },
      });
      await flushPromises();

      await setTriggerType(wrapper, 'record_created');

      const emitted = wrapper.emitted('update:trigger') as any[][];
      expect(emitted).toBeTruthy();
      const lastTrigger = emitted[emitted.length - 1][0];
      expect(lastTrigger.trigger_type).toBe('record_created');
      expect(lastTrigger.filter_config.schedule).toBeUndefined();
    });

    it('修改定时器配置字段应触发 update:trigger 事件并更新 schedule', async () => {
      const wrapper = mountTriggerConfig({
        trigger: {
          ...mockTrigger,
          trigger_type: 'specified_time',
          field_ids: [],
          filter_config: {
            schedule: {
              start_date: '2026-06-28',
              start_time: '23:55',
              repeat_type: 'no_repeat',
              custom_interval: 1,
              custom_unit: 'day',
              end_type: 'never',
            },
          },
        },
      });
      await flushPromises();

      const dateInput = wrapper.find('.schedule-start-date .el-date-picker');
      await dateInput.setValue('2026-07-01');
      await dateInput.trigger('input');
      await flushPromises();

      const emitted = wrapper.emitted('update:trigger') as any[][];
      expect(emitted).toBeTruthy();
      const lastTrigger = emitted[emitted.length - 1][0];
      expect(lastTrigger.filter_config.schedule.start_date).toBe('2026-07-01');
    });

    it('选择自定义重复时显示自定义间隔和单位', async () => {
      const wrapper = mountTriggerConfig({
        trigger: {
          ...mockTrigger,
          trigger_type: 'specified_time',
          filter_config: {
            schedule: {
              start_date: '2026-06-28',
              start_time: '23:55',
              repeat_type: 'custom',
              custom_interval: 2,
              custom_unit: 'week',
              end_type: 'never',
            },
          },
        },
      });
      await flushPromises();

      expect(wrapper.find('.schedule-custom-row').exists()).toBe(true);
      expect(wrapper.find('.schedule-custom-unit').exists()).toBe(true);
      const intervalInput = wrapper.find('.schedule-custom-row .el-input-number');
      expect((intervalInput.element as HTMLInputElement).value).toBe('2');
    });

    it('选择截止日期为指定日期时显示结束日期选择器', async () => {
      const wrapper = mountTriggerConfig({
        trigger: {
          ...mockTrigger,
          trigger_type: 'specified_time',
          filter_config: {
            schedule: {
              start_date: '2026-06-28',
              start_time: '23:55',
              repeat_type: 'no_repeat',
              custom_interval: 1,
              custom_unit: 'day',
              end_type: 'end_date',
              end_date: '2028-06-27',
            },
          },
        },
      });
      await flushPromises();

      expect(wrapper.find('.schedule-end-date').exists()).toBe(true);
      const endDateInput = wrapper.find('.schedule-end-date .el-date-picker');
      expect((endDateInput.element as HTMLInputElement).value).toBe('2028-06-27');
    });

    it('readonly 状态下定时器字段应被禁用', async () => {
      const wrapper = mountTriggerConfig({
        readonly: true,
        trigger: {
          ...mockTrigger,
          trigger_type: 'specified_time',
          filter_config: {
            schedule: {
              start_date: '2026-06-28',
              start_time: '23:55',
              repeat_type: 'no_repeat',
              custom_interval: 1,
              custom_unit: 'day',
              end_type: 'never',
            },
          },
        },
      });
      await flushPromises();

      expect(wrapper.find('.schedule-start-date .el-date-picker').attributes('disabled')).toBeDefined();
      expect(wrapper.find('.schedule-start-time .el-time-picker').attributes('disabled')).toBeDefined();
      const repeatSelect = wrapper.find('.schedule-repeat-type .el-select');
      expect(repeatSelect.attributes('disabled')).toBeDefined();
    });
  });
});
