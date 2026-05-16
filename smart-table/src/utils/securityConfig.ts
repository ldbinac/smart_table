/**
 * 安全配置工具
 * 提供系统安全配置的获取和验证功能
 * 使用公开配置接口，无需登录
 */

import { getPublicConfigs } from '@/services/api/adminApiService'

// 安全配置键常量
export const SECURITY_CONFIG_KEYS = {
  PASSWORD_MIN_LENGTH: 'password_min_length',
  SESSION_TIMEOUT: 'session_timeout',
  ENABLE_2FA: 'enable_2fa',
  ENABLE_REGISTRATION: 'enable_registration',
  PASSWORD_REQUIRE_UPPERCASE: 'password_require_uppercase',
  PASSWORD_REQUIRE_LOWERCASE: 'password_require_lowercase',
  PASSWORD_REQUIRE_DIGIT: 'password_require_digit',
  PASSWORD_REQUIRE_SPECIAL: 'password_require_special'
} as const

// 默认配置值
export const DEFAULT_SECURITY_CONFIGS = {
  [SECURITY_CONFIG_KEYS.PASSWORD_MIN_LENGTH]: 8,
  [SECURITY_CONFIG_KEYS.SESSION_TIMEOUT]: 60, // 60分钟
  [SECURITY_CONFIG_KEYS.ENABLE_2FA]: false,
  [SECURITY_CONFIG_KEYS.ENABLE_REGISTRATION]: true,
  [SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_UPPERCASE]: false,
  [SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_LOWERCASE]: false,
  [SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_DIGIT]: false,
  [SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_SPECIAL]: false
}

// 本地缓存配置
interface SecurityConfigCache {
  data: Record<string, any> | null
  timestamp: number
  ttl: number // 缓存有效期（毫秒）
}

let configCache: SecurityConfigCache = {
  data: null,
  timestamp: 0,
  ttl: 5 * 60 * 1000 // 默认缓存5分钟
}

/**
 * 获取公开配置
 */
async function fetchPublicConfigs(): Promise<Record<string, any>> {
  try {
    const response = await getPublicConfigs()
    return response?.security || {}
  } catch (error) {
    console.error('获取公开配置失败:', error)
    return {}
  }
}

/**
 * 检查缓存是否有效
 */
function isCacheValid(): boolean {
  return (
    configCache.data !== null &&
    Date.now() - configCache.timestamp < configCache.ttl
  )
}

/**
 * 获取安全配置（带本地缓存）
 */
async function getSecurityConfigs(): Promise<Record<string, any>> {
  if (isCacheValid()) {
    return configCache.data!
  }

  const configs = await fetchPublicConfigs()
  const mergedConfigs = { ...DEFAULT_SECURITY_CONFIGS, ...configs }
  configCache = {
    data: mergedConfigs,
    timestamp: Date.now(),
    ttl: configCache.ttl
  }
  return mergedConfigs
}

/**
 * 清除配置缓存（当配置更新时调用）
 */
export function clearConfigCache(): void {
  configCache = {
    data: null,
    timestamp: 0,
    ttl: configCache.ttl
  }
}

/**
 * 设置缓存有效期
 * @param ttl 有效期（毫秒）
 */
export function setCacheTTL(ttl: number): void {
  configCache.ttl = ttl
}

/**
 * 获取密码最小长度配置
 * @returns 密码最小长度
 */
export async function getPasswordMinLength(): Promise<number> {
  try {
    const configs = await getSecurityConfigs()
    const value = configs[SECURITY_CONFIG_KEYS.PASSWORD_MIN_LENGTH]
    // 确保值在合理范围内
    return Math.max(6, Math.min(50, Number(value) || DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.PASSWORD_MIN_LENGTH]))
  } catch {
    return DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.PASSWORD_MIN_LENGTH]
  }
}

/**
 * 获取密码大写字母要求配置
 * @returns 是否需要大写字母
 */
export async function getPasswordRequireUppercase(): Promise<boolean> {
  try {
    const configs = await getSecurityConfigs()
    const value = configs[SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_UPPERCASE]
    return Boolean(value ?? DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_UPPERCASE])
  } catch {
    return DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_UPPERCASE]
  }
}

