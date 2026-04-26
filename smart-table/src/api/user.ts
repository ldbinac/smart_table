/**
 * 用户 API 服务
 * 处理用户搜索、查询等用户相关 API
 */
import { apiClient } from './client'
import type { User } from './types'

export interface SearchUsersParams {
  query?: string
  base_id?: string
  page?: number
  per_page?: number
}

export interface SearchUsersResponse {
  users: User[]
  total: number
}

/**
 * 搜索用户
 * @param params 搜索参数
 * @returns 用户列表
 */
export const searchUsers = async (params: SearchUsersParams): Promise<SearchUsersResponse> => {
  return apiClient.get<SearchUsersResponse>('/users/search', params)
}

/**
 * 根据ID获取用户信息
 * @param id 用户ID
 * @returns 用户信息
 */
export const getUserById = async (id: string): Promise<User> => {
  return apiClient.get<User>(`/users/${id}`)
}

/**
 * 根据ID批量获取用户信息
 * @param ids 用户ID列表
 * @returns 用户列表
 */
export const getUsersByIds = async (ids: string[]): Promise<User[]> => {
  return apiClient.post<User[]>('/users/batch', { ids })
}

/**
 * 获取当前Base的成员列表
 * @param baseId 基础ID
 * @returns 成员列表
 */
export const getBaseMembers = async (baseId: string): Promise<User[]> => {
  return apiClient.get<User[]>(`/bases/${baseId}/members`)
}

export const userApi = {
  searchUsers,
  getUserById,
  getUsersByIds,
  getBaseMembers,
}

export default userApi
