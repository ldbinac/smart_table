import { ref, onUnmounted, toRefs } from 'vue'
import { useCollaborationStore } from '../stores/collaborationStore'
import { createSocketClient, type RealtimeSocketClient } from '../services/realtime/socketClient'
import type {
  OnlineUser,
  PresenceViewChangedRequest,
  PresenceCellSelectedRequest,
  LockAcquireRequest,
  LockReleaseRequest,
  PresenceUserJoinedBroadcast,
  PresenceUserLeftBroadcast,
  PresenceViewChangedBroadcast,
  PresenceCellSelectedBroadcast,
  LockAcquiredBroadcast,
  LockReleasedBroadcast,
  DataRecordCreatedBroadcast,
  DataRecordUpdatedBroadcast,
  DataRecordDeletedBroadcast,
  DataFieldCreatedBroadcast,
  DataFieldUpdatedBroadcast,
  DataFieldDeletedBroadcast,
  DataViewUpdatedBroadcast,
  DataTableCreatedBroadcast,
  DataTableUpdatedBroadcast,
  DataTableDeletedBroadcast,
} from '../services/realtime/eventTypes'
import { apiClient } from '@/api/client'
import { useAuthStore } from '../stores/authStore'
import { realtimeEventEmitter } from '../services/realtime/eventEmitter'
import { ElMessage } from 'element-plus'
import type { ConflictInfo } from '@/components/collaboration/ConflictDialog.vue'

interface RealtimeStatusResponse {
  enabled: boolean
}