/**
 * 获取密码小写字母要求配置
 * @returns 是否需要小写字母
 */
export async function getPasswordRequireLowercase(): Promise<boolean> {
  try {
    const configs = await getSecurityConfigs()
    const value = configs[SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_LOWERCASE]
    return Boolean(value ?? DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_LOWERCASE])
  } catch {
    return DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_LOWERCASE]
  }
}

/**
 * 获取密码数字要求配置
 * @returns 是否需要数字
 */
export async function getPasswordRequireDigit(): Promise<boolean> {
  try {
    const configs = await getSecurityConfigs()
    const value = configs[SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_DIGIT]
    return Boolean(value ?? DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_DIGIT])
  } catch {
    return DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_DIGIT]
  }
}

/**
 * 获取密码特殊字符要求配置
 * @returns 是否需要特殊字符
 */
export async function getPasswordRequireSpecial(): Promise<boolean> {
  try {
    const configs = await getSecurityConfigs()
    const value = configs[SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_SPECIAL]
    return Boolean(value ?? DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_SPECIAL])
  } catch {
    return DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.PASSWORD_REQUIRE_SPECIAL]
  }
}

/**
 * 验证密码强度
 * @param password 密码
 * @returns [是否有效, 错误信息]
 */
export async function validatePasswordStrength(password: string): Promise<[boolean, string?]> {
  const minLength = await getPasswordMinLength()
  const requireUppercase = await getPasswordRequireUppercase()
  const requireLowercase = await getPasswordRequireLowercase()
  const requireDigit = await getPasswordRequireDigit()
  const requireSpecial = await getPasswordRequireSpecial()
  
  // 检查长度
  if (!password || password.length < minLength) {
    return [false, `密码长度至少为${minLength}位`]
  }
  
  // 检查大写字母
  if (requireUppercase && !/[A-Z]/.test(password)) {
    return [false, '密码必须包含大写字母']
  }
  
  // 检查小写字母
  if (requireLowercase && !/[a-z]/.test(password)) {
    return [false, '密码必须包含小写字母']
  }
  
  // 检查数字
  if (requireDigit && !/[0-9]/.test(password)) {
    return [false, '密码必须包含数字']
  }
  
  // 检查特殊字符
  const specialChars = /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?/]/
  if (requireSpecial && !specialChars.test(password)) {
    return [false, '密码必须包含特殊字符 (!@#$%^&*()_+-=[]{}|;:,.<>?/)']
  }
  
  return [true]
}

/**
 * 检查是否允许注册
 * @returns 是否允许注册
 */
export async function isRegistrationEnabled(): Promise<boolean> {
  try {
    const configs = await getSecurityConfigs()
    const value = configs[SECURITY_CONFIG_KEYS.ENABLE_REGISTRATION]
    return Boolean(value ?? DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.ENABLE_REGISTRATION])
  } catch {
    return DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.ENABLE_REGISTRATION]
  }
}

/**
 * 获取会话超时时间（分钟）
 * @returns 会话超时分钟数
 */
export async function getSessionTimeoutMinutes(): Promise<number> {
  try {
    const configs = await getSecurityConfigs()
    const value = configs[SECURITY_CONFIG_KEYS.SESSION_TIMEOUT]
    // 确保值在合理范围内（5分钟-24小时）
    return Math.max(5, Math.min(1440, Number(value) || DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.SESSION_TIMEOUT]))
  } catch {
    return DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.SESSION_TIMEOUT]
  }
}

/**
 * 检查是否启用双因素认证
 * @returns 是否启用2FA
 */
export async function is2FAEnabled(): Promise<boolean> {
  try {
    const configs = await getSecurityConfigs()
    const value = configs[SECURITY_CONFIG_KEYS.ENABLE_2FA]
    return Boolean(value ?? DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.ENABLE_2FA])
  } catch {
    return DEFAULT_SECURITY_CONFIGS[SECURITY_CONFIG_KEYS.ENABLE_2FA]
  }
}
