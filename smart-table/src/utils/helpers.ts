import type { CellValue } from "../types";
import type { FieldEntity } from "../db/schema";

export function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

export function isEqual(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function pick<T extends object, K extends keyof T>(
  obj: T,
  keys: K[],
): Pick<T, K> {
  const result = {} as Pick<T, K>;
  for (const key of keys) {
    if (key in obj) {
      result[key] = obj[key];
    }
  }
  return result;
}

export function omit<T extends object, K extends keyof T>(
  obj: T,
  keys: K[],
): Omit<T, K> {
  const result = { ...obj };
  for (const key of keys) {
    delete result[key];
  }
  return result;
}

export function groupBy<T>(
  array: T[],
  keyFn: (item: T) => string,
): Record<string, T[]> {
  return array.reduce(
    (groups, item) => {
      const key = keyFn(item);
      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(item);
      return groups;
    },
    {} as Record<string, T[]>,
  );
}

export function sortBy<T>(
  array: T[],
  keyFn: (item: T) => unknown,
  order: "asc" | "desc" = "asc",
): T[] {
  return [...array].sort((a, b) => {
    const aVal = keyFn(a);
    const bVal = keyFn(b);

    if (aVal === bVal) return 0;
    if (aVal === null || aVal === undefined) return 1;
    if (bVal === null || bVal === undefined) return -1;

    const comparison = aVal < bVal ? -1 : 1;
    return order === "asc" ? comparison : -comparison;
  });
}

export function uniqBy<T>(array: T[], keyFn: (item: T) => unknown): T[] {
  const seen = new Set<unknown>();
  return array.filter((item) => {
    const key = keyFn(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function chunk<T>(array: T[], size: number): T[][] {
  const result: T[][] = [];
  for (let i = 0; i < array.length; i += size) {
    result.push(array.slice(i, i + size));
  }
  return result;
}

export function getValueByPath(
  obj: Record<string, unknown>,
  path: string,
): unknown {
  return path.split(".").reduce((current: unknown, key) => {
    if (current && typeof current === "object") {
      return (current as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}

export function setValueByPath(
  obj: Record<string, unknown>,
  path: string,
  value: unknown,
): void {
  const keys = path.split(".");
  const lastKey = keys.pop()!;
  const target = keys.reduce((current, key) => {
    if (!(key in current)) {
      current[key] = {} as Record<string, unknown>;
    }
    return current[key] as Record<string, unknown>;
  }, obj);
  target[lastKey] = value;
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

export function formatDate(
  timestamp: number,
  format: string = "YYYY-MM-DD",
): string {
  const date = new Date(timestamp);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");

  return format
    .replace("YYYY", String(year))
    .replace("MM", month)
    .replace("DD", day)
    .replace("HH", hours)
    .replace("mm", minutes)
    .replace("ss", seconds);
}

export function generateColor(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = seed.charCodeAt(i) + ((hash << 5) - hash);
  }

  const hue = hash % 360;
  return `hsl(${hue}, 65%, 50%)`;
}

export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.substring(0, maxLength - 3) + "...";
}

/**
 * 去除HTML标签，返回纯文本
 * @param html 包含HTML标签的字符串
 * @returns 纯文本字符串
 */
export function stripHtml(html: string): string {
  if (!html) return "";
  // 创建一个临时DOM元素来解析HTML
  const tmp = document.createElement("div");
  tmp.innerHTML = html;
  return tmp.textContent || tmp.innerText || "";
}

/**
 * 截取富文本内容（去除HTML后截取）
 * @param html 包含HTML标签的字符串
 * @param maxLength 最大长度，默认30
 * @returns 截取后的纯文本
 */
export function truncateRichText(html: string, maxLength: number = 30): string {
  if (!html) return "";
  const plainText = stripHtml(html);
  if (plainText.length <= maxLength) return plainText;
  return plainText.substring(0, maxLength) + "...";
}

/**
 * 允许的标签白名单
 */
const ALLOWED_TAGS = [
  'b', 'strong', 'i', 'em', 'u', 's', 'strike', 'del',
  'p', 'br', 'div', 'span',
  'ul', 'ol', 'li',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'blockquote', 'pre', 'code'
];

/**
 * 允许的HTML属性白名单
 */
const ALLOWED_ATTRS: Record<string, string[]> = {
  '*': ['class'],
  'a': ['href', 'title', 'target'],
  'img': ['src', 'alt', 'title', 'width', 'height']
};

/**
 * 净化HTML内容，移除危险标签和属性
 * @param html 原始HTML字符串
 * @returns 净化后的HTML字符串
 */
export function sanitizeHtml(html: string): string {
  if (!html) return '';
  
  // 创建一个临时的div元素
  const tmp = document.createElement('div');
  tmp.innerHTML = html;
  
  // 递归清理节点
  function cleanNode(node: Node): Node | null {
    // 文本节点直接保留
    if (node.nodeType === Node.TEXT_NODE) {
      return node.cloneNode(true);
    }
    
    // 元素节点需要检查
    if (node.nodeType === Node.ELEMENT_NODE) {
      const element = node as HTMLElement;
      const tagName = element.tagName.toLowerCase();
      
      // 检查标签是否在白名单中
      if (!ALLOWED_TAGS.includes(tagName)) {
        // 不在白名单中，返回其文本内容
        return document.createTextNode(element.textContent || '');
      }
      
      // 创建新元素
      const newElement = document.createElement(tagName);
      
      // 复制允许的属性和样式
      const allowedAttrs = [...(ALLOWED_ATTRS['*'] || []), ...(ALLOWED_ATTRS[tagName] || [])];
      
      // 处理class属性
      if (allowedAttrs.includes('class') && element.className) {
        newElement.className = element.className;
      }
      
      // 处理其他属性
      for (const attr of allowedAttrs) {
        if (attr !== 'class' && element.hasAttribute(attr)) {
          const value = element.getAttribute(attr);
          if (value) {
            // 对href和src进行安全检查
            if (attr === 'href' || attr === 'src') {
              // 只允许http/https/mailto/tel协议
              if (/^(https?:|mailto:|tel:|data:image\/(png|jpeg|gif|webp);)/i.test(value)) {
                newElement.setAttribute(attr, value);
              }
            } else {
              newElement.setAttribute(attr, value);
            }
          }
        }
      }
      
      // 递归处理子节点
      while (element.firstChild) {
        const child = cleanNode(element.firstChild);
        if (child) {
          newElement.appendChild(child);
        }
        element.removeChild(element.firstChild);
      }
      
      return newElement;
    }
    
    // 其他类型的节点返回null
    return null;
  }
  
  // 清理所有子节点
  const fragment = document.createDocumentFragment();
  while (tmp.firstChild) {
    const cleaned = cleanNode(tmp.firstChild);
    if (cleaned) {
      fragment.appendChild(cleaned);
    }
    tmp.removeChild(tmp.firstChild);
  }
  
  // 将清理后的内容放回tmp
  tmp.appendChild(fragment);
  
  return tmp.innerHTML;
}

export function getCellDisplayValue(
  value: CellValue,
  field: FieldEntity,
): string {
  if (value === null || value === undefined) return "";

  switch (field.type) {
    case "checkbox":
      return value ? "是" : "否";

    case "multi_select":
      if (Array.isArray(value)) {
        return value
          .map((v) =>
            typeof v === "object" ? (v as { name: string }).name : v,
          )
          .join(", ");
      }
      return String(value);

    case "date":
      return formatDate(Number(value), "YYYY-MM-DD");

    case "attachment":
      if (Array.isArray(value)) {
        return `${value.length} 个附件`;
      }
      return "";

    case "single_select":
      if (
        typeof value === "object" &&
        value !== null &&
        !Array.isArray(value)
      ) {
        return (value as { name: string }).name;
      }
      return String(value);

    default:
      return String(value);
  }
}

// 清新配色方案 - 用于仪表盘等组件
export const freshColors = {
  primary: "#3B82F6",
  primaryLight: "#EFF6FF",
  success: "#10B981",
  warning: "#F59E0B",
  danger: "#EF4444",
  gray50: "#F9FAFB",
  gray100: "#F3F4F6",
  gray200: "#E5E7EB",
  gray300: "#D1D5DB",
  gray400: "#9CA3AF",
  gray500: "#6B7280",
  gray600: "#4B5563",
  gray700: "#374151",
  gray800: "#1F2937",
};
