import type { CellValue } from '@/types';

/**
 * 将值转换为可被 IndexedDB 结构化克隆的普通对象。
 * Vue 的 reactive/ref 返回的是 Proxy，而结构化克隆算法无法克隆 Proxy，
 * 直接存入 IndexedDB 会抛出 DataCloneError(#<Object> could not be cloned)。
 * 这里通过 JSON 往返把 Proxy 解包为普通对象（字段值均为 JSON 安全的纯数据）。
 */
function toCloneable(value: unknown): unknown {
  if (value === null || typeof value !== 'object') return value;
  if (value instanceof Date) return value;
  if (Array.isArray(value)) {
    return value.map((item) => toCloneable(item));
  }
  // 对象（含 reactive Proxy）：经 JSON 往返解包为普通对象
  try {
    return JSON.parse(JSON.stringify(value));
  } catch {
    // 极端情况下回退为原值（不阻断保存，交由 IndexedDB 报错提示）
    return value;
  }
}

/**
 * 序列化记录值，将数组转换为 JSON 字符串以便 IndexedDB 存储；
 * 对象类型（如地理字段的 GeoValue）解包为可结构化克隆的普通对象。
 */
export function serializeRecordValues(values: Record<string, CellValue>): Record<string, CellValue> {
  const serialized: Record<string, CellValue> = {};

  for (const [key, value] of Object.entries(values)) {
    if (Array.isArray(value)) {
      // 将数组序列化为 JSON 字符串
      serialized[key] = JSON.stringify(value);
    } else if (value !== null && typeof value === 'object') {
      // 对象（地理/成员/关联等）：解包 reactive Proxy，避免 DataCloneError
      serialized[key] = toCloneable(value) as CellValue;
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
