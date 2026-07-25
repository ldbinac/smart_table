/**
 * Token自动续期服务
 * 实现token的主动式自动续期机制,确保用户在操作期间不会因token过期而中断
 */

import { useAuthStore } from '@/stores/authStore'
import { getToken, getRefreshToken, getTokenExpiry, isTokenExpired, parseToken } from '@/utils/auth/token'
import { message } from '@/utils/message'
import devLog from '@/utils/logger'

/**
 * 续期配置
 */
const REFRESH_CONFIG = {
  // 续期阈值: token有效期剩余20%时触发续期
  REFRESH_THRESHOLD_RATIO: 0.2,

  // 定时检查间隔: 每5分钟检查一次
  CHECK_INTERVAL: 5 * 60 * 1000,

  // 续期失败重试次数
  MAX_RETRY_COUNT: 3,

  // 重试间隔(毫秒)
  RETRY_DELAY: 10 * 1000,

  // 最小续期提前时间(秒) - 如果剩余时间小于此值,立即续期
  // 注意：此值应该小于后端配置的token有效期
  // 如果token有效期是10分钟(600秒)，这里应该设置为更小的值，比如120秒(2分钟)
  MIN_REFRESH_AHEAD: 2 * 60, // 2分钟

  // 续期锁定超时时间(毫秒) - 防止多标签页同时续期
  LOCK_TIMEOUT: 30 * 1000,

  // 续期后最小等待时间(秒) - 防止刚续期就再次触发续期
  MIN_REFRESH_INTERVAL: 60 // 1分钟
}

/**
 * Token自动续期服务类
 * 提供单例模式,确保全局只有一个实例
 */
class TokenAutoRefreshService {
  private checkTimer: number | null = null
  private isRefreshing: boolean = false
  private refreshFailureCount: number = 0
  private lockAcquired: boolean = false
  private lockTimestamp: number = 0
  private lastRefreshTime: number = 0 // 上次续期时间戳（秒）

  // 单例实例
  private static instance: TokenAutoRefreshService | null = null

  /**
   * 获取单例实例
   */
  public static getInstance(): TokenAutoRefreshService {
    if (!TokenAutoRefreshService.instance) {
      TokenAutoRefreshService.instance = new TokenAutoRefreshService()
    }
    return TokenAutoRefreshService.instance
  }

  /**
   * 私有构造函数(单例模式)
   */
  private constructor() {
    // 监听页面可见性变化
    this.setupVisibilityListener()

    // 监听storage事件(多标签页同步)
    this.setupStorageListener()
  }

  /**
   * 启动自动续期服务
   */
  public start(): void {
    if (this.checkTimer !== null) {
      devLog.warn('[TokenRefresh] 服务已在运行中')
      return
    }

    devLog.info('[TokenRefresh] 启动自动续期服务')

    // 延迟5秒后开始检查,给应用初始化时间
    // 这样可以避免在用户信息还没恢复时就触发续期
    setTimeout(() => {
      // 再次检查是否已停止
      if (this.checkTimer === null) {
        this.checkTokenExpiry()

        // 设置定时检查
        this.checkTimer = window.setInterval(() => {
          this.checkTokenExpiry()
        }, REFRESH_CONFIG.CHECK_INTERVAL)
      }
    }, 5000)
  }

  /**
   * 停止自动续期服务
   */
  public stop(): void {
    if (this.checkTimer !== null) {
      window.clearInterval(this.checkTimer)
      this.checkTimer = null
      devLog.info('[TokenRefresh] 停止自动续期服务')
    }

    // 释放锁
    this.releaseLock()
  }

  /**
   * 检查token有效期
   */
  private checkTokenExpiry(): void {
    const token = getToken()

    // 没有token,不需要续期
    if (!token) {
      return
    }

    // token已真正过期,不触发续期(由API拦截器处理)
    if (isTokenExpired(token)) {
      devLog.warn('[TokenRefresh] Token已过期,等待API拦截器处理')
      return
    }

    // 检查是否即将过期(提前20%或10分钟)
    if (this.shouldRefreshToken(token)) {
      devLog.info('[TokenRefresh] Token即将过期,触发自动续期')
      this.performRefresh()
    }
  }

  /**
   * 判断是否需要续期
   * @param token 当前token
   * @returns 是否需要续期
   */
  private shouldRefreshToken(token: string): boolean {
    // 检查是否刚续期过（防止频繁续期）
    const now = Math.floor(Date.now() / 1000)
    if (this.lastRefreshTime > 0) {
      const timeSinceLastRefresh = now - this.lastRefreshTime
      if (timeSinceLastRefresh < REFRESH_CONFIG.MIN_REFRESH_INTERVAL) {
        devLog.debug(`[TokenRefresh] 距离上次续期仅${timeSinceLastRefresh}秒，跳过续期`)
        return false
      }
    }

    const expiryTime = getTokenExpiry(token)

    if (!expiryTime) {
      return false
    }

    const remainingTime = expiryTime - now

    // 剩余时间小于最小续期提前时间(2分钟),立即续期
    if (remainingTime <= REFRESH_CONFIG.MIN_REFRESH_AHEAD) {
      devLog.debug(`[TokenRefresh] 剩余时间${remainingTime}秒 <= ${REFRESH_CONFIG.MIN_REFRESH_AHEAD}秒,需要立即续期`)
      return true
    }

    // 计算续期阈值(20%)
    // 从token本身计算实际有效期，而不是硬编码
    const tokenPayload = parseToken(token)
    if (!tokenPayload || !tokenPayload.iat || !tokenPayload.exp) {
      return false
    }

    // token实际有效期（秒）
    const tokenLifetime = (tokenPayload.exp as number) - (tokenPayload.iat as number)
    const refreshThreshold = Math.floor(tokenLifetime * REFRESH_CONFIG.REFRESH_THRESHOLD_RATIO)

    devLog.debug(`[TokenRefresh] token有效期${tokenLifetime}秒,阈值${refreshThreshold}秒,剩余${remainingTime}秒`)

    // 剩余时间小于阈值,需要续期
    return remainingTime <= refreshThreshold
  }

