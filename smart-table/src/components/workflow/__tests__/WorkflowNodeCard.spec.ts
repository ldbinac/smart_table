import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import type { WorkflowNode } from '@/types/workflow';
import WorkflowNodeCard from '../WorkflowNodeCard.vue';

vi.mock('@element-plus/icons-vue', () => ({
  Share: { name: 'Share', template: '<span class="icon-share" />' },
  EditPen: { name: 'EditPen', template: '<span class="icon-edit-pen" />' },
  Plus: { name: 'Plus', template: '<span class="icon-plus" />' },
  Link: { name: 'Link', template: '<span class="icon-link" />' },
  Message: { name: 'Message', template: '<span class="icon-message" />' },
  CircleCheck: { name: 'CircleCheck', template: '<span class="icon-circle-check" />' },
  Delete: { name: 'Delete', template: '<span class="icon-delete" />' },
}));

function mountCard(overrideProps: Record<string, any> = {}) {
  return mount(WorkflowNodeCard, {
    props: {
      id: 'node-1',
      type: 'workflow',
      data: {
        node: overrideProps.node ?? mockNode,
      },
      selected: overrideProps.selected ?? false,
      ...overrideProps,
    },
    global: {
      stubs: {
        'el-icon': {
          template: '<i class="el-icon"><slot /></i>',
        },
        'el-dropdown': {
          template: '<div class="el-dropdown"><slot /><slot name="dropdown" /></div>',
        },
        'el-dropdown-menu': {
          template: '<div class="el-dropdown-menu"><slot /></div>',
        },
        'el-dropdown-item': {
          template: '<div class="el-dropdown-item"><slot /></div>',
        },
        Handle: {
          name: 'Handle',
          template: '<div class="vue-flow__handle"><slot /></div>',
        },
      },
    },
  });
}

const mockNode: WorkflowNode = {
  id: 'node-1',
  workflow_id: 'wf-1',
  node_type: 'update_record',
  name: '更新项目状态',
  config: {},
  order: 0,
  next_nodes: [],
};

