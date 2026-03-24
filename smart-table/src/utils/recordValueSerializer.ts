import type { CellValue } from '@/types';

/**
 * 序列化记录值，将数组转换为 JSON 字符串以便 IndexedDB 存储
 */
export function serializeRecordValues(values: Record<string, CellValue>): Record<string, CellValue> {
  const serialized: Record<string, CellValue> = {};
  
  for (const [key, value] of Object.entries(values)) {
    if (Array.isArray(value)) {
      // 将数组序列化为 JSON 字符串
      serialized[key] = JSON.stringify(value);
    } else {
      serialized[key] = value;
    }
  }
  
  return serialized;
}

/**
 * 反序列化记录值，将 JSON 字符串还原为数组
 */
export function deserializeRecordValues(values: Record<string, CellValue>): Record<string, CellValue> {
  const deserialized: Record<string, CellValue> = {};
  
  for (const [key, value] of Object.entries(values)) {
    if (typeof value === 'string') {
      try {
        // 尝试解析 JSON 字符串
        const parsed = JSON.parse(value);
        if (Array.isArray(parsed)) {
          deserialized[key] = parsed;
        } else {
          deserialized[key] = value;
        }
      } catch {
        // 不是有效的 JSON，保持原值
        deserialized[key] = value;
      }
    } else {
      deserialized[key] = value;
    }
  }
  
  return deserialized;
}

/**
 * 检查值是否需要序列化（是否为数组）
 */
export function needsSerialization(value: CellValue): boolean {
  return Array.isArray(value);
}
