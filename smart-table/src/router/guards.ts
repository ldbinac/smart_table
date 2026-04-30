/**
 * 路由守卫
 * 处理认证和权限控制
 */

import type { NavigationGuardNext, RouteLocationNormalized } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'

const whiteList = ['/login', '/register', '/forgot-password']

export const authGuard = async (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
): Promise<void> => {
  const authStore = useAuthStore()
  
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
    from: RouteLocationNormalized,
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
  from: RouteLocationNormalized,
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
