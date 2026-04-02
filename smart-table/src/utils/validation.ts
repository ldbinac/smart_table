import type { FieldEntity, RecordEntity } from "@/db/schema";
import { FieldType, type CellValue } from "@/types";
import type { FieldTypeValue } from "@/types";

export interface ValidationError {
  fieldId: string;
  fieldName: string;
  message: string;
  type: "required" | "unique" | "format" | "custom";
}

export interface ValidationRule {
  type: "required" | "unique" | "format" | "custom";
  enabled: boolean;
  message?: string;
  pattern?: string;
  validator?: (
    value: CellValue,
    record: RecordEntity,
    field: FieldEntity,
  ) => boolean;
}

export class DataValidator {
  private records: RecordEntity[];

  constructor(records: RecordEntity[] = []) {
    this.records = records;
  }

  setRecords(records: RecordEntity[]) {
    this.records = records;
  }

  validateField(
    field: FieldEntity,
    value: CellValue,
    record?: RecordEntity,
  ): ValidationError[] {
    const errors: ValidationError[] = [];
    const rules = field.options?.validation as ValidationRule[] | undefined;

    if (!rules) return errors;

    for (const rule of rules) {
      if (!rule.enabled) continue;

      switch (rule.type) {
        case "required":
          if (this.isRequired(field) && this.isEmpty(value)) {
            errors.push({
              fieldId: field.id,
              fieldName: field.name,
              message: rule.message || `${field.name}为必填项`,
              type: "required",
            });
          }
          break;

        case "unique":
          if (!this.isUnique(field.id, value, record?.id)) {
            errors.push({
              fieldId: field.id,
              fieldName: field.name,
              message: rule.message || `${field.name}的值必须唯一`,
              type: "unique",
            });
          }
          break;

        case "format":
          if (
            !this.isEmpty(value) &&
            !this.validateFormat(value, field, rule.pattern)
          ) {
            errors.push({
              fieldId: field.id,
              fieldName: field.name,
              message: rule.message || `${field.name}格式不正确`,
              type: "format",
            });
          }
          break;

        case "custom":
          if (
            rule.validator &&
            record &&
            !rule.validator(value, record, field)
          ) {
            errors.push({
              fieldId: field.id,
              fieldName: field.name,
              message: rule.message || `${field.name}验证失败`,
              type: "custom",
            });
          }
          break;
      }
    }

    return errors;
  }

  validateRecord(
    fields: FieldEntity[],
    record: RecordEntity,
  ): ValidationError[] {
    const errors: ValidationError[] = [];

    for (const field of fields) {
      const value = record.values[field.id];
      const fieldErrors = this.validateField(field, value, record);
      errors.push(...fieldErrors);
    }

    return errors;
  }

  validateRecords(
    fields: FieldEntity[],
    records: RecordEntity[],
  ): Map<string, ValidationError[]> {
    const errorMap = new Map<string, ValidationError[]>();

    for (const record of records) {
      const errors = this.validateRecord(fields, record);
      if (errors.length > 0) {
        errorMap.set(record.id, errors);
      }
    }

    return errorMap;
  }

  private isRequired(field: FieldEntity): boolean {
    return field.options?.required === true;
  }

  private isEmpty(value: CellValue): boolean {
    if (value === null || value === undefined) return true;
    if (typeof value === "string" && value.trim() === "") return true;
    if (Array.isArray(value) && value.length === 0) return true;
    return false;
  }

  private isUnique(
    fieldId: string,
    value: CellValue,
    excludeRecordId?: string,
  ): boolean {
    if (this.isEmpty(value)) return true;

    const duplicate = this.records.find((r) => {
      if (r.id === excludeRecordId) return false;
      return JSON.stringify(r.values[fieldId]) === JSON.stringify(value);
    });

    return !duplicate;
  }

  private validateFormat(
    value: CellValue,
    field: FieldEntity,
    pattern?: string,
  ): boolean {
    if (!pattern) {
      return this.validateByFieldType(value, field);
    }

    try {
      const regex = new RegExp(pattern);
      return regex.test(String(value));
    } catch {
      return true;
    }
  }

  private validateByFieldType(value: CellValue, field: FieldEntity): boolean {
    const strValue = String(value);

    switch (field.type) {
      case FieldType.EMAIL:
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(strValue);

      case FieldType.PHONE:
        return /^1[3-9]\d{9}$/.test(strValue);

      case FieldType.URL:
        try {
          new URL(strValue);
          return true;
        } catch {
          return false;
        }

      case FieldType.NUMBER:
        return !isNaN(Number(value));

      default:
        return true;
    }
  }
}

export const dataValidator = new DataValidator();

export function createValidationRule(
  type: ValidationRule["type"],
  options: Partial<ValidationRule> = {},
): ValidationRule {
  return {
    type,
    enabled: true,
    ...options,
  };
}

// ==================== 必填字段校验工具函数 ====================

export interface RequiredValidationResult {
  valid: boolean;
  errors: Array<{
    fieldId: string;
    fieldName: string;
    message: string;
  }>;
}

/**
 * 检查字段是否为必填字段
 * 优先使用 field.isRequired，其次检查 options.required
 */
export function isFieldRequired(field: FieldEntity): boolean {
  return field.isRequired === true || field.options?.required === true;
}

/**
 * 检查值是否为空
 * - null/undefined 视为空
 * - 空字符串或仅包含空格的字符串视为空
 * - 空数组视为空
 * - 0 和 false 不视为空
 */
export function isValueEmpty(value: CellValue): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === "string" && value.trim() === "") return true;
  if (Array.isArray(value) && value.length === 0) return true;
  return false;
}

