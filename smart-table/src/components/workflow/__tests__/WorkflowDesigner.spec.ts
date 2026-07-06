/**
 * WorkflowDesigner 组件测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { nextTick } from 'vue';
import { ElMessageBox } from 'element-plus';
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

vi.mock('../WorkflowCanvas.vue', () => ({
  default: {
    name: 'WorkflowCanvas',
    template: '<div class="workflow-canvas-stub"><slot /></div>',
    props: ['nodes', 'readonly', 'selectedNodeId'],
    emits: ['update:nodes', 'select-node', 'node-drag-stop', 'edge-insert', 'add-node', 'delete-node'],
    setup(_props: any, { expose }: any) {
      expose({
        fitView: vi.fn(),
        zoomIn: vi.fn(),
        zoomOut: vi.fn(),
      });
      return {};
    },
  },
}));

vi.mock('../WorkflowCanvasToolbar.vue', () => ({
  default: {
    name: 'WorkflowCanvasToolbar',
    template: `
      <div class="workflow-canvas-toolbar-stub">
        <button class="toolbar-zoom-in" @click="$emit('zoom-in')">+</button>
        <button class="toolbar-zoom-out" @click="$emit('zoom-out')">-</button>
        <button class="toolbar-fit-view" @click="$emit('fit-view')">fit</button>
        <button class="toolbar-toggle-pan" @click="$emit('toggle-pan-mode')">pan</button>
      </div>
    `,
    props: ['panMode'],
    emits: ['zoom-in', 'zoom-out', 'fit-view', 'toggle-pan-mode'],
  },
}));

// Mock vue-router
vi.mock('vue-router', () => ({
  onBeforeRouteLeave: vi.fn((guard) => {
    (globalThis as any).__testRouteGuard = guard;
  }),
  useRoute: () => ({}),
  useRouter: () => ({}),
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
  const mockNext = vi.fn();

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
          'el-button-group': {
            template: '<div class="el-button-group"><slot /></div>',
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
    // 第一个菜单项是更新记录节点
    await dropdownItems[0].trigger('click');
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    expect(lastNodes.length).toBe(3);
    expect(lastNodes[2].node_type).toBe('update_record');
    expect(lastNodes[2].name).toContain('更新记录');
    // 验证自动维护 next_nodes 执行链
    expect(lastNodes[0].next_nodes).toEqual([lastNodes[1].id]);
    expect(lastNodes[1].next_nodes).toEqual([lastNodes[2].id]);
    expect(lastNodes[2].next_nodes).toEqual([]);
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

  it('暂停状态显示保存按钮并触发 save 事件', async () => {
    const wrapper = mountDesigner({
      workflow: { ...mockWorkflow, status: 'paused' as const },
    });
    await nextTick();
    const saveButton = wrapper.findAll('.footer-actions .el-button').find((btn) =>
      btn.text().includes('保存')
    );
    expect(saveButton).toBeTruthy();
    await saveButton!.trigger('click');
    expect(wrapper.emitted('save')).toBeTruthy();
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

  it('create_record 节点未配置字段映射时保存应弹窗并阻止 save 事件', async () => {
    const alertMock = vi.spyOn(ElMessageBox, 'alert').mockResolvedValue(undefined as any);
    const wrapper = mountDesigner({
      nodes: [
        {
          id: 'node-1',
          workflow_id: 'wf-1',
          node_type: 'create_record' as const,
          name: '创建记录 1',
          config: { target_table_id: 'table-1', field_mappings: [] },
          order: 0,
          next_nodes: [],
        },
      ],
    });
    await nextTick();

    const saveButton = wrapper.findAll('.footer-actions .el-button').find((btn) =>
      btn.text().includes('保存')
    );
    await saveButton!.trigger('click');
    await flushPromises();

    expect(alertMock).toHaveBeenCalled();
    expect(wrapper.emitted('save')).toBeFalsy();
    alertMock.mockRestore();
  });

  it('update_record 节点未配置字段映射时保存应弹窗并阻止 save 事件', async () => {
    const alertMock = vi.spyOn(ElMessageBox, 'alert').mockResolvedValue(undefined as any);
    const wrapper = mountDesigner({
      nodes: [
        {
          id: 'node-1',
          workflow_id: 'wf-1',
          node_type: 'update_record' as const,
          name: '更新记录 1',
          config: { updates: [] },
          order: 0,
          next_nodes: [],
        },
      ],
    });
    await nextTick();

    const saveButton = wrapper.findAll('.footer-actions .el-button').find((btn) =>
      btn.text().includes('保存')
    );
    await saveButton!.trigger('click');
    await flushPromises();

    expect(alertMock).toHaveBeenCalled();
    expect(wrapper.emitted('save')).toBeFalsy();
    alertMock.mockRestore();
  });

  it('多个节点未配置映射时弹窗内容应列出所有节点名称', async () => {
    const alertMock = vi.spyOn(ElMessageBox, 'alert').mockResolvedValue(undefined as any);
    const wrapper = mountDesigner({
      nodes: [
        {
          id: 'node-1',
          workflow_id: 'wf-1',
          node_type: 'create_record' as const,
          name: '创建记录 1',
          config: { target_table_id: 'table-1', field_mappings: [] },
          order: 0,
          next_nodes: [],
        },
        {
          id: 'node-2',
          workflow_id: 'wf-1',
          node_type: 'update_record' as const,
          name: '更新记录 2',
          config: { updates: [] },
          order: 1,
          next_nodes: [],
        },
      ],
    });
    await nextTick();

    const saveButton = wrapper.findAll('.footer-actions .el-button').find((btn) =>
      btn.text().includes('保存')
    );
    await saveButton!.trigger('click');
    await flushPromises();

    const [message] = alertMock.mock.calls[0];
    expect(String(message)).toContain('创建记录 1');
    expect(String(message)).toContain('更新记录 2');
    alertMock.mockRestore();
  });

  it('create_record 与 update_record 均配置映射时保存正常触发 save 事件', async () => {
    const alertMock = vi.spyOn(ElMessageBox, 'alert').mockResolvedValue(undefined as any);
    const wrapper = mountDesigner({
      nodes: [
        {
          id: 'node-1',
          workflow_id: 'wf-1',
          node_type: 'create_record' as const,
          name: '创建记录 1',
          config: {
            target_table_id: 'table-1',
            field_mappings: [{ target_field_id: 'field-1', source_field_id: '', value_template: '' }],
          },
          order: 0,
          next_nodes: [],
        },
        {
          id: 'node-2',
          workflow_id: 'wf-1',
          node_type: 'update_record' as const,
          name: '更新记录 2',
          config: {
            updates: [{ field_id: 'field-1', value_template: '' }],
          },
          order: 1,
          next_nodes: [],
        },
      ],
    });
    await nextTick();

    const saveButton = wrapper.findAll('.footer-actions .el-button').find((btn) =>
      btn.text().includes('保存')
    );
    await saveButton!.trigger('click');
    await flushPromises();

    expect(alertMock).not.toHaveBeenCalled();
    expect(wrapper.emitted('save')).toBeTruthy();
    alertMock.mockRestore();
  });

  it('存在未配置映射节点时路由离开应弹出确认', async () => {
    const confirmMock = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue(undefined as any);
    mountDesigner({
      nodes: [
        {
          id: 'node-1',
          workflow_id: 'wf-1',
          node_type: 'create_record' as const,
          name: '创建记录 1',
          config: { target_table_id: 'table-1', field_mappings: [] },
          order: 0,
          next_nodes: [],
        },
      ],
    });
    await nextTick();

    const guard = (globalThis as any).__testRouteGuard;
    expect(guard).toBeDefined();
    guard({}, {}, mockNext);

    expect(confirmMock).toHaveBeenCalled();
    confirmMock.mockRestore();
  });

  it('存在未配置映射节点时 beforeunload 事件应阻止默认行为', async () => {
    mountDesigner({
      nodes: [
        {
          id: 'node-1',
          workflow_id: 'wf-1',
          node_type: 'create_record' as const,
          name: '创建记录 1',
          config: { target_table_id: 'table-1', field_mappings: [] },
          order: 0,
          next_nodes: [],
        },
      ],
    });
    await nextTick();

    const event = new Event('beforeunload', { cancelable: true });
    const preventDefaultSpy = vi.spyOn(event, 'preventDefault');
    window.dispatchEvent(event);

    expect(preventDefaultSpy).toHaveBeenCalled();
    preventDefaultSpy.mockRestore();
  });

  async function switchToCanvas(wrapper: ReturnType<typeof mountDesigner>) {
    const canvasButton = wrapper.findAll('.el-button').find((btn) =>
      btn.text().includes('画布')
    );
    expect(canvasButton).toBeTruthy();
    await canvasButton!.trigger('click');
    await nextTick();
  }

  it('默认视图为列表视图', () => {
    const wrapper = mountDesigner();
    expect(wrapper.find('.trigger-section').exists()).toBe(true);
    expect(wrapper.find('.workflow-canvas-stub').exists()).toBe(false);
  });

  it('切换到画布视图应渲染画布', async () => {
    const wrapper = mountDesigner();
    await switchToCanvas(wrapper);
    expect(wrapper.find('.workflow-canvas-stub').exists()).toBe(true);
    expect(wrapper.find('.trigger-section').exists()).toBe(false);
  });

  it('画布中选中节点应更新右侧面板', async () => {
    const wrapper = mountDesigner();
    await switchToCanvas(wrapper);
    const canvas = wrapper.findComponent({ name: 'WorkflowCanvas' });
    await canvas.vm.$emit('select-node', 'node-2');
    await nextTick();

    const nodeConfig = wrapper.findComponent({ name: 'WorkflowNodeConfig' });
    expect(nodeConfig.props('node').id).toBe('node-2');
  });

  it('切换视图时保留当前选中节点', async () => {
    const wrapper = mountDesigner();
    await nextTick();
    const nodeItems = wrapper.findAll('.node-item');
    await nodeItems[1].trigger('click');
    await nextTick();
    expect(nodeItems[1].classes()).toContain('active');

    await switchToCanvas(wrapper);
    const canvas = wrapper.findComponent({ name: 'WorkflowCanvas' });
    expect(canvas.props('selectedNodeId')).toBe('node-2');

    const listButton = wrapper.findAll('.el-button').find((btn) =>
      btn.text().includes('列表')
    );
    expect(listButton).toBeTruthy();
    await listButton!.trigger('click');
    await nextTick();
    expect(wrapper.findAll('.node-item')[1].classes()).toContain('active');
  });

  it('缺少 ui_layout 的节点加载后自动布局', async () => {
    const wrapper = mountDesigner({ nodes: mockNodes });
    await switchToCanvas(wrapper);
    const canvas = wrapper.findComponent({ name: 'WorkflowCanvas' });
    const nodes = canvas.props('nodes') as any[];
    expect(nodes.length).toBe(mockNodes.length);
    expect(nodes.every((node) => node.ui_layout && typeof node.ui_layout.x === 'number')).toBe(true);
  });

  it('画布中拖拽节点应持久化 ui_layout', async () => {
    const wrapper = mountDesigner();
    await switchToCanvas(wrapper);
    const canvas = wrapper.findComponent({ name: 'WorkflowCanvas' });
    const updatedNodes = mockNodes.map((node) =>
      node.id === 'node-1' ? { ...node, ui_layout: { x: 120, y: 200 } } : node
    );
    await canvas.vm.$emit('update:nodes', updatedNodes);
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    const node1 = lastNodes.find((node) => node.id === 'node-1');
    expect(node1.ui_layout).toEqual({ x: 120, y: 200 });
  });

  it('通过画布边线按钮插入节点', async () => {
    const wrapper = mountDesigner();
    await switchToCanvas(wrapper);
    const canvas = wrapper.findComponent({ name: 'WorkflowCanvas' });
    await canvas.vm.$emit('edge-insert', { sourceId: 'node-1', targetId: 'node-2', nodeType: 'webhook' });
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    expect(lastNodes.length).toBe(3);

    const newNode = lastNodes.find((node) => node.node_type === 'webhook');
    expect(newNode).toBeTruthy();

    const sourceIndex = lastNodes.findIndex((node) => node.id === 'node-1');
    const newIndex = lastNodes.findIndex((node) => node.id === newNode!.id);
    const targetIndex = lastNodes.findIndex((node) => node.id === 'node-2');
    expect(sourceIndex).toBeLessThan(newIndex);
    expect(newIndex).toBeLessThan(targetIndex);

    const sourceNode = lastNodes[sourceIndex];
    expect(sourceNode.next_nodes).toContain(newNode!.id);
    expect(newNode!.next_nodes).toContain('node-2');
  });

  it('在空白画布添加第一个节点', async () => {
    const wrapper = mountDesigner({ nodes: [] });
    await switchToCanvas(wrapper);
    const canvas = wrapper.findComponent({ name: 'WorkflowCanvas' });
    await canvas.vm.$emit('add-node', { position: 'first', nodeType: 'create_record' });
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    expect(lastNodes.length).toBe(1);
    expect(lastNodes[0].node_type).toBe('create_record');
    expect(lastNodes[0].order).toBe(0);
    expect(lastNodes[0].next_nodes).toEqual([]);

    const nodeConfig = wrapper.findComponent({ name: 'WorkflowNodeConfig' });
    expect(nodeConfig.props('node').id).toBe(lastNodes[0].id);
  });

  it('在已有节点前面添加节点', async () => {
    const wrapper = mountDesigner();
    await switchToCanvas(wrapper);
    const canvas = wrapper.findComponent({ name: 'WorkflowCanvas' });
    await canvas.vm.$emit('add-node', { position: 'before', nodeType: 'webhook', targetId: 'node-2' });
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    expect(lastNodes.length).toBe(3);

    const newNode = lastNodes.find((node) => node.node_type === 'webhook');
    expect(newNode).toBeTruthy();

    const newIndex = lastNodes.findIndex((node) => node.id === newNode!.id);
    const targetIndex = lastNodes.findIndex((node) => node.id === 'node-2');
    expect(newIndex).toBeLessThan(targetIndex);
    expect(newNode!.next_nodes).toContain('node-2');
  });

  it('在已有节点后面添加节点', async () => {
    const wrapper = mountDesigner();
    await switchToCanvas(wrapper);
    const canvas = wrapper.findComponent({ name: 'WorkflowCanvas' });
    await canvas.vm.$emit('add-node', { position: 'after', nodeType: 'update_record', targetId: 'node-1' });
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    expect(lastNodes.length).toBe(3);

    const newNode = lastNodes.find((node) => node.node_type === 'update_record');
    expect(newNode).toBeTruthy();

    const targetIndex = lastNodes.findIndex((node) => node.id === 'node-1');
    const newIndex = lastNodes.findIndex((node) => node.id === newNode!.id);
    expect(targetIndex).toBeLessThan(newIndex);
    expect(lastNodes[targetIndex].next_nodes).toContain(newNode!.id);
    expect(newNode!.next_nodes).toContain('node-2');
  });

  it('从画布删除节点应更新节点列表', async () => {
    const wrapper = mountDesigner();
    await switchToCanvas(wrapper);
    const canvas = wrapper.findComponent({ name: 'WorkflowCanvas' });
    await canvas.vm.$emit('delete-node', 'node-1');
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    expect(lastNodes.length).toBe(1);
    expect(lastNodes[0].id).toBe('node-2');
  });

  it('画布工具栏按钮应调用画布方法', async () => {
    const wrapper = mountDesigner();
    await switchToCanvas(wrapper);
    const canvas = wrapper.findComponent({ name: 'WorkflowCanvas' });
    const toolbar = wrapper.findComponent({ name: 'WorkflowCanvasToolbar' });

    await toolbar.vm.$emit('zoom-in');
    await toolbar.vm.$emit('zoom-out');
    await toolbar.vm.$emit('fit-view');

    expect(canvas.vm.zoomIn).toHaveBeenCalled();
    expect(canvas.vm.zoomOut).toHaveBeenCalled();
    expect(canvas.vm.fitView).toHaveBeenCalled();
  });

  it('画布抓手模式状态可切换', async () => {
    const wrapper = mountDesigner();
    await switchToCanvas(wrapper);
    const toolbar = wrapper.findComponent({ name: 'WorkflowCanvasToolbar' });
    expect(toolbar.props('panMode')).toBe(false);

    await toolbar.vm.$emit('toggle-pan-mode');
    await nextTick();
    expect(wrapper.findComponent({ name: 'WorkflowCanvasToolbar' }).props('panMode')).toBe(true);
  });

  it('已发布工作流在画布中应只读', async () => {
    const wrapper = mountDesigner({
      workflow: { ...mockWorkflow, status: 'active' as const },
    });
    await switchToCanvas(wrapper);
    const canvas = wrapper.findComponent({ name: 'WorkflowCanvas' });
    expect(canvas.props('readonly')).toBe(true);
  });

  it('列表视图和画布视图均显示可拖拽分隔条', () => {
    const wrapper = mountDesigner();
    expect(wrapper.find('.designer-splitter').exists()).toBe(true);

    switchToCanvas(wrapper);
    expect(wrapper.find('.designer-splitter').exists()).toBe(true);
  });

  it('画布视图下左右面板默认各占 50%', async () => {
    const wrapper = mountDesigner();
    await switchToCanvas(wrapper);
    const left = wrapper.find('.designer-left');
    const right = wrapper.find('.designer-right');
    expect(left.attributes('style')).toContain('flex: 0 0 50%');
    expect(right.attributes('style')).toContain('flex: 0 0 50%');
  });

  it('mousedown 时分隔条添加 is-resizing 类，mouseup 后移除', async () => {
    const wrapper = mountDesigner();
    const splitter = wrapper.find('.designer-splitter');
    await splitter.trigger('mousedown', { clientX: 100 });
    expect(splitter.classes()).toContain('is-resizing');

    document.dispatchEvent(new MouseEvent('mouseup'));
    await nextTick();
    expect(wrapper.find('.designer-splitter').classes()).not.toContain('is-resizing');
  });

  it('拖拽分隔条可调整画布视图左右面板宽度', async () => {
    const wrapper = mountDesigner();
    await switchToCanvas(wrapper);
    const layout = wrapper.find('.designer-layout').element;
    Object.defineProperty(layout, 'clientWidth', { value: 1000, configurable: true });

    const splitter = wrapper.find('.designer-splitter');
    await splitter.trigger('mousedown', { clientX: 500 });
    document.dispatchEvent(new MouseEvent('mousemove', { clientX: 700 }));
    await nextTick();

    const left = wrapper.find('.designer-left');
    expect(left.attributes('style')).toContain('flex: 0 0 70%');

    const right = wrapper.find('.designer-right');
    expect(right.attributes('style')).toContain('flex: 0 0 30%');

    document.dispatchEvent(new MouseEvent('mouseup'));
  });

  it('拖拽分隔条可调整列表视图左侧面板宽度', async () => {
    const wrapper = mountDesigner();
    const layout = wrapper.find('.designer-layout').element;
    Object.defineProperty(layout, 'clientWidth', { value: 1000, configurable: true });

    const splitter = wrapper.find('.designer-splitter');
    await splitter.trigger('mousedown', { clientX: 360 });
    document.dispatchEvent(new MouseEvent('mousemove', { clientX: 500 }));
    await nextTick();

    const left = wrapper.find('.designer-left');
    expect(left.attributes('style')).toContain('flex: 0 0 500px');

    document.dispatchEvent(new MouseEvent('mouseup'));
  });
});
