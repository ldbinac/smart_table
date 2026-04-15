/**
 * 邮件服务 API
 */
import apiClient from '@/api/client'

export interface EmailTemplate {
  id: string
  template_key: string
  name: string
  subject: string
  content_html: string
  content_text: string
  description: string
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface EmailLog {
  id: string
  recipient_email: string
  recipient_name: string
  template_key: string
  subject: string
  status: 'pending' | 'sent' | 'failed' | 'retrying'
  retry_count: number
  error_message: string | null
  sent_at: string | null
  created_at: string
}

export interface EmailStats {
  total_emails: number
  sent_count: number
  failed_count: number
  pending_count: number
  retrying_count: number
  success_rate: number
  template_stats: {
    template_key: string
    total: number
    sent: number
    failed: number
    success_rate: number
  }[]
}

export interface TemplateForm {
  name: string
  subject: string
  content_html: string
  content_text: string
  description: string
}

export const emailApiService = {
  /**
   * 获取邮件模板列表
   */
  getTemplates: async (): Promise<{ data: EmailTemplate[] }> => {
    return apiClient.get('/admin/email/templates')
  },

  /**
   * 获取单个邮件模板
   */
  getTemplate: async (templateKey: string): Promise<{ data: EmailTemplate }> => {
    return apiClient.get(`/admin/email/templates/${templateKey}`)
  },

  /**
   * 更新邮件模板
   */
  updateTemplate: async (templateKey: string, data: TemplateForm): Promise<{ success: boolean; message: string }> => {
    return apiClient.put(`/admin/email/templates/${templateKey}`, data)
  },

  /**
   * 重置邮件模板为默认
   */
  resetTemplate: async (templateKey: string): Promise<{ success: boolean; message: string }> => {
    return apiClient.post(`/admin/email/templates/${templateKey}/reset`)
  },

  /**
   * 删除邮件模板
   */
  deleteTemplate: async (templateKey: string): Promise<{ success: boolean; message: string }> => {
    return apiClient.delete(`/admin/email/templates/${templateKey}`)
  },

  /**
   * 获取邮件发送日志
   */
  getLogs: async (params: {
    page?: number
    per_page?: number
    status?: string
    template_key?: string
    recipient_email?: string
    start_date?: string
    end_date?: string
  }): Promise<{
    data: EmailLog[]
    meta?: {
      pagination: {
        page: number
        per_page: number
        total: number
        total_pages: number
        has_next: boolean
        has_prev: boolean
      }
    }
  }> => {
    return apiClient.get('/admin/email/logs', params)
  },

  /**
   * 获取邮件发送统计
   */
  getStats: async (): Promise<{
    data: {
      total: number
      sent: number
      failed: number
      pending: number
      retrying: number
      success_rate: number
      by_status: Record<string, number>
      by_template: Record<string, {
        total: number
        sent: number
        failed: number
        pending: number
        retrying: number
      }>
    }
    success: boolean
    message: string
  }> => {
    return apiClient.get('/admin/email/stats')
  }
}

export default emailApiService
