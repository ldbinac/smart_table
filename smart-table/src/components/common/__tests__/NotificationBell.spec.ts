import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { reactive } from 'vue'
import NotificationBell from '../NotificationBell.vue'
import type { AppNotification } from '@/services/api/notificationApiService'

// 集中声明 mock 函数：vi.hoisted 保证其在 vi.mock 工厂中可用
const mocks = vi.hoisted(() => ({
  push: vi.fn(),
  refresh: vi.fn(),
  fetchUnreadCount: vi.fn(),
  reset: vi.fn(),
  markAsRead: vi.fn(),
  markAllAsRead: vi.fn(),
}))

// store 持有者：每个用例可重置其内部状态
const storeHolder = vi.hoisted(() => ({ current: null as any }))

// 认证状态持有者：用于覆盖已登录/未登录两种场景
const authHolder = vi.hoisted(() => ({
  current: { isAuthenticated: true } as { isAuthenticated: boolean },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mocks.push }),
}))

// 必须 mock 真实 authStore：其依赖链会经由 api client 加载 src/router/index.ts，
// 而上面 vue-router 的 mock 未提供 createRouter，导致整个测试文件收集失败
vi.mock('@/stores/auth/authStore', () => ({
  useAuthStore: () => authHolder.current,
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

// 未安装真实 i18n 实例，t() 直接返回 key，断言统一按 key 匹配
vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key: string) => key }),
}))

// 规避 formatRelativeTime 对 Pinia/adminStore 的依赖
vi.mock('@/utils/timezone', () => ({
  formatRelativeTime: vi.fn(() => '刚刚'),
  formatDateTime: vi.fn(() => '2024-01-01 00:00'),
}))

// 详情弹窗会重新拉取单条站内信，需 mock 以避免加载真实 api client 依赖链
vi.mock('@/services/api/notificationApiService', () => ({
  notificationApiService: {
    getNotification: vi.fn(async () => ({ data: null })),
  },
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
    fetchUnreadCount: mocks.fetchUnreadCount,
    reset: mocks.reset,
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
    // 默认已登录，个别用例会覆盖为未登录
    authHolder.current = { isAuthenticated: true }
  })

  afterEach(() => {
    wrapper?.unmount()
    authHolder.current = { isAuthenticated: true }
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

  it('未登录时不请求通知数据', async () => {
    authHolder.current = { isAuthenticated: false }
    wrapper = mountBell()
    await flushPromises()
    expect(mocks.refresh).not.toHaveBeenCalled()
    expect(mocks.fetchUnreadCount).not.toHaveBeenCalled()
  })

  it('点击全部已读调用 markAllAsRead', async () => {
    wrapper = mountBell({ unreadCount: 3, recentNotifications: buildNotifications() })
    await flushPromises()
    // 点击徽标展开下拉面板
    await wrapper.find('.notification-badge').trigger('click')
    await flushPromises()
    const markAllBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('notification.markAllRead'))
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

  it('点击未读通知直接打开详情弹窗，不跳转列表页', async () => {
    wrapper = mountBell({ unreadCount: 1, recentNotifications: buildNotifications() })
    await flushPromises()
    await wrapper.find('.notification-badge').trigger('click')
    await flushPromises()

    const unreadItem = wrapper
      .findAll('.notification-item')
      .find((i) => i.classes().includes('is-unread'))
    expect(unreadItem).toBeTruthy()

    await unreadItem!.trigger('click')
    await flushPromises()

    // 打开详情弹窗而非跳转消息中心
    expect(mocks.push).not.toHaveBeenCalled()
    expect(mocks.markAsRead).toHaveBeenCalledWith('n1')
    // el-dialog 内容通过 teleport 异步挂载，直接断言弹窗组件已打开
    const dialog = wrapper.findComponent({ name: 'ElDialog' })
    expect(dialog.exists()).toBe(true)
    expect(dialog.props('modelValue')).toBe(true)
  })
})
