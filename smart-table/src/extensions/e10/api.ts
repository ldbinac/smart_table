/**
 * 泛微 E10 OAuth2 单点登录前端 API。
 *
 * 该文件属于可选集成扩展（src/extensions/e10），不修改上游 API 层。
 */
import { apiClient } from '@/api/client'
import type { LoginResponse } from '@/api/types'

export interface E10SsoConfig {
  enabled: boolean
  ready: boolean
  provider_name: string
  login_url: string | null
  logout_url: string
  logout_with_e10: boolean
  password_login_enabled: boolean
  auto_create_users: boolean
}

export interface E10ExchangeResponse extends LoginResponse {
  redirect?: string
}

let cachedConfig: E10SsoConfig | null = null
let configPromise: Promise<E10SsoConfig> | null = null

/** 读取 E10 SSO 配置（默认缓存，失败时由调用方降级）。 */
export async function getE10Config(force = false): Promise<E10SsoConfig> {
  if (!force && cachedConfig) return cachedConfig
  if (!force && configPromise) return configPromise

  configPromise = apiClient
    .get<E10SsoConfig>(
      '/integrations/e10/config',
      undefined,
      { skipAuthRedirect: true } as unknown as Record<string, unknown>,
    )
    .then((config) => {
      cachedConfig = config
      return config
    })
    .finally(() => {
      configPromise = null
    })

  return configPromise
}

/** 构造 E10 登录入口地址。 */
export function buildE10LoginUrl(config: E10SsoConfig, redirect?: string): string {
  const base = config.login_url || '/api/integrations/e10/login'
  const url = new URL(base, window.location.origin)
  if (redirect) {
    url.searchParams.set('redirect', redirect)
  }
  return url.toString()
}

/** 用后端一次性票据换取 SmartTable JWT。 */
export async function exchangeE10Ticket(ticket: string): Promise<E10ExchangeResponse> {
  return apiClient.post<E10ExchangeResponse>(
    '/integrations/e10/exchange',
    { ticket },
    { skipAuthRedirect: true } as unknown as Record<string, unknown>,
  )
}

/** 登出 E10 会话后回到登录页。 */
export function buildE10LogoutUrl(redirect = '/login'): string {
  const params = new URLSearchParams({ redirect })
  return `/api/integrations/e10/logout?${params.toString()}`
}
