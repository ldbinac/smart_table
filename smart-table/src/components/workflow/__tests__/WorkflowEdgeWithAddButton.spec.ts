import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowEdgeWithAddButton from '../WorkflowEdgeWithAddButton.vue'

const mockPath = 'M 0 0 C 50 0 50 100 100 100'
const mockLabelX = 50
const mockLabelY = 50

vi.mock('@vue-flow/core', async () => {
  const vue = await import('vue')
  const { h, defineComponent } = vue

  return {
    BaseEdge: defineComponent({
      name: 'BaseEdge',
      props: ['path'],
      render() {
        return h('path', { class: 'base-edge-stub', d: this.path })
      },
    }),
    EdgeLabelRenderer: defineComponent({
      name: 'EdgeLabelRenderer',
      setup(_props, { slots }) {
        return () => h('div', { class: 'edge-label-renderer-stub' }, slots.default?.())
      },
    }),
    getSmoothStepPath: vi.fn(() => [mockPath, mockLabelX, mockLabelY, 0, 0]),
  }
})

vi.mock('@element-plus/icons-vue', () => ({
  Plus: { name: 'Plus', template: '<span class="icon-plus" />' },
  Delete: { name: 'Delete', template: '<span class="icon-delete" />' },
  EditPen: { name: 'EditPen', template: '<span class="icon-edit-pen" />' },
  Search: { name: 'Search', template: '<span class="icon-search" />' },
  Message: { name: 'Message', template: '<span class="icon-message" />' },
  Link: { name: 'Link', template: '<span class="icon-link" />' },
  Share: { name: 'Share', template: '<span class="icon-share" />' },
  CircleCheck: { name: 'CircleCheck', template: '<span class="icon-circle-check" />' },
}))

const defaultProps: Record<string, any> = {
  id: 'e-node-1-node-2',
  source: 'node-1',
  target: 'node-2',
  sourceX: 0,
  sourceY: 0,
  targetX: 100,
  targetY: 100,
  sourcePosition: 'bottom',
  targetPosition: 'top',
  sourceNode: {},
  targetNode: {},
  type: 'workflow',
  markerStart: '',
  markerEnd: 'arrowclosed',
  events: {},
  data: {},
}

function mountEdge(props: Record<string, any> = {}) {
  return mount(WorkflowEdgeWithAddButton, {
    props: {
      ...defaultProps,
      ...props,
    } as any,
  })
}

describe('WorkflowEdgeWithAddButton', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该渲染基础边路径', () => {
    const wrapper = mountEdge()
    expect(wrapper.find('.base-edge-stub').exists()).toBe(true)
  })

  it('应该在中点渲染"+"按钮', () => {
    const wrapper = mountEdge()
    const button = wrapper.find('.edge-add-button')
    expect(button.exists()).toBe(true)
    expect(button.find('.icon-plus').exists()).toBe(true)
  })

  it('点击"+"按钮应该显示节点类型菜单', async () => {
    const wrapper = mountEdge()
    expect(wrapper.find('.edge-add-menu').exists()).toBe(false)

    await wrapper.find('.edge-add-button').trigger('click')
    expect(wrapper.find('.edge-add-menu').exists()).toBe(true)
  })

  it('选择菜单项时应该触发 edge-insert 事件', async () => {
    const wrapper = mountEdge()
    await wrapper.find('.edge-add-button').trigger('click')

    const menuItems = wrapper.findAll('.edge-add-menu-item')
    expect(menuItems.length).toBe(6)
    expect(menuItems[0].text()).toBe('更新记录')
    expect(menuItems[1].text()).toBe('创建记录')
    expect(menuItems[2].text()).toBe('查找记录')
    expect(menuItems[3].text()).toBe('发送邮件')
    expect(menuItems[4].text()).toBe('Webhook')
    expect(menuItems[5].text()).toBe('条件节点')

    await menuItems[1].trigger('click')

    expect(wrapper.emitted('edge-insert')).toBeTruthy()
    expect(wrapper.emitted('edge-insert')![0]).toEqual([
      { sourceId: 'node-1', targetId: 'node-2', nodeType: 'create_record' },
    ])
  })

  it('只读模式下应该隐藏"+"按钮', () => {
    const wrapper = mountEdge({ data: { readonly: true } })
    expect(wrapper.find('.edge-add-button').exists()).toBe(false)
  })

  it('源节点为条件节点时应该显示"满足条件"标签', () => {
    const wrapper = mountEdge({ data: { sourceNodeType: 'condition' } })
    expect(wrapper.find('.edge-source-label').exists()).toBe(true)
    expect(wrapper.find('.edge-source-label').text()).toBe('满足条件')
  })

  it('源节点不是条件节点时不应该显示"满足条件"标签', () => {
    const wrapper = mountEdge({ data: { sourceNodeType: 'update_record' } })
    expect(wrapper.find('.edge-source-label').exists()).toBe(false)
  })

  it('源节点为条件节点时显示删除按钮而非添加按钮', () => {
    const wrapper = mountEdge({ data: { sourceNodeType: 'condition', branchId: 'b1', branchName: 'VIP' } })
    expect(wrapper.find('.edge-add-button').exists()).toBe(false)
    expect(wrapper.find('.edge-delete-button').exists()).toBe(true)
  })

  it('点击条件边删除按钮触发 edge-delete 事件', async () => {
    const wrapper = mountEdge({ data: { sourceNodeType: 'condition', branchId: 'b1', branchName: 'VIP' } })
    await wrapper.find('.edge-delete-button').trigger('click')

    expect(wrapper.emitted('edge-delete')).toBeTruthy()
    expect(wrapper.emitted('edge-delete')![0]).toEqual([
      { sourceId: 'node-1', targetId: 'node-2', branchId: 'b1' },
    ])
  })

  it('源节点为条件节点时显示指定分支名称', () => {
    const wrapper = mountEdge({ data: { sourceNodeType: 'condition', branchName: 'VIP 客户' } })
    expect(wrapper.find('.edge-source-label').text()).toBe('VIP 客户')
  })
})
