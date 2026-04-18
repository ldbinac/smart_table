/**
 * 条件日志工具
 * 仅在开发环境中输出日志，生产环境自动静默
 */

const isDev = import.meta.env.DEV

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
}

export default devLog
