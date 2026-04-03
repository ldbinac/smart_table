/**
 * 认证服务
 * 处理用户认证相关的API调用
 */

import { apiClient } from '@/api/client'
import type { 
  LoginRequest, 
  LoginResponse, 
  RegisterRequest, 
  User,
  RefreshTokenRequest,
  RefreshTokenResponse
} from '@/api/types'

/**
 * 用户登录
 */
export const login = async (data: LoginRequest): Promise<LoginResponse> => {
  const response = await apiClient.post<LoginResponse>('/auth/login', data as Record<string, unknown>)
  return response.data
}

/**
 * 用户注册
 */
export const register = async (data: RegisterRequest): Promise<User> => {
  const response = await apiClient.post<User>('/auth/register', data as Record<string, unknown>)
  return response.data
}

/**
 * 用户登出
 */
export const logout = async (): Promise<void> => {
  await apiClient.post('/auth/logout')
}

/**
 * 刷新Token
 */
export const refreshToken = async (refreshToken: string): Promise<RefreshTokenResponse> => {
  const data: RefreshTokenRequest = { refresh_token: refreshToken }
  const response = await apiClient.post<RefreshTokenResponse>('/auth/refresh', data as Record<string, unknown>)
  return response.data
}

/**
 * 获取当前用户信息
 */
export const getCurrentUser = async (): Promise<User> => {
  const response = await apiClient.get<User>('/auth/me')
  return response.data
}

/**
 * 修改密码
 */
export const changePassword = async (oldPassword: string, newPassword: string): Promise<void> => {
  await apiClient.put('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword
  })
}

/**
 * 更新用户信息
 */
export const updateProfile = async (data: Partial<User>): Promise<User> => {
  const response = await apiClient.put<User>('/auth/profile', data as Record<string, unknown>)
  return response.data
}

// 导出认证服务
export const authService = {
  login,
  register,
  logout,
  refreshToken,
  getCurrentUser,
  changePassword,
  updateProfile
}

export default authService
