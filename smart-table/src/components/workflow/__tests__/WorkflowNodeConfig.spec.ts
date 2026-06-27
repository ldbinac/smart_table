/**
 * WorkflowNodeConfig 组件测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import { fieldService } from '@/db/services/fieldService';
import type { FieldEntity } from '@/db/schema';
import WorkflowNodeConfig from '../WorkflowNodeConfig.vue';

// Mock Element Plus 图标
vi.mock('@element-plus/icons-vue', () => ({
  Delete: { template: '<span class="icon-delete" />' },
  Plus: { template: '<span class="icon-plus" />' },
  EditPen: { template: '<span class="icon-edit-pen" />' },
  Check: { template: '<span class="icon-check" />' },
  Close: { template: '<span class="icon-close" />' },
  Document: { template: '<span class="icon-document" />' },
  Memo: { template: '<span class="icon-memo" />' },
  ScaleToOriginal: { template: '<span class="icon-scale-to-original" />' },
  Calendar: { template: '<span class="icon-calendar" />' },
  AlarmClock: { template: '<span class="icon-alarm-clock" />' },
  CircleCheck: { template: '<span class="icon-circle-check" />' },
  FolderChecked: { template: '<span class="icon-folder-checked" />' },
  TurnOff: { template: '<span class="icon-turn-off" />' },
  Star: { template: '<span class="icon-star" />' },
  User: { template: '<span class="icon-user" />' },
  Link: { template: '<span class="icon-link" />' },
  Paperclip: { template: '<span class="icon-paperclip" />' },
  Phone: { template: '<span class="icon-phone" />' },
  Message: { template: '<span class="icon-message" />' },
  PieChart: { template: '<span class="icon-pie-chart" />' },
  List: { template: '<span class="icon-list" />' },
  Share: { template: '<span class="icon-share" />' },
  Search: { template: '<span class="icon-search" />' },
  Timer: { template: '<span class="icon-timer" />' },
}));

// Mock 工具函数
vi.mock('@/utils/filter', () => ({
  getOperatorsForFieldType: vi.fn(() => []),
  OPERATOR_LABELS: {},
  operatorRequiresValue: vi.fn(() => true),
}));

// Mock fieldService
vi.mock('@/db/services/fieldService', () => ({
  fieldService: {
    getFieldsByTable: vi.fn(() => Promise.resolve([])),
  },
}));

describe('WorkflowNodeConfig', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockNode = {
    id: 'node-1',
    workflow_id: 'wf-1',
    node_type: 'approval' as const,
    name: '审批节点 1',
    config: {},
    order: 0,
    next_nodes: [],
  };

  const mockFields = [
    { id: 'field-1', name: '标题', type: 'single_line_text' },
    { id: 'field-2', name: '状态', type: 'single_select' },
    { id: 'field-3', name: '完成度', type: 'progress' },
    { id: 'field-4', name: '是否通过', type: 'checkbox' },
  ];

  const mockTargetFields = [
    { id: 'target-1', name: '目标标题', type: 'single_line_text' },
    { id: 'target-2', name: '目标状态', type: 'single_select' },
    { id: 'target-3', name: '目标完成度', type: 'progress' },
  ] as FieldEntity[];

  const mockTables = [
    { id: 'table-1', name: '源表' },
    { id: 'table-2', name: '目标表' },
  ];

  function mountConfig(overrideProps: any = {}) {
    return mount(WorkflowNodeConfig, {
      props: {
        node: overrideProps.node ?? mockNode,
        fields: overrideProps.fields ?? mockFields,
        tables: overrideProps.tables,
        webhooks: overrideProps.webhooks,
        readonly: overrideProps.readonly ?? false,
      },
      global: {
        stubs: {
          'el-button': {
            template: '<button class="el-button" :class="$props.class" @click="$emit(\'click\')"><slot /></button>',
            props: ['type', 'icon', 'link', 'size', 'class'],
            emits: ['click'],
          },
          'el-input': {
            template: '<input class="el-input" :class="$props.class" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" @blur="$emit(\'blur\')" @keydown="$emit(\'keydown\', $event)" />',
            props: ['modelValue', 'size', 'class'],
            emits: ['update:modelValue', 'blur', 'keydown'],
          },
          'el-form': { template: '<form class="el-form"><slot /></form>' },
          'el-form-item': { template: '<div class="el-form-item"><slot /></div>' },
          'el-radio-group': { template: '<div class="el-radio-group"><slot /></div>' },
          'el-radio': { template: '<label class="el-radio"><slot /></label>' },
          'el-select': { template: '<select class="el-select" :class="$props.class" :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value); $emit(\'change\', $event.target.value)"><slot /></select>', props: ['class', 'modelValue'], emits: ['update:modelValue', 'change'] },
          'el-option': { template: '<option class="el-option"><slot /></option>' },
          'el-input-number': { template: '<div class="el-input-number"><input /><slot /></div>' },
          'el-date-picker': { template: '<input class="el-date-picker" />' },
          'el-switch': { template: '<button class="el-switch" @click="$emit(\'update:modelValue\', !modelValue)"><slot /></button>', props: ['modelValue'], emits: ['update:modelValue'] },
          'el-rate': { template: '<div class="el-rate"><slot /></div>' },
          'el-divider': { template: '<hr class="el-divider" />' },
          'el-empty': { template: '<div class="el-empty"><slot /></div>' },
          'el-icon': { template: '<i class="el-icon"><slot /></i>' },
          'FieldValueInput': { template: '<input class="field-value-input" />' },
        },
      },
    });
  }

  it('应该渲染节点名称（纯文本模式）', () => {
    const wrapper = mountConfig();
    const nameSpan = wrapper.find('.node-name');
    expect(nameSpan.exists()).toBe(true);
    expect(nameSpan.text()).toBe('审批节点 1');
  });

  it('草稿态下应该显示编辑按钮', () => {
    const wrapper = mountConfig({ readonly: false });
    const editBtn = wrapper.find('.edit-name-btn');
    expect(editBtn.exists()).toBe(true);
  });

  it('非草稿态下不应该显示编辑按钮', () => {
    const wrapper = mountConfig({ readonly: true });
    const editBtn = wrapper.find('.edit-name-btn');
    expect(editBtn.exists()).toBe(false);
  });

  it('点击编辑按钮应该进入编辑模式并显示输入框', async () => {
    const wrapper = mountConfig();
    const editBtn = wrapper.find('.edit-name-btn');
    await editBtn.trigger('click');
    await nextTick();

    const nameInput = wrapper.find('.name-input');
    expect(nameInput.exists()).toBe(true);
    expect(wrapper.find('.node-name').exists()).toBe(false);
  });

  it('修改名称后按 Enter 应该保存并触发 update:node 事件', async () => {
    const wrapper = mountConfig();
    const editBtn = wrapper.find('.edit-name-btn');
    await editBtn.trigger('click');
    await nextTick();

    const input = wrapper.find('.name-input');
    await input.setValue('新审批节点');
    await input.trigger('keydown', { key: 'Enter' });
    await nextTick();

    const emitted = wrapper.emitted('update:node') as any[][];
    expect(emitted).toBeTruthy();
    const lastNode = emitted[emitted.length - 1][0];
    expect(lastNode.name).toBe('新审批节点');
    expect(wrapper.find('.node-name').text()).toBe('新审批节点');
  });

  it('按 Esc 应该取消编辑并恢复原名', async () => {
    const wrapper = mountConfig();
    const editBtn = wrapper.find('.edit-name-btn');
    await editBtn.trigger('click');
    await nextTick();

    const input = wrapper.find('.name-input');
    await input.setValue('临时名称');
    await input.trigger('keydown', { key: 'Escape' });
    await nextTick();

    expect(wrapper.find('.node-name').text()).toBe('审批节点 1');
    // 取消编辑不应触发名称变更的事件（可能已有其他 config 变更事件，但名称应保持原值）
    // 由于 watch 机制，如果 config 没变，可能不会触发。这里主要验证 DOM 恢复
    expect(wrapper.find('.node-name').exists()).toBe(true);
  });

  it('输入空名称后按 Enter 应该取消编辑并恢复原名', async () => {
    const wrapper = mountConfig();
    const editBtn = wrapper.find('.edit-name-btn');
    await editBtn.trigger('click');
    await nextTick();

    const input = wrapper.find('.name-input');
    await input.setValue('   ');
    await input.trigger('keydown', { key: 'Enter' });
    await nextTick();

    expect(wrapper.find('.node-name').text()).toBe('审批节点 1');
  });

  it('更新记录节点的静态值字段应直接显示 FieldValueInput 且隐藏值模板输入', async () => {
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'update_record',
        config: {
          updates: [{ field_id: 'field-2', value_template: '' }],
        },
      },
    });
    await nextTick();

    expect(wrapper.find('.template-input').exists()).toBe(false);
    expect(wrapper.find('.field-value-input').exists()).toBe(true);
    expect(wrapper.find('.el-switch').exists()).toBe(false);
  });

  it('更新记录节点的非静态值字段默认启用静态值模式', async () => {
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'update_record',
        config: {
          updates: [{ field_id: 'field-1', value_template: '' }],
        },
      },
    });
    await nextTick();

    expect(wrapper.find('.template-input').exists()).toBe(false);
    expect(wrapper.findAll('.el-switch').length).toBe(1);
    expect(wrapper.find('.field-value-input').exists()).toBe(true);
  });

  it('更新记录节点开启表达式开关后显示表达式输入', async () => {
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'update_record',
        config: {
          updates: [{ field_id: 'field-1', value_template: '' }],
        },
      },
    });
    await nextTick();

    const switchEl = wrapper.find('.el-switch');
    expect(switchEl.exists()).toBe(true);

    await switchEl.trigger('click');
    await nextTick();

    expect(wrapper.find('.template-input').exists()).toBe(true);
    expect(wrapper.find('.field-value-input').exists()).toBe(false);
  });

  it('创建记录节点的静态值字段应直接显示 FieldValueInput 且隐藏值模板输入', async () => {
    vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'create_record',
        config: {
          target_table_id: 'table-2',
          field_mappings: [{ target_field_id: 'target-3', source_field_id: '', value_template: '' }],
        },
      },
      tables: mockTables,
    });
    await nextTick();

    expect(wrapper.find('.template-input').exists()).toBe(false);
    expect(wrapper.find('.field-value-input').exists()).toBe(true);
    expect(wrapper.find('.el-switch').exists()).toBe(false);
  });

  it('创建记录节点的非静态值字段默认启用静态值模式', async () => {
    vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'create_record',
        config: {
          target_table_id: 'table-2',
          field_mappings: [{ target_field_id: 'target-1', source_field_id: '', value_template: '' }],
        },
      },
      tables: mockTables,
    });
    await nextTick();

    expect(wrapper.find('.template-input').exists()).toBe(false);
    expect(wrapper.findAll('.el-switch').length).toBe(1);
    expect(wrapper.find('.field-value-input').exists()).toBe(true);
  });

  it('创建记录节点开启表达式开关后显示表达式输入', async () => {
    vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'create_record',
        config: {
          target_table_id: 'table-2',
          field_mappings: [{ target_field_id: 'target-1', source_field_id: '', value_template: '' }],
        },
      },
      tables: mockTables,
    });
    await nextTick();

    const switchEl = wrapper.find('.el-switch');
    expect(switchEl.exists()).toBe(true);

    await switchEl.trigger('click');
    await nextTick();

    expect(wrapper.find('.template-input').exists()).toBe(true);
    expect(wrapper.find('.field-value-input').exists()).toBe(false);
  });

  it('创建记录节点目标字段下拉从目标表加载字段', async () => {
    vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'create_record',
        config: {
          target_table_id: 'table-2',
          field_mappings: [{ target_field_id: '', source_field_id: '', value_template: '' }],
        },
      },
      tables: mockTables,
    });
    await nextTick();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(fieldService.getFieldsByTable).toHaveBeenCalledWith('table-2');
    const fieldSelects = wrapper.findAll('.field-select');
    const targetSelect = fieldSelects[0];
    expect(targetSelect.findAll('.el-option').length).toBe(mockTargetFields.length);
  });

  it('创建记录节点切换目标表后清空字段映射', async () => {
    vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'create_record',
        config: {
          target_table_id: 'table-2',
          field_mappings: [{ target_field_id: 'target-1', source_field_id: '', value_template: '' }],
        },
      },
      tables: mockTables,
    });
    await nextTick();

    const targetTableSelect = wrapper.find('.full-width');
    await targetTableSelect.setValue('table-1');
    await targetTableSelect.trigger('change');
    await nextTick();
    await new Promise((resolve) => setTimeout(resolve, 0));

    const emitted = wrapper.emitted('update:node') as any[][];
    expect(emitted).toBeTruthy();
    const lastNode = emitted[emitted.length - 1][0];
    expect(lastNode.config.target_table_id).toBe('table-1');
    expect(lastNode.config.field_mappings).toEqual([]);
  });

  it('创建记录节点选择源字段后自动填充表达式', async () => {
    vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'create_record',
        config: {
          target_table_id: 'table-2',
          field_mappings: [{ target_field_id: 'target-1', source_field_id: '', value_template: '' }],
        },
      },
      tables: mockTables,
    });
    await nextTick();

    const fieldSelects = wrapper.findAll('.field-select');
    const sourceSelect = fieldSelects[1];
    await sourceSelect.setValue('field-1');
    await sourceSelect.trigger('change');
    await nextTick();

    expect(wrapper.find('.template-input').exists()).toBe(true);
    expect(wrapper.find('.field-value-input').exists()).toBe(false);

    const emitted = wrapper.emitted('update:node') as any[][];
    expect(emitted).toBeTruthy();
    const lastNode = emitted[emitted.length - 1][0];
    expect(lastNode.config.field_mappings[0].source_field_id).toBe('field-1');
    expect(lastNode.config.field_mappings[0].value_template).toBe('{{trigger.record.field-1}}');
  });
});
