import type { FieldEntity, RecordEntity } from "@/db/schema";
import { FieldType, type CellValue } from "@/types";
import { formulaFunctions } from "./functions";

export interface FormulaError {
  message: string;
  code: string;
}

export interface ParseResult {
  type:
    | "literal"
    | "field"
    | "function"
    | "operator"
    | "number"
    | "string"
    | "boolean"
    | "expression";
  value: string | number | boolean | null;
  children?: ParseResult[];
}

export class FormulaEngine {
  private fields: Map<string, FieldEntity>;
  private fieldNameToId: Map<string, string>;

  constructor(fields: FieldEntity[]) {
    this.fields = new Map(fields.map((f) => [f.id, f]));
    this.fieldNameToId = new Map(
      fields.map((f) => [f.name.toLowerCase(), f.id]),
    );
  }

  parseFieldRefs(formula: string): string[] {
    const refs: string[] = [];
    const regex = /\{([^}]+)\}/g;
    let match;
    while ((match = regex.exec(formula)) !== null) {
      const fieldName = match[1].toLowerCase();
      const fieldId = this.fieldNameToId.get(fieldName);
      if (fieldId) {
        refs.push(fieldId);
      }
    }
    return refs;
  }

  calculate(record: RecordEntity, formula: string): CellValue | FormulaError {
    try {
      const result = this.evaluate(formula, record);
      return result;
    } catch (error) {
      return {
        message: error instanceof Error ? error.message : "计算错误",
        code: "CALCULATION_ERROR",
      };
    }
  }

  private evaluate(formula: string, record: RecordEntity): CellValue {
    let expression = formula.trim();

    expression = this.replaceFieldRefs(expression, record);
    expression = this.evaluateFunctions(expression);
    expression = this.evaluateExpression(expression);

    try {
      const result = this.safeEval(expression);
      return this.normalizeResult(result);
    } catch {
      return "#ERROR";
    }
  }

  private replaceFieldRefs(expression: string, record: RecordEntity): string {
    const regex = /\{([^}]+)\}/g;
    return expression.replace(regex, (_match, fieldName) => {
      const fieldId = this.fieldNameToId.get(fieldName.toLowerCase());
      if (!fieldId) return "null";

      const field = this.fields.get(fieldId);
      const value = record.values[fieldId];

      return this.valueToExpression(value, field);
    });
  }

  private valueToExpression(
    value: CellValue,
    field: FieldEntity | undefined,
  ): string {
    if (value === null || value === undefined) return "null";

    if (!field) return JSON.stringify(String(value));

    switch (field.type) {
      case FieldType.NUMBER:
      case FieldType.RATING:
      case FieldType.PROGRESS:
      case FieldType.AUTO_NUMBER:
        return String(Number(value) || 0);

      case FieldType.CHECKBOX:
        return Boolean(value) ? "1" : "0";

      case FieldType.DATE:
      case FieldType.CREATED_TIME:
      case FieldType.UPDATED_TIME:
        return String(Number(value) || 0);

      default:
        return JSON.stringify(String(value));
    }
  }

  private evaluateFunctions(expression: string): string {
    const functionNames = Object.keys(formulaFunctions).join("|");
    const regex = new RegExp(`(${functionNames})\\s*\\(([^)]*)\\)`, "gi");

    return expression.replace(regex, (match, funcName, args) => {
      const func = formulaFunctions[funcName.toUpperCase()];
      if (!func) return match;

      try {
        const parsedArgs = this.parseArguments(args);
        const result = func(...parsedArgs);
        return this.valueToExpression(result as CellValue, undefined);
      } catch {
        return "#ERROR";
      }
    });
  }

  private parseArguments(argsStr: string): unknown[] {
    if (!argsStr.trim()) return [];

    const args: unknown[] = [];
    let current = "";
    let depth = 0;
    let inString = false;
    let stringChar = "";

    for (let i = 0; i < argsStr.length; i++) {
      const char = argsStr[i];

      if (inString) {
        current += char;
        if (char === stringChar && argsStr[i - 1] !== "\\") {
          inString = false;
        }
        continue;
      }

      if (char === '"' || char === "'") {
        inString = true;
        stringChar = char;
        current += char;
        continue;
      }

      if (char === "(" || char === "[") {
        depth++;
        current += char;
        continue;
      }

      if (char === ")" || char === "]") {
        depth--;
        current += char;
        continue;
      }

      if (char === "," && depth === 0) {
        args.push(this.parseValue(current.trim()));
        current = "";
        continue;
      }

      current += char;
    }

    if (current.trim()) {
      args.push(this.parseValue(current.trim()));
    }

    return args;
  }

  private parseValue(value: string): unknown {
    if (value === "null" || value === "") return null;
    if (value === "true") return true;
    if (value === "false") return false;

    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      return value.slice(1, -1);
    }

    const num = Number(value);
    if (!isNaN(num)) return num;

    return value;
  }

  private evaluateExpression(expression: string): string {
    return expression;
  }

  private safeEval(expression: string): unknown {
    const sanitized = expression.replace(
      /[^0-9+\-*/().,%<>=!&|?:'" \t\n]/g,
      "",
    );

    if (sanitized !== expression) {
      throw new Error("Invalid expression");
    }

    try {
      return Function(`"use strict"; return (${expression})`)();
    } catch {
      return expression;
    }
  }

  private normalizeResult(result: unknown): CellValue {
    if (result === null || result === undefined) return null;
    if (typeof result === "number") {
      if (isNaN(result) || !isFinite(result)) return "#ERROR";
      return Math.round(result * 1000000) / 1000000;
    }
    if (typeof result === "boolean") return result ? 1 : 0;
    return String(result);
  }

  validateFormula(formula: string): { valid: boolean; error?: string } {
    try {
      const regex = /\{([^}]+)\}/g;
      let match;
      const missingFields: string[] = [];

      while ((match = regex.exec(formula)) !== null) {
        const fieldName = match[1].toLowerCase();
        if (!this.fieldNameToId.has(fieldName)) {
          missingFields.push(match[1]);
        }
      }

      if (missingFields.length > 0) {
        return {
          valid: false,
          error: `未知字段引用: ${missingFields.join(", ")}`,
        };
      }
      return { valid: true };
    } catch (error) {
      return {
        valid: false,
        error: error instanceof Error ? error.message : "公式验证失败",
      };
    }
  }

  getFormulaDescription(formula: string): string {
    const refs = this.parseFieldRefs(formula);
    const fieldNames = refs.map((id) => {
      const field = this.fields.get(id);
      return field ? field.name : "未知字段";
    });

    if (fieldNames.length === 0) {
      return "无字段引用";
    }

    return `引用字段: ${fieldNames.join(", ")}`;
  }
}

export const formulaEngine = {
  createEngine(fields: FieldEntity[]) {
    return new FormulaEngine(fields);
  },
};
