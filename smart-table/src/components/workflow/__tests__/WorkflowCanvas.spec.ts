import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import type { WorkflowNode } from '@/types/workflow'
// @ts-expect-error 该成员由 vi.mock 工厂注入，仅用于测试
import { __testMocks as flowMocks } from '@vue-flow/core'
import WorkflowCanvas from '../WorkflowCanvas.vue'

vi.mock('@vue-flow/core', async () => {
  const vue = await import('vue')
  const { h, defineComponent } = vue

  const testMocks = {
    fitView: vi.fn(),
    zoomIn: vi.fn(),
    zoomOut: vi.fn(),
  }

  const VueFlow = defineComponent({
    name: 'VueFlow',
    props: {
      nodes: {
        type: Array as any,
        default: () => [],
      },
      edges: {
        type: Array as any,
        default: () => [],
      },
    },
    emits: ['nodeClick', 'nodeDragStop', 'edgeClick'],
    setup(props, { expose, slots }) {
      expose({
        fitView: testMocks.fitView,
        zoomIn: testMocks.zoomIn,
        zoomOut: testMocks.zoomOut,
      })

      return () =>
        h('div', { class: 'vue-flow-stub' }, [
          slots.default?.(),
          h(
            'div',
            { class: 'vue-flow-nodes' },
            (props.nodes as any[]).map((node) =>
              h('div', {
                key: node.id,
                class: ['vue-flow-node-stub', node.class],
                'data-node-id': node.id,
              }, node.data?.node?.name ?? node.id),
            ),
          ),
          h(
            'div',
            { class: 'vue-flow-edges' },
            (props.edges as any[]).map((edge) =>
              h('div', {
                key: edge.id,
                class: 'vue-flow-edge-stub',
                'data-edge-id': edge.id,
              }, edge.label),
            ),
          ),
        ])
    },
  })

  return {
    VueFlow,
    __testMocks: testMocks,
  }
})

vi.mock('@vue-flow/background', async () => {
  const vue = await import('vue')
  const { h, defineComponent } = vue
  return {
    Background: defineComponent({
      name: 'Background',
      render: () => h('div', { class: 'background-stub' }),
    }),
  }
})

vi.mock('@vue-flow/controls', async () => {
  const vue = await import('vue')
  const { h, defineComponent } = vue
  return {
    Controls: defineComponent({
      name: 'Controls',
      render: () => h('div', { class: 'controls-stub' }),
    }),
  }
})

const mockNodes: WorkflowNode[] = [
  {
    id: 'node-1',
    workflow_id: 'wf-1',
    node_type: 'send_email',
    name: '发送邮件节点',
    config: {},
    order: 0,
    next_nodes: ['node-2'],
    ui_layout: { x: 10, y: 20 },
  },
  {
    id: 'node-2',
    workflow_id: 'wf-1',
    node_type: 'condition',
    name: '条件节点',
    config: {
      branches: [
        { id: 'b1', name: '满足条件', conditions: [], conjunction: 'and', target_node_id: 'node-3' },
        { id: 'b2', name: '其他分支', conditions: [], conjunction: 'and' },
      ],
    },
    order: 1,
    next_nodes: ['node-3'],
  },
  {
    id: 'node-3',
    workflow_id: 'wf-1',
    node_type: 'update_record',
    name: '更新记录',
    config: {},
    order: 2,
    next_nodes: [],
  },
]

