import type { FieldEntity, RecordEntity } from "@/db/schema";
import { FieldType, type CellValue } from "@/types";
import { formulaFunctions, matchesCriteria } from "./functions";
import dayjs from "dayjs";
import { t } from "@/i18n";

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

/** 可被整列引用的表数据（字段 + 全表记录） */
export interface FormulaTableData {
  fields: FieldEntity[];
  records: RecordEntity[];
}

/**
 * 表上下文：用于 [表].[字段] 整列引用。
 * tableName 为本表表名；tables 以表名小写为 key，须包含本表自身。
 * 未注入时整列引用求值退化为 null（兼容 FormShare 等无全表上下文的场景）。
 */
export interface FormulaTableContext {
  tableName: string;
  tables: Map<string, FormulaTableData>;
}

/** CurrentValue 哨兵：惰性条件中代表遍历到的当前元素值 */
const CV_SENTINEL = "\u0000CV\u0000";

/** 支持 CurrentValue 惰性条件求值的统计函数 */
const STATISTICAL_FUNCS = new Set(["FILTER", "COUNTIF", "SUMIF", "AVERAGEIF"]);

export class FormulaEngine {
  private fields: Map<string, FieldEntity>;
  private fieldNameToId: Map<string, string>;
  private tableContext?: FormulaTableContext;

