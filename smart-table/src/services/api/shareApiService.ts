/**
 * 分享管理 API 服务
 * 提供成员管理和分享链接相关的 API 调用
 */
import axios from 'axios';
import type { BaseMember, BaseShare } from '@/stores/baseStore';
import type { Base } from '@/api/types';

const API_BASE = '/api';

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器，添加认证 token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器，处理错误
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    console.error('[shareApiService] Error:', error);
    const message = error.response?.data?.message || '请求失败，请稍后重试';
    return Promise.reject(new Error(message));
  }
);

export const shareApiService = {
  /**
   * 获取 Base 成员列表
   */
  async getMembers(baseId: string): Promise<BaseMember[]> {
    const response = await apiClient.get(`/bases/${baseId}/members`);
    return response.data || [];
  },

  /**
   * 添加成员
   */
  async addMember(baseId: string, email: string, role: string): Promise<BaseMember> {
    const response = await apiClient.post(`/bases/${baseId}/members`, { email, role });
    return response.data || {};
  },

  /**
   * 批量添加成员
   */
  async batchAddMembers(
    baseId: string,
    members: Array<{ email: string; role: string }>
  ): Promise<{
    success_count: number;
    failed_count: number;
    successful: BaseMember[];
    failed: Array<{ index: number; email: string; error: string }>;
  }> {
    const response = await apiClient.post(`/bases/${baseId}/members/batch`, { members });
    return response.data || {};
  },

  /**
   * 更新成员角色
   */
  async updateMemberRole(baseId: string, userId: string, role: string): Promise<BaseMember> {
    const response = await apiClient.put(`/bases/${baseId}/members/${userId}`, { role });
    return response.data || {};
  },

  /**
   * 移除成员
   */
  async removeMember(baseId: string, userId: string): Promise<void> {
    await apiClient.delete(`/bases/${baseId}/members/${userId}`);
  },

  /**
   * 获取 Base 分享列表
   */
  async getShares(baseId: string): Promise<BaseShare[]> {
    const response = await apiClient.get(`/bases/${baseId}/shares`);
    return response.data || [];
  },

  /**
   * 创建分享链接
   */
  async createShare(
    baseId: string,
    permission: 'view' | 'edit',
    expiresAt?: number
  ): Promise<BaseShare> {
    const response = await apiClient.post(`/bases/${baseId}/shares`, {
      permission,
      expires_at: expiresAt
    });
    return response.data || {};
  },

  /**
   * 删除分享链接
   */
  async deleteShare(shareId: string): Promise<void> {
    await apiClient.delete(`/shares/${shareId}`);
  },

  /**
   * 更新分享链接
   */
  async updateShare(
    shareId: string,
    data: {
      is_active?: boolean;
      permission?: 'view' | 'edit';
      expires_at?: number;
    }
  ): Promise<BaseShare> {
    const response = await apiClient.put(`/shares/${shareId}`, data);
    return response.data || {};
  },

  /**
   * 获取分享给当前用户的 Base 列表
   */
  async getSharedWithMe(): Promise<Base[]> {
    const response = await apiClient.get('/bases/shared-with-me');
    return response.data || [];
  },

  /**
   * 获取当前用户创建的分享列表
   */
  async getSharedByMe(): Promise<BaseShare[]> {
    const response = await apiClient.get('/bases/shared-by-me');
    return response.data || [];
  },

  /**
   * 通过分享令牌访问 Base
   */
  async accessShare(shareToken: string): Promise<{
    base: Base;
    permission: 'view' | 'edit';
    share_token: string;
  }> {
    const response = await apiClient.get(`/share/${shareToken}`);
    return response.data || {};
  }
};
