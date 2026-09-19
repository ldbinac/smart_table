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
   * 获取最近站内信（未读优先）
   *
   * 先取未读项，保证未读站内信必定出现在铃铛下拉列表；
   * 不足 limit 时再用最近站内信补齐并去重。最终按「未读在前、组内按创建时间倒序」排序。
   */
  async function fetchRecent(limit: number = 5) {
    loading.value = true
    try {
      const unreadRes = await notificationApiService.getNotifications({
        is_read: false,
        per_page: limit,
      })
      const list: AppNotification[] = [...(unreadRes.data || [])]

      if (list.length < limit) {
        const recentRes = await notificationApiService.getNotifications({ per_page: limit })
        const seen = new Set(list.map((n) => n.id))
        for (const item of recentRes.data || []) {
          if (list.length >= limit) break
          if (!seen.has(item.id)) {
            seen.add(item.id)
            list.push(item)
          }
        }
      }

      list.sort((a, b) => {
        if (a.is_read !== b.is_read) return a.is_read ? 1 : -1
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      })

      recentNotifications.value = list
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
    if (target) {
      target.is_read = true
    }
    // 目标可能不在 recent 列表中（如从列表页标记的旧站内信），
    // 统一以服务端计数校正，避免本地递减产生漂移
    await fetchUnreadCount()
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

  /**
   * 清空本地状态（登出时调用，避免残留上一位用户的未读数与列表）
   */
  function reset() {
    unreadCount.value = 0
    recentNotifications.value = []
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
    decrementUnread,
    reset
  }
})