  /**
   * 执行续期
   */
  private async performRefresh(): Promise<void> {
    // 检查是否正在续期
    if (this.isRefreshing) {
      devLog.debug('[TokenRefresh] 正在续期中,跳过本次续期请求')
      return
    }

    // 尝试获取锁(多标签页场景)
    if (!this.acquireLock()) {
      devLog.debug('[TokenRefresh] 其他标签页正在续期,等待完成')
      return
    }

    const authStore = useAuthStore()
    this.isRefreshing = true

    try {
      devLog.info('[TokenRefresh] 开始执行续期请求')

      const success = await authStore.refreshAccessToken()

      if (success) {
        devLog.info('[TokenRefresh] 续期成功')
        this.refreshFailureCount = 0
        this.lastRefreshTime = Math.floor(Date.now() / 1000) // 记录续期时间
        this.releaseLock()

        // 通知其他标签页
        this.notifyOtherTabs()
      } else {
        throw new Error('续期失败')
      }
    } catch (error) {
      devLog.error('[TokenRefresh] 续期失败:', error)
      this.handleRefreshFailure()
    } finally {
      this.isRefreshing = false
    }
  }

  /**
   * 处理续期失败
   */
  private handleRefreshFailure(): void {
    this.refreshFailureCount++
    this.releaseLock()

    devLog.warn(`[TokenRefresh] 续期失败次数: ${this.refreshFailureCount}`)

    // 连续失败超过阈值,强制登出
    if (this.refreshFailureCount >= REFRESH_CONFIG.MAX_RETRY_COUNT) {
      devLog.error('[TokenRefresh] 续期连续失败,强制登出')
      message.error('登录已过期,请重新登录')

      const authStore = useAuthStore()
      authStore.logout()

      return
    }

    // 显示友好提示
    message.warning('网络连接异常,正在重试...')

    // 延迟重试
    setTimeout(() => {
      const token = getToken()
      if (token && this.shouldRefreshToken(token)) {
        this.performRefresh()
      }
    }, REFRESH_CONFIG.RETRY_DELAY)
  }

  /**
   * 页面可见性变化处理
   */
  private setupVisibilityListener(): void {
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        devLog.debug('[TokenRefresh] 页面重新可见,立即检查token')
        this.checkTokenExpiry()
      }
    })
  }

  /**
   * 监听storage事件(多标签页同步)
   */
  private setupStorageListener(): void {
    window.addEventListener('storage', (event) => {
      // 监听token更新事件
      if (event.key === 'token_refreshed') {
        devLog.info('[TokenRefresh] 收到其他标签页的续期通知')
        // 其他标签页续期成功,无需再续期
        this.refreshFailureCount = 0
      }

      // 监听登出事件
      if (event.key === 'user-logout') {
        devLog.info('[TokenRefresh] 收到登出通知,停止续期服务')
        this.stop()
      }
    })
  }

  /**
   * 尝试获取续期锁
   * 使用localStorage实现简单的分布式锁
   */
  private acquireLock(): boolean {
    const now = Date.now()
    const lockKey = 'token_refresh_lock'
    const lockValue = localStorage.getItem(lockKey)

    // 检查是否有其他标签页持有锁
    if (lockValue) {
      const lockTime = parseInt(lockValue, 10)

      // 锁已超时,可以获取
      if (now - lockTime > REFRESH_CONFIG.LOCK_TIMEOUT) {
        localStorage.setItem(lockKey, now.toString())
        this.lockAcquired = true
        this.lockTimestamp = now
        return true
      }

      // 锁未超时,无法获取
      return false
    }

    // 没有锁,直接获取
    localStorage.setItem(lockKey, now.toString())
    this.lockAcquired = true
    this.lockTimestamp = now
    return true
  }

  /**
   * 释放续期锁
   */
  private releaseLock(): void {
    if (this.lockAcquired) {
      const lockKey = 'token_refresh_lock'
      const lockValue = localStorage.getItem(lockKey)

      // 只释放自己持有的锁
      if (lockValue && parseInt(lockValue, 10) === this.lockTimestamp) {
        localStorage.removeItem(lockKey)
      }

      this.lockAcquired = false
      this.lockTimestamp = 0
    }
  }

  /**
   * 通知其他标签页续期成功
   */
  private notifyOtherTabs(): void {
    // 触发storage事件,通知其他标签页
    localStorage.setItem('token_refreshed', Date.now().toString())

    // 短暂延迟后清除标记
    setTimeout(() => {
      localStorage.removeItem('token_refreshed')
    }, 1000)
  }

  /**
   * 清理资源
   */
  public destroy(): void {
    this.stop()
    TokenAutoRefreshService.instance = null
  }
}

// 导出单例获取方法
export const getTokenRefreshService = (): TokenAutoRefreshService => {
  return TokenAutoRefreshService.getInstance()
}

export default TokenAutoRefreshService