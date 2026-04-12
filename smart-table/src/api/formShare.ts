/**
 * 表单分享 API
 * 处理表单分享的创建、管理和数据提交
 */
import { apiClient } from "./client";
import type { ApiResponse, PaginatedResponse } from "./client";

/**
 * 表单分享配置
 */
export interface FormShareConfig {
  id: string;
  table_id: string;
  share_token: string;
  is_active: boolean;
  allow_anonymous: boolean;
  require_captcha: boolean;
  expires_at: number | null;
  max_submissions: number | null;
  current_submissions: number;
  allowed_fields: string[];
  title: string | null;
  description: string | null;
  submit_button_text: string;
  success_message: string;
  theme: string;
  created_at: string;
  updated_at: string;
  created_by: string;
  // 统计信息
  is_expired?: boolean;
  is_reached_limit?: boolean;
  can_submit?: boolean;
}

/**
 * 表单提交记录
 */
export interface FormSubmission {
  id: string;
  form_share_id: string;
  record_id: string | null;
  submitter_ip: string | null;
  submitter_user_agent: string | null;
  submitter_info: Record<string, unknown>;
  submitted_at: string;
}

/**
 * 表单结构（字段定义）
 */
export interface FormSchema {
  table_id: string;
  table_name: string;
  form_title: string;
  form_description: string | null;
  submit_button_text: string;
  success_message: string;
  theme: string;
  require_captcha: boolean;
  fields: FormFieldSchema[];
}

/**
 * 表单字段定义
 */
export interface FormFieldSchema {
  id: string;
  name: string;
  type: string;
  required: boolean;
  config: Record<string, unknown>;
  description: string | null;
}

/**
 * 创建表单分享请求
 */
export interface CreateFormShareRequest {
  allow_anonymous?: boolean;
  require_captcha?: boolean;
  expires_at?: number | null;
  max_submissions?: number | null;
  allowed_fields?: string[];
  title?: string;
  description?: string;
  submit_button_text?: string;
  success_message?: string;
  theme?: string;
}

/**
 * 更新表单分享请求
 */
export interface UpdateFormShareRequest {
  is_active?: boolean;
  allow_anonymous?: boolean;
  require_captcha?: boolean;
  expires_at?: number | null;
  max_submissions?: number | null;
  allowed_fields?: string[];
  title?: string;
  description?: string;
  submit_button_text?: string;
  success_message?: string;
  theme?: string;
}

/**
 * 提交表单数据请求
 */
export interface SubmitFormRequest {
  values: Record<string, unknown>;
  submitter_info?: Record<string, unknown>;
  captcha?: string;
}

/**
 * 提交表单数据响应
 */
export interface SubmitFormResponse {
  record_id: string;
  submitted_at: string;
}

/**
 * 表单分享验证响应
 */
export interface ValidateFormShareResponse {
  valid: boolean;
  require_captcha: boolean;
  can_submit: boolean;
}

/**
 * 表单分享服务
 */
export const formShareApi = {
  /**
   * 创建表单分享
   * @param tableId 表格ID
   * @param data 表单分享配置
   */
  createFormShare(
    tableId: string,
    data: CreateFormShareRequest
  ): Promise<FormShareConfig & { share_url: string }> {
    return apiClient.post(`/tables/${tableId}/form-shares`, data);
  },

  /**
   * 获取表格的所有表单分享
   * @param tableId 表格ID
   */
  getFormShares(tableId: string): Promise<FormShareConfig[]> {
    return apiClient.get(`/tables/${tableId}/form-shares`);
  },

  /**
   * 获取表单分享详情
   * @param shareId 表单分享ID
   */
  getFormShare(shareId: string): Promise<FormShareConfig> {
    return apiClient.get(`/form-shares/${shareId}`);
  },

  /**
   * 更新表单分享配置
   * @param shareId 表单分享ID
   * @param data 更新数据
   */
  updateFormShare(
    shareId: string,
    data: UpdateFormShareRequest
  ): Promise<FormShareConfig> {
    return apiClient.put(`/form-shares/${shareId}`, data);
  },

  /**
   * 删除表单分享
   * @param shareId 表单分享ID
   */
  deleteFormShare(shareId: string): Promise<void> {
    return apiClient.delete(`/form-shares/${shareId}`);
  },

  /**
   * 获取表单提交记录
   * @param shareId 表单分享ID
   * @param page 页码
   * @param perPage 每页数量
   */
  getFormSubmissions(
    shareId: string,
    page: number = 1,
    perPage: number = 20
  ): Promise<PaginatedResponse<FormSubmission>> {
    return apiClient.get(`/form-shares/${shareId}/submissions`, {
      page,
      per_page: perPage,
    });
  },

  // ==================== 公开接口（无需认证） ====================

  /**
   * 获取表单结构（公开接口）
   * @param token 分享令牌
   */
  getFormSchema(token: string): Promise<FormSchema> {
    return apiClient.get(`/form-shares/${token}/schema`);
  },

  /**
   * 验证表单分享是否有效（公开接口）
   * @param token 分享令牌
   */
  validateFormShare(token: string): Promise<ValidateFormShareResponse> {
    return apiClient.get(`/form-shares/${token}/validate`);
  },

  /**
   * 提交表单数据（公开接口）
   * @param token 分享令牌
   * @param data 提交数据
   */
  submitForm(
    token: string,
    data: SubmitFormRequest
  ): Promise<SubmitFormResponse> {
    return apiClient.post(`/form-shares/${token}/submit`, data);
  },
};

export default formShareApi;