  constructor(fields: FieldEntity[], tableContext?: FormulaTableContext) {
    this.fields = new Map(fields.map((f) => [f.id, f]));
    this.fieldNameToId = new Map(
      fields.map((f) => [f.name.toLowerCase(), f.id]),
    );
    this.tableContext = tableContext;
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
        message: error instanceof Error ? error.message : t('formula.calcError'),
        code: "CALCULATION_ERROR",
      };
    }
  }

  private evaluate(formula: string, record: RecordEntity): CellValue {
    let expression = formula.trim();

    // 1. 整列引用 [表].[字段] → 数组字面量（须先于行级字段引用）
    expression = this.replaceColumnRefs(expression);
    // 2. CurrentValue → 哨兵（供统计函数惰性求值）
    expression = this.replaceCurrentValueToken(expression);
    // 3. 行级字段引用 {字段} → 当前记录字段值
    expression = this.replaceFieldRefs(expression, record);
    // 4. 函数求值（统计函数含 CurrentValue 时走惰性分支）
    expression = this.evaluateFunctions(expression);
    expression = this.evaluateExpression(expression);

    try {
      const resolvedValue = this.tryResolveFullyEvaluatedValue(expression);
      if (resolvedValue !== undefined) {
        return this.normalizeResult(resolvedValue);
      }
      const result = this.safeEval(expression);
      return this.normalizeResult(result);
    } catch {
      return "#ERROR";
    }
  }

  private tryResolveFullyEvaluatedValue(expression: string): unknown | undefined {
    const trimmed = expression.trim();

    if (trimmed === "null") return null;
    if (trimmed === "true") return true;
    if (trimmed === "false") return false;

    // 表达式整体为数组字面量（如纯整列引用或 FILTER 结果外露）
    if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
      try {
        return JSON.parse(trimmed);
      } catch {
        return undefined;
      }
    }

    const num = Number(trimmed);
    if (!isNaN(num) && trimmed !== "") return num;
    
    if ((trimmed.startsWith('"') && trimmed.endsWith('"')) || 
        (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
      try {
        return JSON.parse(trimmed);
      } catch {
        return trimmed.slice(1, -1);
      }
    }
    
    return undefined;
  }

  /**
   * 整列引用展开：[表名].[字段名] → 该字段全表值集合的 JSON 数组字面量。
   * 表名/字段名大小写不敏感；未注入表上下文或找不到表/字段时退化为 null。
   * CurrentValue.[字段] 形态不匹配本正则（P1 仅支持 CurrentValue 单元格形态）。
   */
  private replaceColumnRefs(expression: string): string {
    if (!this.tableContext) return expression;
    const regex = /\[([^\[\]{}]+)\]\s*\.\s*\[([^\[\]{}]+)\]/g;
    return expression.replace(regex, (_match, tableName, fieldName) => {
      const table = this.tableContext!.tables.get(
        String(tableName).trim().toLowerCase(),
      );
      if (!table) return "null";
      const field = table.fields.find(
        (f) => f.name.toLowerCase() === String(fieldName).trim().toLowerCase(),
      );
      if (!field) return "null";
      const values = table.records.map((r) => r.values[field.id] ?? null);
      return this.arrayToExpression(values, field);
    });
  }

  /** 整列值 → JSON 数组字面量（元素遵循 valueToExpression 的标量投影规则） */
  private arrayToExpression(values: CellValue[], field: FieldEntity): string {
    const isDateField = (
      [
        FieldType.DATE,
        FieldType.DATE_TIME,
        FieldType.CREATED_TIME,
        FieldType.UPDATED_TIME,
      ] as string[]
    ).includes(field.type);
    const items = values.map((v) => {
      if (v === null || v === undefined) return "null";
      if (typeof v === "number") return String(v);
      if (typeof v === "boolean") return v ? "1" : "0";
      if (typeof v === "string" && isDateField) {
        const ts = dayjs(v).valueOf();
        return String(isNaN(ts) ? 0 : ts);
      }
      return JSON.stringify(String(v));
    });
    return `[${items.join(",")}]`;
  }

  /** CurrentValue → 哨兵；CurrentValue.[字段] 形态保留原文（P1 不支持，降级为不命中） */
  private replaceCurrentValueToken(expression: string): string {
    return expression.replace(/CurrentValue(?!\s*\.)/gi, CV_SENTINEL);
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

    // 数组值（整列引用/函数返回的数组）→ JSON 数组字面量，保证数组可在函数间传递
    if (Array.isArray(value)) {
      const items = value.map((v) => {
        if (v === null || v === undefined) return "null";
        if (typeof v === "number") return String(v);
        if (typeof v === "boolean") return v ? "1" : "0";
        return JSON.stringify(String(v));
      });
      return `[${items.join(",")}]`;
    }

    // 无字段上下文时（如函数返回值），根据值类型直接转换
    if (!field) {
      if (typeof value === "number") return String(value);
      if (typeof value === "boolean") return value ? "1" : "0";
      return JSON.stringify(String(value));
    }

    switch (field.type) {
      case FieldType.NUMBER:
      case FieldType.RATING:
      case FieldType.PROGRESS:
      case FieldType.AUTO_NUMBER:
        return String(Number(value) || 0);

      case FieldType.CHECKBOX:
        return Boolean(value) ? "1" : "0";

      case FieldType.DATE:
      case FieldType.DATE_TIME:
      case FieldType.CREATED_TIME:
      case FieldType.UPDATED_TIME:
        // 日期/时间字段值可能是：毫秒时间戳（数字）、ISO 字符串、或日期字符串。
        // 统一转为毫秒时间戳（与 TODAY()/NOW() 返回的时间戳基准一致），
        // 否则字符串与数字时间戳比较会失效（IF({结束日期}>TODAY(),'1','2') 误判）
        if (typeof value === "number") {
          return String(value);
        }
        if (typeof value === "string") {
          // 解析日期字符串为毫秒时间戳
          const ts = dayjs(value).valueOf();
          return String(ts);
        }
        return "0";

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
          const upperName = funcName.toUpperCase();

          // 统计函数惰性求值：FILTER 始终走专用分支；
          // COUNTIF/SUMIF/AVERAGEIF 仅当参数含 CurrentValue 哨兵时走专用分支
          if (
            upperName === "FILTER" ||
            (STATISTICAL_FUNCS.has(upperName) && args.includes(CV_SENTINEL))
          ) {
            const statResult = this.evaluateStatisticalFunction(
              upperName,
              evaluatedArgs,
            );
            return this.valueToExpression(statResult as CellValue, undefined);
          }

          const parsedArgs = this.parseArguments(evaluatedArgs);
          const funcResult = func(...parsedArgs);
          return this.valueToExpression(funcResult as CellValue, undefined);
        } catch (e) {
          const errorMsg = e instanceof Error ? e.message : String(e);
          return `#ERROR: ${funcName}(${args}) - ${errorMsg}`;
        }
      });
    } while (result !== prevResult);

    return result;
  }

  /**
   * 统计函数（FILTER/COUNTIF/SUMIF/AVERAGEIF）专用求值。
   * 条件参数含 CurrentValue 哨兵时逐元素惰性求值；否则退化为 matchesCriteria 字符串条件。
   * range 须为数组（来自整列引用或函数返回的数组），非数组时按单元素数组处理。
   */
  private evaluateStatisticalFunction(
    funcName: string,
    argsStr: string,
  ): unknown {
    const parsedArgs = this.parseArguments(argsStr);
    if (parsedArgs.length < 2) {
      throw new Error(`${funcName} requires at least 2 arguments`);
    }

    const range = parsedArgs[0];
    const criteria = parsedArgs[1];
    const third = parsedArgs[2];

    const values: unknown[] = Array.isArray(range) ? range : [range];

    // 当前元素 → 表达式投影（与数组字面量序列化规则一致）
    const elementToExpr = (v: unknown): string => {
      if (v === null || v === undefined) return "null";
      if (typeof v === "number") return String(v);
      if (typeof v === "boolean") return v ? "1" : "0";
      return JSON.stringify(String(v));
    };

    // 逐元素求值条件：哨兵替换为当前元素后走 parseAndEvaluate
    const condContainsSentinel =
      typeof criteria === "string" && criteria.includes(CV_SENTINEL);
    const evalCondition = (v: unknown): boolean => {
      if (!condContainsSentinel) {
        return matchesCriteria(v, criteria);
      }
      const cond = String(criteria).split(CV_SENTINEL).join(elementToExpr(v));
      try {
        const r = this.parseAndEvaluate(cond.trim());
        return typeof r === "boolean" ? r : false;
      } catch {
        return false;
      }
    };

    const matched = values.map((v) => evalCondition(v));

    switch (funcName) {
      case "FILTER": {
        return values.filter((_, i) => matched[i]);
      }
      case "COUNTIF": {
        return matched.filter(Boolean).length;
      }
      case "SUMIF": {
        const sumValues =
          third !== undefined
            ? Array.isArray(third)
              ? third
              : [third]
            : values;
        let sum = 0;
        values.forEach((_, i) => {
          if (matched[i]) sum += Number(sumValues[i]) || 0;
        });
        return sum;
      }
      case "AVERAGEIF": {
        const avgValues =
          third !== undefined
            ? Array.isArray(third)
              ? third
              : [third]
            : values;
        let sum = 0;
        let count = 0;
        values.forEach((_, i) => {
          if (matched[i]) {
            sum += Number(avgValues[i]) || 0;
            count++;
          }
        });
        return count > 0 ? sum / count : 0;
      }
      default:
        throw new Error(`Unsupported statistical function: ${funcName}`);
    }
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

    // 数组字面量（整列引用/函数返回的数组在表达式中的载体）
    if (value.startsWith("[") && value.endsWith("]")) {
      try {
        return JSON.parse(value);
      } catch {
        // 非法数组字面量，按普通字符串处理
      }
    }

    if (value.startsWith('"') && value.endsWith('"')) {
      try {
        return JSON.parse(value);
      } catch {
        return value.slice(1, -1);
      }
    }
    
    if (value.startsWith("'") && value.endsWith("'")) {
      return value.slice(1, -1);
    }

    const num = Number(value);
    if (!isNaN(num)) return num;

    // 若参数是比较表达式（如 "1753987200000>1754688000000"），需先求值，
    // 否则 IF/AND/OR/NOT/IFS 等逻辑函数会把比较字符串当成非空文本而恒为真，
    // 导致 IF({结束日期}>TODAY(),'1','2') 永远返回 trueValue（如永远返回 '1'）
    const trimmedVal = value.trim();
    if (
      /[<>=!]/.test(trimmedVal) &&
      !/^["'].*["']$/.test(trimmedVal)
    ) {
      try {
        const cmpResult = this.parseAndEvaluate(trimmedVal);
        if (typeof cmpResult === "boolean") return cmpResult;
        if (typeof cmpResult === "number") return cmpResult;
      } catch {
        // 不是有效比较表达式，继续后续处理
      }
    }

    // 尝试将表达式作为算术运算求值（如 "10+11" → 21）
    // 确保函数参数中的算术表达式能被正确计算
    try {
      const evalResult = this.evaluateArithmetic(value);
      if (typeof evalResult === 'number') return evalResult;
    } catch {
      // 求值失败，当作普通字符串返回
    }

    return value;
  }

  private evaluateExpression(expression: string): string {
    return expression;
  }

  private safeEval(expression: string): unknown {
    const trimmed = expression.trim();
    
    // 如果表达式是一个纯字符串（被引号包裹），直接返回字符串内容
    const stringMatch = trimmed.match(/^["'](.+)["']$/);
    if (stringMatch) {
      return stringMatch[1];
    }

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

    // 处理数字比较（运算符按多字符优先匹配：>= <= == != <> 以及单字符 > < = !）
    const comparisonMatch = expr.match(/^(.+?)([<>=!]=?|<>)(.+)$/);
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
    // 对毫秒时间戳等浮点数值，使用容差比较相等，避免 === 因精度差异误判
    const EPS = 1e-6;
    const eq = Math.abs(left - right) < EPS;
    switch (op) {
      case "<":
        return left < right && !eq;
      case ">":
        return left > right && !eq;
      case "<=":
        return left < right || eq;
      case ">=":
        return left > right || eq;
      case "==":
      case "=":
        return eq;
      case "!=":
      case "<>":
        return !eq;
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
      case "<>":
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

    // 处理加减法（低优先级，贪婪匹配左侧以实现左结合）
    const addSubMatch = expr.match(/^(.+)([+\-])(.+)$/);
    if (addSubMatch) {
      const [, left, op, right] = addSubMatch;
      const leftVal = this.evaluateArithmetic(left);
      const rightVal = this.evaluateArithmetic(right);
      return op === "+" ? leftVal + rightVal : leftVal - rightVal;
    }

    // 处理乘除法（高优先级，贪婪匹配左侧以实现左结合）
    const mulDivMatch = expr.match(/^(.+)([*\/])(.+)$/);
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
          error: t('formula.unknownFieldReference', [missingFields.join(", ")]),
        };
      }

      // 整列引用校验（仅在注入了表上下文时执行）
      if (this.tableContext) {
        const colRegex = /\[([^\[\]{}]+)\]\s*\.\s*\[([^\[\]{}]+)\]/g;
        const missingColumns: string[] = [];
        while ((match = colRegex.exec(formula)) !== null) {
          const table = this.tableContext.tables.get(
            match[1].trim().toLowerCase(),
          );
          if (!table) {
            missingColumns.push(match[1].trim());
            continue;
          }
          const field = table.fields.find(
            (f) =>
              f.name.toLowerCase() === match[2].trim().toLowerCase(),
          );
          if (!field) {
            missingColumns.push(`${match[1].trim()}.${match[2].trim()}`);
          }
        }
        if (missingColumns.length > 0) {
          return {
            valid: false,
            error: t('formula.unknownColumnReference', [missingColumns.join(", ")]),
          };
        }
      }

      return { valid: true };
    } catch (error) {
      return {
        valid: false,
        error: error instanceof Error ? error.message : t('formula.validationFailed'),
      };
    }
  }

  getFormulaDescription(formula: string): string {
    const refs = this.parseFieldRefs(formula);
    const fieldNames = refs.map((id) => {
      const field = this.fields.get(id);
      return field ? field.name : t('formula.unknownField');
    });

    if (fieldNames.length === 0) {
      return t('formula.noFieldReference');
    }

    return t('formula.referencedFields', [fieldNames.join(", ")]);
  }

  /**
   * 推断公式的结果类型
   * 用于决定显示格式（日期时间、日期、数字、文本等）
   */
  static inferResultType(formula: string): "datetime" | "date" | "number" | "text" {
    if (!formula || typeof formula !== "string") return "text";

    const upperFormula = formula.toUpperCase();

    // 1. 返回日期时间类型的函数（带时分秒）
    const datetimeFunctions = [
      "NOW",           // 返回当前日期时间
      "DATETIME",      // 构造日期时间
    ];

    // 2. 返回日期类型的函数（只有年月日）
    const dateFunctions = [
      "DATEADD",       // 日期加减
      "TODAY",         // 当前日期
      "DATE",          // 构造日期
      "EDATE",         // 指定月份偏移后的日期
      "EOMONTH",       // 月末日期
      "WORKDAY",       // 工作日日期
    ];

    // 3. 返回整数/数值类型的日期函数（提取日期部分或时间戳）
    const integerFunctions = [
      "YEAR",          // 年份
      "MONTH",         // 月份
      "DAY",           // 日
      "HOUR",          // 小时
      "MINUTE",        // 分钟
      "SECOND",        // 秒
      "WEEKDAY",       // 星期几
      "UNIXTIMESTAMP", // Unix 时间戳
      "FROMUNIXTIME",  // 时间戳转日期时间（返回毫秒数）
      "DATEDIF",       // 日期差
      "DATEDIFF",      // 日期差（DATEDIF 别名）
      "COUNTIF",       // 条件计数
      "SUMIF",         // 条件求和
      "AVERAGEIF",     // 条件平均
    ];

    // 检查整数函数（提取日期部分的函数，返回数值）
    // 必须最先检查，因为 YEAR(TODAY()) 应返回 number 而非 date，
    // YEAR(NOW()) 应返回 number 而非 datetime
    for (const func of integerFunctions) {
      const regex = new RegExp(`\\b${func}\\s*\\(`, "i");
      if (regex.test(upperFormula)) {
        return "number";
      }
    }

    // 检查日期时间函数
    for (const func of datetimeFunctions) {
      const regex = new RegExp(`\\b${func}\\s*\\(`, "i");
      if (regex.test(upperFormula)) {
        return "datetime";
      }
    }

    // 检查日期函数
    for (const func of dateFunctions) {
      const regex = new RegExp(`\\b${func}\\s*\\(`, "i");
      if (regex.test(upperFormula)) {
        return "date";
      }
    }

    // 纯数字运算（无文本操作）
    const hasTextOp = /["']/.test(formula) || /\b(CONCAT|TEXT|LEFT|RIGHT|MID|LEN|TRIM|UPPER|LOWER|SUBSTITUTE|REPLACE|REPT)\s*\(/i.test(formula);

    if (!hasTextOp) {
      // 检查是否包含字段引用或数字运算符
      if (/\{[^}]+\}/.test(formula) || /[\d+\-*/]/.test(formula)) {
        return "number";
      }
    }

    return "text";
  }
}

export const formulaEngine = {
  createEngine(fields: FieldEntity[], tableContext?: FormulaTableContext) {
    return new FormulaEngine(fields, tableContext);
  },
};