function mountCanvas(props: Record<string, any> = {}) {
  return mount(WorkflowCanvas, {
    props: {
      nodes: mockNodes,
      ...props,
    },
    global: {
      stubs: {
        'el-button': {
          template: '<button class="el-button"><slot /></button>',
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
      },
    },
  })
}

describe('WorkflowCanvas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该正确渲染画布、节点和连线', () => {
    const wrapper = mountCanvas()

    expect(wrapper.find('.workflow-canvas').exists()).toBe(true)
    expect(wrapper.find('.vue-flow-stub').exists()).toBe(true)
    expect(wrapper.find('.background-stub').exists()).toBe(true)
    expect(wrapper.find('.controls-stub').exists()).toBe(true)

    const nodeStubs = wrapper.findAll('.vue-flow-node-stub')
    expect(nodeStubs.length).toBe(3)
    expect(nodeStubs[0].attributes('data-node-id')).toBe('node-1')

    const edgeStubs = wrapper.findAll('.vue-flow-edge-stub')
    expect(edgeStubs.length).toBe(2)
    expect(edgeStubs[0].attributes('data-edge-id')).toBe('e-node-1-node-2')
  })

  it('条件节点的连线应该显示"满足条件"标签', () => {
    const wrapper = mountCanvas()
    const edgeStubs = wrapper.findAll('.vue-flow-edge-stub')
    expect(edgeStubs[0].text()).toBe('')
    expect(edgeStubs[1].text()).toBe('满足条件')
  })

  it('点击节点应该触发 select-node 事件', async () => {
    const wrapper = mountCanvas()
    const vueFlow = wrapper.findComponent({ name: 'VueFlow' })

    await vueFlow.vm.$emit('nodeClick', {
      node: { id: 'node-2', position: { x: 0, y: 0 }, data: { node: mockNodes[1] } },
    })

    expect(wrapper.emitted('select-node')).toBeTruthy()
    expect(wrapper.emitted('select-node')![0]).toEqual(['node-2'])
  })

  it('节点拖拽停止时应该触发 node-drag-stop 和 update:nodes 事件', async () => {
    const wrapper = mountCanvas()
    const vueFlow = wrapper.findComponent({ name: 'VueFlow' })

    await vueFlow.vm.$emit('nodeDragStop', {
      node: { id: 'node-1', position: { x: 120, y: 80 }, data: { node: mockNodes[0] } },
    })

    expect(wrapper.emitted('node-drag-stop')).toBeTruthy()
    expect(wrapper.emitted('node-drag-stop')![0]).toEqual([
      { nodeId: 'node-1', position: { x: 120, y: 80 } },
    ])

    expect(wrapper.emitted('update:nodes')).toBeTruthy()
    const updatedNodes = wrapper.emitted('update:nodes')![0][0] as WorkflowNode[]
    expect(updatedNodes.find((n) => n.id === 'node-1')?.ui_layout).toEqual({ x: 120, y: 80 })
    expect(updatedNodes.find((n) => n.id === 'node-2')?.ui_layout).toBeUndefined()
  })

  it('只读模式下节点不可选且不可拖拽', () => {
    const wrapper = mountCanvas({ readonly: true })
    const vueFlow = wrapper.findComponent({ name: 'VueFlow' })

    const nodes = vueFlow.props('nodes') as any[]
    expect(nodes[0].selectable).toBe(false)
    expect(nodes[0].draggable).toBe(false)
  })

  it('编辑模式下节点默认可选且可拖拽', () => {
    const wrapper = mountCanvas()
    const vueFlow = wrapper.findComponent({ name: 'VueFlow' })

    const nodes = vueFlow.props('nodes') as any[]
    expect(nodes[0].selectable).toBe(true)
    expect(nodes[0].draggable).toBe(true)
  })

  it('选中节点应该添加 selected 样式类', () => {
    const wrapper = mountCanvas({ selectedNodeId: 'node-1' })
    const nodeStub = wrapper.find('[data-node-id="node-1"]')
    expect(nodeStub.classes()).toContain('selected')
  })

  it('暴露的 fitView、zoomIn、zoomOut 方法应该调用 VueFlow 实例方法', () => {
    const wrapper = mountCanvas()

    wrapper.vm.fitView()
    expect(flowMocks.fitView).toHaveBeenCalled()

    wrapper.vm.zoomIn()
    expect(flowMocks.zoomIn).toHaveBeenCalled()

    wrapper.vm.zoomOut()
    expect(flowMocks.zoomOut).toHaveBeenCalled()
  })

  it('连线类型应该为自定义 workflow 边并携带只读和源节点类型数据', () => {
    const wrapper = mountCanvas()
    const vueFlow = wrapper.findComponent({ name: 'VueFlow' })

    const edges = vueFlow.props('edges') as any[]
    expect(edges[0].type).toBe('workflow')
    expect(edges[0].data).toEqual({
      readonly: false,
      sourceNodeType: 'send_email',
    })
  })

  it('只读模式下连线数据应标记为只读', () => {
    const wrapper = mountCanvas({ readonly: true })
    const vueFlow = wrapper.findComponent({ name: 'VueFlow' })

    const edges = vueFlow.props('edges') as any[]
    expect(edges[0].data.readonly).toBe(true)
  })

  it('空白画布应显示添加节点按钮', () => {
    const wrapper = mountCanvas({ nodes: [] })
    expect(wrapper.find('.canvas-empty-add').exists()).toBe(true)
  })

  it('只读模式下空白画布不显示添加节点按钮', () => {
    const wrapper = mountCanvas({ nodes: [], readonly: true })
    expect(wrapper.find('.canvas-empty-add').exists()).toBe(false)
  })

  it('点击空白画布添加按钮应触发 add-node 事件', async () => {
    const wrapper = mountCanvas({ nodes: [] })
    const dropdownItems = wrapper.findAll('.canvas-empty-add .el-dropdown-item')
    expect(dropdownItems.length).toBeGreaterThan(0)
    await dropdownItems[0].trigger('click')

    expect(wrapper.emitted('add-node')).toBeTruthy()
    expect(wrapper.emitted('add-node')![0]).toEqual([
      { position: 'first', nodeType: 'update_record' },
    ])
  })

  it('条件节点未连线的分支不生成边', () => {
    const wrapper = mountCanvas()
    const vueFlow = wrapper.findComponent({ name: 'VueFlow' })
    const edges = vueFlow.props('edges') as any[]
    const branchEdges = edges.filter((e) => e.source === 'node-2')
    expect(branchEdges.length).toBe(1)
    expect(branchEdges[0].sourceHandle).toBe('b1')
  })

  it('条件节点出边标签显示分支名称', () => {
    const wrapper = mountCanvas()
    const edgeStubs = wrapper.findAll('.vue-flow-edge-stub')
    const conditionEdge = edgeStubs.find((e) => e.attributes('data-edge-id')?.startsWith('e-node-2-'))
    expect(conditionEdge?.text()).toBe('满足条件')
  })

  it('从条件节点 handle 连线会更新对应分支目标', async () => {
    const wrapper = mountCanvas()
    const vueFlow = wrapper.findComponent({ name: 'VueFlow' })

    await vueFlow.vm.$emit('connect', {
      source: 'node-2',
      sourceHandle: 'b2',
      target: 'node-3',
    })

    const emitted = wrapper.emitted('update:nodes') as any[][]
    expect(emitted).toBeTruthy()
    const updatedNodes = emitted[emitted.length - 1][0] as WorkflowNode[]
    const conditionNode = updatedNodes.find((n) => n.id === 'node-2')!
    const branches = (conditionNode.config as any).branches
    const branchB = branches.find((b: any) => b.id === 'b2')
    expect(branchB.target_node_id).toBe('node-3')
  })

  it('手动连线后 next_nodes 从 branches 重建，不残留旧目标', async () => {
    const wrapper = mountCanvas()
    const vueFlow = wrapper.findComponent({ name: 'VueFlow' })

    // b1 原本指向 node-3，现在改指向 node-1
    await vueFlow.vm.$emit('connect', {
      source: 'node-2',
      sourceHandle: 'b1',
      target: 'node-1',
    })

    const emitted = wrapper.emitted('update:nodes') as any[][]
    expect(emitted).toBeTruthy()
    const updatedNodes = emitted[emitted.length - 1][0] as WorkflowNode[]
    const conditionNode = updatedNodes.find((n) => n.id === 'node-2')!

    // next_nodes 应只包含当前分支目标，node-3 已被替换为 node-1
    expect(conditionNode.next_nodes).toContain('node-1')
    expect(conditionNode.next_nodes).not.toContain('node-3')
    // 不应有重复
    expect(conditionNode.next_nodes.length).toBe(
      new Set(conditionNode.next_nodes).size,
    )
  })

  it('删除条件边会清除对应分支目标', async () => {
    const wrapper = mountCanvas()

    ;(wrapper.vm as any).handleEdgeDelete({
      sourceId: 'node-2',
      targetId: 'node-3',
      branchId: 'b1',
    })
    await nextTick()

    const emitted = wrapper.emitted('update:nodes') as any[][]
    expect(emitted).toBeTruthy()
    const updatedNodes = emitted[emitted.length - 1][0] as WorkflowNode[]
    const conditionNode = updatedNodes.find((n) => n.id === 'node-2')!
    const branches = (conditionNode.config as any).branches
    const branchA = branches.find((b: any) => b.id === 'b1')
    expect(branchA.target_node_id).toBeUndefined()
    expect(conditionNode.next_nodes).toEqual([])
  })
})
