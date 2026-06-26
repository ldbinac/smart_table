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
})
