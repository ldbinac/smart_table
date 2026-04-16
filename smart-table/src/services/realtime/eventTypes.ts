export interface SocketError {
  code: number
  message: string
}

export interface RoomJoinRequest {
  base_id: string
}

export interface RoomJoinCallback {
  success: boolean
  online_users?: OnlineUser[]
}

export interface RoomLeaveRequest {
  base_id: string
}

export interface OnlineUser {
  user_id: string
  nickname: string
  avatar?: string
  current_view?: CurrentView
}

export interface CurrentView {
  table_id: string
  view_id: string
  view_type: string
}

export interface PresenceViewChangedRequest {
  base_id: string
  table_id: string
  view_id: string
  view_type: string
}

export interface PresenceViewChangedBroadcast {
  user_id: string
  nickname: string
  avatar?: string
  table_id: string
  view_id: string
  view_type: string
}

export interface PresenceCellSelectedRequest {
  base_id: string
  table_id: string
  record_id: string
  field_id: string
}

export interface PresenceCellSelectedBroadcast {
  user_id: string
  nickname: string
  avatar?: string
  table_id: string
  record_id: string
  field_id: string
}

export interface PresenceUserJoinedBroadcast {
  user_id: string
  nickname: string
  avatar?: string
  current_view?: CurrentView
}

export interface PresenceUserLeftBroadcast {
  user_id: string
  nickname: string
}

export interface LockAcquireRequest {
  table_id: string
  record_id: string
  field_id: string
}

export interface LockAcquireCallback {
  success: boolean
  locked_by?: { user_id: string; nickname: string; avatar?: string }
}

export interface LockAcquiredBroadcast {
  user_id: string
  nickname: string
  avatar?: string
  table_id: string
  record_id: string
  field_id: string
}

export interface LockReleaseRequest {
  table_id: string
  record_id: string
  field_id: string
}

export interface LockReleasedBroadcast {
  user_id: string
  table_id: string
  record_id: string
  field_id: string
  reason?: 'manual' | 'timeout' | 'disconnect'
}

export interface FieldChange {
  field_id: string
  old_value: unknown
  new_value: unknown
}

export interface DataRecordCreatedBroadcast {
  table_id: string
  record: Record<string, unknown>
  changed_by: string
  timestamp: string
}

export interface DataRecordUpdatedBroadcast {
  table_id: string
  record_id: string
  changes: FieldChange[]
  changed_by: string
  timestamp: string
  version: number
}

export interface DataRecordDeletedBroadcast {
  table_id: string
  record_id: string
  snapshot: Record<string, unknown>
  changed_by: string
  timestamp: string
}

export interface DataFieldCreatedBroadcast {
  table_id: string
  field: Record<string, unknown>
  changed_by: string
  timestamp: string
}

export interface DataFieldUpdatedBroadcast {
  table_id: string
  field_id: string
  changes: Record<string, unknown>
  changed_by: string
  timestamp: string
}

export interface DataFieldDeletedBroadcast {
  table_id: string
  field_id: string
  changed_by: string
  timestamp: string
}

export interface DataViewUpdatedBroadcast {
  table_id: string
  view_id: string
  changes: Record<string, unknown>
  changed_by: string
  timestamp: string
}

export interface DataTableCreatedBroadcast {
  base_id: string
  table: Record<string, unknown>
  changed_by: string
  timestamp: string
}

export interface DataTableUpdatedBroadcast {
  base_id: string
  table_id: string
  changes: Record<string, unknown>
  changed_by: string
  timestamp: string
}

export interface DataTableDeletedBroadcast {
  base_id: string
  table_id: string
  changed_by: string
  timestamp: string
}

export type ClientToServerEvents = {
  'room:join': (request: RoomJoinRequest, callback: (response: RoomJoinCallback) => void) => void
  'room:leave': (request: RoomLeaveRequest) => void
  'presence:view_changed': (request: PresenceViewChangedRequest) => void
  'presence:cell_selected': (request: PresenceCellSelectedRequest) => void
  'lock:acquire': (request: LockAcquireRequest, callback: (response: LockAcquireCallback) => void) => void
  'lock:release': (request: LockReleaseRequest) => void
}

export type ServerToClientEvents = {
  'presence:user_joined': (data: PresenceUserJoinedBroadcast) => void
  'presence:user_left': (data: PresenceUserLeftBroadcast) => void
  'presence:view_changed': (data: PresenceViewChangedBroadcast) => void
  'presence:cell_selected': (data: PresenceCellSelectedBroadcast) => void
  'lock:acquired': (data: LockAcquiredBroadcast) => void
  'lock:released': (data: LockReleasedBroadcast) => void
  'data:record_created': (data: DataRecordCreatedBroadcast) => void
  'data:record_updated': (data: DataRecordUpdatedBroadcast) => void
  'data:record_deleted': (data: DataRecordDeletedBroadcast) => void
  'data:field_created': (data: DataFieldCreatedBroadcast) => void
  'data:field_updated': (data: DataFieldUpdatedBroadcast) => void
  'data:field_deleted': (data: DataFieldDeletedBroadcast) => void
  'data:view_updated': (data: DataViewUpdatedBroadcast) => void
  'data:table_created': (data: DataTableCreatedBroadcast) => void
  'data:table_updated': (data: DataTableUpdatedBroadcast) => void
  'data:table_deleted': (data: DataTableDeletedBroadcast) => void
}

export type RealtimeEventMap = ServerToClientEvents & {
  connect: () => void
  disconnect: (reason: string) => void
  error: (data: SocketError) => void
}
