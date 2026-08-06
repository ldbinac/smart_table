/**
 * 站内信状态管理 Store
 * 管理未读数量与最近站内信列表
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { notificationApiService, type AppNotification } from '@/services/api/notificationApiService'

export const useNotificationStore = defineStore('notification', () => {
  // 状态
  const unreadCount = ref(0)
  const recentNotifications = ref<AppNotification[]>([])
  const loading = ref(false)

  /**
   * 获取未读站内信数量
   */
  async function fetchUnreadCount() {
    try {
      const res = await notificationApiService.getUnreadCount()
      unreadCount.value = res.count
    } catch (error) {
      console.error('[notificationStore] fetchUnreadCount failed:', error)
    }
  }

  /**
   * 获取最近站内信
   */
  async function fetchRecent(limit: number = 5) {
    loading.value = true
    try {
      const res = await notificationApiService.getNotifications({ per_page: limit })
      recentNotifications.value = res.data
    } catch (error) {
      console.error('[notificationStore] fetchRecent failed:', error)
    } finally {
      loading.value = false
    }
  }

  /**
   * 刷新：并行获取未读数量与最近站内信
   */
  async function refresh() {
    await Promise.all([fetchUnreadCount(), fetchRecent()])
  }

  /**
   * 标记单条站内信为已读
   */
  async function markAsRead(id: string) {
    await notificationApiService.markAsRead(id)
    const target = recentNotifications.value.find((n) => n.id === id)
    if (target && !target.is_read) {
      target.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  }

  /**
   * 标记所有站内信为已读
   */
  async function markAllAsRead() {
    await notificationApiService.markAllAsRead()
    recentNotifications.value.forEach((n) => {
      n.is_read = true
    })
    unreadCount.value = 0
  }

  /**
   * 未读数量递减
   */
  function decrementUnread() {
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  }

  return {
    // 状态
    unreadCount,
    recentNotifications,
    loading,
    // 方法
    fetchUnreadCount,
    fetchRecent,
    refresh,
    markAsRead,
    markAllAsRead,
    decrementUnread
  }
})
