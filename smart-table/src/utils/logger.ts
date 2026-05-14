/**
 * 条件日志工具
 * 仅在开发环境中输出日志，生产环境自动静默
 * 增强版：添加 API 错误追踪和 request_id 记录
 */

const isDev = import.meta.env.DEV

// API 错误追踪存储（开发环境）
interface ErrorTrace {
  requestId: string
  timestamp: number
  url: string
  method: string
  status: number
  message: string
  stack?: string
}

const errorTraces: ErrorTrace[] = []
const MAX_ERROR_TRACES = 50

export const devLog = {
  log: (...args: any[]) => {
    if (isDev) {
      console.log('[DEV]', ...args)
    }
  },
  
  warn: (...args: any[]) => {
    if (isDev) {
      console.warn('[DEV]', ...args)
    }
  },
  
  error: (...args: any[]) => {
    if (isDev) {
      console.error('[DEV]', ...args)
    }
  },
  
  debug: (...args: any[]) => {
    if (isDev) {
      console.debug('[DEV]', ...args)
    }
  },
  
  info: (...args: any[]) => {
    if (isDev) {
      console.info('[DEV]', ...args)
    }
  },
  
  group: (label: string) => {
    if (isDev) {
      console.group(label)
    }
  },
  
  groupEnd: () => {
    if (isDev) {
      console.groupEnd()
    }
  },
  
  time: (label: string) => {
    if (isDev) {
      console.time(label)
    }
  },
  
  timeEnd: (label: string) => {
    if (isDev) {
      console.timeEnd(label)
    }
  },

  // 新增：API 错误追踪
  apiError: (error: {
    requestId?: string
    url?: string
    method?: string
    status?: number
    message: string
    stack?: string
  }) => {
    if (isDev) {
      const trace: ErrorTrace = {
        requestId: error.requestId || 'unknown',
        timestamp: Date.now(),
        url: error.url || 'unknown',
        method: error.method || 'unknown',
        status: error.status || 500,
        message: error.message,
        stack: error.stack
      }
      
      errorTraces.push(trace)
      
      // 保持最大数量
      if (errorTraces.length > MAX_ERROR_TRACES) {
        errorTraces.shift()
      }
      
      console.group('[API ERROR]')
      console.error(`Request ID: ${trace.requestId}`)
      console.error(`URL: ${trace.method} ${trace.url}`)
      console.error(`Status: ${trace.status}`)
      console.error(`Message: ${trace.message}`)
      if (trace.stack) {
        console.error('Stack:', trace.stack)
      }
      console.groupEnd()
    }
  },

  // 获取错误历史（开发调试用）
  getErrorTraces: (): ErrorTrace[] => {
    return [...errorTraces]
  },

  // 清除错误历史
  clearErrorTraces: () => {
    errorTraces.length = 0
  }
}

export default devLog
