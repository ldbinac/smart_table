/**
 * 站内信服务 API
 */
import apiClient from '@/api/client'

export type NotificationStatus = 'pending' | 'sent' | 'failed' | 'retrying'

export interface AppNotification {
  id: string
  recipient_user_id: string
  recipient_email: string | null
  title: string
  content: string
  content_text: string | null
  template_key: string | null
  source: string
  status: NotificationStatus
  is_read: boolean
  read_at: string | null
  sent_at: string | null
  created_at: string
  retry_count: number
  error_message: string | null
  metadata: Record<string, unknown> | null
}

export interface NotificationStats {
  total: number
  sent: number
  failed: number
  pending: number
  retrying: number
  read: number
  unread: number
  by_source: Record<string, number>
  by_template: Record<string, number>
}

export const notificationApiService = {
  /**
   * 获取站内信列表
   */
  getNotifications: async (params: {
    page?: number
    per_page?: number
    is_read?: boolean
    source?: string
    status?: NotificationStatus
  }): Promise<{
    data: AppNotification[]
    meta?: {
      pagination: {
        page: number
        per_page: number
        total: number
        total_pages: number
        has_next: boolean
        has_prev: boolean
      }
    }
  }> => {
    return apiClient.get('/notifications', params)
  },

  /**
   * 获取未读站内信数量
   */
  getUnreadCount: async (): Promise<{ count: number }> => {
    return apiClient.get('/notifications/unread-count')
  },

  /**
   * 获取单个站内信详情
   */
  getNotification: async (id: string): Promise<{ data: AppNotification }> => {
    return apiClient.get(`/notifications/${id}`)
  },

  /**
   * 标记站内信为已读
   */
  markAsRead: async (id: string): Promise<{ success: boolean; message: string }> => {
    return apiClient.post(`/notifications/${id}/read`)
  },

  /**
   * 标记所有站内信为已读
   */
  markAllAsRead: async (): Promise<{ success: boolean; updated_count: number }> => {
    return apiClient.post('/notifications/read-all')
  },

  /**
   * 删除站内信
   */
  deleteNotification: async (id: string): Promise<{ success: boolean; message: string }> => {
    return apiClient.delete(`/notifications/${id}`)
  },

  /**
   * 获取站内信发送日志（管理端）
   */
  getLogs: async (params: {
    page?: number
    per_page?: number
    status?: NotificationStatus
    source?: string
    recipient_user_id?: string
    is_read?: boolean
    start_date?: string
    end_date?: string
  }): Promise<{
    data: AppNotification[]
    meta?: {
      pagination: {
        page: number
        per_page: number
        total: number
        total_pages: number
        has_next: boolean
        has_prev: boolean
      }
    }
  }> => {
    return apiClient.get('/admin/notifications/logs', params)
  },

  /**
   * 获取站内信统计（管理端）
   */
  getStats: async (): Promise<{
    data: NotificationStats
    success: boolean
    message: string
  }> => {
    return apiClient.get('/admin/notifications/stats')
  },

  /**
   * 重试发送站内信（管理端）
   */
  retryNotification: async (id: string): Promise<{ success: boolean; message: string }> => {
    return apiClient.post(`/admin/notifications/${id}/retry`)
  }
}

export default notificationApiService
