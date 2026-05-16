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
  return apiClient.get<SearchUsersResponse>('/users/search', params as Record<string, unknown>)
}

/**
 * 根据ID获取用户信息
 * @param id 用户ID
 * @returns 用户信息
 */
export const getUserById = async (id: string): Promise<User> => {
  if (!id || id.trim() === '') {
    throw new Error('用户ID不能为空')
  }
  return apiClient.get<User>(`/users/${id}`)
}

/**
 * 根据ID批量获取用户信息
 * @param ids 用户ID列表
 * @returns 用户列表
 */
export const getUsersByIds = async (ids: string[]): Promise<User[]> => {
  // 验证输入
  if (!ids || ids.length === 0) {
    console.warn('[UserApi] 用户ID列表为空，跳过API请求')
    return []
  }
  
  // 过滤无效ID
  const validIds = ids.filter(id => {
    const strId = String(id)
    return strId && strId.trim() !== '' && strId !== '[]'
  })
  
  if (validIds.length === 0) {
    console.warn('[UserApi] 过滤后无有效用户ID，跳过API请求')
    return []
  }
  
  console.log(`[UserApi] 批量查询 ${validIds.length} 个用户`)
  return apiClient.post<User[]>('/users/batch', { ids: validIds })
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
