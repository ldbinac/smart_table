/**
 * 认证状态管理Store
 * 管理用户认证状态和用户信息
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, LoginRequest, RegisterRequest } from '@/api/types'
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
  triggerLogoutEvent,
  onLogoutEvent
} from '@/utils/auth/token'
import { message } from '@/utils/message'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const user = ref<User | null>(null)
  const isAuthenticated = ref(false)
  const isLoading = ref(false)
  const isLoggingOut = ref(false)
  
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
      
      // 存储 Token - 注意后端返回的是 tokens 对象
      // 默认使用 localStorage，这样多标签页可以共享 token
      setToken(response.tokens.access_token, remember)
      setRefreshToken(response.tokens.refresh_token, remember)
      setRememberMe(remember)
      
      // 更新状态
      user.value = response.user
      isAuthenticated.value = true
      
      message.success('登录成功')
      return true
    } catch (error) {
      message.error('登录失败，请检查邮箱和密码')
      return false
    } finally {
      isLoading.value = false
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
      message.error('注册失败，请检查输入信息')
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
    const token = getToken()
    if (!token || isTokenExpired(token)) {
      return false
    }
    
    try {
      const userData = await authService.getCurrentUser()
      user.value = userData
      isAuthenticated.value = true
      return true
    } catch {
      // Token无效，清除状态
      clearToken()
      user.value = null
      isAuthenticated.value = false
      return false
    }
  }
  
  /**
   * 刷新Token
   */
  const refreshAccessToken = async (): Promise<boolean> => {
    const refreshTokenValue = getRefreshToken()
    if (!refreshTokenValue) {
      return false
    }
    
    try {
      const response = await authService.refreshToken(refreshTokenValue)
      const remember = getRememberMe()
      setToken(response.access_token, remember)
      return true
    } catch {
      // 刷新失败，清除状态
      clearToken()
      user.value = null
      isAuthenticated.value = false
      return false
    }
  }
  
  /**
   * 检查认证状态
   */
  const checkAuth = async (): Promise<boolean> => {
    if (isAuthenticated.value && user.value) {
      return true
    }
    
    return await fetchCurrentUser()
  }
  
  /**
   * 更新用户信息
   */
  const updateUser = (data: Partial<User>): void => {
    if (user.value) {
      user.value = { ...user.value, ...data }
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
    
    // 计算属性
    isLoggedIn,
    userRole,
    isAdmin,
    
    // 方法
    login,
    register,
    logout,
    fetchCurrentUser,
    refreshAccessToken,
    checkAuth,
    updateUser,
    hasPermission
  }
})