export function useRealtimeCollaboration(baseId: string) {
  const collaborationStore = useCollaborationStore()
  const authStore = useAuthStore()

  const socketClient = ref<RealtimeSocketClient | null>(null)

  const pendingChanges = ref<Map<string, { fieldId: string; value: unknown; timestamp: number }>>(new Map())
  const conflictVisible = ref(false)
  const currentConflict = ref<ConflictInfo | null>(null)
  const waitingForLocks = ref<Set<string>>(new Set())

  const {
    isRealtimeAvailable,
    connectionStatus,
    onlineUsers,
    lockedCells,
    offlineQueue,
    currentBaseId,
    queueFull,
  } = toRefs(collaborationStore)

  async function checkRealtimeAvailability(): Promise<boolean> {
    try {
      const response = await apiClient.get<RealtimeStatusResponse>('/realtime/status')
      const enabled = response.enabled === true
      collaborationStore.setRealtimeAvailable(enabled)
      return enabled
    } catch {
      collaborationStore.setRealtimeAvailable(false)
      return false
    }
  }

  async function connect() {
    if (!baseId) return

    collaborationStore.setCurrentBase(baseId)
    collaborationStore.setConnectionStatus('connecting')

    const available = await checkRealtimeAvailability()
    if (!available) {
      collaborationStore.setConnectionStatus('disconnected')
      return
    }

    const token = authStore.token
    if (!token) {
      collaborationStore.setConnectionStatus('disconnected')
      return
    }

    const serverUrl = import.meta.env.VITE_REALTIME_URL || window.location.origin
    const client = await createSocketClient(serverUrl, token)
    socketClient.value = client

    setupEventListeners()

    await client.connect()
  }

  function setupEventListeners() {
    if (!socketClient.value) return

    socketClient.value.on('connect', () => {
      collaborationStore.setConnectionStatus('connected')
      if (collaborationStore.offlineQueue.length > 0) {
        collaborationStore.processOfflineQueue()
      }
    })

    socketClient.value.on('disconnect', () => {
      collaborationStore.setConnectionStatus('reconnecting')
    })

    socketClient.value.on('presence:user_joined', handleUserJoined)
    socketClient.value.on('presence:user_left', handleUserLeft)
    socketClient.value.on('presence:view_changed', handleViewChanged)
    socketClient.value.on('presence:cell_selected', handleCellSelected)
    socketClient.value.on('lock:acquired', handleLockAcquired)
    socketClient.value.on('lock:released', handleLockReleased)
    socketClient.value.on('data:record_created', handleRecordCreated)
    socketClient.value.on('data:record_updated', handleRecordUpdated)
    socketClient.value.on('data:record_deleted', handleRecordDeleted)
    socketClient.value.on('data:field_created', handleFieldCreated)
    socketClient.value.on('data:field_updated', handleFieldUpdated)
    socketClient.value.on('data:field_deleted', handleFieldDeleted)
    socketClient.value.on('data:view_updated', handleViewUpdated)
    socketClient.value.on('data:table_created', handleTableCreated)
    socketClient.value.on('data:table_updated', handleTableUpdated)
    socketClient.value.on('data:table_deleted', handleTableDeleted)
  }

  function removeEventListeners() {
    if (!socketClient.value) return

    socketClient.value.off('connect', () => {})
    socketClient.value.off('disconnect', () => {})
    socketClient.value.off('presence:user_joined', handleUserJoined)
    socketClient.value.off('presence:user_left', handleUserLeft)
    socketClient.value.off('presence:view_changed', handleViewChanged)
    socketClient.value.off('presence:cell_selected', handleCellSelected)
    socketClient.value.off('lock:acquired', handleLockAcquired)
    socketClient.value.off('lock:released', handleLockReleased)
    socketClient.value.off('data:record_created', handleRecordCreated)
    socketClient.value.off('data:record_updated', handleRecordUpdated)
    socketClient.value.off('data:record_deleted', handleRecordDeleted)
    socketClient.value.off('data:field_created', handleFieldCreated)
    socketClient.value.off('data:field_updated', handleFieldUpdated)
    socketClient.value.off('data:field_deleted', handleFieldDeleted)
    socketClient.value.off('data:view_updated', handleViewUpdated)
    socketClient.value.off('data:table_created', handleTableCreated)
    socketClient.value.off('data:table_updated', handleTableUpdated)
    socketClient.value.off('data:table_deleted', handleTableDeleted)
  }

  function handleUserJoined(data: PresenceUserJoinedBroadcast) {
    collaborationStore.addOnlineUser({
      user_id: data.user_id,
      nickname: data.nickname,
      avatar: data.avatar,
      current_view: data.current_view,
    })
  }

  function handleUserLeft(data: PresenceUserLeftBroadcast) {
    collaborationStore.removeOnlineUser(data.user_id)
  }

  function handleViewChanged(_data: PresenceViewChangedBroadcast) {
  }

  function handleCellSelected(_data: PresenceCellSelectedBroadcast) {
  }

  function handleLockAcquired(data: LockAcquiredBroadcast) {
    const key = `${data.record_id}:${data.field_id}`
    collaborationStore.setLockedCell(key, {
      user_id: data.user_id,
      nickname: data.nickname,
      avatar: data.avatar,
      table_id: data.table_id,
      record_id: data.record_id,
      field_id: data.field_id,
    })
  }

  function handleLockReleased(data: LockReleasedBroadcast) {
    const key = `${data.record_id}:${data.field_id}`
    collaborationStore.removeLockedCell(key)

    if (waitingForLocks.value.has(key)) {
      waitingForLocks.value.delete(key)
      if (data.reason === 'timeout') {
        ElMessage.warning('编辑锁已超时释放')
      } else {
        ElMessage.info('单元格已解锁，可以开始编辑')
      }
    }
  }

  function handleRecordCreated(_data: DataRecordCreatedBroadcast) {
  }

  function handleRecordUpdated(data: DataRecordUpdatedBroadcast) {
    const currentUserId = authStore.user?.id
    if (data.changed_by === currentUserId) return

    for (const change of data.changes) {
      const pendingKey = `${data.record_id}:${change.field_id}`
      const pending = pendingChanges.value.get(pendingKey)
      if (pending) {
        currentConflict.value = {
          fieldName: change.field_id,
          fieldId: change.field_id,
          recordId: data.record_id,
          myValue: pending.value,
          otherValue: change.new_value,
          otherUserName: data.changed_by,
        }
        conflictVisible.value = true
        pendingChanges.value.delete(pendingKey)
      }
    }
  }

  function handleRecordDeleted(_data: DataRecordDeletedBroadcast) {
  }

  function handleFieldCreated(_data: DataFieldCreatedBroadcast) {
  }

  function handleFieldUpdated(_data: DataFieldUpdatedBroadcast) {
  }

  function handleFieldDeleted(_data: DataFieldDeletedBroadcast) {
  }

  function handleViewUpdated(_data: DataViewUpdatedBroadcast) {
  }

  function handleTableCreated(_data: DataTableCreatedBroadcast) {
  }

  function handleTableUpdated(_data: DataTableUpdatedBroadcast) {
  }

  function handleTableDeleted(_data: DataTableDeletedBroadcast) {
  }

  function joinRoom() {
    if (!collaborationStore.isRealtimeAvailable || !socketClient.value) return
    socketClient.value.emit('room:join' as never, { base_id: baseId } as never)
  }

  function leaveRoom() {
    if (!collaborationStore.isRealtimeAvailable || !socketClient.value) return
    socketClient.value.emit('room:leave' as never, { base_id: baseId } as never)
  }

  function sendPresenceViewChange(data: PresenceViewChangedRequest) {
    if (!collaborationStore.isRealtimeAvailable || !socketClient.value) return
    socketClient.value.emit('presence:view_changed' as never, data as never)
  }

  function sendPresenceCellSelect(data: PresenceCellSelectedRequest) {
    if (!collaborationStore.isRealtimeAvailable || !socketClient.value) return
    socketClient.value.emit('presence:cell_selected' as never, data as never)
  }

  function acquireLock(data: LockAcquireRequest): Promise<{ success: boolean; reason?: string }> {
    if (!collaborationStore.isRealtimeAvailable || !socketClient.value) {
      return Promise.resolve({ success: false, reason: 'realtime_unavailable' })
    }

    return new Promise((resolve) => {
      const key = `${data.record_id}:${data.field_id}`
      const existingLock = collaborationStore.lockedCells.get(key)
      if (existingLock && existingLock.user_id !== authStore.user?.id) {
        ElMessage.warning(`${existingLock.nickname} 正在编辑此单元格`)
        waitingForLocks.value.add(key)
        resolve({ success: false, reason: 'locked' })
        return
      }

      socketClient.value!.emit('lock:acquire' as never, data as never)
      resolve({ success: true })
    })
  }

  function releaseLock(data: LockReleaseRequest) {
    if (!collaborationStore.isRealtimeAvailable || !socketClient.value) return
    socketClient.value.emit('lock:release' as never, data as never)
  }

  function disconnect() {
    if (socketClient.value) {
      removeEventListeners()
      socketClient.value.disconnect()
      socketClient.value = null
    }
    collaborationStore.setConnectionStatus('disconnected')
    collaborationStore.onlineUsers.clear()
    collaborationStore.lockedCells.clear()
    collaborationStore.setCurrentBase(null)
    pendingChanges.value.clear()
    waitingForLocks.value.clear()
  }

  function trackPendingChange(recordId: string, fieldId: string, value: unknown) {
    const key = `${recordId}:${fieldId}`
    pendingChanges.value.set(key, { fieldId, value, timestamp: Date.now() })
  }

  function removePendingChange(recordId: string, fieldId: string) {
    const key = `${recordId}:${fieldId}`
    pendingChanges.value.delete(key)
  }

  function resolveConflict(choice: 'mine' | 'theirs' | 'history') {
    if (!currentConflict.value) return

    if (choice === 'mine') {
      trackPendingChange(currentConflict.value.recordId, currentConflict.value.fieldId, currentConflict.value.myValue)
    }

    currentConflict.value = null
    conflictVisible.value = false
  }

  connect()

  onUnmounted(() => {
    disconnect()
  })

  return {
    isRealtimeAvailable,
    connectionStatus,
    onlineUsers,
    lockedCells,
    offlineQueue,
    currentBaseId,
    queueFull,
    joinRoom,
    leaveRoom,
    sendPresenceViewChange,
    sendPresenceCellSelect,
    acquireLock,
    releaseLock,
    disconnect,
    conflictVisible,
    currentConflict,
    resolveConflict,
    trackPendingChange,
    removePendingChange,
  }
}
