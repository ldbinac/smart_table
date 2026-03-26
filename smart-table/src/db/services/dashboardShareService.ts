import { db } from '../schema'
import type { DashboardShare } from '../schema'
import { generateId } from '../../utils/id'

export interface CreateShareData {
  dashboardId: string
  expiresInHours?: number
  maxAccessCount?: number
  requireAccessCode?: boolean
  permission?: 'view' | 'edit'
}

export interface ShareValidationResult {
  valid: boolean
  share?: DashboardShare
  error?: string
}

export class DashboardShareService {
  /**
   * 生成随机分享令牌
   */
  private generateShareToken(): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    let token = ''
    for (let i = 0; i < 16; i++) {
      token += chars.charAt(Math.floor(Math.random() * chars.length))
    }
    return token
  }

  /**
   * 生成访问密码
   */
  private generateAccessCode(): string {
    const digits = '0123456789'
    let code = ''
    for (let i = 0; i < 6; i++) {
      code += digits.charAt(Math.floor(Math.random() * digits.length))
    }
    return code
  }

  /**
   * 创建分享链接
   */
  async createShare(data: CreateShareData): Promise<DashboardShare> {
    const share: DashboardShare = {
      id: generateId(),
      dashboardId: data.dashboardId,
      shareToken: this.generateShareToken(),
      accessCode: data.requireAccessCode ? this.generateAccessCode() : undefined,
      expiresAt: data.expiresInHours ? Date.now() + data.expiresInHours * 60 * 60 * 1000 : undefined,
      maxAccessCount: data.maxAccessCount,
      currentAccessCount: 0,
      isActive: true,
      permission: data.permission || 'view',
      createdAt: Date.now(),
      createdBy: undefined // 可以传入当前用户ID
    }

    await db.dashboardShares.add(share)
    return share
  }

  /**
   * 通过分享令牌获取分享信息
   */
  async getShareByToken(token: string): Promise<DashboardShare | undefined> {
    return db.dashboardShares.where('shareToken').equals(token).first()
  }

  /**
   * 获取仪表盘的所有分享链接
   */
  async getSharesByDashboard(dashboardId: string): Promise<DashboardShare[]> {
    return db.dashboardShares
      .where('dashboardId')
      .equals(dashboardId)
      .and(share => share.isActive)
      .sortBy('createdAt')
  }

  /**
   * 验证分享链接是否有效
   */
  async validateShare(token: string, accessCode?: string): Promise<ShareValidationResult> {
    const share = await this.getShareByToken(token)

    if (!share) {
      return { valid: false, error: '分享链接不存在' }
    }

    if (!share.isActive) {
      return { valid: false, share, error: '分享链接已被禁用' }
    }

    if (share.expiresAt && Date.now() > share.expiresAt) {
      return { valid: false, share, error: '分享链接已过期' }
    }

    if (share.maxAccessCount && share.currentAccessCount >= share.maxAccessCount) {
      return { valid: false, share, error: '分享链接访问次数已达上限' }
    }

    if (share.accessCode && share.accessCode !== accessCode) {
      return { valid: false, share, error: '访问密码错误' }
    }

    return { valid: true, share }
  }

  /**
   * 记录访问
   */
  async recordAccess(shareId: string): Promise<void> {
    const share = await db.dashboardShares.get(shareId)
    if (!share) return

    await db.dashboardShares.update(shareId, {
      currentAccessCount: share.currentAccessCount + 1,
      lastAccessedAt: Date.now()
    })
  }

  /**
   * 禁用分享链接
   */
  async deactivateShare(shareId: string): Promise<void> {
    await db.dashboardShares.update(shareId, {
      isActive: false
    })
  }

  /**
   * 删除分享链接
   */
  async deleteShare(shareId: string): Promise<void> {
    await db.dashboardShares.delete(shareId)
  }

  /**
   * 清理过期的分享链接
   */
  async cleanupExpiredShares(): Promise<number> {
    const now = Date.now()
    const expiredShares = await db.dashboardShares
      .where('expiresAt')
      .below(now)
      .and(share => share.isActive)
      .toArray()

    for (const share of expiredShares) {
      await db.dashboardShares.update(share.id, { isActive: false })
    }

    return expiredShares.length
  }

  /**
   * 生成分享链接URL
   */
  generateShareUrl(token: string): string {
    const baseUrl = window.location.origin
    return `${baseUrl}/#/share/dashboard/${token}`
  }

  /**
   * 复制链接到剪贴板
   */
  async copyToClipboard(text: string): Promise<boolean> {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text)
        return true
      }

      // 降级方案
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      textArea.style.top = '-999999px'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()

      const result = document.execCommand('copy')
      document.body.removeChild(textArea)
      return result
    } catch (error) {
      console.error('复制失败:', error)
      return false
    }
  }
}

export const dashboardShareService = new DashboardShareService()
