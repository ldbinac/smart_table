/**
 * 路由守卫
 * 处理认证和权限控制
 */

import type { NavigationGuardNext, RouteLocationNormalized } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import { isRegistrationEnabled } from '@/utils/securityConfig'

const whiteList = ['/login', '/register', '/forgot-password']

export const authGuard = async (
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext
): Promise<void> => {
  console.log('[authGuard] 路由守卫触发,目标路径:', to.path)
  
  const authStore = useAuthStore()
  
  // 如果是注册页，先检查是否启用了注册
  if (to.path === '/register') {
    try {
      const enabled = await isRegistrationEnabled()
      if (!enabled) {
        // 注册未启用，跳转到登录页
        next('/login')
        return
      }
    } catch (error) {
      console.warn('[authGuard] 检查注册配置失败:', error)
      // 检查失败时，默认允许访问，由后端进行最终验证
    }
  }

  if (whiteList.includes(to.path) || to.meta.public) {
    console.log('[authGuard] 白名单路径,允许访问')
    // 分享页面等 public 路由允许任何人访问（无论是否已登录）
    // 其他白名单页面（登录/注册）在已登录时重定向到首页
    if (authStore.isAuthenticated && !to.meta.public) {
      console.log('[authGuard] 已登录,重定向到首页')
      next('/')
      return
    }
    next()
    return
  }

  console.log('[authGuard] 检查认证状态,当前状态:', authStore.isAuthenticated)
  const isAuthenticated = await authStore.checkAuth()
  console.log('[authGuard] 认证检查结果:', isAuthenticated)
  
  if (isAuthenticated) {
    console.log('[authGuard] 认证成功,允许访问')
    next()
  } else {
    console.log('[authGuard] 认证失败,重定向到登录页')
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    })
  }
}

export const permissionGuard = (requiredRole: string) => {
  return async (
    to: RouteLocationNormalized,
    _from: RouteLocationNormalized,
    next: NavigationGuardNext
  ): Promise<void> => {
    const authStore = useAuthStore()
    
    if (!authStore.isAuthenticated) {
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
      return
    }
    
    if (authStore.hasPermission(requiredRole)) {
      next()
    } else {
      next({
        path: '/403',
        query: { message: '您没有权限访问此页面' }
      })
    }
  }
}

export const adminGuard = async (
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext
): Promise<void> => {
  const authStore = useAuthStore()
  
  if (!authStore.isAuthenticated) {
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    })
    return
  }
  
  if (authStore.isAdmin) {
    next()
  } else {
    next({
      path: '/403',
      query: { message: '需要管理员权限' }
    })
  }
}

export const titleGuard = (
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext
): void => {
  const title = to.meta.title as string
  if (title) {
    document.title = `${title} - SmartTable`
  } else {
    document.title = 'SmartTable - 多维表格管理系统'
  }
  next()
}

export const scrollBehavior = (
  _to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  savedPosition: { left: number; top: number } | null
): { left: number; top: number } | void => {
  if (savedPosition) {
    return savedPosition
  } else {
    return { left: 0, top: 0 }
  }
}
