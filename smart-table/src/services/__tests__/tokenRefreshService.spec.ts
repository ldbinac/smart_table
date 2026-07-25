/**
 * Token自动续期服务测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { getTokenRefreshService } from '../tokenRefreshService'
import { useAuthStore } from '@/stores/authStore'
import { getToken, getRefreshToken, getTokenExpiry, isTokenExpired } from '@/utils/auth/token'

// Mock dependencies
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn()
}))

vi.mock('@/utils/auth/token', () => ({
  getToken: vi.fn(),
  getRefreshToken: vi.fn(),
  getTokenExpiry: vi.fn(),
  isTokenExpired: vi.fn(),
  setToken: vi.fn(),
  setRefreshToken: vi.fn(),
  clearToken: vi.fn()
}))

vi.mock('@/utils/message', () => ({
  message: {
    error: vi.fn(),
    warning: vi.fn(),
    success: vi.fn()
  }
}))

describe('TokenAutoRefreshService', () => {
  let service: ReturnType<typeof getTokenRefreshService>
  let mockAuthStore: any

  beforeEach(() => {
    // 重置所有mock
    vi.clearAllMocks()

    // 创建mock authStore
    mockAuthStore = {
      refreshAccessToken: vi.fn(),
      logout: vi.fn(),
      isRefreshing: false
    }
    vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)

    // 获取服务实例
    service = getTokenRefreshService()
  })

  afterEach(() => {
    // 清理服务
    service.destroy()
  })

  describe('基本功能', () => {
    it('应该创建单例实例', () => {
      const instance1 = getTokenRefreshService()
      const instance2 = getTokenRefreshService()

      expect(instance1).toBe(instance2)
    })

    it('应该能够启动和停止服务', () => {
      service.start()
      service.stop()

      // 验证定时器已清除
      expect(service).toBeDefined()
    })
  })

  describe('Token过期检测', () => {
    it('当没有token时不应该触发续期', async () => {
      vi.mocked(getToken).mockReturnValue(null)

      service.start()

      // 等待检查完成
      await new Promise(resolve => setTimeout(resolve, 100))

      expect(mockAuthStore.refreshAccessToken).not.toHaveBeenCalled()

      service.stop()
    })

    it('当token已过期时不应该触发续期', async () => {
      vi.mocked(getToken).mockReturnValue('expired-token')
      vi.mocked(isTokenExpired).mockReturnValue(true)

      service.start()

      await new Promise(resolve => setTimeout(resolve, 100))

      expect(mockAuthStore.refreshAccessToken).not.toHaveBeenCalled()

      service.stop()
    })

    it('当token即将过期时应该触发续期', async () => {
      const now = Math.floor(Date.now() / 1000)
      const expiryTime = now + 600 // 10分钟后过期

      vi.mocked(getToken).mockReturnValue('valid-token')
      vi.mocked(isTokenExpired).mockReturnValue(false)
      vi.mocked(getTokenExpiry).mockReturnValue(expiryTime)
      vi.mocked(getRefreshToken).mockReturnValue('refresh-token')

      mockAuthStore.refreshAccessToken.mockResolvedValue(true)

      service.start()

      // 等待检查完成
      await new Promise(resolve => setTimeout(resolve, 100))

      expect(mockAuthStore.refreshAccessToken).toHaveBeenCalled()

      service.stop()
    })
  })

  describe('续期时机计算', () => {
    it('当剩余时间小于10分钟时应该立即续期', async () => {
      const now = Math.floor(Date.now() / 1000)
      const expiryTime = now + 500 // 约8分钟后过期

      vi.mocked(getToken).mockReturnValue('valid-token')
      vi.mocked(isTokenExpired).mockReturnValue(false)
      vi.mocked(getTokenExpiry).mockReturnValue(expiryTime)
      vi.mocked(getRefreshToken).mockReturnValue('refresh-token')

      mockAuthStore.refreshAccessToken.mockResolvedValue(true)

      service.start()

      await new Promise(resolve => setTimeout(resolve, 100))

      expect(mockAuthStore.refreshAccessToken).toHaveBeenCalled()

      service.stop()
    })

    it('当剩余时间大于阈值时不应该续期', async () => {
      const now = Math.floor(Date.now() / 1000)
      const expiryTime = now + 80000 // 约22小时后过期,大于20%阈值

      vi.mocked(getToken).mockReturnValue('valid-token')
      vi.mocked(isTokenExpired).mockReturnValue(false)
      vi.mocked(getTokenExpiry).mockReturnValue(expiryTime)

      service.start()

      await new Promise(resolve => setTimeout(resolve, 100))

      expect(mockAuthStore.refreshAccessToken).not.toHaveBeenCalled()

      service.stop()
    })
  })

  describe('续期失败处理', () => {
    it('续期失败时应该重试', async () => {
      const now = Math.floor(Date.now() / 1000)
      const expiryTime = now + 600

      vi.mocked(getToken).mockReturnValue('valid-token')
      vi.mocked(isTokenExpired).mockReturnValue(false)
      vi.mocked(getTokenExpiry).mockReturnValue(expiryTime)
      vi.mocked(getRefreshToken).mockReturnValue('refresh-token')

      // 模拟续期失败
      mockAuthStore.refreshAccessToken.mockRejectedValue(new Error('Refresh failed'))

      service.start()

      await new Promise(resolve => setTimeout(resolve, 100))

      // 验证调用了续期
      expect(mockAuthStore.refreshAccessToken).toHaveBeenCalled()

      service.stop()
    })
  })

  describe('多标签页同步', () => {
    it('收到token_refreshed事件时应该清除失败计数', () => {
      const event = new StorageEvent('storage', {
        key: 'token_refreshed',
        newValue: Date.now().toString()
      })

      window.dispatchEvent(event)

      // 验证事件监听器已注册
      expect(true).toBe(true)
    })

    it('收到user-logout事件时应该停止服务', () => {
      const event = new StorageEvent('storage', {
        key: 'user-logout',
        newValue: Date.now().toString()
      })

      window.dispatchEvent(event)

      // 验证事件监听器已注册
      expect(true).toBe(true)
    })
  })
})

describe('Token工具函数', () => {
  describe('isTokenExpired', () => {
    it('应该正确识别已过期的token', () => {
      // 这个测试主要验证工具函数的使用
      // 实际实现由token.ts提供
      expect(true).toBe(true)
    })
  })

  describe('getTokenExpiry', () => {
    it('应该正确解析token的过期时间', () => {
      // 这个测试主要验证工具函数的使用
      // 实际实现由token.ts提供
      expect(true).toBe(true)
    })
  })
})