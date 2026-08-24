/**
 * 公式计算结果显示工具
 *
 * 统一表格视图（TableCell）与导出（Excel / CSV / JSON）的公式字段显示逻辑：
 * 1. 优先使用后端预计算结果 record.computed_values[field.name]；
 * 2. 若该结果缺失（例如前端从 IndexedDB 读回的记录被剥离了 computed_values），
 *    则回退到前端 FormulaEngine.calculate 重新计算（与表格视图行为一致）。
 *
 * 格式化规则与表格视图保持一致：
 * - 字符串（日期/时间/错误）：日期串只取日期部分，其余原样返回；
 * - 数字：按公式返回类型（datetime/date/number）格式化，数字带千分位与精度。
 */
import { FormulaEngine } from "@/utils/formula/engine";
import { formatDate, formatDateTime } from "@/utils/timezone";
import type { FieldEntity, RecordEntity } from "@/db/schema";

export function calculateFormulaDisplay(
  field: FieldEntity,
  record: RecordEntity,
  allFields: FieldEntity[],
): string {
  const fieldOptions = field.options;
  const formula = (fieldOptions as any)?.formula as string;
  if (!formula) return "";

  const precision = (fieldOptions as any)?.precision ?? 2;

  // 1. 优先使用后端预计算结果（字段名作为 key）
  const computedValues = (record as any)?.computed_values;
  let precomputed: unknown =
    computedValues && typeof computedValues === "object"
      ? computedValues[field.name]
      : undefined;

  // 2. 缺失则前端回退计算
  if (precomputed === null || precomputed === undefined) {
    if (!allFields || allFields.length === 0) return "";
    try {
      const engine = new FormulaEngine(allFields);
      const result = engine.calculate(record, formula);
      if (result === "#ERROR") return "#ERROR";
      precomputed = result;
    } catch {
      return "";
    }
  }

  // 3. 格式化显示（与表格视图一致）
  if (typeof precomputed === "string") {
    const dateMatch = precomputed.match(/^\d{4}-\d{2}-\d{2}/);
    if (dateMatch) {
      return precomputed.split("T")[0]; // 只返回日期部分
    }
    return precomputed;
  }

  if (typeof precomputed === "number") {
    const resultType = FormulaEngine.inferResultType(formula);
    if (resultType === "datetime") {
      return formatDateTime(precomputed);
    }
    if (resultType === "date") {
      return formatDate(precomputed);
    }
    return precomputed.toLocaleString("zh-CN", {
      minimumFractionDigits: precision,
      maximumFractionDigits: precision,
    });
  }

  return String(precomputed);
}

/**
 * 取公式字段的原始计算值（用于 JSON 等数据交换导出）。
 * 优先后端预计算结果，缺失时回退前端 FormulaEngine 计算。
 */
export function getFormulaRawValue(
  field: FieldEntity,
  record: RecordEntity,
  allFields: FieldEntity[],
): unknown {
  const formula = (field.options as any)?.formula as string;
  if (!formula) return undefined;

  const computedValues = (record as any)?.computed_values;
  let raw: unknown =
    computedValues && typeof computedValues === "object"
      ? computedValues[field.name]
      : undefined;

  if (raw === null || raw === undefined) {
    if (!allFields || allFields.length === 0) return undefined;
    try {
      const engine = new FormulaEngine(allFields);
      const result = engine.calculate(record, formula);
      if (result === "#ERROR") return undefined;
      raw = result;
    } catch {
      return undefined;
    }
  }

  return raw;
}
