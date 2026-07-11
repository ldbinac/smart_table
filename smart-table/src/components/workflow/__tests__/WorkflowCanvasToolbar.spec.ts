import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowCanvasToolbar from '../WorkflowCanvasToolbar.vue'

vi.mock('@element-plus/icons-vue', () => ({
  Plus: { template: '<span class="icon-plus" />' },
  Minus: { template: '<span class="icon-minus" />' },
  FullScreen: { template: '<span class="icon-fullscreen" />' },
  Handbag: { template: '<span class="icon-handbag" />' },
  Pointer: { template: '<span class="icon-pointer" />' },
}))

function mountToolbar(props: Record<string, any> = {}) {
  return mount(WorkflowCanvasToolbar, {
    props,
    global: {
      stubs: {
        'el-button-group': {
          template: '<div class="el-button-group"><slot /></div>',
        },
        'el-button': {
          template: '<button class="el-button" @click="$emit(\'click\')"><slot /></button>',
          emits: ['click'],
        },
        'el-icon': {
          template: '<i class="el-icon"><slot /></i>',
        },
      },
    },
  })
}

describe('WorkflowCanvasToolbar', () => {
  let wrapper: ReturnType<typeof mountToolbar>

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    wrapper?.unmount()
  })

  it('应该渲染悬浮工具栏', () => {
    wrapper = mountToolbar()
    expect(wrapper.find('.workflow-canvas-toolbar').exists()).toBe(true)
    expect(wrapper.find('.el-button-group').exists()).toBe(true)
  })

  it('点击放大按钮应该触发 zoom-in 事件', async () => {
    wrapper = mountToolbar()
    const buttons = wrapper.findAll('.el-button')
    await buttons[1].trigger('click')
    expect(wrapper.emitted('zoom-in')).toBeTruthy()
  })

  it('点击缩小按钮应该触发 zoom-out 事件', async () => {
    wrapper = mountToolbar()
    const buttons = wrapper.findAll('.el-button')
    await buttons[2].trigger('click')
    expect(wrapper.emitted('zoom-out')).toBeTruthy()
  })

  it('点击适应视图按钮应该触发 fit-view 事件', async () => {
    wrapper = mountToolbar()
    const buttons = wrapper.findAll('.el-button')
    await buttons[3].trigger('click')
    expect(wrapper.emitted('fit-view')).toBeTruthy()
  })

  it('点击抓手切换按钮应该触发 toggle-pan-mode 事件', async () => {
    wrapper = mountToolbar()
    const buttons = wrapper.findAll('.el-button')
    await buttons[0].trigger('click')
    expect(wrapper.emitted('toggle-pan-mode')).toBeTruthy()
  })

  it('panMode 为 true 时抓手按钮应处于激活状态', () => {
    wrapper = mountToolbar({ panMode: true })
    const buttons = wrapper.findAll('.el-button')
    expect(buttons[0].classes()).toContain('active')
    expect(buttons[0].find('.icon-handbag').exists()).toBe(true)
  })

  it('panMode 为 false 时抓手按钮不应处于激活状态', () => {
    wrapper = mountToolbar({ panMode: false })
    const buttons = wrapper.findAll('.el-button')
    expect(buttons[0].classes()).not.toContain('active')
    expect(buttons[0].find('.icon-pointer').exists()).toBe(true)
  })

  it('Ctrl + Plus 应该触发 zoom-in 事件', () => {
    wrapper = mountToolbar()
    const event = new KeyboardEvent('keydown', { key: '+', ctrlKey: true })
    window.dispatchEvent(event)
    expect(wrapper.emitted('zoom-in')).toBeTruthy()
  })

  it('Cmd + Plus 应该触发 zoom-in 事件', () => {
    wrapper = mountToolbar()
    const event = new KeyboardEvent('keydown', { key: '+', metaKey: true })
    window.dispatchEvent(event)
    expect(wrapper.emitted('zoom-in')).toBeTruthy()
  })

  it('Ctrl + Minus 应该触发 zoom-out 事件', () => {
    wrapper = mountToolbar()
    const event = new KeyboardEvent('keydown', { key: '-', ctrlKey: true })
    window.dispatchEvent(event)
    expect(wrapper.emitted('zoom-out')).toBeTruthy()
  })

  it('Ctrl + 0 应该触发 fit-view 事件', () => {
    wrapper = mountToolbar()
    const event = new KeyboardEvent('keydown', { key: '0', ctrlKey: true })
    window.dispatchEvent(event)
    expect(wrapper.emitted('fit-view')).toBeTruthy()
  })

  it('未按下 Ctrl/Cmd 的按键不应触发事件', () => {
    wrapper = mountToolbar()
    const event = new KeyboardEvent('keydown', { key: '+' })
    window.dispatchEvent(event)
    expect(wrapper.emitted('zoom-in')).toBeFalsy()
    expect(wrapper.emitted('zoom-out')).toBeFalsy()
    expect(wrapper.emitted('fit-view')).toBeFalsy()
  })

  it('组件卸载后应移除键盘监听', () => {
    wrapper = mountToolbar()
    wrapper.unmount()
    const event = new KeyboardEvent('keydown', { key: '+', ctrlKey: true })
    window.dispatchEvent(event)
    expect(wrapper.emitted('zoom-in')).toBeFalsy()
  })
})
