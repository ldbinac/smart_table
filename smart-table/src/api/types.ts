/**
 * API 类型定义
 * 与后端 Flask API 响应格式保持一致
 */

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface PaginationParams {
  page?: number
  per_page?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface User {
  id: string
  email: string
  name: string
  avatar?: string
  role: UserRole
  status: UserStatus
  email_verified: boolean
  last_login_at?: string
  created_at: string
  updated_at: string
}

export type UserRole = 'admin' | 'workspace_admin' | 'editor' | 'viewer'
export type UserStatus = 'active' | 'inactive' | 'suspended' | 'deleted'

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  name: string
  password: string
}

export interface LoginResponse {
  user: User
  tokens: {
    access_token: string
    refresh_token: string
  }
}

export interface TokenPair {
  access_token: string
  refresh_token: string
}

export interface Base {
  id: string
  name: string
  description?: string
  owner_id: string
  icon?: string
  color?: string
  is_personal: boolean
  is_starred: boolean
  created_at: string
  updated_at: string
  member_count?: number
  table_count?: number
}

export interface BaseMember {
  id: string
  base_id: string
  user_id: string
  role: MemberRole
  invited_by?: string
  joined_at: string
  user?: Pick<User, 'id' | 'name' | 'avatar'>
}

export type MemberRole = 'owner' | 'admin' | 'editor' | 'commenter' | 'viewer'

export interface Table {
  id: string
  base_id: string
  name: string
  description?: string
  order: number
  primary_field_id?: string
  record_count?: number
  field_count?: number
  created_at: string
  updated_at: string
}

export type FieldType =
  | 'single_line_text'
  | 'long_text'
  | 'rich_text'
  | 'number'
  | 'currency'
  | 'percent'
  | 'rating'
  | 'date'
  | 'date_time'
  | 'duration'
  | 'single_select'
  | 'multi_select'
  | 'checkbox'
  | 'link_to_record'
  | 'lookup'
  | 'rollup'
  | 'created_by'
  | 'last_modified_by'
  | 'collaborator'
  | 'attachment'
  | 'formula'
  | 'auto_number'
  | 'barcode'
  | 'email'
  | 'phone'
  | 'url'
  | 'button'

export interface FieldOption {
  id: string
  label: string
  color?: string
  order?: number
}

export interface FieldConfig {
  formula?: string
  precision?: number
  icon?: string
  options?: FieldOption[]
  linked_table_id?: string
  lookup_field_id?: string
  rollup_expression?: string
  auto_number_prefix?: string
  barcode_format?: string
  button_action?: string
}

export interface Field {
  id: string
  table_id: string
  name: string
  type: FieldType
  description?: string
  order: number
  is_primary: boolean
  is_required: boolean
  options?: Record<string, unknown>
  config?: FieldConfig
  defaultValue?: unknown
  created_at: string
  updated_at: string
}

export interface Record {
  id: string
  table_id: string
  values: Record<string, unknown>
  primary_value?: string
  created_by?: string
  updated_by?: string
  created_at: string
  updated_at: string
}

export interface RecordComment {
  id: string
  record_id: string
  user_id: string
  content: string
  parent_id?: string
  created_at: string
  updated_at: string
  user?: { id: string; name: string; avatar?: string }
}

export type ViewType = 'table' | 'gallery' | 'kanban' | 'calendar' | 'timeline' | 'list'

export interface ViewFilter {
  field_id: string
  operator: 'eq' | 'ne' | 'contains' | 'not_contains' | 'gt' | 'lt' | 'gte' | 'lte' | 'is_empty' | 'is_not_empty'
  value: unknown
}

export interface ViewSortConfig {
  field_id: string
  direction: 'asc' | 'desc'
}

export interface ViewGroupConfig {
  field_id: string
  sort_direction?: 'asc' | 'desc'
}

export interface View {
  id: string
  table_id: string
  name: string
  type: ViewType
  description?: string
  order: number
  is_default: boolean
  is_public: boolean
  filters?: ViewFilter[]
  sort_config?: ViewSortConfig[]
  group_config?: ViewGroupConfig
  field_visibility?: Record<string, boolean>
  created_at: string
  updated_at: string
}

export interface Dashboard {
  id: string
  base_id: string
  user_id?: string
  name: string
  description?: string
  layout?: { columns: number; gap: number }
  widgets?: DashboardWidget[]
  is_public: boolean
  created_at: string
  updated_at: string
}

export interface DashboardWidget {
  id: string
  dashboard_id: string
  type: DashboardWidgetType
  title?: string
  config?: Record<string, unknown>
  position_x: number
  position_y: number
  width: number
  height: number
  order: number
  created_at: string
  updated_at: string
}

export type DashboardWidgetType = 'stat' | 'chart' | 'table' | 'text' | 'image'

export type AttachmentType = 'image' | 'document' | 'video' | 'audio' | 'archive' | 'other'

export interface Attachment {
  id: string
  record_id?: string
  field_id?: string
  filename: string
  original_name: string
  file_size: number
  human_size: string
  mime_type: string
  storage_type: string
  url?: string
  thumbnail_url?: string
  uploaded_by?: string
  created_at: string
}

export interface UploadResult {
  attachment: Attachment
}

export interface ImportPreview {
  total_rows: number
  columns: Array<{ name: string; index: number; sample_values: unknown[] }>
  sample_data: Record<string, unknown>[]
  preview: boolean
}

export interface ImportOptions {
  table_id: string
  field_mapping: Record<string, string>
  skip_first_row?: boolean
  encoding?: string
}

export interface ImportResult {
  imported_count: number
  failed_count: number
  errors?: Array<{ row: number; message: string }>
}

export interface ExportOptions {
  table_id: string
  format: 'csv' | 'excel' | 'json'
  field_ids?: string[]
  record_ids?: string[]
  view_id?: string
  include_headers?: boolean
}

export interface TaskStatus {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  result_url?: string
  error?: string
}

export interface FormulaInfo {
  name: string
  syntax: string
  desc: string
  category: string
}
