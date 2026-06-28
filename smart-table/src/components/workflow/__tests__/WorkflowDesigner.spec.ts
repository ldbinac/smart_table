/**
 * WorkflowDesigner 组件测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { nextTick } from 'vue';
import WorkflowDesigner from '../WorkflowDesigner.vue';

// Mock Sortablejs
const mockSortableDestroy = vi.fn();
let sortableConstructorCallCount = 0;
vi.mock('sortablejs', () => {
  return {
    default: vi.fn(() => {
      sortableConstructorCallCount += 1;
      return {
        destroy: mockSortableDestroy,
      };
    }),
  };
});

// Mock 子组件
vi.mock('../WorkflowNodeConfig.vue', () => ({
  default: {
    name: 'WorkflowNodeConfig',
    template: '<div class="workflow-node-config-mock"><slot /></div>',
    props: ['node', 'fields', 'tables', 'webhooks'],
    emits: ['update:node'],
  },
}));

vi.mock('../WorkflowTriggerConfig.vue', () => ({
  default: {
    name: 'WorkflowTriggerConfig',
    template: '<div class="workflow-trigger-config-mock"><slot /></div>',
    props: ['trigger', 'fields'],
    emits: ['update:trigger'],
  },
}));

// Mock Element Plus 图标
vi.mock('@element-plus/icons-vue', () => ({
  CircleCheck: { template: '<span class="icon-circle-check" />' },
  Share: { template: '<span class="icon-share" />' },
  EditPen: { template: '<span class="icon-edit-pen" />' },
  Plus: { template: '<span class="icon-plus" />' },
  Message: { template: '<span class="icon-message" />' },
  Link: { template: '<span class="icon-link" />' },
  Delete: { template: '<span class="icon-delete" />' },
  Rank: { template: '<span class="icon-rank" />' },
  CircleClose: { template: '<span class="icon-circle-close" />' },
  Timer: { template: '<span class="icon-timer" />' },
  CopyDocument: { template: '<span class="icon-copy-document" />' },
}));

describe('WorkflowDesigner', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sortableConstructorCallCount = 0;
  });

  const mockWorkflow = {
    id: 'wf-1',
    base_id: 'base-1',
    table_id: 'table-1',
    name: '测试工作流',
    status: 'draft' as const,
    current_version: 1,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    is_deleted: false,
  };

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

  const mockNodes = [
    {
      id: 'node-1',
      workflow_id: 'wf-1',
      node_type: 'approval' as const,
      name: '审批节点 1',
      config: {},
      order: 0,
      next_nodes: [],
    },
    {
      id: 'node-2',
      workflow_id: 'wf-1',
      node_type: 'condition' as const,
      name: '条件节点 1',
      config: {},
      order: 1,
      next_nodes: [],
    },
  ];

  function mountDesigner(overrideProps: any = {}) {
    return mount(WorkflowDesigner, {
      props: {
        workflow: overrideProps.workflow ?? mockWorkflow,
        nodes: overrideProps.nodes ?? mockNodes,
        trigger: overrideProps.trigger ?? mockTrigger,
        fields: overrideProps.fields ?? mockFields,
        loading: overrideProps.loading ?? false,
        tables: overrideProps.tables,
        webhooks: overrideProps.webhooks,
      },
      global: {
        stubs: {
          'el-button': {
            template: '<button class="el-button"><slot /></button>',
          },
          'el-icon': { template: '<i class="el-icon"><slot /></i>' },
          'el-tag': { template: '<span class="el-tag"><slot /></span>' },
          'el-empty': { template: '<div class="el-empty"><slot /></div>' },
          'el-dropdown': {
            template: '<div class="el-dropdown"><slot /><slot name="dropdown" /></div>',
          },
          'el-dropdown-menu': { template: '<div class="el-dropdown-menu"><slot /></div>' },
          'el-dropdown-item': {
            template: '<div class="el-dropdown-item"><slot /></div>',
          },
        },
      },
    });
  }

  it('应该正确渲染组件', () => {
    const wrapper = mountDesigner();
    expect(wrapper.exists()).toBe(true);
    expect(wrapper.find('.workflow-designer').exists()).toBe(true);
  });

  it('应该渲染触发器配置区域', () => {
    const wrapper = mountDesigner();
    expect(wrapper.find('.trigger-section').exists()).toBe(true);
    expect(wrapper.find('.workflow-trigger-config-mock').exists()).toBe(true);
  });

  it('应该渲染节点列表', () => {
    const wrapper = mountDesigner();
    const nodeItems = wrapper.findAll('.node-item');
    expect(nodeItems.length).toBe(2);
    expect(nodeItems[0].find('.node-name').text()).toBe('审批节点 1');
    expect(nodeItems[1].find('.node-name').text()).toBe('条件节点 1');
  });

  it('应该默认选中第一个节点', async () => {
    const wrapper = mountDesigner();
    await nextTick();
    const nodeItems = wrapper.findAll('.node-item');
    expect(nodeItems[0].classes()).toContain('active');
  });

  it('点击节点应该切换选中状态', async () => {
    const wrapper = mountDesigner();
    await nextTick();
    const nodeItems = wrapper.findAll('.node-item');
    await nodeItems[1].trigger('click');
    expect(nodeItems[1].classes()).toContain('active');
    expect(nodeItems[0].classes()).not.toContain('active');
  });

  it('点击添加节点菜单应该添加新节点', async () => {
    const wrapper = mountDesigner();
    await nextTick();
    const dropdownItems = wrapper.findAll('.el-dropdown-item');
    expect(dropdownItems.length).toBeGreaterThan(0);
    // 第一个菜单项是审批节点
    await dropdownItems[0].trigger('click');
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    expect(lastNodes.length).toBe(3);
    expect(lastNodes[2].node_type).toBe('approval');
    expect(lastNodes[2].name).toContain('审批节点');
  });

  it('点击删除按钮应该移除节点', async () => {
    const wrapper = mountDesigner();
    await nextTick();
    const deleteButtons = wrapper.findAll('.delete-btn');
    await deleteButtons[0].trigger('click');
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    expect(lastNodes.length).toBe(1);
    expect(lastNodes[0].id).toBe('node-2');
  });

  it('删除最后一个节点后应该清空选中', async () => {
    const wrapper = mountDesigner({ nodes: [mockNodes[0]] });
    await nextTick();
    const deleteButton = wrapper.find('.delete-btn');
    await deleteButton.trigger('click');
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    expect(lastNodes.length).toBe(0);
    expect(wrapper.find('.el-empty').exists()).toBe(true);
  });

  it('子组件更新节点应该触发 update:nodes 事件并同步左侧列表名称', async () => {
    const wrapper = mountDesigner();
    await nextTick();
    const nodeConfig = wrapper.findComponent({ name: 'WorkflowNodeConfig' });
    const updatedNode = { ...mockNodes[0], name: '更新后的节点' };
    await nodeConfig.vm.$emit('update:node', updatedNode);
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    expect(lastNodes[0].name).toBe('更新后的节点');

    // 验证左侧列表 DOM 同步更新
    const nodeItems = wrapper.findAll('.node-item');
    expect(nodeItems[0].find('.node-name').text()).toBe('更新后的节点');
  });

  it('触发器更新应该触发 update:trigger 事件', async () => {
    const wrapper = mountDesigner();
    await nextTick();
    const triggerConfig = wrapper.findComponent({ name: 'WorkflowTriggerConfig' });
    const updatedTrigger = { ...mockTrigger, trigger_type: 'record_updated' as const };
    await triggerConfig.vm.$emit('update:trigger', updatedTrigger);
    await nextTick();

    const emitted = wrapper.emitted('update:trigger') as any[][];
    expect(emitted).toBeTruthy();
    expect(emitted[emitted.length - 1][0]).toMatchObject(updatedTrigger);
  });

  it('点击保存按钮应该触发 save 事件', async () => {
    const wrapper = mountDesigner();
    await nextTick();
    const saveButton = wrapper.findAll('.footer-actions .el-button').find((btn) =>
      btn.text().includes('保存')
    );
    expect(saveButton).toBeTruthy();
    await saveButton!.trigger('click');
    expect(wrapper.emitted('save')).toBeTruthy();
  });

  it('点击发布按钮应该触发 publish 事件', async () => {
    const wrapper = mountDesigner({
      workflow: { ...mockWorkflow, status: 'paused' as const },
    });
    await nextTick();
    const publishButton = wrapper.findAll('.footer-actions .el-button').find((btn) =>
      btn.text().includes('发布')
    );
    expect(publishButton).toBeTruthy();
    await publishButton!.trigger('click');
    expect(wrapper.emitted('publish')).toBeTruthy();
  });

  it('应该根据工作流状态显示草稿标签', () => {
    const wrapper = mountDesigner();
    const statusTag = wrapper.find('.workflow-status .el-tag');
    expect(statusTag.text()).toContain('草稿');
  });

  it('已发布工作流应该显示已发布标签', () => {
    const wrapper = mountDesigner({
      workflow: { ...mockWorkflow, status: 'active' as const },
    });
    const statusTag = wrapper.find('.workflow-status .el-tag');
    expect(statusTag.text()).toContain('已发布');
  });

  it('加载状态应该应用 loading 指令', async () => {
    const wrapper = mountDesigner({ loading: true });
    await nextTick();
    expect(wrapper.find('.workflow-designer').classes()).toContain('is-loading');
  });

  it('初始化时应该创建 Sortable 实例', async () => {
    mountDesigner();
    await flushPromises();
    expect(sortableConstructorCallCount).toBeGreaterThan(0);
  });

  it('节点列表变化时应该重新初始化 Sortable', async () => {
    const wrapper = mountDesigner({ nodes: [] });
    await flushPromises();
    const callCount = sortableConstructorCallCount;

    await wrapper.setProps({ nodes: mockNodes });
    await flushPromises();
    expect(sortableConstructorCallCount).toBeGreaterThan(callCount);
  });
});
