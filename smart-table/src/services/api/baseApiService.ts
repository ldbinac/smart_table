/**
 * Base API服务
 * 处理Base相关的API调用
 */

import { apiClient } from '@/api/client'
import type { 
  Base, 
  BaseMember, 
  BaseRole,
  PaginatedData, 
  PaginationParams 
} from '@/api/types'

/**
 * 获取Base列表
 */
export const getBases = async (params?: PaginationParams & { include_archived?: boolean }): Promise<PaginatedData<Base>> => {
  const response = await apiClient.get<PaginatedData<Base>>('/bases', params as Record<string, unknown>)
  return response.data
}

/**
 * 获取单个Base
 */
export const getBase = async (id: string): Promise<Base> => {
  const response = await apiClient.get<Base>(`/bases/${id}`)
  return response.data
}

/**
 * 创建Base
 */
export const createBase = async (data: Partial<Base>): Promise<Base> => {
  const response = await apiClient.post<Base>('/bases', data as Record<string, unknown>)
  return response.data
}

/**
 * 更新Base
 */
export const updateBase = async (id: string, data: Partial<Base>): Promise<Base> => {
  const response = await apiClient.put<Base>(`/bases/${id}`, data as Record<string, unknown>)
  return response.data
}

/**
 * 删除Base
 */
export const deleteBase = async (id: string): Promise<void> => {
  await apiClient.delete(`/bases/${id}`)
}

/**
 * 归档/取消归档Base
 */
export const toggleArchiveBase = async (id: string): Promise<Base> => {
  const response = await apiClient.put<Base>(`/bases/${id}/archive`)
  return response.data
}

/**
 * 切换Base收藏状态
 */
export const toggleStarBase = async (id: string): Promise<Base> => {
  const response = await apiClient.post<Base>(`/bases/${id}/star`)
  return response.data
}

/**
 * 复制Base
 */
export const duplicateBase = async (id: string, name?: string): Promise<Base> => {
  const response = await apiClient.post<Base>(`/bases/${id}/duplicate`, name ? { name } : undefined)
  return response.data
}

// ==================== 成员管理 ====================

/**
 * 获取Base成员列表
 */
export const getBaseMembers = async (baseId: string): Promise<BaseMember[]> => {
  const response = await apiClient.get<BaseMember[]>(`/bases/${baseId}/members`)
  return response.data
}

/**
 * 添加Base成员
 */
export const addBaseMember = async (baseId: string, userId: string, role: BaseRole): Promise<BaseMember> => {
  const response = await apiClient.post<BaseMember>(`/bases/${baseId}/members`, {
    user_id: userId,
    role
  })
  return response.data
}

/**
 * 更新成员角色
 */
export const updateMemberRole = async (baseId: string, memberId: string, role: BaseRole): Promise<BaseMember> => {
  const response = await apiClient.put<BaseMember>(`/bases/${baseId}/members/${memberId}`, {
    role
  })
  return response.data
}

/**
 * 移除Base成员
 */
export const removeBaseMember = async (baseId: string, memberId: string): Promise<void> => {
  await apiClient.delete(`/bases/${baseId}/members/${memberId}`)
}

// 导出Base服务
export const baseApiService = {
  getBases,
  getBase,
  createBase,
  updateBase,
  deleteBase,
  toggleArchiveBase,
  toggleStarBase,
  duplicateBase,
  getBaseMembers,
  addBaseMember,
  updateMemberRole,
  removeBaseMember
}

export default baseApiService
