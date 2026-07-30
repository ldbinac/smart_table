import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowExecutionLog from '../WorkflowExecutionLog.vue'
import type { WorkflowInstance, WorkflowExecutionLog as WorkflowExecutionLogType } from '@/types/workflow'

vi.mock('@/utils/timezone', () => ({
  formatDateTime: (v: string) => v,
}))

const baseInstance: WorkflowInstance = {
  id: 'inst-1',
  workflow_id: 'wf-1',
  version_number: 1,
  trigger_type: 'record_created',
  status: 'completed',
  started_at: '2026-07-07T10:00:00Z',
  completed_at: '2026-07-07T10:01:00Z',
} as any

function makeLog(overrides: Partial<WorkflowExecutionLogType>): WorkflowExecutionLogType {
  return {
    id: 'log-1',
    instance_id: 'inst-1',
    node_id: 'node-1',
    node_name: null,
    node_type: 'action',
    status: 'completed',
    input_context: {},
    output_result: {},
    error_message: null,
    started_at: '2026-07-07T10:00:00Z',
    completed_at: '2026-07-07T10:00:30Z',
    ...overrides,
  } as any
}

describe('WorkflowExecutionLog', () => {
  it('当 log 有 node_name 时紧邻 node-type 显示节点名称', () => {
    const log = makeLog({ node_name: '通知用户' })
    const wrapper = mount(WorkflowExecutionLog, {
      props: { instance: baseInstance, logs: [log], workflowId: 'wf-1' },
    })
    const nodeType = wrapper.find('.node-type')
    const nodeName = wrapper.find('.node-name')
    expect(nodeType.exists()).toBe(true)
    expect(nodeName.exists()).toBe(true)
    expect(nodeType.text()).toBe('动作节点')
    expect(nodeName.text()).toBe('通知用户')
    // 节点名称应紧邻 node-type（DOM 顺序）
    const titleEl = wrapper.find('.log-title')
    const children = titleEl.element.children
    const nodeTypeIndex = Array.from(children).indexOf(nodeType.element)
    const nodeNameIndex = Array.from(children).indexOf(nodeName.element)
    expect(nodeNameIndex).toBe(nodeTypeIndex + 1)
  })

  it('当 log.node_name 为空时不渲染 node-name span', () => {
    const log = makeLog({ node_name: null })
    const wrapper = mount(WorkflowExecutionLog, {
      props: { instance: baseInstance, logs: [log], workflowId: 'wf-1' },
    })
    expect(wrapper.find('.node-name').exists()).toBe(false)
    expect(wrapper.find('.node-type').exists()).toBe(true)
  })

  it('不同日志条目按节点名称区分显示', () => {
    const logs = [
      makeLog({ id: 'log-1', node_name: '通知管理员', node_type: 'webhook' }),
      makeLog({ id: 'log-2', node_name: '通知用户', node_type: 'webhook' }),
    ]
    const wrapper = mount(WorkflowExecutionLog, {
      props: { instance: baseInstance, logs, workflowId: 'wf-1' },
    })
    const names = wrapper.findAll('.node-name').map((n) => n.text())
    expect(names).toEqual(['通知管理员', '通知用户'])
  })

  it('长节点名称使用 title 属性展示完整文本', () => {
    const longName = '这是一个非常非常非常长的节点名称用于测试省略号效果是否正常工作'
    const log = makeLog({ node_name: longName })
    const wrapper = mount(WorkflowExecutionLog, {
      props: { instance: baseInstance, logs: [log], workflowId: 'wf-1' },
    })
    const nodeName = wrapper.find('.node-name')
    expect(nodeName.attributes('title')).toBe(longName)
    expect(nodeName.text()).toBe(longName)
  })
})
