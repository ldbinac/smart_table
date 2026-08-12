import { ref, onUnmounted, toRefs } from 'vue'
import { useCollaborationStore } from '../stores/collaborationStore'
import { createSocketClient, type RealtimeSocketClient } from '../services/realtime/socketClient'
import type {
  OnlineUser,
  PresenceViewChangedRequest,
  PresenceCellSelectedRequest,
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
import { REALTIME_BASE_URL } from '@/api/config'
import { useAuthStore } from '../stores/authStore'
import { getToken } from '@/utils/auth/token'
import { ElMessage } from 'element-plus'
import { useTableStore } from '../stores/tableStore'
import { useViewStore } from '../stores/viewStore'
import type { FieldEntity } from '../db/schema'
import { normalizeFieldType } from '@/types/fields'

interface RealtimeStatusResponse {
  enabled: boolean
}

// 实时状态缓存常量
const REALTIME_STATUS_CACHE_KEY = 'realtime_status_cache'
const REALTIME_STATUS_CACHE_TTL = 2 * 60 * 60 * 1000 // 2小时（毫秒）

interface RealtimeStatusCache {
  enabled: boolean
  timestamp: number
}

function getRealtimeStatusCache(): RealtimeStatusCache | null {
  try {
    const raw = localStorage.getItem(REALTIME_STATUS_CACHE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as RealtimeStatusCache
    if (typeof parsed.enabled !== 'boolean' || typeof parsed.timestamp !== 'number') return null
    return parsed
  } catch {
    return null
  }
}

function setRealtimeStatusCache(enabled: boolean): void {
  try {
    const cache: RealtimeStatusCache = { enabled, timestamp: Date.now() }
    localStorage.setItem(REALTIME_STATUS_CACHE_KEY, JSON.stringify(cache))
  } catch (error) {
    console.warn('[realtime] Failed to write status cache:', error)
  }
}

function isRealtimeStatusCacheValid(cache: RealtimeStatusCache): boolean {
  return Date.now() - cache.timestamp < REALTIME_STATUS_CACHE_TTL
}

function convertApiFieldToEntity(apiField: any): FieldEntity {
  return {
    id: apiField.id,
    tableId: apiField.table_id,
    name: apiField.name,
    type: normalizeFieldType(apiField.type),
    options: apiField.options as Record<string, unknown> | undefined,
    config: apiField.config as Record<string, unknown> | undefined,
    isPrimary: apiField.is_primary || false,
    isSystem: apiField.is_system || false,
    isRequired: apiField.is_required || false,
    isVisible: apiField.is_visible ?? true,
    defaultValue: apiField.default_value,
    description: apiField.description,
    order: apiField.order ?? 0,
    createdAt: new Date(apiField.created_at).getTime(),
    updatedAt: new Date(apiField.updated_at).getTime(),
  }
}

export function useRealtimeCollaboration(baseId: string) {
  const collaborationStore = useCollaborationStore()
  const authStore = useAuthStore()
  const tableStore = useTableStore()
  const viewStore = useViewStore()

  const socketClient = ref<RealtimeSocketClient | null>(null)

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
    // 检查缓存
    const cached = getRealtimeStatusCache()
    if (cached && isRealtimeStatusCacheValid(cached)) {
      collaborationStore.setRealtimeAvailable(cached.enabled)
      return cached.enabled
    }

    try {
      const response = await apiClient.get<RealtimeStatusResponse>('/realtime/status')
      const enabled = response.enabled === true
      collaborationStore.setRealtimeAvailable(enabled)
      // 写入缓存
      setRealtimeStatusCache(enabled)
      return enabled
    } catch {
      collaborationStore.setRealtimeAvailable(false)
      // 请求失败时，如有过期缓存则使用过期缓存作为 fallback
      if (cached) {
        collaborationStore.setRealtimeAvailable(cached.enabled)
        return cached.enabled
      }
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

    const token = getToken()
    if (!token) {
      collaborationStore.setConnectionStatus('disconnected')
      return
    }

    const client = await createSocketClient(REALTIME_BASE_URL, token)
    socketClient.value = client

    // 注册 socket client 到共享锁服务（会自动监听 lock_result 事件）
    collaborationStore.registerLockClient(client)

    setupEventListeners()

    await client.connect()
  }

  function handleConnect() {
    console.log('[COLLAB-DEBUG] socket connected, joining room', baseId)
    collaborationStore.setConnectionStatus('connected')
    joinRoom()
    if (collaborationStore.offlineQueue.length > 0) {
      collaborationStore.processOfflineQueue()
    }
  }

  function handleDisconnect() {
    collaborationStore.setConnectionStatus('reconnecting')
  }

  function setupEventListeners() {
    if (!socketClient.value) return

    removeEventListeners()

    socketClient.value.on('connect', handleConnect)

    socketClient.value.on('room:joined', (data: { base_id: string; online_users: OnlineUser[] }) => {
      collaborationStore.setOnlineUsers(data.online_users || [])
    })

    socketClient.value.on('disconnect', handleDisconnect)

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

    socketClient.value.off('connect', handleConnect)
    socketClient.value.off('disconnect', handleDisconnect)
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
      name: data.name,
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
    console.log('[COLLAB-DEBUG] lock:acquired received', data)
    const key = `${data.record_id}:${data.field_id}`
    collaborationStore.setLockedCell(key, {
      user_id: data.user_id,
      nickname: data.nickname,
      name: data.name,
      avatar: data.avatar,
      table_id: data.table_id,
      record_id: data.record_id,
      field_id: data.field_id,
    })
  }

  function handleLockReleased(data: LockReleasedBroadcast) {
    const key = `${data.record_id}:${data.field_id}`
    collaborationStore.removeLockedCell(key)

    if (data.reason === 'timeout') {
      ElMessage.warning('编辑锁已超时释放')
    }
  }

  function handleRecordCreated(data: DataRecordCreatedBroadcast) {
    const currentUserId = authStore.user?.id
    if (data.changed_by === currentUserId) return

    if (data.record && data.table_id) {
      tableStore.addRecordFromRemote(data.table_id, data.record as any)
    }
  }

  function handleRecordUpdated(data: DataRecordUpdatedBroadcast) {
    const currentUserId = authStore.user?.id
    if (data.changed_by === currentUserId) {
      return
    }

    if (data.table_id && data.record_id) {
      tableStore.updateRecordFromRemote(data.table_id, data.record_id, data.changes)
    }

    // 乐观冲突检测：检查远程更新是否与本地待提交变更冲突
    collaborationStore.checkConflictOnRemoteUpdate(data, currentUserId || '')
  }

  function handleRecordDeleted(data: DataRecordDeletedBroadcast) {
    const currentUserId = authStore.user?.id
    if (data.changed_by === currentUserId) return

    if (data.table_id && data.record_id) {
      tableStore.deleteRecordFromRemote(data.table_id, data.record_id)
    }
  }

  function handleFieldCreated(data: DataFieldCreatedBroadcast) {
    const currentUserId = authStore.user?.id
    if (data.changed_by === currentUserId) return

    if (data.field && data.table_id) {
      const fieldEntity = convertApiFieldToEntity(data.field)
      tableStore.addFieldFromRemote(data.table_id, fieldEntity)
    }
  }

  function handleFieldUpdated(data: DataFieldUpdatedBroadcast) {
    const currentUserId = authStore.user?.id
    if (data.changed_by === currentUserId) return

    if (data.table_id && data.field_id && data.field) {
      const fieldEntity = convertApiFieldToEntity(data.field)
      tableStore.updateFieldFromRemote(data.table_id, data.field_id, fieldEntity)
    }
  }

  function handleFieldDeleted(data: DataFieldDeletedBroadcast) {
    const currentUserId = authStore.user?.id
    if (data.changed_by === currentUserId) return

    if (data.table_id && data.field_id) {
      tableStore.deleteFieldFromRemote(data.table_id, data.field_id)
    }
  }

  function handleViewUpdated(data: DataViewUpdatedBroadcast) {
    const currentUserId = authStore.user?.id
    if (data.changed_by === currentUserId) return

    if (data.view_id) {
      viewStore.updateViewFromRemote(data.view_id, data.changes)
    }
  }

  function handleTableCreated(data: DataTableCreatedBroadcast) {
    const currentUserId = authStore.user?.id
    if (data.changed_by === currentUserId) return

    if (data.table) {
      tableStore.addTableFromRemote(data.table as any)
    }
  }

  function handleTableUpdated(data: DataTableUpdatedBroadcast) {
    const currentUserId = authStore.user?.id
    if (data.changed_by === currentUserId) return

    if (data.table_id) {
      tableStore.updateTableFromRemote(data.table_id, data.changes)
    }
  }

  function handleTableDeleted(data: DataTableDeletedBroadcast) {
    const currentUserId = authStore.user?.id
    if (data.changed_by === currentUserId) return

    if (data.table_id) {
      tableStore.deleteTableFromRemote(data.table_id)
    }
  }

  function joinRoom() {
    if (!collaborationStore.isRealtimeAvailable || !socketClient.value) {
      return
    }
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

  function releaseLock(data: LockReleaseRequest) {
    collaborationStore.releaseLock(data)
  }

  function disconnect() {
    if (socketClient.value) {
      removeEventListeners()
      socketClient.value.disconnect()
      socketClient.value = null
    }
    collaborationStore.clearLockClient()
    collaborationStore.setConnectionStatus('disconnected')
    collaborationStore.onlineUsers.clear()
    collaborationStore.lockedCells.clear()
    collaborationStore.setCurrentBase(null)
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
    releaseLock,
    disconnect,
  }
}
