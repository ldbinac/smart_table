/**
 * 认证状态管理Store
 * 管理用户认证状态和用户信息
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, LoginResponse, LoginRequest, RegisterRequest } from '@/api/types'
import { authService } from '@/services/api/authService'
import {
  setToken,
  setRefreshToken,
  clearToken,
  getToken,
  getRefreshToken,
  setRememberMe,
  getRememberMe,
  isTokenExpired,
  triggerLogoutEvent
} from '@/utils/auth/token'
import { message } from '@/utils/message'

// 用户信息缓存常量
const USER_CACHE_KEY = 'auth_user_cache'
const USER_CACHE_TTL = 2 * 60 * 60 * 1000 // 2小时（毫秒）

interface UserCache {
  data: User
  timestamp: number
}

function getUserCache(): UserCache | null {
  try {
    const raw = localStorage.getItem(USER_CACHE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as UserCache
    if (!parsed.data || typeof parsed.timestamp !== 'number') return null
    return parsed
  } catch {
    return null
  }
}

function setUserCache(data: User): void {
  try {
    const cache: UserCache = { data, timestamp: Date.now() }
    localStorage.setItem(USER_CACHE_KEY, JSON.stringify(cache))
  } catch (error) {
    console.warn('[authStore] Failed to write user cache:', error)
  }
}

function clearUserCache(): void {
  try {
    localStorage.removeItem(USER_CACHE_KEY)
  } catch {
    // ignore
  }
}

function isUserCacheValid(cache: UserCache): boolean {
  return Date.now() - cache.timestamp < USER_CACHE_TTL
}

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const user = ref<User | null>(null)
  const isAuthenticated = ref(false)
  const isLoading = ref(false)
  const isLoggingOut = ref(false)
  const isRefreshing = ref(false) // 新增: 续期状态

  // 计算属性
  const isLoggedIn = computed(() => isAuthenticated.value && !!user.value)
  const userRole = computed(() => user.value?.role || null)
  const isAdmin = computed(() => user.value?.role === 'admin')
  
  /**
   * 用户登录
   */
  const login = async (credentials: LoginRequest, remember: boolean = true): Promise<boolean> => {
    isLoading.value = true
    try {
      const response = await authService.login(credentials)
      return await completeLogin(response, remember)
    } catch (error) {
      console.error('登录失败:', error)
      message.error('登录失败，请检查邮箱和密码')
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 完成登录（供普通登录和 Gitee 回调复用）
   */
  const completeLogin = async (response: LoginResponse, remember: boolean = true): Promise<boolean> => {
    try {
      if (!response.tokens?.access_token || !response.tokens?.refresh_token || !response.user) {
        message.error('登录响应数据不完整')
        return false
      }

      setToken(response.tokens.access_token, remember)
      setRefreshToken(response.tokens.refresh_token, remember)
      setRememberMe(remember)

      user.value = response.user
      isAuthenticated.value = true
      setUserCache(response.user)

      message.success('登录成功')
      return true
    } catch (error) {
      console.error('[authStore] 完成登录失败:', error)
      message.error('登录状态保存失败')
      return false
    }
  }
  
  /**
   * 用户注册
   */
  const register = async (data: RegisterRequest): Promise<boolean> => {
    isLoading.value = true
    try {
      await authService.register(data)
      message.success('注册成功，请登录')
      return true
    } catch (error) {
      // 错误信息已在 API 客户端显示，这里不需要重复显示
      console.error('注册失败:', error)
      return false
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * 用户登出
   */
  const logout = async (logoutAll: boolean = false): Promise<void> => {
    isLoggingOut.value = true
    try {
      if (logoutAll) {
        // 退出所有设备
        await authService.logoutAll()
        message.success('已从所有设备退出')
      } else {
        // 退出当前设备
        await authService.logout()
      }
    } catch (error) {
      // 网络错误或其他错误时，仍然清除本地状态
      console.error('Logout error:', error)
      if (logoutAll) {
        message.warning('退出所有设备失败，但已清除本地登录状态')
      }
    } finally {
      // 无论成功失败都清除本地状态
      clearToken()
      user.value = null
      isAuthenticated.value = false
      isLoggingOut.value = false
      // 清除用户缓存
      clearUserCache()

      // 触发登出事件，通知其他标签页
      triggerLogoutEvent()

      if (!logoutAll) {
        message.success('已安全退出')
      }
    }
  }
  
  /**
   * 获取当前用户信息
   */
  const fetchCurrentUser = async (): Promise<boolean> => {
    console.log('[authStore] 开始获取当前用户信息')
    
    const token = getToken()
    console.log('[authStore] Token:', token ? '存在' : '不存在')
    
    if (!token) {
      console.log('[authStore] 没有token,返回false')
      return false
    }
    
    const expired = isTokenExpired(token)
    console.log('[authStore] Token是否过期:', expired)
    
    if (expired) {
      console.log('[authStore] Token已过期,返回false')
      return false
    }

    // 检查缓存
    const cached = getUserCache()
    if (cached && isUserCacheValid(cached)) {
      console.log('[authStore] 使用缓存的用户信息')
      user.value = cached.data
      isAuthenticated.value = true
      return true
    }

    console.log('[authStore] 从API获取用户信息')
    try {
      const userData = await authService.getCurrentUser()
      user.value = userData
      isAuthenticated.value = true
      // 更新用户缓存
      setUserCache(userData)
      console.log('[authStore] 用户信息获取成功')
      return true
    } catch (error: any) {
      console.error('[authStore] 获取用户信息失败:', error)
      // 只在明确的认证失败（401/403）时才清除状态
      // 其他错误（如网络问题）不清除状态，保留用户的登录状态
      if (error?.code === 401 || error?.code === 403) {
        console.warn('[authStore] 认证失败,清除状态')
        clearToken()
        user.value = null
        isAuthenticated.value = false
        clearUserCache()
      } else {
        // 网络错误等,不清除状态,让用户可以继续使用
        console.error('[authStore] 网络错误或其他错误,不清除状态')
      }
      return false
    }
  }
  
  /**
   * 刷新Token
   */
  const refreshAccessToken = async (): Promise<boolean> => {
    // 如果正在续期,返回false
    if (isRefreshing.value) {
      console.warn('[authStore] 正在续期中,跳过重复请求')
      return false
    }

    const refreshTokenValue = getRefreshToken()
    if (!refreshTokenValue) {
      console.warn('[authStore] 没有refresh_token,无法续期')
      return false
    }

    isRefreshing.value = true
    console.log('[authStore] 开始续期...')

    try {
      const response = await authService.refreshToken(refreshTokenValue)
      console.log('[authStore] 续期响应:', response)
      console.log('[authStore] 新token:', response.access_token)

      const remember = getRememberMe()
      setToken(response.access_token, remember)
      console.log('[authStore] 新token已保存到localStorage')

      // 验证新token是否正确保存
      const savedToken = getToken()
      console.log('[authStore] 验证localStorage中的token:', savedToken === response.access_token ? '匹配' : '不匹配')

      // 续期成功,清除用户缓存以获取最新信息
      clearUserCache()

      return true
    } catch (error) {
      console.error('[authStore] Token续期失败:', error)
      // 续期失败时,只在用户已登录的情况下才清除状态
      // 避免在应用初始化时错误地清除正在恢复的认证状态
      if (isAuthenticated.value) {
        clearToken()
        user.value = null
        isAuthenticated.value = false
        clearUserCache()
      }
      return false
    } finally {
      isRefreshing.value = false
      console.log('[authStore] 续期结束')
    }
  }
  
  /**
   * 检查认证状态
   */
  const checkAuth = async (): Promise<boolean> => {
    console.log('[authStore] checkAuth: 检查认证状态')
    console.log('[authStore] checkAuth: isAuthenticated=', isAuthenticated.value, 'user=', user.value ? '存在' : '不存在')
    
    if (isAuthenticated.value && user.value) {
      console.log('[authStore] checkAuth: 已认证,返回true')
      return true
    }
    
    console.log('[authStore] checkAuth: 未认证,调用fetchCurrentUser')
    return await fetchCurrentUser()
  }
  
  /**
   * 更新用户信息
   */
  const updateUser = (data: Partial<User>): void => {
    if (user.value) {
      user.value = { ...user.value, ...data }
      // 更新用户缓存
      setUserCache(user.value)
    }
  }
  
  /**
   * 检查是否有权限
   */
  const hasPermission = (requiredRole: string): boolean => {
    if (!user.value) return false
    
    const roleHierarchy: Record<string, number> = {
      'viewer': 1,
      'commenter': 2,
      'editor': 3,
      'admin': 4,
      'owner': 5
    }
    
    const userRoleLevel = roleHierarchy[user.value.role] || 0
    const requiredRoleLevel = roleHierarchy[requiredRole] || 0
    
    return userRoleLevel >= requiredRoleLevel
  }
  
  return {
    // 状态
    user,
    isAuthenticated,
    isLoading,
    isLoggingOut,
    isRefreshing,

    // 计算属性
    isLoggedIn,
    userRole,
    isAdmin,

    // 方法
    login,
    completeLogin,
    register,
    logout,
    fetchCurrentUser,
    refreshAccessToken,
    checkAuth,
    updateUser,
    hasPermission
  }
})
