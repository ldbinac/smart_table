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
    props: ['node', 'fields', 'tables', 'webhooks', 'allNodes', 'readonly'],
    emits: ['update:node', 'add-child-node', 'remove-child-node', 'select-child-node'],
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
  Search: { template: '<span class="icon-search" />' },
  Refresh: { template: '<span class="icon-refresh" />' },
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
      node_type: 'send_email' as const,
      name: '发送邮件 1',
      config: {},
      order: 0,
      next_nodes: [],
    },
    {
      id: 'node-2',
      workflow_id: 'wf-1',
      node_type: 'update_record' as const,
      name: '更新记录 1',
      config: { updates: [{ field_id: 'field-1', value_template: '' }] },
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
    expect(nodeItems[0].find('.node-name').text()).toBe('发送邮件 1');
    expect(nodeItems[1].find('.node-name').text()).toBe('更新记录 1');
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

  it('添加 find_records 节点时应初始化默认配置', async () => {
    const workflowWithTable = {
      ...mockWorkflow,
      table_id: 'default-table-id',
    };
    const wrapper = mountDesigner({ workflow: workflowWithTable });
    await nextTick();
    const dropdownItems = wrapper.findAll('.el-dropdown-item');
    // 第三个菜单项是查找记录节点
    const findRecordsItem = dropdownItems.find(
      (item) => item.text().trim() === '查找记录'
    );
    expect(findRecordsItem).toBeTruthy();
    await findRecordsItem!.trigger('click');
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    const newNode = lastNodes[lastNodes.length - 1];
    expect(newNode.node_type).toBe('find_records');
    expect(newNode.config.target_table_id).toBe('default-table-id');
    expect(newNode.config.result_variable).toBe('records');
    expect(newNode.config.conditions).toEqual([]);
    expect(newNode.config.sort_direction).toBe('asc');
    expect(newNode.config.limit).toBe(100);
    expect(newNode.config.empty_action).toBe('continue');
  });

  it('添加节点菜单应包含发送邮件选项', async () => {
    const wrapper = mountDesigner();
    await nextTick();
    const dropdownItems = wrapper.findAll('.el-dropdown-item');
    const sendEmailItem = dropdownItems.find(
      (item) => item.text().trim() === '发送邮件'
    );
    expect(sendEmailItem).toBeTruthy();
    await sendEmailItem!.trigger('click');
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    const newNode = lastNodes[lastNodes.length - 1];
    expect(newNode.node_type).toBe('send_email');
    expect(newNode.name).toContain('发送邮件');
  });

  it('find_records 节点使用默认配置时保存应通过', async () => {
    const alertMock = vi.spyOn(ElMessageBox, 'alert').mockResolvedValue(undefined as any);
    const workflowWithTable = {
      ...mockWorkflow,
      table_id: 'default-table-id',
    };
    const wrapper = mountDesigner({ workflow: workflowWithTable });
    await nextTick();
    const dropdownItems = wrapper.findAll('.el-dropdown-item');
    const findRecordsItem = dropdownItems.find(
      (item) => item.text().trim() === '查找记录'
    );
    await findRecordsItem!.trigger('click');
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

  it('在条件节点后面添加节点时自动分配到可用分支', async () => {
    const nodes: any[] = [
      {
        id: 'cond-1',
        workflow_id: 'wf-1',
        node_type: 'condition',
        name: '条件节点',
        config: {
          branches: [
            { id: 'b1', name: '分支 A', conditions: [{ field_id: 'f1', operator: 'equals', value: 'a' }], conjunction: 'and' },
            { id: 'b2', name: '分支 B', conditions: [{ field_id: 'f1', operator: 'equals', value: 'b' }], conjunction: 'and' },
          ],
        },
        order: 0,
        next_nodes: [],
      },
    ];
    const wrapper = mountDesigner({ nodes });
    await switchToCanvas(wrapper);
    const canvas = wrapper.findComponent({ name: 'WorkflowCanvas' });
    await canvas.vm.$emit('add-node', { position: 'after', nodeType: 'update_record', targetId: 'cond-1' });
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    expect(lastNodes.length).toBe(2);

    const conditionNode = lastNodes.find((n) => n.id === 'cond-1');
    const newNode = lastNodes.find((n) => n.node_type === 'update_record');
    expect(newNode).toBeTruthy();

    // 第一个分支应自动指向新节点
    expect(conditionNode.config.branches[0].target_node_id).toBe(newNode!.id);
    expect(conditionNode.config.branches[1].target_node_id).toBeUndefined();
    expect(conditionNode.next_nodes).toContain(newNode!.id);
  });

  it('为条件节点添加多个分支目标时保持独立并行关系', async () => {
    const nodes: any[] = [
      {
        id: 'cond-1',
        workflow_id: 'wf-1',
        node_type: 'condition',
        name: '条件节点',
        config: {
          branches: [
            { id: 'b1', name: '分支 A', conditions: [{ field_id: 'f1', operator: 'equals', value: 'a' }], conjunction: 'and' },
            { id: 'b2', name: '分支 B', conditions: [{ field_id: 'f1', operator: 'equals', value: 'b' }], conjunction: 'and' },
          ],
        },
        order: 0,
        next_nodes: [],
      },
    ];
    const wrapper = mountDesigner({ nodes });
    await switchToCanvas(wrapper);
    const canvas = wrapper.findComponent({ name: 'WorkflowCanvas' });

    // 添加第一个分支目标
    await canvas.vm.$emit('add-node', { position: 'after', nodeType: 'update_record', targetId: 'cond-1' });
    await nextTick();

    // 添加第二个分支目标
    await canvas.vm.$emit('add-node', { position: 'after', nodeType: 'create_record', targetId: 'cond-1' });
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    expect(lastNodes.length).toBe(3);

    const conditionNode = lastNodes.find((n) => n.id === 'cond-1');
    const branchNodes = lastNodes.filter((n) => n.id !== 'cond-1');
    expect(branchNodes.length).toBe(2);

    // 两个分支分别指向不同的目标节点（不依赖节点顺序）
    const branch0Target = conditionNode.config.branches[0].target_node_id;
    const branch1Target = conditionNode.config.branches[1].target_node_id;
    expect(branch0Target).toBeTruthy();
    expect(branch1Target).toBeTruthy();
    expect(branch0Target).not.toBe(branch1Target);
    expect(branchNodes.map((n: any) => n.id)).toEqual(
      expect.arrayContaining([branch0Target, branch1Target]),
    );
    expect(conditionNode.next_nodes).toEqual(
      expect.arrayContaining([branch0Target, branch1Target]),
    );

    // 两个分支目标节点应保持独立，不互相串联
    branchNodes.forEach((branchNode: any) => {
      expect(branchNode.next_nodes).toEqual([]);
      branchNodes.forEach((other: any) => {
        if (other.id !== branchNode.id) {
          expect(branchNode.next_nodes).not.toContain(other.id);
        }
      });
    });
  });

  it('条件分支目标节点不被 rebuildNodeChain 串联', async () => {
    const nodes: any[] = [
      {
        id: 'cond-1',
        workflow_id: 'wf-1',
        node_type: 'condition',
        name: '条件节点',
        config: {
          branches: [
            { id: 'b1', name: '分支 A', conditions: [{ field_id: 'f1', operator: 'equals', value: 'a' }], conjunction: 'and', target_node_id: 'branch-a' },
            { id: 'b2', name: '分支 B', conditions: [{ field_id: 'f1', operator: 'equals', value: 'b' }], conjunction: 'and', target_node_id: 'branch-b' },
          ],
        },
        order: 0,
        next_nodes: ['branch-a', 'branch-b'],
      },
      {
        id: 'branch-a',
        workflow_id: 'wf-1',
        node_type: 'update_record',
        name: '分支 A 目标',
        config: { updates: [{ field_id: 'f1', value_template: '' }] },
        order: 1,
        next_nodes: [],
      },
      {
        id: 'branch-b',
        workflow_id: 'wf-1',
        node_type: 'create_record',
        name: '分支 B 目标',
        config: { target_table_id: 't1', field_mappings: [{ target_field_id: 'f1', source_field_id: '', value_template: '' }] },
        order: 2,
        next_nodes: [],
      },
    ];
    const wrapper = mountDesigner({ nodes });
    await switchToCanvas(wrapper);
    const canvas = wrapper.findComponent({ name: 'WorkflowCanvas' });
    const canvasNodes = canvas.props('nodes') as any[];

    const branchA = canvasNodes.find((n) => n.id === 'branch-a');
    const branchB = canvasNodes.find((n) => n.id === 'branch-b');

    // 分支目标节点不应被互相串联
    expect(branchA.next_nodes).not.toContain('branch-b');
    expect(branchB.next_nodes).not.toContain('branch-a');
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

  it('删除被条件节点指向的节点会清空对应分支目标', async () => {
    const nodes: any[] = [
      {
        id: 'n1',
        workflow_id: 'wf-1',
        node_type: 'condition',
        name: '条件',
        config: {
          branches: [
            { id: 'b1', name: 'B1', conditions: [{ field_id: 'f1', operator: 'equals', value: 'a' }], conjunction: 'and', target_node_id: 'n2' },
          ],
        },
        order: 0,
        next_nodes: ['n2'],
      },
      {
        id: 'n2',
        workflow_id: 'wf-1',
        node_type: 'update_record',
        name: '更新',
        config: { updates: [{ field_id: 'f1', value_template: '' }] },
        order: 1,
        next_nodes: [],
      },
    ];
    const wrapper = mountDesigner({ nodes });
    await nextTick();

    const deleteBtn = wrapper.find('.node-item[data-node-id="n2"] .delete-btn');
    await deleteBtn.trigger('click');
    await nextTick();

    const emitted = wrapper.emitted('update:nodes') as any[][];
    expect(emitted).toBeTruthy();
    const lastNodes = emitted[emitted.length - 1][0] as any[];
    const conditionNode = lastNodes.find((n) => n.id === 'n1');
    expect(conditionNode.config.branches[0].target_node_id).toBeUndefined();
    expect(conditionNode.next_nodes).toEqual([]);
  });

  it('条件节点存在空条件分支时保存被阻止', async () => {
    const nodes: any[] = [
      {
        id: 'n1',
        workflow_id: 'wf-1',
        node_type: 'condition',
        name: '条件',
        config: {
          branches: [
            { id: 'b1', name: 'B1', conditions: [], conjunction: 'and' },
          ],
        },
        order: 0,
        next_nodes: [],
      },
    ];
    const wrapper = mountDesigner({ nodes });
    await nextTick();

    expect((wrapper.vm as any).hasInvalidMappingNodes).toBe(true);
  });

  it('find_records 节点变量名非法时保存被阻止并提示具体原因', async () => {
    const alertMock = vi.spyOn(ElMessageBox, 'alert').mockResolvedValue(undefined as any);
    const wrapper = mountDesigner({
      nodes: [
        {
          id: 'node-1',
          workflow_id: 'wf-1',
          node_type: 'find_records' as const,
          name: '查找记录 1',
          config: {
            target_table_id: 'table-1',
            result_variable: '123invalid',
            conditions: [],
          },
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
    expect(alertMock.mock.calls[0][0]).toContain('结果变量名格式不正确');
    expect(alertMock.mock.calls[0][1]).toBe('节点配置不完整');
    expect(wrapper.emitted('save')).toBeFalsy();
    alertMock.mockRestore();
  });

  it('find_records 节点目标表格未选择时保存被阻止并提示具体原因', async () => {
    const alertMock = vi.spyOn(ElMessageBox, 'alert').mockResolvedValue(undefined as any);
    const wrapper = mountDesigner({
      nodes: [
        {
          id: 'node-1',
          workflow_id: 'wf-1',
          node_type: 'find_records' as const,
          name: '查找记录 1',
          config: {
            target_table_id: '',
            result_variable: 'records',
            conditions: [],
          },
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
    expect(alertMock.mock.calls[0][0]).toContain('目标表格未选择');
    expect(alertMock.mock.calls[0][1]).toBe('节点配置不完整');
    expect(wrapper.emitted('save')).toBeFalsy();
    alertMock.mockRestore();
  });
});
