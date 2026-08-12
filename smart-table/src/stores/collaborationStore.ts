import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { OnlineUser, LockAcquireRequest, LockReleaseRequest, LockResultBroadcast, DataRecordUpdatedBroadcast } from '../services/realtime/eventTypes'
import type { RealtimeSocketClient } from '../services/realtime/socketClient'
import type { ConflictInfo } from '@/components/collaboration/ConflictDialog.vue'
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

interface PendingLockRequest {
  resolve: (result: { success: boolean; reason?: string; locked_by?: { name: string; nickname: string } }) => void
  timeout: ReturnType<typeof setTimeout>
}

interface PendingChange {
  fieldId: string
  value: unknown
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

  // 等待 lock_result 回执的锁请求（key: `${record_id}:${field_id}`）
  const pendingLockRequests = ref<Map<string, PendingLockRequest>>(new Map())

  // 本地待提交的单元格变更（用于乐观冲突检测）
  const pendingChanges = ref<Map<string, PendingChange>>(new Map())

  // 冲突对话框状态
  const conflictVisible = ref(false)
  const currentConflict = ref<ConflictInfo | null>(null)

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
    // 注册 lock_result 事件监听器，处理服务端返回的锁申请结果
    client.on('lock_result', handleLockResult as never)
  }

  function clearLockClient() {
    if (lockSocketClient.value) {
      lockSocketClient.value.off('lock_result', handleLockResult as never)
    }
    lockSocketClient.value = null
    // socket 断开，所有等待中的锁请求立即失败
    pendingLockRequests.value.forEach((pending) => {
      clearTimeout(pending.timeout)
      pending.resolve({ success: false, reason: 'disconnected' })
    })
    pendingLockRequests.value.clear()
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

  /**
   * 处理服务端返回的 lock_result 事件，匹配 pendingLockRequests 并 resolve。
   * 由 registerLockClient 注册的监听器调用。
   */
  function handleLockResult(data: LockResultBroadcast) {
    console.log('[COLLAB-DEBUG] lock_result received', data)
    const key = `${data.record_id}:${data.field_id}`
    const pending = pendingLockRequests.value.get(key)

    if (pending) {
      clearTimeout(pending.timeout)
      pendingLockRequests.value.delete(key)

      if (data.success) {
        currentEditingLocks.value.add(key)
        pending.resolve({ success: true })
      } else {
        const lockedBy = data.locked_by
        if (lockedBy && lockedBy.user_id) {
          // 真正被其他用户持有锁
          pending.resolve({
            success: false,
            reason: 'locked',
            locked_by: { name: lockedBy.name, nickname: lockedBy.nickname || lockedBy.name },
          })
        } else {
          // 锁服务故障（Redis 不可用 / 参数缺失 / 后端异常）——不阻塞用户编辑
          console.warn('[COLLAB-DEBUG] lock service unavailable, allowing edit', data)
          pending.resolve({ success: true, reason: 'service_unavailable' })
        }
      }
    }
  }

  /** 尝试获取编辑锁 */
  function acquireLock(data: LockAcquireRequest, currentUserId: string): Promise<{ success: boolean; reason?: string; locked_by?: { name: string; nickname: string } }> {
    const ready = isLockClientReady()
    console.log('[COLLAB-DEBUG] acquireLock called', {
      data,
      currentUserId,
      isRealtimeAvailable: isRealtimeAvailable.value,
      hasLockClient: !!lockSocketClient.value,
      isConnected: lockSocketClient.value?.isConnected(),
      isLockClientReady: ready,
    })
    if (!ready) {
      console.warn('[COLLAB-DEBUG] acquireLock aborted: realtime not ready')
      return Promise.resolve({ success: false, reason: 'realtime_unavailable' })
    }

    const key = `${data.record_id}:${data.field_id}`
    const existingLock = lockedCells.value.get(key)
    if (existingLock && existingLock.user_id !== currentUserId) {
      return Promise.resolve({ success: false, reason: 'locked', locked_by: { name: existingLock.name, nickname: existingLock.nickname || existingLock.name } })
    }

    // 如果是当前用户自己的锁，直接返回成功
    if (existingLock && existingLock.user_id === currentUserId) {
      return Promise.resolve({ success: true })
    }

    return new Promise((resolve) => {
      // 如果已有等待中的请求，先清除
      const existingPending = pendingLockRequests.value.get(key)
      if (existingPending) {
        clearTimeout(existingPending.timeout)
        pendingLockRequests.value.delete(key)
      }

      // 设置超时（8秒）
      const timeout = setTimeout(() => {
        pendingLockRequests.value.delete(key)
        resolve({ success: false, reason: 'timeout' })
      }, 8000)

      // 存储等待中的请求
      pendingLockRequests.value.set(key, { resolve, timeout })

      // 发送锁请求（不带 ack 回调，通过 lock_result 事件接收结果）
      try {
        lockSocketClient.value!.emit('lock:acquire' as never, data as never)
      } catch {
        clearTimeout(timeout)
        pendingLockRequests.value.delete(key)
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
  function releaseAllCurrentLocks(baseId: string, tableId: string) {
    currentEditingLocks.value.forEach((key) => {
      const [recordId, fieldId] = key.split(':')
      if (recordId && fieldId) {
        try {
          lockSocketClient.value!.emit('lock:release' as never, { base_id: baseId, table_id: tableId, record_id: recordId, field_id: fieldId } as never)
        } catch {
          // ignore
        }
      }
    })
    currentEditingLocks.value.clear()
  }

  // ── 乐观冲突检测 ──

  /** 记录本地待提交的单元格变更 */
  function trackPendingChange(recordId: string, fieldId: string, value: unknown) {
    const key = `${recordId}:${fieldId}`
    pendingChanges.value.set(key, { fieldId, value, timestamp: Date.now() })
  }

  /** 移除已提交的待提交变更 */
  function removePendingChange(recordId: string, fieldId: string) {
    const key = `${recordId}:${fieldId}`
    pendingChanges.value.delete(key)
  }

  /**
   * 收到远程记录更新广播时，检查是否与本地待提交变更冲突。
   * 如果冲突，弹出 ConflictDialog 让用户裁决。
   * 返回是否有冲突。
   */
  function checkConflictOnRemoteUpdate(data: DataRecordUpdatedBroadcast, currentUserId: string): boolean {
    if (data.changed_by === currentUserId) return false
    if (!data.changes || data.changes.length === 0) return false

    let hasConflict = false
    for (const change of data.changes) {
      const pendingKey = `${data.record_id}:${change.field_id}`
      const pending = pendingChanges.value.get(pendingKey)
      if (pending) {
        // 从在线用户列表查找用户名
        const onlineUser = onlineUsers.value.get(data.changed_by)
        const otherUserName = onlineUser?.nickname || onlineUser?.name || data.changed_by

        currentConflict.value = {
          fieldName: change.field_id,
          fieldId: change.field_id,
          recordId: data.record_id,
          myValue: pending.value,
          otherValue: change.new_value,
          otherUserName,
        }
        conflictVisible.value = true
        pendingChanges.value.delete(pendingKey)
        hasConflict = true
      }
    }
    return hasConflict
  }

  /** 处理冲突对话框的用户选择 */
  function resolveConflict(choice: 'mine' | 'theirs' | 'history') {
    if (!currentConflict.value) return

    if (choice === 'mine') {
      // 用户选择保留自己的修改，重新加入待提交队列等待下次提交
      trackPendingChange(currentConflict.value.recordId, currentConflict.value.fieldId, currentConflict.value.myValue)
    }

    currentConflict.value = null
    conflictVisible.value = false
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
    // 清理等待中的锁请求
    pendingLockRequests.value.forEach((pending) => {
      clearTimeout(pending.timeout)
      pending.resolve({ success: false, reason: 'disconnected' })
    })
    pendingLockRequests.value.clear()
    pendingChanges.value.clear()
    conflictVisible.value = false
    currentConflict.value = null
  }

  return {
    isRealtimeAvailable,
    connectionStatus,
    onlineUsers,
    lockedCells,
    offlineQueue,
    currentBaseId,
    queueFull,
    conflictVisible,
    currentConflict,
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
    handleLockResult,
    acquireLock,
    releaseLock,
    releaseAllCurrentLocks,
    trackPendingChange,
    removePendingChange,
    checkConflictOnRemoteUpdate,
    resolveConflict,
    currentEditingLocks,
    $reset,
  }
})
