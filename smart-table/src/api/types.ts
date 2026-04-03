/**
 * API类型定义
 * 定义统一的请求/响应类型
 */

// API响应基础接口
export interface ApiResponse<T = unknown> {
  success: boolean
  message: string
  data: T
  meta?: ApiMeta
}

// 分页元数据
export interface ApiMeta {
  total: number
  page: number
  per_page: number
  pages: number
}

// API错误接口
export interface ApiError {
  code: number
  message: string
  details?: Record<string, string[]>
}

// 分页请求参数
export interface PaginationParams {
  page?: number
  per_page?: number
}

// 分页响应数据
export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

// 用户类型
export interface User {
  id: string
  email: string
  username: string
  nickname?: string
  avatar_url?: string
  role: 'user' | 'admin'
  status: 'active' | 'inactive'
  created_at: string
  updated_at: string
}

// 登录请求
export interface LoginRequest {
  email: string
  password: string
}

// 登录响应
export interface LoginResponse {
  access_token: string
  refresh_token: string
  expires_in: number
  user: User
}

// 注册请求
export interface RegisterRequest {
  email: string
  username: string
  password: string
  nickname?: string
}

// 刷新Token请求
export interface RefreshTokenRequest {
  refresh_token: string
}

// 刷新Token响应
export interface RefreshTokenResponse {
  access_token: string
  expires_in: number
}

// Base成员角色
export type BaseRole = 'owner' | 'admin' | 'editor' | 'commenter' | 'viewer'

// Base成员
export interface BaseMember {
  id: string
  base_id: string
  user_id: string
  user?: User
  role: BaseRole
  joined_at: string
}

// Base
export interface Base {
  id: string
  name: string
  description?: string
  icon: string
  color: string
  owner_id: string
  is_archived: boolean
  created_at: string
  updated_at: string
  members?: BaseMember[]
}

// Table
export interface Table {
  id: string
  base_id: string
  name: string
  description?: string
  order: number
  record_count: number
  created_at: string
  updated_at: string
}

// 字段类型
export type FieldType =
  | 'text'
  | 'number'
  | 'date'
  | 'single_select'
  | 'multi_select'
  | 'checkbox'
  | 'attachment'
  | 'link'
  | 'formula'
  | 'lookup'
  | 'rollup'
  | 'created_time'
  | 'last_modified_time'
  | 'created_by'
  | 'last_modified_by'
  | 'auto_number'
  | 'barcode'
  | 'button'
  | 'rating'
  | 'email'
  | 'phone'
  | 'url'

// 字段选项
export interface FieldOption {
  value: string
  color?: string
}

// Field
export interface Field {
  id: string
  table_id: string
  name: string
  type: FieldType
  options?: {
    choices?: FieldOption[]
    precision?: number
    format?: string
    [key: string]: unknown
  }
  order: number
  is_required: boolean
  is_unique: boolean
  is_system: boolean
  default_value?: string
  description?: string
  created_at: string
  updated_at: string
}

// Record
export interface Record {
  id: string
  table_id: string
  values: Record<string, unknown>
  created_by?: string
  updated_by?: string
  created_at: string
  updated_at: string
}

// 视图类型
export type ViewType = 'grid' | 'gallery' | 'kanban' | 'gantt' | 'calendar' | 'form'

// 筛选条件
export interface FilterCondition {
  field_id: string
  operator: string
  value: unknown
}

// 排序规则
export interface SortRule {
  field_id: string
  direction: 'asc' | 'desc'
}

// View
export interface View {
  id: string
  table_id: string
  name: string
  type: ViewType
  description?: string
  config?: Record<string, unknown>
  filters: FilterCondition[]
  sorts: SortRule[]
  hidden_fields: string[]
  field_widths: Record<string, number>
  order: number
  is_default: boolean
  created_at: string
  updated_at: string
}

// Dashboard Widget
export interface DashboardWidget {
  id: string
  type: string
  title: string
  config: Record<string, unknown>
  position: {
    x: number
    y: number
    w: number
    h: number
  }
}

// Dashboard
export interface Dashboard {
  id: string
  base_id: string
  name: string
  description?: string
  layout: 'grid' | 'free'
  widgets: DashboardWidget[]
  is_default: boolean
  created_at: string
  updated_at: string
}

// 附件
export interface Attachment {
  id: string
  filename: string
  original_name: string
  mime_type: string
  size: number
  url: string
  thumbnail_url?: string
  created_at: string
}
