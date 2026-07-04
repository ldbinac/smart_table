/**
 * 公开配置 API
 */
import { apiClient } from './client'
import type { DemoConfig } from './types'

export const getDemoConfig = async (): Promise<DemoConfig> => {
  return apiClient.get<DemoConfig>('/config/demo')
}

export const demoApi = {
  getDemoConfig
}

export default demoApi