describe('WorkflowNodeCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('应该渲染节点名称和类型标签', () => {
    const wrapper = mountCard();

    expect(wrapper.find('.node-name').text()).toBe('更新项目状态');
    expect(wrapper.find('.node-type-label').text()).toBe('更新记录');
  });

  it('应该根据节点类型渲染对应的图标', () => {
    const wrapper = mountCard();
    expect(wrapper.find('.icon-edit-pen').exists()).toBe(true);
  });

  it('条件节点应该渲染分支图标和条件节点样式', () => {
    const wrapper = mountCard({
      node: {
        ...mockNode,
        node_type: 'condition',
        name: '金额大于 1000',
      },
    });

    expect(wrapper.find('.icon-share').exists()).toBe(true);
    expect(wrapper.find('.node-name').text()).toBe('金额大于 1000');
    expect(wrapper.find('.node-type-label').text()).toBe('条件节点');
    expect(wrapper.find('.workflow-node-card').classes()).toContain('is-condition');
  });

  it('创建记录节点应该渲染 Plus 图标和对应标签', () => {
    const wrapper = mountCard({
      node: {
        ...mockNode,
        node_type: 'create_record',
        name: '创建任务记录',
      },
    });

    expect(wrapper.find('.icon-plus').exists()).toBe(true);
    expect(wrapper.find('.node-type-label').text()).toBe('创建记录');
  });

  it('Webhook 节点应该渲染 Link 图标和对应标签', () => {
    const wrapper = mountCard({
      node: {
        ...mockNode,
        node_type: 'webhook',
        name: '同步到外部系统',
      },
    });

    expect(wrapper.find('.icon-link').exists()).toBe(true);
    expect(wrapper.find('.node-type-label').text()).toBe('Webhook');
  });

  it('未知节点类型应该使用默认图标和标签', () => {
    const wrapper = mountCard({
      node: {
        ...mockNode,
        node_type: 'unknown_type' as any,
        name: '未知节点',
      },
    });

    expect(wrapper.find('.icon-circle-check').exists()).toBe(true);
    expect(wrapper.find('.node-type-label').text()).toBe('unknown_type');
  });

  it('选中状态应该添加高亮样式类', () => {
    const wrapper = mountCard({ selected: true });
    expect(wrapper.find('.workflow-node-card').classes()).toContain('is-selected');
  });

  it('支持通过 data.selected 传递选中状态', () => {
    const wrapper = mountCard({
      data: { node: mockNode, selected: true },
      selected: false,
    });
    expect(wrapper.find('.workflow-node-card').classes()).toContain('is-selected');
  });

  it('hover 时显示前后添加按钮', async () => {
    const wrapper = mountCard();
    expect(wrapper.find('.node-add-before').exists()).toBe(true);
    expect(wrapper.find('.node-add-after').exists()).toBe(true);
  });

  it('只读模式下不显示前后添加按钮', () => {
    const wrapper = mountCard({
      data: { node: mockNode, readonly: true },
    });
    expect(wrapper.find('.node-add-before').exists()).toBe(false);
    expect(wrapper.find('.node-add-after').exists()).toBe(false);
  });

  it('点击前面添加按钮应触发 add-before 事件', async () => {
    const wrapper = mountCard();
    const beforeItems = wrapper.find('.node-add-before').findAll('.el-dropdown-item');
    expect(beforeItems.length).toBeGreaterThan(0);
    await beforeItems[0].trigger('click');

    expect(wrapper.emitted('add-before')).toBeTruthy();
    expect(wrapper.emitted('add-before')![0]).toEqual(['update_record']);
  });

  it('点击后面添加按钮应触发 add-after 事件', async () => {
    const wrapper = mountCard();
    const afterItems = wrapper.find('.node-add-after').findAll('.el-dropdown-item');
    expect(afterItems.length).toBeGreaterThan(0);
    await afterItems[0].trigger('click');

    expect(wrapper.emitted('add-after')).toBeTruthy();
    expect(wrapper.emitted('add-after')![0]).toEqual(['update_record']);
  });

  it('hover 时显示删除按钮', () => {
    const wrapper = mountCard();
    expect(wrapper.find('.node-delete-btn').exists()).toBe(true);
  });

  it('只读模式下不显示删除按钮', () => {
    const wrapper = mountCard({
      data: { node: mockNode, readonly: true },
    });
    expect(wrapper.find('.node-delete-btn').exists()).toBe(false);
  });

  it('点击删除按钮应触发 delete-node 事件', async () => {
    const wrapper = mountCard();
    await wrapper.find('.node-delete-btn').trigger('click');

    expect(wrapper.emitted('delete-node')).toBeTruthy();
  });

  it('条件节点渲染 target handle 和与分支数量一致的 source handle', () => {
    const wrapper = mountCard({
      node: {
        ...mockNode,
        node_type: 'condition',
        config: {
          branches: [
            { id: 'b1', name: '分支 A', conditions: [], conjunction: 'and' },
            { id: 'b2', name: '分支 B', conditions: [], conjunction: 'and' },
          ],
        },
      },
    });

    const handles = wrapper.findAll('.vue-flow__handle');
    // 1 个 target handle（顶部） + 2 个分支 source handle（右侧）
    expect(handles.length).toBe(3);
    expect(wrapper.find('.node-handle-target').exists()).toBe(true);
  });

  it('非条件节点渲染 target handle 和默认 source handle', () => {
    const wrapper = mountCard();
    const handles = wrapper.findAll('.vue-flow__handle');
    // 1 个 target handle（顶部） + 1 个默认 source handle（底部）
    expect(handles.length).toBe(2);
    expect(wrapper.find('.node-handle-target').exists()).toBe(true);
    expect(wrapper.find('.node-handle-source').exists()).toBe(true);
  });

  it('条件节点不渲染默认 source handle', () => {
    const wrapper = mountCard({
      node: {
        ...mockNode,
        node_type: 'condition',
        config: {
          branches: [
            { id: 'b1', name: '分支 A', conditions: [], conjunction: 'and' },
          ],
        },
      },
    });
    // 条件节点只有 target handle + 分支 source handle，没有默认 source handle
    expect(wrapper.find('.node-handle-source').exists()).toBe(false);
  });
});
