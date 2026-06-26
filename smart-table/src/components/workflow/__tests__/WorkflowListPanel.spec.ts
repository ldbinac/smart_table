import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import {
  ElButton,
  ElCard,
  ElRadioGroup,
  ElRadioButton,
  ElTag,
  ElIcon,
  ElEmpty,
  ElDialog,
  ElForm,
  ElFormItem,
  ElSelect,
  ElOption,
  ElInput,
} from 'element-plus'
import WorkflowListPanel from '../WorkflowListPanel.vue'
import type { Workflow } from '@/types/workflow'

const mockWorkflow: Workflow = {
  id: 'w1',
  base_id: 'b1',
  name: '测试工作流',
  description: '这是一个测试工作流',
  status: 'draft',
  current_version: 1,
  table_id: null,
  is_deleted: false,
  created_by: 'u1',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const mockWorkflows: Workflow[] = [
  {
    id: 'w1',
    base_id: 'b1',
    name: '订单处理工作流',
    description: '处理订单状态变更',
    status: 'draft',
    current_version: 1,
    table_id: null,
    is_deleted: false,
    created_by: 'u1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'w2',
    base_id: 'b1',
    name: '库存同步工作流',
    description: '每天同步库存数量到仓库系统',
    status: 'active',
    current_version: 2,
    table_id: null,
    is_deleted: false,
    created_by: 'u1',
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
  },
]

const globalComponents = {
  ElButton,
  ElCard,
  ElRadioGroup,
  ElRadioButton,
  ElTag,
  ElIcon,
  ElEmpty,
  ElDialog,
  ElForm,
  ElFormItem,
  ElSelect,
  ElOption,
  ElInput,
}

const loadingDirective = {
  mounted(el: HTMLElement, binding: { value: boolean }) {
    if (binding.value) {
      el.classList.add('is-loading')
    }
  },
  updated(el: HTMLElement, binding: { value: boolean }) {
    if (binding.value) {
      el.classList.add('is-loading')
    } else {
      el.classList.remove('is-loading')
    }
  },
}

function mountPanel(props = {}) {
  return mount(WorkflowListPanel, {
    props: { baseId: 'b1', workflows: [mockWorkflow], ...props },
    global: {
      plugins: [createPinia()],
      components: globalComponents,
      directives: { loading: loadingDirective },
    },
  })
}

describe('WorkflowListPanel', () => {
  it('toggles collapsed state when collapse button is clicked', async () => {
    const wrapper = mountPanel()

    const panel = wrapper.find('.workflow-list-panel')
    expect(panel.classes()).not.toContain('collapsed')

    const collapseBtn = wrapper.find('.collapse-btn')
    expect(collapseBtn.exists()).toBe(true)

    await collapseBtn.trigger('click')
    expect(panel.classes()).toContain('collapsed')

    await collapseBtn.trigger('click')
    expect(panel.classes()).not.toContain('collapsed')
  })

  it('keeps filter tabs and description in DOM when collapsed', async () => {
    const wrapper = mountPanel()

    await wrapper.find('.collapse-btn').trigger('click')
    await wrapper.vm.$nextTick()

    const panel = wrapper.find('.workflow-list-panel')
    expect(panel.classes()).toContain('collapsed')
    // 在 jsdom 中 scoped CSS 的可见性由 CSS 负责控制，这里只验证元素仍保留在 DOM 中
    expect(wrapper.find('.filter-tabs').exists()).toBe(true)
    expect(wrapper.find('.workflow-description').exists()).toBe(true)
  })

  it('changes collapse button title based on state', async () => {
    const wrapper = mountPanel()

    const collapseBtn = wrapper.find('.collapse-btn')
    expect(collapseBtn.attributes('title')).toBe('收缩')

    await collapseBtn.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.collapse-btn').attributes('title')).toBe('展开')
  })

  it('filters workflows by name', async () => {
    const wrapper = mountPanel({ workflows: mockWorkflows })
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.workflow-card').length).toBe(2)

    const input = wrapper.find('.workflow-search input')
    await input.setValue('订单')

    const filteredCards = wrapper.findAll('.workflow-card')
    expect(filteredCards.length).toBe(1)
    expect(filteredCards[0].find('.workflow-name').text()).toBe('订单处理工作流')
  })

  it('filters workflows by description', async () => {
    const wrapper = mountPanel({ workflows: mockWorkflows })
    await wrapper.vm.$nextTick()

    const input = wrapper.find('.workflow-search input')
    await input.setValue('仓库')

    const filteredCards = wrapper.findAll('.workflow-card')
    expect(filteredCards.length).toBe(1)
    expect(filteredCards[0].find('.workflow-name').text()).toBe('库存同步工作流')
  })

  it('shows empty state when no workflow matches search', async () => {
    const wrapper = mountPanel({ workflows: mockWorkflows })
    await wrapper.vm.$nextTick()

    const input = wrapper.find('.workflow-search input')
    await input.setValue('不存在的关键词')

    expect(wrapper.findAll('.workflow-card').length).toBe(0)
    expect(wrapper.find('.el-empty').exists()).toBe(true)
    expect(wrapper.find('.el-empty__description').text()).toBe('没有找到匹配的工作流')
  })

  it('restores all workflows after clearing search', async () => {
    const wrapper = mountPanel({ workflows: mockWorkflows })
    await wrapper.vm.$nextTick()

    const input = wrapper.find('.workflow-search input')
    await input.setValue('订单')
    expect(wrapper.findAll('.workflow-card').length).toBe(1)

    await input.setValue('')
    expect(wrapper.findAll('.workflow-card').length).toBe(2)
  })

  it('keeps search input in DOM when collapsed', async () => {
    const wrapper = mountPanel()

    await wrapper.find('.collapse-btn').trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.workflow-list-panel').classes()).toContain('collapsed')
    expect(wrapper.find('.workflow-search').exists()).toBe(true)
  })
})
