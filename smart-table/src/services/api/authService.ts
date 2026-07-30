/**
 * 认证服务
 * 处理用户认证相关的API调用
 */

import axios from 'axios';
import { apiClient } from '@/api/client';
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  User,
  TokenPair,
  GiteeAuthorizeResponse
} from '@/api/types';
import { apiConfig } from '@/api/config';

// 创建独立的 axios 实例用于刷新令牌（不经过拦截器）
const refreshClient = axios.create({
  baseURL: apiConfig.baseURL,
  timeout: apiConfig.timeout,
  headers: {
    'Content-Type': 'application/json'
  }
});

export const login = async (data: LoginRequest): Promise<LoginResponse> => {
  return apiClient.post<LoginResponse>('/auth/login', data);
};

export const register = async (data: RegisterRequest): Promise<User> => {
  return apiClient.post<User>('/auth/register', data);
};

export const logout = async (): Promise<void> => {
  await apiClient.post<void>('/auth/logout');
};

export const logoutAll = async (): Promise<void> => {
  await apiClient.post<void>('/auth/logout-all');
};

export const refreshToken = async (refreshTokenValue: string): Promise<TokenPair> => {
  // 刷新接口需要使用 refresh_token 作为 Authorization header
  // 使用独立的 axios 实例，不经过默认拦截器（避免自动添加 access_token）
  const response = await refreshClient.post<{ success: boolean; data: TokenPair }>('/auth/refresh', {}, {
    headers: {
      Authorization: `Bearer ${refreshTokenValue}`
    }
  });

  // 适配后端响应格式 {success, data}
  if (response.data.success && response.data.data) {
    return response.data.data;
  }

  throw new Error('Token refresh failed');
};

export const getCurrentUser = async (): Promise<User> => {
  return apiClient.get<User>('/auth/me');
};

export const changePassword = async (oldPassword: string, newPassword: string): Promise<void> => {
  await apiClient.put<void>('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword
  });
};

export const updateProfile = async (data: Partial<User>): Promise<User> => {
  return apiClient.put<User>('/auth/profile', data);
};

export const getGiteeStarAuthorizeUrl = async (userId: string): Promise<GiteeAuthorizeResponse> => {
  return apiClient.post<GiteeAuthorizeResponse>('/auth/gitee-star/authorize', {
    user_id: userId,
  });
};

export const verifyGiteeStarCallback = async (code: string, state: string): Promise<LoginResponse> => {
  return apiClient.post<LoginResponse>('/auth/gitee-star-callback', { code, state });
};

export const authService = {
  login,
  register,
  logout,
  logoutAll,
  refreshToken,
  getCurrentUser,
  changePassword,
  updateProfile,
  getGiteeStarAuthorizeUrl,
  verifyGiteeStarCallback
};

export default authService;
