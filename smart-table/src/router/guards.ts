/**
 * 路由守卫
 * 处理认证和权限控制
 */

import type { NavigationGuardNext, RouteLocationNormalized } from 'vue-router'
import { useAuthStore } from '@/stores/auth/authStore'

// 白名单路由（不需要认证）
const whiteList = ['/login', '/register', '/forgot-password']

/**
 * 认证守卫
 * 检查用户是否已登录
 */
export const authGuard = async (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
): Promise<void> => {
  const authStore = useAuthStore()
  
  // 检查是否在白名单中
  if (whiteList.includes(to.path)) {
    // 如果已登录，跳转到首页
    if (authStore.isLoggedIn) {
      next('/')
      return
    }
    next()
    return
  }
  
  // 检查认证状态
  const isAuthenticated = await authStore.checkAuth()
  
  if (isAuthenticated) {
    next()
  } else {
    // 未登录，重定向到登录页
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    })
  }
}

/**
 * 权限守卫
 * 检查用户是否有权限访问
 */
export const permissionGuard = (requiredRole: string) => {
  return async (
    to: RouteLocationNormalized,
    from: RouteLocationNormalized,
    next: NavigationGuardNext
  ): Promise<void> => {
    const authStore = useAuthStore()
    
    // 先检查认证
    if (!authStore.isLoggedIn) {
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
      return
    }
    
    // 检查权限
    if (authStore.hasPermission(requiredRole)) {
      next()
    } else {
      // 无权限，跳转到403页面或首页
      next({
        path: '/403',
        query: { message: '您没有权限访问此页面' }
      })
    }
  }
}

/**
 * 管理员守卫
 * 检查用户是否为管理员
 */
export const adminGuard = async (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
): Promise<void> => {
  const authStore = useAuthStore()
  
  if (!authStore.isLoggedIn) {
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

/**
 * 页面标题守卫
 * 设置页面标题
 */
export const titleGuard = (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
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

/**
 * 滚动行为守卫
 * 控制页面滚动
 */
export const scrollBehavior = (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  savedPosition: { left: number; top: number } | null
): { left: number; top: number } | void => {
  if (savedPosition) {
    return savedPosition
  } else {
    return { left: 0, top: 0 }
  }
}
