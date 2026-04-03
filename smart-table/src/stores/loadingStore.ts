/**
 * 加载状态管理Store
 * 管理全局加载状态
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useLoadingStore = defineStore('loading', () => {
  // 请求计数器
  const requestCount = ref(0)
  
  // 延迟显示计时器
  let delayTimer: ReturnType<typeof setTimeout> | null = null
  
  // 是否显示加载状态（延迟后）
  const isLoading = ref(false)
  
  // 是否正在加载（立即响应）
  const isLoadingImmediate = computed(() => requestCount.value > 0)
  
  // 开始加载
  const startLoading = () => {
    requestCount.value++
    
    // 延迟显示加载状态（避免闪烁）
    if (!delayTimer) {
      delayTimer = setTimeout(() => {
        if (requestCount.value > 0) {
          isLoading.value = true
        }
      }, 200)
    }
  }
  
  // 结束加载
  const endLoading = () => {
    if (requestCount.value > 0) {
      requestCount.value--
    }
    
    // 如果没有请求了，清除加载状态
    if (requestCount.value === 0) {
      isLoading.value = false
      
      if (delayTimer) {
        clearTimeout(delayTimer)
        delayTimer = null
      }
    }
  }
  
  // 强制结束所有加载
  const endAllLoading = () => {
    requestCount.value = 0
    isLoading.value = false
    
    if (delayTimer) {
      clearTimeout(delayTimer)
      delayTimer = null
    }
  }
  
  return {
    isLoading,
    isLoadingImmediate,
    startLoading,
    endLoading,
    endAllLoading
  }
})
