/**
 * WorkflowNodeConfig 组件测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import WorkflowNodeConfig from '../WorkflowNodeConfig.vue';

// Mock Element Plus 图标
vi.mock('@element-plus/icons-vue', () => ({
  Delete: { template: '<span class="icon-delete" />' },
  Plus: { template: '<span class="icon-plus" />' },
  EditPen: { template: '<span class="icon-edit-pen" />' },
  Check: { template: '<span class="icon-check" />' },
  Close: { template: '<span class="icon-close" />' },
}));

// Mock 工具函数
vi.mock('@/utils/filter', () => ({
  getOperatorsForFieldType: vi.fn(() => []),
  OPERATOR_LABELS: {},
  operatorRequiresValue: vi.fn(() => true),
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
            template: '<input class="el-input name-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" @blur="$emit(\'blur\')" @keydown="$emit(\'keydown\', $event)" />',
            props: ['modelValue', 'size', 'class'],
            emits: ['update:modelValue', 'blur', 'keydown'],
          },
          'el-form': { template: '<form class="el-form"><slot /></form>' },
          'el-form-item': { template: '<div class="el-form-item"><slot /></div>' },
          'el-radio-group': { template: '<div class="el-radio-group"><slot /></div>' },
          'el-radio': { template: '<label class="el-radio"><slot /></label>' },
          'el-select': { template: '<select class="el-select"><slot /></select>' },
          'el-option': { template: '<option class="el-option"><slot /></option>' },
          'el-input-number': { template: '<input class="el-input-number" /><slot /></div>' },
          'el-divider': { template: '<hr class="el-divider" />' },
          'el-empty': { template: '<div class="el-empty"><slot /></div>' },
          'el-icon': { template: '<i class="el-icon"><slot /></i>' },
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
});
