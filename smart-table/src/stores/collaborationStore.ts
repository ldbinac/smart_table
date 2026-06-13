import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { OnlineUser, LockAcquireRequest, LockReleaseRequest, LockAcquireCallback } from '../services/realtime/eventTypes'
import type { RealtimeSocketClient } from '../services/realtime/socketClient'
import { apiClient } from '@/api/client'

export interface LockInfo {
  user_id: string
  nickname: string
  name: string
  avatar?: string
  table_id: string
  record_id: string
  field_id: string
}

export interface OfflineOperation {
  id: string
  type: string
  resource: string
  data: any
  timestamp: number
}

export const useCollaborationStore = defineStore('collaboration', () => {
  const isRealtimeAvailable = ref(false)
  const connectionStatus = ref<'disconnected' | 'connecting' | 'connected' | 'reconnecting'>('disconnected')
  const onlineUsers = ref<Map<string, OnlineUser>>(new Map())
  const lockedCells = ref<Map<string, LockInfo>>(new Map())
  const offlineQueue = ref<OfflineOperation[]>([])
  const currentBaseId = ref<string | null>(null)
  const queueFull = ref(false)

  // 用于锁操作的 socket client 引用（由 useRealtimeCollaboration 注册）
  const lockSocketClient = ref<RealtimeSocketClient | null>(null)

  const MAX_QUEUE_SIZE = 100

  // 当前组件持有的锁（组件卸载时需要释放）
  const currentEditingLocks = ref<Set<string>>(new Set())

  function setRealtimeAvailable(val: boolean) {
    isRealtimeAvailable.value = val
  }

  function setConnectionStatus(status: 'disconnected' | 'connecting' | 'connected' | 'reconnecting') {
    connectionStatus.value = status
  }

  function addOnlineUser(user: OnlineUser) {
    onlineUsers.value.set(user.user_id, user)
  }

  function removeOnlineUser(userId: string) {
    onlineUsers.value.delete(userId)
  }

  function setOnlineUsers(users: OnlineUser[]) {
    onlineUsers.value.clear()
    for (const user of users) {
      onlineUsers.value.set(user.user_id, user)
    }
  }

  function setLockedCell(key: string, info: LockInfo) {
    lockedCells.value.set(key, info)
  }

  function removeLockedCell(key: string) {
    lockedCells.value.delete(key)
  }

  function addToOfflineQueue(op: OfflineOperation) {
    if (queueFull.value) return
    offlineQueue.value.push(op)
    if (offlineQueue.value.length >= MAX_QUEUE_SIZE) {
      queueFull.value = true
    }
  }

  function clearOfflineQueue() {
    offlineQueue.value = []
    queueFull.value = false
  }

  function setCurrentBase(baseId: string | null) {
    currentBaseId.value = baseId
  }

  async function processOfflineQueue() {
    if (offlineQueue.value.length === 0) return

    const queue = [...offlineQueue.value]
    const failed: OfflineOperation[] = []

    for (const op of queue) {
      try {
        await apiClient.post(op.resource, op.data)
      } catch {
        failed.push(op)
      }
    }

    if (failed.length === 0) {
      clearOfflineQueue()
    } else {
      offlineQueue.value = failed
      queueFull.value = failed.length >= MAX_QUEUE_SIZE
    }
  }

  // ── 锁操作方法 ──
  // useRealtimeCollaboration 创建 socket client 后调用此方法注册
  function registerLockClient(client: RealtimeSocketClient) {
    lockSocketClient.value = client
  }

  function clearLockClient() {
    lockSocketClient.value = null
  }

  /** 判断当前 socket client 是否可用 */
  function isLockClientReady(): boolean {
    return !!(isRealtimeAvailable.value && lockSocketClient.value?.isConnected())
  }

  /** 检查指定 cell 是否被其他用户锁定 */
  function isCellLockedByOther(recordId: string, fieldId: string, currentUserId: string): boolean {
    const key = `${recordId}:${fieldId}`
    const lock = lockedCells.value.get(key)
    return !!lock && lock.user_id !== currentUserId
  }

  /** 获取锁定当前 cell 的用户信息 */
  function getCellLockInfo(recordId: string, fieldId: string): LockInfo | undefined {
    const key = `${recordId}:${fieldId}`
    return lockedCells.value.get(key)
  }

  /** 尝试获取编辑锁 */
  function acquireLock(data: LockAcquireRequest, currentUserId: string): Promise<{ success: boolean; reason?: string; locked_by?: { name: string; nickname: string } }> {
    if (!isLockClientReady()) {
      return Promise.resolve({ success: false, reason: 'realtime_unavailable' })
    }

    const key = `${data.record_id}:${data.field_id}`
    const existingLock = lockedCells.value.get(key)
    if (existingLock && existingLock.user_id !== currentUserId) {
      return Promise.resolve({ success: false, reason: 'locked', locked_by: { name: existingLock.name, nickname: existingLock.nickname } })
    }

    // 如果是当前用户自己的锁，直接返回成功
    if (existingLock && existingLock.user_id === currentUserId) {
      return Promise.resolve({ success: true })
    }

    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        resolve({ success: false, reason: 'timeout' })
      }, 8000)

      try {
        lockSocketClient.value!.emit('lock:acquire' as never, data, ((response: LockAcquireCallback) => {
          clearTimeout(timeout)
          if (response?.success) {
            currentEditingLocks.value.add(key)
            resolve({ success: true })
          } else {
            resolve({
              success: false,
              reason: 'locked',
              locked_by: response?.locked_by ? { name: response.locked_by.name, nickname: response.locked_by.nickname } : undefined
            })
          }
        }) as never)
      } catch {
        clearTimeout(timeout)
        resolve({ success: false, reason: 'error' })
      }
    })
  }

  /** 释放编辑锁 */
  function releaseLock(data: LockReleaseRequest) {
    const key = `${data.record_id}:${data.field_id}`
    currentEditingLocks.value.delete(key)
    if (!isLockClientReady()) return
    try {
      lockSocketClient.value!.emit('lock:release' as never, data as never)
    } catch {
      // 释放锁失败不影响主要流程
    }
  }

  /** 释放当前组件持有的所有锁（用于组件卸载时清理） */
  function releaseAllCurrentLocks(tableId: string) {
    currentEditingLocks.value.forEach((key) => {
      const [recordId, fieldId] = key.split(':')
      if (recordId && fieldId) {
        try {
          lockSocketClient.value!.emit('lock:release' as never, { table_id: tableId, record_id: recordId, field_id: fieldId } as never)
        } catch {
          // ignore
        }
      }
    })
    currentEditingLocks.value.clear()
  }

  function $reset() {
    isRealtimeAvailable.value = false
    connectionStatus.value = 'disconnected'
    onlineUsers.value.clear()
    lockedCells.value.clear()
    offlineQueue.value = []
    currentBaseId.value = null
    queueFull.value = false
    lockSocketClient.value = null
    currentEditingLocks.value.clear()
  }

  return {
    isRealtimeAvailable,
    connectionStatus,
    onlineUsers,
    lockedCells,
    offlineQueue,
    currentBaseId,
    queueFull,
    setRealtimeAvailable,
    setConnectionStatus,
    addOnlineUser,
    removeOnlineUser,
    setOnlineUsers,
    setLockedCell,
    removeLockedCell,
    addToOfflineQueue,
    clearOfflineQueue,
    setCurrentBase,
    processOfflineQueue,
    registerLockClient,
    clearLockClient,
    isLockClientReady,
    isCellLockedByOther,
    getCellLockInfo,
    acquireLock,
    releaseLock,
    releaseAllCurrentLocks,
    currentEditingLocks,
    $reset,
  }
})
