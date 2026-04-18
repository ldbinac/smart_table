/**
 * 管理后台 API 服务
 * 处理用户管理、系统配置、操作日志等管理相关 API
 */
import { apiClient } from '@/api/client';
import type { User, UserRole, UserStatus } from '@/api/types';

export interface UserListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  role?: UserRole;
  status?: UserStatus;
}

export interface CreateUserRequest {
  email: string;
  password: string;
  name: string;
  role: UserRole;
}

export interface UpdateUserRequest {
  name?: string;
  email?: string;
  role?: UserRole;
}

export interface OperationLog {
  id: string;
  user_id: string;
  user_name?: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  details?: Record<string, unknown>;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

export interface OperationLogListParams {
  page?: number;
  pageSize?: number;
  userId?: string;
  action?: string;
  entityType?: string;
  startDate?: string;
  endDate?: string;
}

export interface SystemConfig {
  key: string;
  value: string;
  description?: string;
  category?: string;
  updated_at?: string;
}

export interface Role {
  id: string;
  name: string;
  label: string;
  permissions?: string[];
}

export const getUserList = async (params: UserListParams): Promise<{
  items: User[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}> => {
  // 将前端参数名映射为后端期望的参数名
  const backendParams: Record<string, any> = {
    page: params.page,
    per_page: params.pageSize,
    search: params.search,
    role: params.role,
    status: params.status,
  };
  
  const response = await apiClient.get<{
    data: User[];
    meta?: {
      pagination?: {
        total?: number;
        page?: number;
        per_page?: number;
        total_pages?: number;
        has_next?: boolean;
        has_prev?: boolean;
      };
    };
  }>('/admin/users', backendParams);
  
  return {
    items: response.data || [],
    total: response.meta?.pagination?.total || 0,
    page: response.meta?.pagination?.page || 1,
    per_page: response.meta?.pagination?.per_page || 20,
    total_pages: response.meta?.pagination?.total_pages || 0,
  };
};

export const getUser = async (userId: string): Promise<User> => {
  return apiClient.get(`/admin/users/${userId}`);
};

export const createUser = async (data: CreateUserRequest): Promise<User> => {
  return apiClient.post('/admin/users', data);
};

export const updateUser = async (userId: string, data: UpdateUserRequest): Promise<User> => {
  return apiClient.put(`/admin/users/${userId}`, data);
};

export const deleteUser = async (userId: string): Promise<void> => {
  await apiClient.delete(`/admin/users/${userId}`);
};

export const updateUserStatus = async (userId: string, status: UserStatus): Promise<User> => {
  return apiClient.put(`/admin/users/${userId}/status`, { status });
};

export const resetUserPassword = async (userId: string, temporaryPassword?: string): Promise<{
  temporary_password?: string;
  message: string;
}> => {
  return apiClient.post(`/admin/users/${userId}/reset-password`, { temporary_password: temporaryPassword });
};

export const getSystemConfigs = async (): Promise<Record<string, any>> => {
  // 后端返回格式：{"basic": {"site_name": "xxx"}, "email": {...}}
  // apiClient 会提取 response.data，所以这里直接返回 data 部分
  return apiClient.get('/admin/settings');
};

export const updateSystemConfigs = async (configs: Array<{key: string; value: any; group?: string; description?: string}>): Promise<Record<string, any>> => {
  return apiClient.put('/admin/settings', { configs });
};

export const getOperationLogs = async (params: OperationLogListParams): Promise<{
  items: OperationLog[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}> => {
  // 将前端参数名映射为后端期望的参数名
  const backendParams: Record<string, any> = {
    page: params.page,
    per_page: params.pageSize,  // 后端期望 per_page，前端使用 pageSize
    user_id: params.user_id,
    action: params.action,
    entity_type: params.entity_type,
    start_date: params.start_date,
    end_date: params.end_date,
  };
  
  const response = await apiClient.get<{
    data: OperationLog[];
    meta?: {
      pagination?: {
        total?: number;
        page?: number;
        per_page?: number;
        total_pages?: number;
      };
    };
  }>('/admin/operation-logs', backendParams);
  return {
    items: response.data || [],
    total: response.meta?.pagination?.total || 0,
    page: response.meta?.pagination?.page || 1,
    per_page: response.meta?.pagination?.per_page || 20,
    total_pages: response.meta?.pagination?.total_pages || 0,
  };
};

export const exportOperationLogs = async (params: OperationLogListParams): Promise<Blob> => {
  return apiClient.raw().get('/admin/operation-logs/export', {
    params,
    responseType: 'blob',
  }).then((response) => response.data as Blob);
};

export const getRoles = async (): Promise<Role[]> => {
  return apiClient.get('/admin/roles');
};

export interface EmailConfig {
  smtp_host: string;
  smtp_port: number;
  sender_email: string;
  sender_name?: string;
  smtp_username: string;
  smtp_password: string;
  encryption_type: 'ssl' | 'tls' | 'none';
}

export interface SendTestEmailResponse {
  success: boolean;
  message: string;
  data: null;
}

export const sendTestEmail = async (config: EmailConfig, testEmail: string): Promise<SendTestEmailResponse> => {
  // 转换字段名以匹配后端期望的格式
  const backendConfig = {
    smtp_host: config.smtp_host,
    smtp_port: config.smtp_port,
    smtp_username: config.smtp_username,
    smtp_password: config.smtp_password,
    from_email: config.sender_email,
    from_name: config.sender_name,
    smtp_use_tls: config.encryption_type === 'tls',
    smtp_use_ssl: config.encryption_type === 'ssl',
    test_email: testEmail
  };
  // 使用 raw() 获取完整响应，因为后端返回的 data 为 null，但我们需要 success 和 message
  const response = await apiClient.raw().post('/admin/email/test', backendConfig);
  return response.data as SendTestEmailResponse;
};

export const adminApiService = {
  getUserList,
  getUser,
  createUser,
  updateUser,
  deleteUser,
  updateUserStatus,
  resetUserPassword,
  getSystemConfigs,
  updateSystemConfigs,
  getOperationLogs,
  exportOperationLogs,
  getRoles,
  sendTestEmail,
};

export default adminApiService;
