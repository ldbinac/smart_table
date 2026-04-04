/**
 * API配置
 * 管理API相关的所有配置项
 */

// API基础URL配置
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'

// API客户端配置（供client.ts使用）
export const apiConfig = {
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api',
  timeout: 30000
};

// 请求配置
export const REQUEST_CONFIG = {
  // 超时时间（毫秒）
  TIMEOUT: 30000,
  
  // 重试次数
  RETRY_COUNT: 3,
  
  // 重试延迟（毫秒）
  RETRY_DELAY: 1000,
  
  // 请求头
  HEADERS: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
}

// 认证配置
export const AUTH_CONFIG = {
  // Token存储键名
  TOKEN_KEY: 'access_token',
  REFRESH_TOKEN_KEY: 'refresh_token',
  
  // Token过期前刷新时间（秒）
  REFRESH_BEFORE_EXPIRY: 300,
  
  // 记住登录状态存储键名
  REMEMBER_KEY: 'remember_me'
}

// 分页配置
export const PAGINATION_CONFIG = {
  DEFAULT_PAGE: 1,
  DEFAULT_PER_PAGE: 20,
  MAX_PER_PAGE: 100
}

// 限流配置
export const RATE_LIMIT_CONFIG = {
  // 最大请求数
  MAX_REQUESTS: 100,
  
  // 时间窗口（毫秒）
  TIME_WINDOW: 60000
}
