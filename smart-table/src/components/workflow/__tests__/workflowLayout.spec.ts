import { describe, it, expect } from 'vitest'
import type { WorkflowNode } from '@/types/workflow'
import { layoutWorkflowNodes } from '../workflowLayout'

function makeNode(
  id: string,
  nodeType: WorkflowNode['node_type'],
  order: number,
  nextNodes: string[] = [],
  layout?: { x: number; y: number }
): WorkflowNode {
  return {
    id,
    workflow_id: 'wf-1',
    node_type: nodeType,
    name: `node-${id}`,
    config: {},
    order,
    next_nodes: nextNodes,
    ui_layout: layout,
  }
}

describe('layoutWorkflowNodes', () => {
  it('空数组返回空数组', () => {
    expect(layoutWorkflowNodes([])).toEqual([])
  })

  it('为无布局数据的节点按 order 计算单列垂直布局', () => {
    const nodes: WorkflowNode[] = [
      makeNode('n2', 'approval', 1),
      makeNode('n1', 'trigger', 0),
      makeNode('n3', 'update_record', 2),
    ]

    const result = layoutWorkflowNodes(nodes)
    const byId = Object.fromEntries(result.map((n) => [n.id, n.ui_layout]))

    expect(result.map((n) => n.id)).toEqual(['n1', 'n2', 'n3'])
    expect(byId.n1).toEqual({ x: 0, y: 0 })
    expect(byId.n2).toEqual({ x: 0, y: 120 })
    expect(byId.n3).toEqual({ x: 0, y: 240 })
  })

  it('保留已有 ui_layout 的节点，且不覆盖其坐标', () => {
    const nodes: WorkflowNode[] = [
      makeNode('n1', 'trigger', 0, [], { x: 42, y: 99 }),
      makeNode('n2', 'approval', 1),
    ]

    const result = layoutWorkflowNodes(nodes)
    const n1 = result.find((n) => n.id === 'n1')!
    const n2 = result.find((n) => n.id === 'n2')!

    expect(n1.ui_layout).toEqual({ x: 42, y: 99 })
    expect(n1).toBe(nodes[0])
    expect(n2.ui_layout).toEqual({ x: 0, y: 219 })
  })

  it('条件节点的“满足条件”分支节点向右偏移，后续节点逐步回到中心', () => {
    const nodes: WorkflowNode[] = [
      makeNode('n1', 'trigger', 0),
      {
        ...makeNode('n2', 'condition', 1, ['n3']),
        config: {
          branches: [
            { id: 'b1', name: '满足条件', conditions: [], conjunction: 'and', target_node_id: 'n3' },
          ],
        },
      },
      makeNode('n3', 'approval', 2),
      makeNode('n4', 'update_record', 3),
      makeNode('n5', 'webhook', 4),
    ]

    const result = layoutWorkflowNodes(nodes)
    const byId = Object.fromEntries(result.map((n) => [n.id, n.ui_layout]))

    expect(byId.n1).toEqual({ x: 0, y: 0 })
    expect(byId.n2).toEqual({ x: 0, y: 120 })
    expect(byId.n3).toEqual({ x: 240, y: 60 })
    expect(byId.n4).toEqual({ x: 190, y: 240 })
    expect(byId.n5).toEqual({ x: 140, y: 360 })
  })

  it('返回新数组，不修改原始节点对象', () => {
    const nodes: WorkflowNode[] = [makeNode('n1', 'trigger', 0)]
    const result = layoutWorkflowNodes(nodes)

    expect(result).not.toBe(nodes)
    expect(nodes[0].ui_layout).toBeUndefined()
    expect(result[0]).not.toBe(nodes[0])
  })

  it('混合有布局和无布局节点时仍能为无布局节点生成不重叠坐标', () => {
    const nodes: WorkflowNode[] = [
      makeNode('n1', 'trigger', 0, [], { x: 0, y: 0 }),
      makeNode('n2', 'approval', 1),
      makeNode('n3', 'update_record', 2),
    ]

    const result = layoutWorkflowNodes(nodes)
    const byId = Object.fromEntries(result.map((n) => [n.id, n.ui_layout]))

    expect(byId.n1).toEqual({ x: 0, y: 0 })
    expect(byId.n2).toEqual({ x: 0, y: 120 })
    expect(byId.n3).toEqual({ x: 0, y: 240 })
  })
})
