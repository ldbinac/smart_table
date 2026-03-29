/**
 * 序列化视图配置，将数组转换为 JSON 字符串以便 IndexedDB 存储
 */
export function serializeViewConfig(
  config: Record<string, unknown>,
): Record<string, unknown> {
  const serialized: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(config)) {
    if (Array.isArray(value)) {
      // 将数组序列化为 JSON 字符串
      serialized[key] = JSON.stringify(value);
    } else if (typeof value === "object" && value !== null) {
      // 递归处理嵌套对象
      serialized[key] = serializeViewConfig(value as Record<string, unknown>);
    } else {
      serialized[key] = value;
    }
  }

  return serialized;
}

/**
 * 反序列化视图配置，将 JSON 字符串还原为数组
 */
export function deserializeViewConfig(
  config: Record<string, unknown>,
): Record<string, unknown> {
  const deserialized: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(config)) {
    if (typeof value === "string") {
      try {
        // 尝试解析 JSON 字符串
        const parsed = JSON.parse(value);
        if (Array.isArray(parsed)) {
          deserialized[key] = parsed;
        } else if (typeof parsed === "object" && parsed !== null) {
          // 如果解析后是对象，递归处理
          deserialized[key] = deserializeViewConfig(parsed);
        } else {
          deserialized[key] = parsed;
        }
      } catch {
        // 不是有效的 JSON，保持原值
        deserialized[key] = value;
      }
    } else if (
      typeof value === "object" &&
      value !== null &&
      !Array.isArray(value)
    ) {
      // 递归处理嵌套对象
      deserialized[key] = deserializeViewConfig(
        value as Record<string, unknown>,
      );
    } else {
      deserialized[key] = value;
    }
  }

  return deserialized;
}
