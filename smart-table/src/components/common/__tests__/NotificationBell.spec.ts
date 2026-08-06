import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { reactive } from 'vue'
import NotificationBell from '../NotificationBell.vue'
import type { AppNotification } from '@/services/api/notificationApiService'

// 集中声明 mock 函数：vi.hoisted 保证其在 vi.mock 工厂中可用
const mocks = vi.hoisted(() => ({
  push: vi.fn(),
  refresh: vi.fn(),
  markAsRead: vi.fn(),
  markAllAsRead: vi.fn(),
}))

// store 持有者：每个用例可重置其内部状态
const storeHolder = vi.hoisted(() => ({ current: null as any }))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mocks.push }),
}))

vi.mock('@/stores/notificationStore', () => ({
  useNotificationStore: () => storeHolder.current,
}))

// 保留 element-plus 真实组件（el-popover/el-badge 等已通过 test-setup 全局注册），
// 仅替换 ElMessage 以避免弹出真实 toast
vi.mock('element-plus', async () => {
  const actual = await vi.importActual<typeof import('element-plus')>('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      warning: vi.fn(),
      error: vi.fn(),
    },
  }
})

vi.mock('@element-plus/icons-vue', () => ({
  Bell: { template: '<i class="mock-bell-icon" />' },
}))

// 规避 formatRelativeTime 对 Pinia/adminStore 的依赖
vi.mock('@/utils/timezone', () => ({
  formatRelativeTime: vi.fn(() => '刚刚'),
}))

// 构造两条最近通知
function buildNotifications(): AppNotification[] {
  return [
    {
      id: 'n1',
      recipient_user_id: 'u1',
      recipient_email: null,
      title: '欢迎使用 SmartTable',
      content: '<p>这是一条系统通知</p>',
      content_text: '这是一条系统通知',
      template_key: null,
      source: 'system',
      status: 'sent',
      is_read: false,
      read_at: null,
      sent_at: '2024-01-01T00:00:00Z',
      created_at: '2024-01-01T00:00:00Z',
      retry_count: 0,
      error_message: null,
      metadata: null,
    },
    {
      id: 'n2',
      recipient_user_id: 'u1',
      recipient_email: null,
      title: '审批已通过',
      content: '<p>您的审批已通过</p>',
      content_text: '您的审批已通过',
      template_key: null,
      source: 'approval',
      status: 'sent',
      is_read: true,
      read_at: '2024-01-02T00:00:00Z',
      sent_at: '2024-01-02T00:00:00Z',
      created_at: '2024-01-02T00:00:00Z',
      retry_count: 0,
      error_message: null,
      metadata: null,
    },
  ]
}

// 创建响应式 mock store，模拟 Pinia 的 ref 自动解包行为
function createStore(
  overrides: Partial<{ unreadCount: number; recentNotifications: AppNotification[] }> = {},
) {
  return reactive({
    unreadCount: 0,
    recentNotifications: [] as AppNotification[],
    refresh: mocks.refresh,
    markAsRead: mocks.markAsRead,
    markAllAsRead: mocks.markAllAsRead,
    ...overrides,
  })
}

function mountBell(
  overrides: Partial<{ unreadCount: number; recentNotifications: AppNotification[] }> = {},
) {
  storeHolder.current = createStore(overrides)
  return mount(NotificationBell)
}

describe('NotificationBell', () => {
  let wrapper: ReturnType<typeof mount>

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    wrapper?.unmount()
  })

  it('未读数大于0时显示徽标', async () => {
    wrapper = mountBell({ unreadCount: 3 })
    await flushPromises()
    const badge = wrapper.find('.el-badge__content')
    expect(badge.exists()).toBe(true)
    expect(badge.isVisible()).toBe(true)
    expect(badge.text()).toBe('3')
  })

  it('未读数为0时隐藏徽标', async () => {
    wrapper = mountBell({ unreadCount: 0 })
    await flushPromises()
    // el-badge 在 hidden=true 时不渲染徽标内容元素
    expect(wrapper.find('.el-badge__content').exists()).toBe(false)
  })

  it('onMounted 调用 refresh 拉取数据', async () => {
    wrapper = mountBell()
    await flushPromises()
    expect(mocks.refresh).toHaveBeenCalled()
  })

  it('点击全部已读调用 markAllAsRead', async () => {
    wrapper = mountBell({ unreadCount: 3, recentNotifications: buildNotifications() })
    await flushPromises()
    // 点击徽标展开下拉面板
    await wrapper.find('.notification-badge').trigger('click')
    await flushPromises()
    const markAllBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('全部已读'))
    expect(markAllBtn).toBeTruthy()
    await markAllBtn!.trigger('click')
    await flushPromises()
    expect(mocks.markAllAsRead).toHaveBeenCalled()
  })

  it('下拉列表展示最近通知', async () => {
    wrapper = mountBell({ unreadCount: 2, recentNotifications: buildNotifications() })
    await flushPromises()
    await wrapper.find('.notification-badge').trigger('click')
    await flushPromises()
    const items = wrapper.findAll('.notification-item')
    expect(items).toHaveLength(2)
    const titles = items.map((i) => i.find('.title-text').text())
    expect(titles).toContain('欢迎使用 SmartTable')
    expect(titles).toContain('审批已通过')
  })
})
