/**
 * 认证 API 服务
 * 处理用户登录、注册、Token 刷新等认证相关 API
 */
import { apiClient } from '@/api/client';
import type { User, LoginResponse, TokenPair, RegisterRequest, LoginRequest } from '@/api/types';

export const register = async (data: RegisterRequest): Promise<User> => {
  return apiClient.post<User>('/auth/register', data);
};

export const login = async (data: LoginRequest): Promise<LoginResponse> => {
  return apiClient.post<LoginResponse>('/auth/login', data);
};

export const refreshToken = async (refreshToken: string): Promise<TokenPair> => {
  return apiClient.post<TokenPair>('/auth/refresh', { refresh_token: refreshToken });
};

export const logout = async (): Promise<void> => {
  await apiClient.post<void>('/auth/logout');
};

export const getCurrentUser = async (): Promise<User> => {
  return apiClient.get<User>('/auth/me');
};

export const authApiService = {
  register,
  login,
  refreshToken,
  logout,
  getCurrentUser
};

export default authApiService;
