import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCollaborationStore } from '@/stores/collaborationStore'

describe('CollaborationStore - Disabled Mode', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('isRealtimeAvailable defaults to false', () => {
    const store = useCollaborationStore()
    expect(store.isRealtimeAvailable).toBe(false)
  })

  it('connectionStatus defaults to disconnected', () => {
    const store = useCollaborationStore()
    expect(store.connectionStatus).toBe('disconnected')
  })

  it('onlineUsers is empty by default', () => {
    const store = useCollaborationStore()
    expect(store.onlineUsers.size).toBe(0)
  })

  it('lockedCells is empty by default', () => {
    const store = useCollaborationStore()
    expect(store.lockedCells.size).toBe(0)
  })

  it('offlineQueue is empty by default', () => {
    const store = useCollaborationStore()
    expect(store.offlineQueue.length).toBe(0)
  })

  it('queueFull defaults to false', () => {
    const store = useCollaborationStore()
    expect(store.queueFull).toBe(false)
  })

  it('setRealtimeAvailable can set to false', () => {
    const store = useCollaborationStore()
    store.setRealtimeAvailable(false)
    expect(store.isRealtimeAvailable).toBe(false)
  })

  it('addOnlineUser works but isRealtimeAvailable stays false', () => {
    const store = useCollaborationStore()
    store.addOnlineUser({
      user_id: 'user-1',
      nickname: 'Test User',
      avatar: null,
      current_view: null
    })
    expect(store.onlineUsers.size).toBe(1)
    expect(store.isRealtimeAvailable).toBe(false)
  })

  it('removeOnlineUser works', () => {
    const store = useCollaborationStore()
    store.addOnlineUser({
      user_id: 'user-1',
      nickname: 'Test User',
      avatar: null,
      current_view: null
    })
    store.removeOnlineUser('user-1')
    expect(store.onlineUsers.size).toBe(0)
  })

  it('setLockedCell works', () => {
    const store = useCollaborationStore()
    store.setLockedCell('record-1:field-1', {
      user_id: 'user-1',
      nickname: 'Test User',
      avatar: null,
      table_id: 'table-1',
      record_id: 'record-1',
      field_id: 'field-1'
    })
    expect(store.lockedCells.has('record-1:field-1')).toBe(true)
  })

  it('removeLockedCell works', () => {
    const store = useCollaborationStore()
    store.setLockedCell('record-1:field-1', {
      user_id: 'user-1',
      nickname: 'Test User',
      avatar: null,
      table_id: 'table-1',
      record_id: 'record-1',
      field_id: 'field-1'
    })
    store.removeLockedCell('record-1:field-1')
    expect(store.lockedCells.has('record-1:field-1')).toBe(false)
  })

  it('addToOfflineQueue adds operations', () => {
    const store = useCollaborationStore()
    store.addToOfflineQueue({
      id: 'op-1',
      type: 'update',
      resource: 'record',
      data: { record_id: 'r1', values: {} },
      timestamp: Date.now()
    })
    expect(store.offlineQueue.length).toBe(1)
  })

  it('offlineQueue limit sets queueFull', () => {
    const store = useCollaborationStore()
    for (let i = 0; i < 101; i++) {
      store.addToOfflineQueue({
        id: `op-${i}`,
        type: 'update',
        resource: 'record',
        data: {},
        timestamp: Date.now()
      })
    }
    expect(store.queueFull).toBe(true)
  })

  it('clearOfflineQueue resets queue', () => {
    const store = useCollaborationStore()
    store.addToOfflineQueue({
      id: 'op-1',
      type: 'update',
      resource: 'record',
      data: {},
      timestamp: Date.now()
    })
    store.clearOfflineQueue()
    expect(store.offlineQueue.length).toBe(0)
    expect(store.queueFull).toBe(false)
  })
})

describe('CollaborationStore - API returns disabled', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('stays unavailable when API returns enabled:false', async () => {
    vi.mock('@/services/api/client', () => ({
      apiClient: {
        get: vi.fn().mockResolvedValue({
          data: { enabled: false, socket_url: null }
        })
      }
    }))

    const store = useCollaborationStore()
    expect(store.isRealtimeAvailable).toBe(false)
  })
})
