import type { FieldEntity } from "@/db/schema";

/**
 * 判断字段值是否算作“已填写”。
 * - null / undefined / 空字符串 / 空数组 / 空对象 视为未填写
 * - 0、false 属于有效值（视为已填写）
 */
export function hasFieldValue(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim() !== "";
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") return Object.keys(value as object).length > 0;
  return true;
}

/**
 * 判断字段是否因“只能编辑一次”而处于锁定（只读）状态。
 *
 * @param field  字段定义（读取 options.editableOnce）
 * @param values 记录的字段值映射（一般是原始保存值）
 */
export function isFieldEditLocked(
  field: FieldEntity | null | undefined,
  values: Record<string, unknown> | null | undefined,
): boolean {
  if (!field) return false;
  const options = (field.options || {}) as Record<string, unknown>;
  if (!options.editableOnce) return false;
  return hasFieldValue(values ? values[field.id] : undefined);
}
