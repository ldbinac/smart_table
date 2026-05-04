import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCollaborationStore } from '@/stores/collaborationStore'
import { realtimeEventEmitter } from '@/services/realtime/eventEmitter'

describe('CollaborationStore - Enabled Mode', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('setRealtimeAvailable can set to true', () => {
    const store = useCollaborationStore()
    store.setRealtimeAvailable(true)
    expect(store.isRealtimeAvailable).toBe(true)
  })

  it('setConnectionStatus works', () => {
    const store = useCollaborationStore()
    store.setConnectionStatus('connecting')
    expect(store.connectionStatus).toBe('connecting')

    store.setConnectionStatus('connected')
    expect(store.connectionStatus).toBe('connected')

    store.setConnectionStatus('reconnecting')
    expect(store.connectionStatus).toBe('reconnecting')

    store.setConnectionStatus('disconnected')
    expect(store.connectionStatus).toBe('disconnected')
  })

  it('setCurrentBase works', () => {
    const store = useCollaborationStore()
    store.setCurrentBase('base-123')
    expect(store.currentBaseId).toBe('base-123')
  })

  it('multiple online users can be tracked', () => {
    const store = useCollaborationStore()
    store.addOnlineUser({ user_id: 'u1', nickname: 'User 1', name: 'User 1', avatar: undefined, current_view: undefined })
    store.addOnlineUser({ user_id: 'u2', nickname: 'User 2', name: 'User 2', avatar: undefined, current_view: undefined })
    store.addOnlineUser({ user_id: 'u3', nickname: 'User 3', name: 'User 3', avatar: undefined, current_view: undefined })
    expect(store.onlineUsers.size).toBe(3)
  })

  it('addOnlineUser updates existing user', () => {
    const store = useCollaborationStore()
    store.addOnlineUser({ user_id: 'u1', nickname: 'User 1', name: 'User 1', avatar: undefined, current_view: undefined })
    store.addOnlineUser({ user_id: 'u1', nickname: 'User 1 Updated', name: 'User 1 Updated', avatar: 'avatar.png', current_view: { table_id: 't1', view_id: 'v1', view_type: 'table' } })
    expect(store.onlineUsers.size).toBe(1)
    expect(store.onlineUsers.get('u1')?.nickname).toBe('User 1 Updated')
  })

  it('multiple locks can be tracked', () => {
    const store = useCollaborationStore()
    store.setLockedCell('r1:f1', { user_id: 'u1', nickname: 'User 1', name: 'User 1', avatar: undefined, table_id: 't1', record_id: 'r1', field_id: 'f1' })
    store.setLockedCell('r2:f2', { user_id: 'u2', nickname: 'User 2', name: 'User 2', avatar: undefined, table_id: 't1', record_id: 'r2', field_id: 'f2' })
    expect(store.lockedCells.size).toBe(2)
  })

  it('lock release removes specific lock', () => {
    const store = useCollaborationStore()
    store.setLockedCell('r1:f1', { user_id: 'u1', nickname: 'User 1', name: 'User 1', avatar: undefined, table_id: 't1', record_id: 'r1', field_id: 'f1' })
    store.setLockedCell('r2:f2', { user_id: 'u2', nickname: 'User 2', name: 'User 2', avatar: undefined, table_id: 't1', record_id: 'r2', field_id: 'f2' })
    store.removeLockedCell('r1:f1')
    expect(store.lockedCells.size).toBe(1)
    expect(store.lockedCells.has('r2:f2')).toBe(true)
  })

  it('$reset clears all state', () => {
    const store = useCollaborationStore()
    store.setRealtimeAvailable(true)
    store.setConnectionStatus('connected')
    store.addOnlineUser({ user_id: 'u1', nickname: 'User 1', name: 'User 1', avatar: undefined, current_view: undefined })
    store.setLockedCell('r1:f1', { user_id: 'u1', nickname: 'User 1', name: 'User 1', avatar: undefined, table_id: 't1', record_id: 'r1', field_id: 'f1' })
    store.setCurrentBase('base-1')
    store.$reset()
    expect(store.isRealtimeAvailable).toBe(false)
    expect(store.connectionStatus).toBe('disconnected')
    expect(store.onlineUsers.size).toBe(0)
    expect(store.lockedCells.size).toBe(0)
    expect(store.currentBaseId).toBeNull()
  })

  it('processOfflineQueue processes items', async () => {
    const store = useCollaborationStore()
    store.addToOfflineQueue({
      id: 'op-1',
      type: 'update',
      resource: 'record',
      data: { record_id: 'r1', values: { f1: 'val1' } },
      timestamp: Date.now()
    })
    store.addToOfflineQueue({
      id: 'op-2',
      type: 'delete',
      resource: 'record',
      data: { record_id: 'r2' },
      timestamp: Date.now()
    })
    expect(store.offlineQueue.length).toBe(2)

    vi.mock('@/services/api/client', () => ({
      apiClient: {
        put: vi.fn().mockResolvedValue({ data: { success: true } }),
        delete: vi.fn().mockResolvedValue({ data: { success: true } })
      }
    }))

    await store.processOfflineQueue()
  })
})

describe('RealtimeEventEmitter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('on and emit work', () => {
    const handler = vi.fn()
    realtimeEventEmitter.on('data:record_updated', handler)
    realtimeEventEmitter.emit('data:record_updated', { table_id: 't1', record_id: 'r1' } as any)
    expect(handler).toHaveBeenCalledWith({ table_id: 't1', record_id: 'r1' })
    realtimeEventEmitter.off('data:record_updated', handler)
  })

  it('off removes handler', () => {
    const handler = vi.fn()
    realtimeEventEmitter.on('data:record_updated', handler)
    realtimeEventEmitter.off('data:record_updated', handler)
    realtimeEventEmitter.emit('data:record_updated', { table_id: 't1' } as any)
    expect(handler).not.toHaveBeenCalled()
  })

  it('removeAllListeners clears all', () => {
    const handler1 = vi.fn()
    const handler2 = vi.fn()
    realtimeEventEmitter.on('data:record_updated', handler1)
    realtimeEventEmitter.on('data:record_created', handler2)
    realtimeEventEmitter.removeAllListeners()
    realtimeEventEmitter.emit('data:record_updated', {} as any)
    realtimeEventEmitter.emit('data:record_created', {} as any)
    expect(handler1).not.toHaveBeenCalled()
    expect(handler2).not.toHaveBeenCalled()
  })
})
