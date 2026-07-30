import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowVersionNodeSnapshot from '../WorkflowVersionNodeSnapshot.vue'
import type { WorkflowNode } from '@/types/workflow'

vi.mock('@element-plus/icons-vue', () => ({
  CircleCheck: { template: '<span class="icon-circle-check" />' },
  Share: { template: '<span class="icon-share" />' },
  EditPen: { template: '<span class="icon-edit-pen" />' },
  Plus: { template: '<span class="icon-plus" />' },
  Message: { template: '<span class="icon-message" />' },
  Link: { template: '<span class="icon-link" />' },
  Search: { template: '<span class="icon-search" />' },
  Refresh: { template: '<span class="icon-refresh" />' },
}))

describe('WorkflowVersionNodeSnapshot', () => {
  it('renders condition node summary', () => {
    const node: WorkflowNode = {
      id: 'n2',
      workflow_id: 'w1',
      node_type: 'condition',
      name: '条件',
      config: {
        conditions: [
          { field_id: 'f1', operator: 'eq', value: 'xxx' }
        ]
      },
      order: 1,
      next_nodes: []
    }
    const wrapper = mount(WorkflowVersionNodeSnapshot, {
      props: {
        node,
        fields: [{ id: 'f1', name: '字段A', type: 'text' } as any]
      }
    })
    expect(wrapper.text()).toContain('条件')
    expect(wrapper.text()).toContain('字段A')
    expect(wrapper.text()).toContain('eq')
  })

  it('renders update_record node summary', () => {
    const node: WorkflowNode = {
      id: 'n3',
      workflow_id: 'w1',
      node_type: 'update_record',
      name: '更新记录',
      config: {
        update_mappings: [
          { field_id: 'f1', value_template: '{{trigger.record.f2}}' }
        ]
      },
      order: 2,
      next_nodes: []
    }
    const wrapper = mount(WorkflowVersionNodeSnapshot, {
      props: {
        node,
        fields: [{ id: 'f1', name: '目标字段', type: 'text' } as any]
      }
    })
    expect(wrapper.text()).toContain('更新记录')
    expect(wrapper.text()).toContain('目标字段')
    expect(wrapper.text()).toContain('{{trigger.record.f2}}')
  })

  it('renders create_record node summary', () => {
    const node: WorkflowNode = {
      id: 'n4',
      workflow_id: 'w1',
      node_type: 'create_record',
      name: '创建记录',
      config: {
        target_table_id: 't1',
        create_record_mappings: [
          { target_field_id: 'f1', source_field_id: 'f2', value_template: '' }
        ]
      },
      order: 3,
      next_nodes: []
    }
    const wrapper = mount(WorkflowVersionNodeSnapshot, {
      props: {
        node,
        fields: [
          { id: 'f1', name: '目标字段', type: 'text' } as any,
          { id: 'f2', name: '源字段', type: 'text' } as any
        ],
        tables: [{ id: 't1', name: '目标表' } as any]
      }
    })
    expect(wrapper.text()).toContain('创建记录')
    expect(wrapper.text()).toContain('目标表')
    expect(wrapper.text()).toContain('目标字段')
    expect(wrapper.text()).toContain('源字段')
  })

  it('renders send_email node summary', () => {
    const node: WorkflowNode = {
      id: 'n5',
      workflow_id: 'w1',
      node_type: 'send_email',
      name: '发送邮件',
      config: {
        recipient_type: 'field',
        recipient_value: ['f1'],
        content_mode: 'custom',
        subject: '通知：{{record.f1}}',
        body: '您好'
      },
      order: 4,
      next_nodes: []
    }
    const wrapper = mount(WorkflowVersionNodeSnapshot, {
      props: {
        node,
        fields: [{ id: 'f1', name: '邮箱字段', type: 'email' } as any]
      }
    })
    expect(wrapper.text()).toContain('发送邮件')
    expect(wrapper.text()).toContain('字段')
    expect(wrapper.text()).toContain('自定义内容')
    expect(wrapper.text()).toContain('通知')
  })

  it('renders webhook node summary', () => {
    const node: WorkflowNode = {
      id: 'n6',
      workflow_id: 'w1',
      node_type: 'webhook',
      name: '通知',
      config: {
        webhook_mode: 'inline',
        inline_webhook: { name: 'Hook', url: 'https://example.com', method: 'POST' }
      },
      order: 5,
      next_nodes: []
    }
    const wrapper = mount(WorkflowVersionNodeSnapshot, { props: { node } })
    expect(wrapper.text()).toContain('通知')
    expect(wrapper.text()).toContain('https://example.com')
    expect(wrapper.text()).toContain('POST')
  })

  it('renders fallback for unknown node type', () => {
    const node: WorkflowNode = {
      id: 'n7',
      workflow_id: 'w1',
      node_type: 'unknown_type' as any,
      name: '未知',
      config: { foo: 'bar' },
      order: 6,
      next_nodes: []
    }
    const wrapper = mount(WorkflowVersionNodeSnapshot, { props: { node } })
    expect(wrapper.text()).toContain('未知')
    expect(wrapper.text()).toContain('原始配置')
  })
})
