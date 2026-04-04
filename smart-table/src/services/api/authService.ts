/**
 * 认证服务
 * 处理用户认证相关的API调用
 */

import { apiClient } from '@/api/client';
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  User,
  TokenPair
} from '@/api/types';

export const login = async (data: LoginRequest): Promise<LoginResponse> => {
  return apiClient.post<LoginResponse>('/auth/login', data);
};

export const register = async (data: RegisterRequest): Promise<User> => {
  return apiClient.post<User>('/auth/register', data);
};

export const logout = async (): Promise<void> => {
  await apiClient.post<void>('/auth/logout');
};

export const refreshToken = async (refreshTokenValue: string): Promise<TokenPair> => {
  return apiClient.post<TokenPair>('/auth/refresh', { refresh_token: refreshTokenValue });
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

export const authService = {
  login,
  register,
  logout,
  refreshToken,
  getCurrentUser,
  changePassword,
  updateProfile
};

export default authService;
