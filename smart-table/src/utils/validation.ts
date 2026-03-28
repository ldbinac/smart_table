import type { FieldEntity, RecordEntity } from "@/db/schema";
import { FieldType, type CellValue } from "@/types";

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