/**
 * 验证必填字段
 * @param fields 字段列表
 * @param values 字段值
 * @returns 验证结果
 */
export function validateRequiredFields(
  fields: FieldEntity[],
  values: Record<string, CellValue>,
): RequiredValidationResult {
  const errors: Array<{
    fieldId: string;
    fieldName: string;
    message: string;
  }> = [];

  for (const field of fields) {
    // 跳过非必填字段
    if (!isFieldRequired(field)) continue;

    // 跳过只读字段（系统字段、公式字段等）
    const readonlyFieldTypes: FieldTypeValue[] = [
      FieldType.FORMULA,
      FieldType.LOOKUP,
      FieldType.CREATED_BY,
      FieldType.CREATED_TIME,
      FieldType.UPDATED_BY,
      FieldType.UPDATED_TIME,
      FieldType.AUTO_NUMBER,
    ];
    if (readonlyFieldTypes.includes(field.type as FieldTypeValue)) {
      continue;
    }

    const value = values[field.id];

    if (isValueEmpty(value)) {
      errors.push({
        fieldId: field.id,
        fieldName: field.name,
        message: `请填写必填字段：${field.name}`,
      });
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * 获取必填字段校验的错误提示信息
 * @param errors 错误列表
 * @returns 格式化的错误提示
 */
export function getRequiredFieldErrorMessage(
  errors: Array<{ fieldName: string }>,
): string {
  if (errors.length === 0) return "";

  const fieldNames = errors.map((e) => e.fieldName).join("、");

  if (errors.length === 1) {
    return `请填写必填字段：${fieldNames}`;
  }

  return `请填写以下必填字段：${fieldNames}`;
}

// ==================== 字段类型格式校验工具函数 ====================

export interface FieldFormatValidationResult {
  valid: boolean;
  error?: string;
}

/**
 * 邮箱校验正则表达式
 * 支持标准邮箱格式：username@domain.com
 */
const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

/**
 * 手机号校验正则表达式（中国大陆）
 * 支持 11 位手机号，以 1 开头，第二位为 3-9
 */
const PHONE_REGEX = /^1[3-9]\d{9}$/;

/**
 * 链接校验正则表达式
 * 支持 http://、https://、ftp://、sftp:// 开头的链接
 */
const URL_REGEX = /^(https?|ftp|sftp):\/\/[^\s/$.?#].[^\s]*$/i;

/**
 * 校验邮箱地址格式
 * @param value 邮箱地址
 * @returns 校验结果
 */
export function validateEmail(value: string): FieldFormatValidationResult {
  if (!value || value.trim() === "") {
    return { valid: true }; // 空值由必填校验处理
  }

  const trimmed = value.trim();
  const valid = EMAIL_REGEX.test(trimmed);

  return {
    valid,
    error: valid ? undefined : "请输入正确的邮箱地址格式，如：example@domain.com",
  };
}

/**
 * 校验手机号码格式（中国大陆）
 * @param value 手机号码
 * @returns 校验结果
 */
export function validatePhone(value: string): FieldFormatValidationResult {
  if (!value || value.trim() === "") {
    return { valid: true };
  }

  // 去除空格、横线、括号等分隔符
  const cleaned = value.replace(/[\s\-\(\)]/g, "");
  const valid = PHONE_REGEX.test(cleaned);

  return {
    valid,
    error: valid ? undefined : "请输入正确的11位手机号码",
  };
}

/**
 * 校验链接地址格式
 * @param value 链接地址
 * @returns 校验结果
 */
export function validateUrl(value: string): FieldFormatValidationResult {
  if (!value || value.trim() === "") {
    return { valid: true };
  }

  const trimmed = value.trim();
  const valid = URL_REGEX.test(trimmed);

  return {
    valid,
    error: valid
      ? undefined
      : "请输入完整的链接地址，需以 http://、https://、ftp:// 或 sftp:// 开头",
  };
}

/**
 * 根据字段类型校验值格式
 * @param value 字段值
 * @param fieldType 字段类型
 * @returns 校验结果
 */
export function validateFieldFormat(
  value: CellValue,
  fieldType: FieldTypeValue,
): FieldFormatValidationResult {
  if (!value || (typeof value === "string" && value.trim() === "")) {
    return { valid: true };
  }

  const strValue = String(value);

  switch (fieldType) {
    case FieldType.EMAIL:
      return validateEmail(strValue);
    case FieldType.PHONE:
      return validatePhone(strValue);
    case FieldType.URL:
      return validateUrl(strValue);
    default:
      return { valid: true };
  }
}

/**
 * 批量校验记录中的字段格式
 * @param fields 字段列表
 * @param values 字段值
 * @returns 校验错误列表
 */
export function validateFieldsFormat(
  fields: FieldEntity[],
  values: Record<string, CellValue>,
): Array<{ fieldId: string; fieldName: string; message: string }> {
  const errors: Array<{ fieldId: string; fieldName: string; message: string }> =
    [];

  for (const field of fields) {
    // 只校验 EMAIL、PHONE、URL 类型字段
    if (
      field.type !== FieldType.EMAIL &&
      field.type !== FieldType.PHONE &&
      field.type !== FieldType.URL
    ) {
      continue;
    }

    const value = values[field.id];
    const result = validateFieldFormat(value, field.type as FieldTypeValue);

    if (!result.valid) {
      errors.push({
        fieldId: field.id,
        fieldName: field.name,
        message: result.error || `${field.name}格式不正确`,
      });
    }
  }

  return errors;
}
