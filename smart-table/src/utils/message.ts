/**
 * 消息提示工具
 * 提供统一的消息提示接口
 */

import { ElMessage, ElNotification } from 'element-plus'
import type { MessageOptions, NotificationOptions } from 'element-plus'

// 消息类型
export type MessageType = 'success' | 'error' | 'warning' | 'info'

// 消息配置
interface MessageConfig {
  message: string
  type?: MessageType
  duration?: number
  showClose?: boolean
}

// 通知配置
interface NotifyConfig extends MessageConfig {
  title?: string
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left'
}

/**
 * 显示消息提示
 */
const showMessage = (config: MessageConfig | string, type: MessageType = 'info') => {
  const options: MessageOptions = typeof config === 'string' 
    ? { message: config, type, duration: 3000 }
    : { 
        message: config.message, 
        type: config.type || type, 
        duration: config.duration ?? 3000,
        showClose: config.showClose ?? true
      }
  
  return ElMessage(options)
}

/**
 * 显示通知
 */
const showNotification = (config: NotifyConfig | string, type: MessageType = 'info') => {
  const options: NotificationOptions = typeof config === 'string'
    ? { 
        title: type === 'error' ? '错误' : type === 'success' ? '成功' : '提示',
        message: config, 
        type, 
        duration: 4500,
        position: 'top-right'
      }
    : {
        title: config.title || (type === 'error' ? '错误' : type === 'success' ? '成功' : '提示'),
        message: config.message,
        type: config.type || type,
        duration: config.duration ?? 4500,
        position: config.position || 'top-right',
        showClose: config.showClose ?? true
      }
  
  return ElNotification(options)
}

/**
 * 消息工具对象
 */
export const message = {
  /**
   * 成功消息
   */
  success: (config: MessageConfig | string) => showMessage(config, 'success'),
  
  /**
   * 错误消息
   */
  error: (config: MessageConfig | string) => showMessage(config, 'error'),
  
  /**
   * 警告消息
   */
  warning: (config: MessageConfig | string) => showMessage(config, 'warning'),
  
  /**
   * 信息消息
   */
  info: (config: MessageConfig | string) => showMessage(config, 'info'),
  
  /**
   * 关闭所有消息
   */
  closeAll: () => ElMessage.closeAll()
}

/**
 * 通知工具对象
 */
export const notification = {
  /**
   * 成功通知
   */
  success: (config: NotifyConfig | string) => showNotification(config, 'success'),
  
  /**
   * 错误通知
   */
  error: (config: NotifyConfig | string) => showNotification(config, 'error'),
  
  /**
   * 警告通知
   */
  warning: (config: NotifyConfig | string) => showNotification(config, 'warning'),
  
  /**
   * 信息通知
   */
  info: (config: NotifyConfig | string) => showNotification(config, 'info'),
  
  /**
   * 关闭所有通知
   */
  closeAll: () => ElNotification.closeAll()
}

/**
 * 使用消息工具（组合式API风格）
 */
export const useMessage = () => message

/**
 * 使用通知工具（组合式API风格）
 */
export const useNotification = () => notification

// 默认导出
export default message
