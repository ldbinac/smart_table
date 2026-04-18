/**
 * HTML 消毒工具
 * 使用 DOMPurify 防止 XSS 攻击
 */
import DOMPurify from 'dompurify'

/**
 * 默认 DOMPurify 配置
 * 允许的标签和属性
 */
const DEFAULT_CONFIG: DOMPurify.Config = {
  ALLOWED_TAGS: [
    'p', 'br', 'strong', 'em', 'u', 's', 'span',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li',
    'a', 'img',
    'blockquote', 'pre', 'code',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'div'
  ],
  ALLOWED_ATTR: [
    'href', 'src', 'alt', 'title', 'class', 'id',
    'target', 'rel',
    'style'
  ],
  ALLOW_DATA_ATTR: false,
  ADD_ATTR: ['target'],
  FORCE_BODY: true,
}

/**
 * 邮件模板配置
 * 允许更多标签用于邮件内容
 */
const EMAIL_TEMPLATE_CONFIG: DOMPurify.Config = {
  ALLOWED_TAGS: [
    'p', 'br', 'strong', 'em', 'u', 's', 'span',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li',
    'a', 'img',
    'blockquote', 'pre', 'code',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'div',
    'hr', 'sub', 'sup',
    'font', 'center'
  ],
  ALLOWED_ATTR: [
    'href', 'src', 'alt', 'title', 'class', 'id',
    'target', 'rel',
    'style', 'color', 'size', 'face',
    'width', 'height', 'align', 'valign',
    'bgcolor', 'border', 'cellpadding', 'cellspacing'
  ],
  ALLOW_DATA_ATTR: false,
  ADD_ATTR: ['target'],
  FORCE_BODY: true,
}

/**
 * 消毒 HTML 内容
 * 移除潜在的恶意脚本和危险标签
 * 
 * @param html - 原始 HTML 字符串
 * @param config - 可选的自定义配置
 * @returns 消毒后的安全 HTML 字符串
 */
export function sanitizeHtml(html: string, config?: DOMPurify.Config): string {
  if (!html) return ''
  
  const mergedConfig = { ...DEFAULT_CONFIG, ...config }
  return DOMPurify.sanitize(html, mergedConfig)
}

/**
 * 消毒邮件模板 HTML 内容
 * 允许更多邮件相关标签
 * 
 * @param html - 原始 HTML 字符串
 * @returns 消毒后的安全 HTML 字符串
 */
export function sanitizeEmailHtml(html: string): string {
  if (!html) return ''
  return DOMPurify.sanitize(html, EMAIL_TEMPLATE_CONFIG)
}

/**
 * 转义 HTML 特殊字符
 * 用于纯文本显示，不解析 HTML
 * 
 * @param text - 原始文本
 * @returns 转义后的文本
 */
export function escapeHtml(text: string): string {
  if (!text) return ''
  
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }
  
  return text.replace(/[&<>"']/g, (char) => map[char])
}

/**
 * 高亮搜索关键词
 * 对文本进行转义后，安全地包裹关键词
 * 
 * @param text - 原始文本
 * @param query - 搜索关键词
 * @param highlightClass - 高亮样式类名
 * @returns 包含高亮标记的安全 HTML
 */
export function highlightText(
  text: string,
  query: string,
  highlightClass: string = 'highlight'
): string {
  if (!text || !query) return escapeHtml(text)
  
  // 先转义整个文本
  const escapedText = escapeHtml(text)
  const escapedQuery = escapeHtml(query)
  
  // 创建正则表达式（不区分大小写）
  const regex = new RegExp(`(${escapeRegExp(escapedQuery)})`, 'gi')
  
  // 替换为高亮 span
  return escapedText.replace(
    regex,
    `<span class="${highlightClass}">$1</span>`
  )
}

/**
 * 转义正则表达式特殊字符
 * 
 * @param string - 原始字符串
 * @returns 转义后的字符串
 */
function escapeRegExp(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export default {
  sanitizeHtml,
  sanitizeEmailHtml,
  escapeHtml,
  highlightText
}
