/**
 * notificationApiService 测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { notificationApiService } from '../notificationApiService'
import { apiClient } from '@/api/client'

// 显式提供工厂，保证命名导出 apiClient 与默认导出指向同一 mock 对象
// （notificationApiService 内部使用默认导入 apiClient）
vi.mock('@/api/client', () => {
  const mockClient = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn(),
  }
  return { apiClient: mockClient, default: mockClient }
})

describe('notificationApiService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('getNotifications 调用 GET /notifications 并传参', async () => {
    const mockResp = {
      data: [],
      meta: {
        pagination: {
          page: 1,
          per_page: 10,
          total: 0,
          total_pages: 0,
          has_next: false,
          has_prev: false,
        },
      },
    }
    ;(apiClient.get as any).mockResolvedValue(mockResp)
    const params = { page: 1, per_page: 10, is_read: false }
    const result = await notificationApiService.getNotifications(params)
    expect(apiClient.get).toHaveBeenCalledWith('/notifications', params)
    expect(result).toEqual(mockResp)
  })

  it('getUnreadCount 调用 GET /notifications/unread-count', async () => {
    ;(apiClient.get as any).mockResolvedValue({ count: 5 })
    const result = await notificationApiService.getUnreadCount()
    expect(apiClient.get).toHaveBeenCalledWith('/notifications/unread-count')
    expect(result).toEqual({ count: 5 })
  })

  it('markAsRead 调用 POST /notifications/<id>/read', async () => {
    ;(apiClient.post as any).mockResolvedValue({ success: true, message: 'ok' })
    const result = await notificationApiService.markAsRead('abc')
    expect(apiClient.post).toHaveBeenCalledWith('/notifications/abc/read')
    expect(result).toEqual({ success: true, message: 'ok' })
  })

  it('markAllAsRead 调用 POST /notifications/read-all', async () => {
    ;(apiClient.post as any).mockResolvedValue({ success: true, updated_count: 3 })
    await notificationApiService.markAllAsRead()
    expect(apiClient.post).toHaveBeenCalledWith('/notifications/read-all')
  })

  it('deleteNotification 调用 DELETE /notifications/<id>', async () => {
    ;(apiClient.delete as any).mockResolvedValue({ success: true, message: 'ok' })
    await notificationApiService.deleteNotification('abc')
    expect(apiClient.delete).toHaveBeenCalledWith('/notifications/abc')
  })

  it('getLogs 调用 GET /admin/notifications/logs 并传参', async () => {
    ;(apiClient.get as any).mockResolvedValue({ data: [] })
    const params = { page: 1, per_page: 20, status: 'failed' as const }
    await notificationApiService.getLogs(params)
    expect(apiClient.get).toHaveBeenCalledWith('/admin/notifications/logs', params)
  })

  it('getStats 调用 GET /admin/notifications/stats', async () => {
    ;(apiClient.get as any).mockResolvedValue({
      data: {
        total: 0,
        sent: 0,
        failed: 0,
        pending: 0,
        retrying: 0,
        read: 0,
        unread: 0,
        by_source: {},
        by_template: {},
      },
      success: true,
      message: 'ok',
    })
    await notificationApiService.getStats()
    expect(apiClient.get).toHaveBeenCalledWith('/admin/notifications/stats')
  })

  it('retryNotification 调用 POST /admin/notifications/<id>/retry', async () => {
    ;(apiClient.post as any).mockResolvedValue({ success: true, message: 'ok' })
    await notificationApiService.retryNotification('abc')
    expect(apiClient.post).toHaveBeenCalledWith('/admin/notifications/abc/retry')
  })
})
