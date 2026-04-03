/**
 * API客户端
 * 封装Axios，提供统一的HTTP请求接口
 */

import axios, { 
  type AxiosInstance, 
  type AxiosRequestConfig, 
  type AxiosResponse,
  type AxiosError 
} from 'axios'
import { API_BASE_URL, REQUEST_CONFIG } from './config'
import { useLoadingStore } from '@/stores/loadingStore'
import { useMessage } from '@/utils/message'
import type { ApiResponse, ApiError } from './types'

// 创建Axios实例
const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_CONFIG.TIMEOUT,
  headers: REQUEST_CONFIG.HEADERS
})

// 请求队列（用于取消重复请求）
const pendingRequests = new Map<string, AbortController>()

// 生成请求唯一标识
const generateRequestKey = (config: AxiosRequestConfig): string => {
  return `${config.method}_${config.url}_${JSON.stringify(config.params)}_${JSON.stringify(config.data)}`
}

// 请求拦截器
axiosInstance.interceptors.request.use(
  (config) => {
    // 添加认证Token
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // 取消重复请求
    const requestKey = generateRequestKey(config)
    if (pendingRequests.has(requestKey)) {
      pendingRequests.get(requestKey)?.abort()
    }
    
    // 创建新的AbortController
    const controller = new AbortController()
    config.signal = controller.signal
    pendingRequests.set(requestKey, controller)
    
    // 显示加载状态
    const loadingStore = useLoadingStore()
    loadingStore.startLoading()
    
    return config
  },
  (error) => {
    const loadingStore = useLoadingStore()
    loadingStore.endLoading()
    return Promise.reject(error)
  }
)

// 响应拦截器
axiosInstance.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    // 移除请求记录
    const requestKey = generateRequestKey(response.config)
    pendingRequests.delete(requestKey)
    
    // 隐藏加载状态
    const loadingStore = useLoadingStore()
    loadingStore.endLoading()
    
    // 返回响应数据
    return response
  },
  async (error: AxiosError<ApiError>) => {
    // 隐藏加载状态
    const loadingStore = useLoadingStore()
    loadingStore.endLoading()
    
    // 处理错误
    const message = useMessage()
    
    if (error.response) {
      // 服务器返回错误
      const status = error.response.status
      const errorData = error.response.data
      
      switch (status) {
        case 401:
          // Token过期，尝试刷新
          message.error('登录已过期，请重新登录')
          // 清除Token并跳转到登录页
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
          break
        case 403:
          message.error('没有权限执行此操作')
          break
        case 404:
          message.error('请求的资源不存在')
          break
        case 422:
          message.error(errorData?.message || '请求数据验证失败')
          break
        case 429:
          message.error('请求过于频繁，请稍后再试')
          break
        case 500:
        case 502:
        case 503:
          message.error('服务器错误，请稍后重试')
          break
        default:
          message.error(errorData?.message || '请求失败')
      }
    } else if (error.request) {
      // 网络错误
      message.error('网络连接失败，请检查网络设置')
    } else {
      // 请求配置错误
      message.error('请求配置错误')
    }
    
    return Promise.reject(error)
  }
)

// API客户端类
class ApiClient {
  /**
   * 发送GET请求
   */
  async get<T>(url: string, params?: Record<string, unknown>): Promise<ApiResponse<T>> {
    const response = await axiosInstance.get<ApiResponse<T>>(url, { params })
    return response.data
  }
  
  /**
   * 发送POST请求
   */
  async post<T>(url: string, data?: Record<string, unknown>): Promise<ApiResponse<T>> {
    const response = await axiosInstance.post<ApiResponse<T>>(url, data)
    return response.data
  }
  
  /**
   * 发送PUT请求
   */
  async put<T>(url: string, data?: Record<string, unknown>): Promise<ApiResponse<T>> {
    const response = await axiosInstance.put<ApiResponse<T>>(url, data)
    return response.data
  }
  
  /**
   * 发送DELETE请求
   */
  async delete<T>(url: string): Promise<ApiResponse<T>> {
    const response = await axiosInstance.delete<ApiResponse<T>>(url)
    return response.data
  }
  
  /**
   * 发送PATCH请求
   */
  async patch<T>(url: string, data?: Record<string, unknown>): Promise<ApiResponse<T>> {
    const response = await axiosInstance.patch<ApiResponse<T>>(url, data)
    return response.data
  }
  
  /**
   * 上传文件
   */
  async upload<T>(url: string, formData: FormData): Promise<ApiResponse<T>> {
    const response = await axiosInstance.post<ApiResponse<T>>(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  }
}

// 导出API客户端实例
export const apiClient = new ApiClient()

// 导出axios实例（用于需要直接访问的场景）
export { axiosInstance }
