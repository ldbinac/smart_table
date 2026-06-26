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
    if (authStore.isAuthenticated) {
      next('/')
      return
    }
    next()
    return
  }

  const isAuthenticated = await authStore.checkAuth()
  
  if (isAuthenticated) {
    next()
  } else {
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
