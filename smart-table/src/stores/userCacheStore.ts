/**
 * 用户缓存存储
 * 统一管理成员信息缓存，避免重复请求
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { userApi } from '@/api/user'

export interface CachedUser {
  id: string
  name: string
  email: string
  avatar?: string
  role?: string
  status?: string
  cachedAt: number
}

export const useUserCacheStore = defineStore('userCache', () => {
  // 用户缓存映射表
  const userCache = ref<Map<string, CachedUser>>(new Map())
  
  // 缓存有效期（毫秒）- 30分钟
  const CACHE_TTL = 30 * 60 * 1000
  
  // 正在加载中的用户ID集合（防止重复请求）
  const loadingUsers = ref<Set<string>>(new Set())
  
  // 获取缓存中的用户
  const getCachedUser = (userId: string): CachedUser | undefined => {
    const user = userCache.value.get(userId)
    if (!user) return undefined
    
    // 检查缓存是否过期
    const now = Date.now()
    if (now - user.cachedAt > CACHE_TTL) {
      userCache.value.delete(userId)
      return undefined
    }
    
    return user
  }
  
  // 批量获取缓存用户
  const getCachedUsers = (userIds: string[]): CachedUser[] => {
    return userIds
      .map(id => getCachedUser(id))
      .filter((user): user is CachedUser => user !== undefined)
  }
  
  // 缓存用户数据
  const cacheUser = (user: Omit<CachedUser, 'cachedAt'>) => {
    userCache.value.set(user.id, {
      ...user,
      cachedAt: Date.now()
    })
  }
  
  // 批量缓存用户数据
  const cacheUsers = (users: Omit<CachedUser, 'cachedAt'>[]) => {
    users.forEach(user => cacheUser(user))
  }
  
  // 获取单个用户信息（带缓存）
  const fetchUser = async (userId: string | unknown): Promise<CachedUser | null> => {
    // 验证 userId
    const id = String(userId)
    if (!id || id.trim() === '') {
      console.warn('[UserCache] 无效的用户ID: 空字符串')
      return null
    }
    
    // 检查缓存
    const cached = getCachedUser(id)
    if (cached) {
      console.log(`[UserCache] 从缓存获取用户: ${id}`)
      return cached
    }
    
    // 检查是否正在加载中
    if (loadingUsers.value.has(id)) {
      console.log(`[UserCache] 用户正在加载中: ${id}`)
      // 等待加载完成
      await waitForUserLoad(id)
      return getCachedUser(id) || null
    }
    
    // 标记为加载中
    loadingUsers.value.add(id)
    
    try {
      console.log(`[UserCache] 从API获取用户: ${id}`)
      const user = await userApi.getUserById(id)
      
      if (user) {
        const cachedUser: CachedUser = {
          id: user.id,
          name: user.name,
          email: user.email,
          avatar: user.avatar,
          role: user.role,
          status: user.status,
          cachedAt: Date.now()
        }
        cacheUser(cachedUser)
        return cachedUser
      }
      
      return null
    } catch (error) {
      console.error(`[UserCache] 获取用户失败: ${id}`, error)
      return null
    } finally {
      loadingUsers.value.delete(id)
    }
  }
  
  // 批量获取用户信息（带缓存）
  const fetchUsers = async (userIds: string[]): Promise<CachedUser[]> => {
    // 去重
    const uniqueIds = [...new Set(userIds)]
    
    // 分离已缓存和未缓存的用户ID
    const cachedUsers: CachedUser[] = []
    const uncachedIds: string[] = []
    
    uniqueIds.forEach(id => {
      const cached = getCachedUser(id)
      if (cached) {
        cachedUsers.push(cached)
      } else {
        uncachedIds.push(id)
      }
    })
    
    console.log(`[UserCache] 缓存命中: ${cachedUsers.length}/${uniqueIds.length}`)
    
    // 如果有未缓存的用户，批量获取
    if (uncachedIds.length > 0) {
      try {
        // 过滤掉正在加载中的用户
        const idsToFetch = uncachedIds.filter(id => !loadingUsers.value.has(id))
        
        if (idsToFetch.length > 0) {
          console.log(`[UserCache] 批量获取用户: ${idsToFetch.join(', ')}`)
          
          // 标记为加载中
          idsToFetch.forEach(id => loadingUsers.value.add(id))
          
          try {
            const users = await userApi.getUsersByIds(idsToFetch)
            
            if (users && users.length > 0) {
              const cachedList = users.map(user => ({
                id: user.id,
                name: user.name,
                email: user.email,
                avatar: user.avatar,
                role: user.role,
                status: user.status,
                cachedAt: Date.now()
              }))
              
              cacheUsers(cachedList)
              cachedUsers.push(...cachedList)
            }
          } finally {
            idsToFetch.forEach(id => loadingUsers.value.delete(id))
          }
        }
        
        // 等待正在加载中的用户
        const loadingIds = uncachedIds.filter(id => loadingUsers.value.has(id))
        if (loadingIds.length > 0) {
          await Promise.all(loadingIds.map(id => waitForUserLoad(id)))
          
          // 再次尝试从缓存获取
          loadingIds.forEach(id => {
            const cached = getCachedUser(id)
            if (cached && !cachedUsers.find(u => u.id === id)) {
              cachedUsers.push(cached)
            }
          })
        }
      } catch (error) {
        console.error('[UserCache] 批量获取用户失败:', error)
      }
    }
    
    return cachedUsers
  }
  
  // 等待用户加载完成
  const waitForUserLoad = (userId: string): Promise<void> => {
    return new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        if (!loadingUsers.value.has(userId) || getCachedUser(userId)) {
          clearInterval(checkInterval)
          resolve()
        }
      }, 100)
      
      // 超时处理（5秒）
      setTimeout(() => {
        clearInterval(checkInterval)
        resolve()
      }, 5000)
    })
  }
  
  // 清除过期缓存
  const clearExpiredCache = () => {
    const now = Date.now()
    let clearedCount = 0
    
    userCache.value.forEach((user, id) => {
      if (now - user.cachedAt > CACHE_TTL) {
        userCache.value.delete(id)
        clearedCount++
      }
    })
    
    if (clearedCount > 0) {
      console.log(`[UserCache] 清除过期缓存: ${clearedCount} 条`)
    }
  }
  
  // 清除所有缓存
  const clearAllCache = () => {
    userCache.value.clear()
    console.log('[UserCache] 清除所有缓存')
  }
  
  // 获取缓存统计
  const cacheStats = computed(() => ({
    size: userCache.value.size,
    loadingCount: loadingUsers.value.size
  }))
  
  // 定期清理过期缓存（每5分钟）
  setInterval(clearExpiredCache, 5 * 60 * 1000)
  
  return {
    userCache,
    getCachedUser,
    getCachedUsers,
    cacheUser,
    cacheUsers,
    fetchUser,
    fetchUsers,
    clearExpiredCache,
    clearAllCache,
    cacheStats
  }
})
