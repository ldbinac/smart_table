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
    
    // 递归处理嵌套函数 - 从内到外处理
    let result = expression;
    let prevResult: string;
    
    // 循环处理直到没有变化（所有函数都被执行）
    do {
      prevResult = result;
      
      // 使用更精确的正则匹配函数调用（处理嵌套括号）
      const regex = new RegExp(`(${functionNames})\\s*\\(([^()]*)\\)`, "gi");
      
      result = result.replace(regex, (match, funcName, args) => {
        const func = formulaFunctions[funcName.toUpperCase()];
        if (!func) return match;

        try {
          // 先递归处理参数中的嵌套函数
          const evaluatedArgs = this.evaluateFunctions(args);
          const parsedArgs = this.parseArguments(evaluatedArgs);
          const funcResult = func(...parsedArgs);
          return this.valueToExpression(funcResult as CellValue, undefined);
        } catch {
          return "#ERROR";
        }
      });
    } while (result !== prevResult);
    
    return result;
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
    // 只允许数字、运算符、括号和常见数学符号
    const sanitized = expression.replace(
      /[^0-9+\-*/().,%<>=!&|?:'" \t\n]/g,
      "",
    );

    if (sanitized !== expression) {
      throw new Error("Invalid expression");
    }

    // 使用安全的数学表达式解析器替代 Function 构造函数
    return this.evaluateMathExpression(sanitized);
  }

  private evaluateMathExpression(expression: string): unknown {
    // 移除所有空白字符
    const expr = expression.replace(/\s+/g, "");

    // 验证表达式只包含允许的字符
    if (!/^[0-9+\-*/().,%<>=!&|?:'"]+$/.test(expr)) {
      throw new Error("Invalid characters in expression");
    }

    // 检查括号匹配
    let depth = 0;
    for (const char of expr) {
      if (char === "(") depth++;
      if (char === ")") depth--;
      if (depth < 0) throw new Error("Mismatched parentheses");
    }
    if (depth !== 0) throw new Error("Mismatched parentheses");

    // 使用安全的数学表达式求值
    try {
      return this.parseAndEvaluate(expr);
    } catch {
      return expression;
    }
  }

  private parseAndEvaluate(expr: string): number | boolean {
    // 处理布尔值
    if (expr === "true") return true;
    if (expr === "false") return false;

    // 处理字符串比较
    const stringMatch = expr.match(/^["'](.+)["']([<>=!]+)["'](.+)["']$/);
    if (stringMatch) {
      const [, left, op, right] = stringMatch;
      return this.compareStrings(left, op, right);
    }

    // 处理数字比较
    const comparisonMatch = expr.match(/^(.+?)([<>=!]+)(.+)$/);
    if (comparisonMatch) {
      const [, left, op, right] = comparisonMatch;
      const leftVal = this.parseNumber(left);
      const rightVal = this.parseNumber(right);
      if (leftVal !== null && rightVal !== null) {
        return this.compareNumbers(leftVal, op, rightVal);
      }
    }

    // 处理三元运算符
    const ternaryMatch = expr.match(/^(.+?)\?(.+?):(.+)$/);
    if (ternaryMatch) {
      const [, condition, trueVal, falseVal] = ternaryMatch;
      const condResult = this.parseAndEvaluate(condition);
      if (typeof condResult === "boolean") {
        return condResult
          ? this.parseAndEvaluate(trueVal)
          : this.parseAndEvaluate(falseVal);
      }
    }

    // 处理逻辑运算符
    if (expr.includes("&&")) {
      const parts = expr.split("&&");
      return parts.every((p) => this.parseAndEvaluate(p.trim()));
    }
    if (expr.includes("||")) {
      const parts = expr.split("||");
      return parts.some((p) => this.parseAndEvaluate(p.trim()));
    }

    // 处理数学表达式
    return this.evaluateArithmetic(expr);
  }

  private parseNumber(str: string): number | null {
    const num = parseFloat(str);
    return isNaN(num) ? null : num;
  }

  private compareNumbers(left: number, op: string, right: number): boolean {
    switch (op) {
      case "<":
        return left < right;
      case ">":
        return left > right;
      case "<=":
        return left <= right;
      case ">=":
        return left >= right;
      case "==":
      case "=":
        return left === right;
      case "!=":
        return left !== right;
      default:
        return false;
    }
  }

  private compareStrings(left: string, op: string, right: string): boolean {
    switch (op) {
      case "==":
      case "=":
        return left === right;
      case "!=":
        return left !== right;
      default:
        return false;
    }
  }

  private evaluateArithmetic(expr: string): number {
    // 处理百分比
    if (expr.endsWith("%")) {
      return this.evaluateArithmetic(expr.slice(0, -1)) / 100;
    }

    // 处理括号
    while (expr.includes("(")) {
      const match = expr.match(/\(([^()]+)\)/);
      if (!match) break;
      const inner = this.evaluateArithmetic(match[1]);
      expr = expr.replace(match[0], String(inner));
    }

    // 处理加减法
    const addSubMatch = expr.match(/^(.+?)([+\-])(.+)$/);
    if (addSubMatch) {
      const [, left, op, right] = addSubMatch;
      const leftVal = this.evaluateArithmetic(left);
      const rightVal = this.evaluateArithmetic(right);
      return op === "+" ? leftVal + rightVal : leftVal - rightVal;
    }

    // 处理乘除法
    const mulDivMatch = expr.match(/^(.+?)([*\/])(.+)$/);
    if (mulDivMatch) {
      const [, left, op, right] = mulDivMatch;
      const leftVal = this.evaluateArithmetic(left);
      const rightVal = this.evaluateArithmetic(right);
      return op === "*" ? leftVal * rightVal : leftVal / rightVal;
    }

    // 处理纯数字
    const num = parseFloat(expr);
    if (!isNaN(num)) return num;

    throw new Error("Invalid expression");
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
