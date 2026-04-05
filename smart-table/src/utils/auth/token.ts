/**
 * Token管理工具
 * 处理JWT Token的存储、读取和验证
 */

import { AUTH_CONFIG } from '@/api/config'

/**
 * 存储 Token
 * 默认使用 localStorage，支持多标签页共享
 */
export const setToken = (token: string, remember: boolean = true): void => {
  if (remember) {
    // 使用 localStorage，多标签页共享
    localStorage.setItem(AUTH_CONFIG.TOKEN_KEY, token)
  } else {
    // 使用 sessionStorage，仅当前标签页有效
    sessionStorage.setItem(AUTH_CONFIG.TOKEN_KEY, token)
  }
}

/**
 * 存储 Refresh Token
 * 默认使用 localStorage，支持多标签页共享
 */
export const setRefreshToken = (token: string, remember: boolean = true): void => {
  if (remember) {
    // 使用 localStorage，多标签页共享
    localStorage.setItem(AUTH_CONFIG.REFRESH_TOKEN_KEY, token)
  } else {
    // 使用 sessionStorage，仅当前标签页有效
    sessionStorage.setItem(AUTH_CONFIG.REFRESH_TOKEN_KEY, token)
  }
}

/**
 * 获取Token
 */
export const getToken = (): string | null => {
  return localStorage.getItem(AUTH_CONFIG.TOKEN_KEY) || 
         sessionStorage.getItem(AUTH_CONFIG.TOKEN_KEY)
}

/**
 * 获取Refresh Token
 */
export const getRefreshToken = (): string | null => {
  return localStorage.getItem(AUTH_CONFIG.REFRESH_TOKEN_KEY) || 
         sessionStorage.getItem(AUTH_CONFIG.REFRESH_TOKEN_KEY)
}

/**
 * 清除Token
 */
export const clearToken = (): void => {
  localStorage.removeItem(AUTH_CONFIG.TOKEN_KEY)
  localStorage.removeItem(AUTH_CONFIG.REFRESH_TOKEN_KEY)
  sessionStorage.removeItem(AUTH_CONFIG.TOKEN_KEY)
  sessionStorage.removeItem(AUTH_CONFIG.REFRESH_TOKEN_KEY)
}

/**
 * 解析Token（获取payload）
 */
export const parseToken = (token: string): Record<string, unknown> | null => {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch {
    return null
  }
}

/**
 * 检查Token是否过期
 */
export const isTokenExpired = (token: string): boolean => {
  const payload = parseToken(token)
  if (!payload || !payload.exp) return true
  
  // 提前5分钟认为过期
  const expiresIn = (payload.exp as number) - AUTH_CONFIG.REFRESH_BEFORE_EXPIRY
  return Date.now() >= expiresIn * 1000
}

/**
 * 获取Token过期时间
 */
export const getTokenExpiry = (token: string): number | null => {
  const payload = parseToken(token)
  return payload?.exp as number || null
}

/**
 * 设置记住登录状态
 */
export const setRememberMe = (remember: boolean): void => {
  localStorage.setItem(AUTH_CONFIG.REMEMBER_KEY, String(remember))
}

/**
 * 获取记住登录状态
 */
export const getRememberMe = (): boolean => {
  return localStorage.getItem(AUTH_CONFIG.REMEMBER_KEY) === 'true'
}

/**
 * 清除记住登录状态
 */
export const clearRememberMe = (): void => {
  localStorage.removeItem(AUTH_CONFIG.REMEMBER_KEY)
}

/**
 * 触发登出事件（用于多标签页同步）
 */
export const triggerLogoutEvent = (): void => {
  // 使用 CustomEvent 通知其他标签页
  window.dispatchEvent(new Event('user-logout'))
}

/**
 * 监听登出事件
 */
export const onLogoutEvent = (callback: () => void): (() => void) => {
  const handler = () => callback()
  window.addEventListener('user-logout', handler)
  
  // 返回取消监听函数
  return () => {
    window.removeEventListener('user-logout', handler)
  }
}
