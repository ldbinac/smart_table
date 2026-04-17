import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { OnlineUser } from '../services/realtime/eventTypes'
import { apiClient } from '@/api/client'

export interface LockInfo {
  user_id: string
  nickname: string
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

  const MAX_QUEUE_SIZE = 100

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

  function $reset() {
    isRealtimeAvailable.value = false
    connectionStatus.value = 'disconnected'
    onlineUsers.value.clear()
    lockedCells.value.clear()
    offlineQueue.value = []
    currentBaseId.value = null
    queueFull.value = false
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
    $reset,
  }
})
