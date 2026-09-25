import type {
  FilterCondition,
  FilterOperatorValue,
  FilterGroup,
} from "../types";
import type { FieldEntity, RecordEntity } from "../db/schema";
import { FilterOperator, FieldType } from "../types";
import { t } from "@/i18n";
import { FormulaEngine } from "./formula/engine";

/** 操作符枚举值到国际化 key 的映射 */
const OPERATOR_KEY_MAP: Record<FilterOperatorValue, string> = {
  [FilterOperator.EQUALS]: "filter.opEquals",
  [FilterOperator.NOT_EQUALS]: "filter.opNotEquals",
  [FilterOperator.CONTAINS]: "filter.opContains",
  [FilterOperator.NOT_CONTAINS]: "filter.opNotContains",
  [FilterOperator.STARTS_WITH]: "filter.opStartsWith",
  [FilterOperator.ENDS_WITH]: "filter.opEndsWith",
  [FilterOperator.IS_EMPTY]: "filter.opIsEmpty",
  [FilterOperator.IS_NOT_EMPTY]: "filter.opIsNotEmpty",
  [FilterOperator.GREATER_THAN]: "filter.opGreaterThan",
  [FilterOperator.LESS_THAN]: "filter.opLessThan",
  [FilterOperator.GREATER_THAN_OR_EQUAL]: "filter.opGreaterThanOrEqual",
  [FilterOperator.LESS_THAN_OR_EQUAL]: "filter.opLessThanOrEqual",
  [FilterOperator.IS_WITHIN]: "filter.opIsWithin",
  [FilterOperator.IS_BEFORE]: "filter.opBefore",
  [FilterOperator.IS_AFTER]: "filter.opAfter",
  [FilterOperator.IS_ANY_OF]: "filter.opIsAnyOf",
  [FilterOperator.IS_NONE_OF]: "filter.opIsNoneOf",
};

export function getOperatorLabel(operator: FilterOperatorValue): string {
  const key = OPERATOR_KEY_MAP[operator];
  return key ? t(key) : operator;
}

export const OPERATORS_BY_FIELD_TYPE: Record<string, FilterOperatorValue[]> = {
  [FieldType.SINGLE_LINE_TEXT]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.CONTAINS,
    FilterOperator.NOT_CONTAINS,
    FilterOperator.STARTS_WITH,
    FilterOperator.ENDS_WITH,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.LONG_TEXT]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.CONTAINS,
    FilterOperator.NOT_CONTAINS,
    FilterOperator.STARTS_WITH,
    FilterOperator.ENDS_WITH,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.RICH_TEXT]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.CONTAINS,
    FilterOperator.NOT_CONTAINS,
    FilterOperator.STARTS_WITH,
    FilterOperator.ENDS_WITH,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.NUMBER]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.GREATER_THAN,
    FilterOperator.LESS_THAN,
    FilterOperator.GREATER_THAN_OR_EQUAL,
    FilterOperator.LESS_THAN_OR_EQUAL,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.DATE]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.IS_BEFORE,
    FilterOperator.IS_AFTER,
    FilterOperator.IS_WITHIN,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.DATE_TIME]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.IS_BEFORE,
    FilterOperator.IS_AFTER,
    FilterOperator.IS_WITHIN,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.SINGLE_SELECT]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.IS_ANY_OF,
    FilterOperator.IS_NONE_OF,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.MULTI_SELECT]: [
    FilterOperator.CONTAINS,
    FilterOperator.NOT_CONTAINS,
    FilterOperator.IS_ANY_OF,
    FilterOperator.IS_NONE_OF,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.CHECKBOX]: [
    FilterOperator.EQUALS,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.EMAIL]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.CONTAINS,
    FilterOperator.NOT_CONTAINS,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.PHONE]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.CONTAINS,
    FilterOperator.NOT_CONTAINS,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.URL]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.CONTAINS,
    FilterOperator.NOT_CONTAINS,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.RATING]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.GREATER_THAN,
    FilterOperator.LESS_THAN,
    FilterOperator.GREATER_THAN_OR_EQUAL,
    FilterOperator.LESS_THAN_OR_EQUAL,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.PROGRESS]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.GREATER_THAN,
    FilterOperator.LESS_THAN,
    FilterOperator.GREATER_THAN_OR_EQUAL,
    FilterOperator.LESS_THAN_OR_EQUAL,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.MEMBER]: [
    FilterOperator.CONTAINS,
    FilterOperator.NOT_CONTAINS,
    FilterOperator.IS_ANY_OF,
    FilterOperator.IS_NONE_OF,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.CREATED_TIME]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.IS_BEFORE,
    FilterOperator.IS_AFTER,
    FilterOperator.IS_WITHIN,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.UPDATED_TIME]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.IS_BEFORE,
    FilterOperator.IS_AFTER,
    FilterOperator.IS_WITHIN,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  [FieldType.AUTO_NUMBER]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.GREATER_THAN,
    FilterOperator.LESS_THAN,
    FilterOperator.GREATER_THAN_OR_EQUAL,
    FilterOperator.LESS_THAN_OR_EQUAL,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  // 关联字段：值为关联记录 ID 数组，按"属于/不属于关联记录"筛选
  [FieldType.LINK]: [
    FilterOperator.IS_ANY_OF,
    FilterOperator.IS_NONE_OF,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  // 查找字段：值由后端注入（原值模式为数组，聚合模式为标量）
  [FieldType.LOOKUP]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.CONTAINS,
    FilterOperator.NOT_CONTAINS,
    FilterOperator.GREATER_THAN,
    FilterOperator.LESS_THAN,
    FilterOperator.GREATER_THAN_OR_EQUAL,
    FilterOperator.LESS_THAN_OR_EQUAL,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
  // 公式字段：按公式结果类型在 getOperatorsForField 中动态分派
  [FieldType.FORMULA]: [
    FilterOperator.EQUALS,
    FilterOperator.NOT_EQUALS,
    FilterOperator.CONTAINS,
    FilterOperator.NOT_CONTAINS,
    FilterOperator.GREATER_THAN,
    FilterOperator.LESS_THAN,
    FilterOperator.GREATER_THAN_OR_EQUAL,
    FilterOperator.LESS_THAN_OR_EQUAL,
    FilterOperator.IS_EMPTY,
    FilterOperator.IS_NOT_EMPTY,
  ],
};

/** 公式字段按结果类型分派操作符（date/datetime 用时间戳数值比较） */
const FORMULA_DATE_OPERATORS: FilterOperatorValue[] = [
  FilterOperator.EQUALS,
  FilterOperator.NOT_EQUALS,
  FilterOperator.GREATER_THAN,
  FilterOperator.LESS_THAN,
  FilterOperator.IS_EMPTY,
  FilterOperator.IS_NOT_EMPTY,
];

export function getOperatorsForFieldType(
  fieldType: string,
): FilterOperatorValue[] {
  return (
    OPERATORS_BY_FIELD_TYPE[fieldType] ||
    OPERATORS_BY_FIELD_TYPE[FieldType.SINGLE_LINE_TEXT]
  );
}

/**
 * 按字段实体获取可用操作符：
 * 公式字段根据公式结果类型（number/date/datetime/text）返回对应操作符组
 */
export function getOperatorsForField(
  field: FieldEntity,
): FilterOperatorValue[] {
  if (field.type === FieldType.FORMULA) {
    const formula = (field.options?.formula ??
      field.config?.formula) as string | undefined;
    const resultType = FormulaEngine.inferResultType(formula || "");
    if (resultType === "number") {
      return OPERATORS_BY_FIELD_TYPE[FieldType.NUMBER];
    }
    if (resultType === "date" || resultType === "datetime") {
      return FORMULA_DATE_OPERATORS;
    }
    return OPERATORS_BY_FIELD_TYPE[FieldType.SINGLE_LINE_TEXT];
  }
  return getOperatorsForFieldType(field.type);
}

export function operatorRequiresValue(operator: FilterOperatorValue): boolean {
  return ![
    FilterOperator.IS_EMPTY as "isEmpty",
    FilterOperator.IS_NOT_EMPTY as "isNotEmpty",
  ].includes(operator as "isEmpty" | "isNotEmpty");
}

function getStringValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean")
    return String(value);
  if (Array.isArray(value)) {
    return value
      .map((v) =>
        typeof v === "object" && v !== null
          ? (v as { name?: string }).name || ""
          : String(v),
      )
      .join(" ");
  }
  if (typeof value === "object" && value !== null) {
    return (value as { name?: string }).name || "";
  }
  return "";
}

function getNumericValue(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return value;
  if (typeof value === "string") {
    // 查找/公式字段的数字值可能经格式化（货币符号、千分位逗号），剥离后再解析
    const cleaned = value.replace(/[¥$€£,]/g, "").trim();
    if (cleaned === "") return null;
    const num = parseFloat(cleaned);
    return isNaN(num) ? null : num;
  }
  return null;
}

function getDateValue(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return value;
  if (typeof value === "string") {
    const s = value.trim();
    // 纯数字字符串为时间戳（如筛选值 ElDatePicker value-format="x" 的毫秒串）
    if (/^\d+$/.test(s)) {
      const n = Number(s);
      // 10 位数字视为秒级时间戳，其余按毫秒处理
      return s.length === 10 ? n * 1000 : n;
    }
    // 纯日期串（YYYY-MM-DD）按本地时区解析：Date.parse 对 date-only 按 UTC 解析，
    // 会与本地时区的筛选值（value-format="x"）相差时区偏移
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
    if (m) {
      return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])).getTime();
    }
    const timestamp = Date.parse(value);
    return isNaN(timestamp) ? null : timestamp;
  }
  return null;
}

function getArrayValue(value: unknown): string[] {
  if (value === null || value === undefined) return [];
  if (Array.isArray(value)) {
    return value
      .map((v) => {
        if (typeof v === "object" && v !== null) {
          return (
            (v as { id?: string; name?: string }).id ||
            (v as { name?: string }).name ||
            ""
          );
        }
        return String(v);
      })
      .filter(Boolean);
  }
  if (typeof value === "object" && value !== null) {
    const id = (value as { id?: string }).id;
    const name = (value as { name?: string }).name;
    if (id) return [id];
    if (name) return [name];
  }
  return [String(value)];
}

/** 数值类字段的静态类型集合 */
const NUMERIC_FIELD_TYPES: string[] = [
  FieldType.NUMBER,
  FieldType.RATING,
  FieldType.PROGRESS,
  FieldType.AUTO_NUMBER,
];

/** 日期类字段的静态类型集合 */
const DATE_FIELD_TYPES: string[] = [
  FieldType.DATE,
  FieldType.DATE_TIME,
  FieldType.CREATED_TIME,
  FieldType.UPDATED_TIME,
];

/** 获取筛选条件的单元格取值：公式字段优先取后端 computed_values，否则前端实时计算 */
function getConditionCellValue(
  record: RecordEntity,
  field: FieldEntity,
  fields: FieldEntity[],
): unknown {
  if (field.type === FieldType.FORMULA) {
    const computedValues = (
      record as RecordEntity & { computed_values?: Record<string, unknown> }
    ).computed_values;
    if (computedValues && typeof computedValues === "object") {
      const precomputed = computedValues[field.name];
      if (precomputed !== null && precomputed !== undefined) {
        return precomputed;
      }
    }
    const formula = (field.options?.formula ??
      field.config?.formula) as string | undefined;
    if (!formula) return null;
    try {
      const engine = new FormulaEngine(fields);
      const result = engine.calculate(record, formula);
      // FormulaError（对象）视为无值
      if (result !== null && typeof result === "object") return null;
      return result;
    } catch {
      return null;
    }
  }
  return record.values[field.id];
}

/** 值是否为日期格式字符串（如 "2026-01-01..."），此类字符串不可按数值解析 */
function isDateString(value: unknown): boolean {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}/.test(value);
}

/**
 * 数组值与筛选值的比较（查找字段原值模式返回数组）：
 * 任一元素满足比较条件即命中；数字元素优先，无数字元素时尝试日期字符串元素
 */
function arrayValueMatches(
  cellValue: unknown[],
  filterValue: unknown,
  cmp: (a: number, b: number) => boolean,
): boolean {
  // 日期格式的筛选值/元素不可按数值解析（"2026-01-01" 会被 parseFloat 解析为 2026）
  const numFilter = isDateString(filterValue)
    ? null
    : getNumericValue(filterValue);
  if (numFilter !== null) {
    const nums = cellValue
      .filter((v) => !isDateString(v))
      .map((v) => getNumericValue(v))
      .filter((n): n is number => n !== null);
    if (nums.length > 0) {
      return nums.some((n) => cmp(n, numFilter));
    }
  }
  const dateFilter = getDateValue(filterValue);
  if (dateFilter !== null) {
    const dates = cellValue
      .filter((v) => isDateString(v))
      .map((v) => getDateValue(v))
      .filter((n): n is number => n !== null);
    if (dates.length > 0) {
      return dates.some((n) => cmp(n, dateFilter));
    }
  }
  return false;
}

/** 是否按数值比较：数值类字段恒定；查找/公式字段在值为数字或可解析的数字字符串时（含日期时间戳）按数值比较 */
function isNumericCompare(field: FieldEntity, cellValue: unknown): boolean {
  if (NUMERIC_FIELD_TYPES.includes(field.type)) return true;
  if (field.type === FieldType.LOOKUP || field.type === FieldType.FORMULA) {
    if (typeof cellValue === "number") return true;
    // 后端查找字段聚合值经格式化后为字符串（如 "30"、"¥1,234.50"），可解析为数字时也按数值比较
    return !isDateString(cellValue) && getNumericValue(cellValue) !== null;
  }
  return false;
}

/** 是否按日期比较：日期类字段恒定；查找/公式字段在值为日期字符串时按日期比较 */
function isDateCompare(field: FieldEntity, cellValue: unknown): boolean {
  if (DATE_FIELD_TYPES.includes(field.type)) return true;
  if (field.type === FieldType.LOOKUP || field.type === FieldType.FORMULA) {
    return isDateString(cellValue);
  }
  return false;
}

export function evaluateCondition(
  record: RecordEntity,
  condition: FilterCondition,
  fields: FieldEntity[],
): boolean {
  const field = fields.find((f) => f.id === condition.fieldId);
  if (!field) return true;

  const cellValue = getConditionCellValue(record, field, fields);
  const operator = condition.operator;
  const filterValue = condition.value;

  switch (operator) {
    case FilterOperator.IS_EMPTY:
      return (
        cellValue === null ||
        cellValue === undefined ||
        cellValue === "" ||
        (Array.isArray(cellValue) && cellValue.length === 0)
      );

    case FilterOperator.IS_NOT_EMPTY:
      return (
        cellValue !== null &&
        cellValue !== undefined &&
        cellValue !== "" &&
        !(Array.isArray(cellValue) && cellValue.length === 0)
      );

    case FilterOperator.EQUALS: {
      // 数组值（成员/关联/多选/查找原值模式）：包含任一筛选值即视为相等
      if (Array.isArray(cellValue)) {
        const arrVal = getArrayValue(cellValue);
        const filterArr = getArrayValue(filterValue);
        return filterArr.some((fv) => arrVal.includes(fv));
      }
      if (isNumericCompare(field, cellValue)) {
        const numVal = getNumericValue(cellValue);
        const numFilter = getNumericValue(filterValue);
        return numVal !== null && numFilter !== null && numVal === numFilter;
      }
      if (isDateCompare(field, cellValue)) {
        const dateVal = getDateValue(cellValue);
        const dateFilter = getDateValue(filterValue);
        return (
          dateVal !== null && dateFilter !== null && dateVal === dateFilter
        );
      }
      if (field.type === FieldType.CHECKBOX) {
        return !!cellValue === !!filterValue;
      }
      if (field.type === FieldType.SINGLE_SELECT) {
        const cellId =
          typeof cellValue === "object" && cellValue !== null
            ? (cellValue as { id?: string }).id
            : cellValue;
        const filterId =
          typeof filterValue === "object" && filterValue !== null
            ? (filterValue as { id?: string }).id
            : filterValue;
        return cellId === filterId;
      }
      return (
        getStringValue(cellValue).toLowerCase() ===
        getStringValue(filterValue).toLowerCase()
      );
    }

    case FilterOperator.NOT_EQUALS: {
      // 数组值：不包含任一筛选值即视为不等
      if (Array.isArray(cellValue)) {
        const arrVal = getArrayValue(cellValue);
        const filterArr = getArrayValue(filterValue);
        return !filterArr.some((fv) => arrVal.includes(fv));
      }
      if (isNumericCompare(field, cellValue)) {
        const numVal = getNumericValue(cellValue);
        const numFilter = getNumericValue(filterValue);
        return numVal === null || numFilter === null || numVal !== numFilter;
      }
      if (isDateCompare(field, cellValue)) {
        const dateVal = getDateValue(cellValue);
        const dateFilter = getDateValue(filterValue);
        return (
          dateVal === null || dateFilter === null || dateVal !== dateFilter
        );
      }
      if (field.type === FieldType.CHECKBOX) {
        return !!cellValue !== !!filterValue;
      }
      if (field.type === FieldType.SINGLE_SELECT) {
        const cellId =
          typeof cellValue === "object" && cellValue !== null
            ? (cellValue as { id?: string }).id
            : cellValue;
        const filterId =
          typeof filterValue === "object" && filterValue !== null
            ? (filterValue as { id?: string }).id
            : filterValue;
        return cellId !== filterId;
      }
      return (
        getStringValue(cellValue).toLowerCase() !==
        getStringValue(filterValue).toLowerCase()
      );
    }

    case FilterOperator.CONTAINS: {
      // 数组值（多选/成员/关联/查找原值模式）：交集判断
      if (Array.isArray(cellValue)) {
        const arrVal = getArrayValue(cellValue);
        const filterArr = getArrayValue(filterValue);
        return filterArr.some((fv) => arrVal.includes(fv));
      }
      const strVal = getStringValue(cellValue).toLowerCase();
      const filterStr = getStringValue(filterValue).toLowerCase();
      return strVal.includes(filterStr);
    }

    case FilterOperator.NOT_CONTAINS: {
      // 数组值（多选/成员/关联/查找原值模式）：无交集判断
      if (Array.isArray(cellValue)) {
        const arrVal = getArrayValue(cellValue);
        const filterArr = getArrayValue(filterValue);
        return !filterArr.some((fv) => arrVal.includes(fv));
      }
      const strVal = getStringValue(cellValue).toLowerCase();
      const filterStr = getStringValue(filterValue).toLowerCase();
      return !strVal.includes(filterStr);
    }

    case FilterOperator.STARTS_WITH: {
      const strVal = getStringValue(cellValue).toLowerCase();
      const filterStr = getStringValue(filterValue).toLowerCase();
      return strVal.startsWith(filterStr);
    }

    case FilterOperator.ENDS_WITH: {
      const strVal = getStringValue(cellValue).toLowerCase();
      const filterStr = getStringValue(filterValue).toLowerCase();
      return strVal.endsWith(filterStr);
    }

    case FilterOperator.GREATER_THAN: {
      // 数组值（查找字段原值模式）：任一元素满足即命中
      if (Array.isArray(cellValue)) {
        return arrayValueMatches(cellValue, filterValue, (a, b) => a > b);
      }
      if (isNumericCompare(field, cellValue)) {
        const numVal = getNumericValue(cellValue);
        const numFilter = getNumericValue(filterValue);
        return numVal !== null && numFilter !== null && numVal > numFilter;
      }
      if (isDateCompare(field, cellValue)) {
        const dateVal = getDateValue(cellValue);
        const dateFilter = getDateValue(filterValue);
        return dateVal !== null && dateFilter !== null && dateVal > dateFilter;
      }
      return false;
    }

    case FilterOperator.LESS_THAN: {
      // 数组值（查找字段原值模式）：任一元素满足即命中
      if (Array.isArray(cellValue)) {
        return arrayValueMatches(cellValue, filterValue, (a, b) => a < b);
      }
      if (isNumericCompare(field, cellValue)) {
        const numVal = getNumericValue(cellValue);
        const numFilter = getNumericValue(filterValue);
        return numVal !== null && numFilter !== null && numVal < numFilter;
      }
      if (isDateCompare(field, cellValue)) {
        const dateVal = getDateValue(cellValue);
        const dateFilter = getDateValue(filterValue);
        return dateVal !== null && dateFilter !== null && dateVal < dateFilter;
      }
      return false;
    }

    case FilterOperator.GREATER_THAN_OR_EQUAL: {
      // 数组值（查找字段原值模式）：任一元素满足即命中
      if (Array.isArray(cellValue)) {
        return arrayValueMatches(cellValue, filterValue, (a, b) => a >= b);
      }
      if (isNumericCompare(field, cellValue)) {
        const numVal = getNumericValue(cellValue);
        const numFilter = getNumericValue(filterValue);
        return numVal !== null && numFilter !== null && numVal >= numFilter;
      }
      if (isDateCompare(field, cellValue)) {
        const dateVal = getDateValue(cellValue);
        const dateFilter = getDateValue(filterValue);
        return dateVal !== null && dateFilter !== null && dateVal >= dateFilter;
      }
      return false;
    }

    case FilterOperator.LESS_THAN_OR_EQUAL: {
      // 数组值（查找字段原值模式）：任一元素满足即命中
      if (Array.isArray(cellValue)) {
        return arrayValueMatches(cellValue, filterValue, (a, b) => a <= b);
      }
      if (isNumericCompare(field, cellValue)) {
        const numVal = getNumericValue(cellValue);
        const numFilter = getNumericValue(filterValue);
        return numVal !== null && numFilter !== null && numVal <= numFilter;
      }
      if (isDateCompare(field, cellValue)) {
        const dateVal = getDateValue(cellValue);
        const dateFilter = getDateValue(filterValue);
        return dateVal !== null && dateFilter !== null && dateVal <= dateFilter;
      }
      return false;
    }

    case FilterOperator.IS_BEFORE: {
      const dateVal = getDateValue(cellValue);
      const dateFilter = getDateValue(filterValue);
      return dateVal !== null && dateFilter !== null && dateVal < dateFilter;
    }

    case FilterOperator.IS_AFTER: {
      const dateVal = getDateValue(cellValue);
      const dateFilter = getDateValue(filterValue);
      return dateVal !== null && dateFilter !== null && dateVal > dateFilter;
    }

    case FilterOperator.IS_WITHIN: {
      const dateVal = getDateValue(cellValue);
      if (dateVal === null) return false;

      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const todayStart = today.getTime();

      const rangeValue = String(filterValue);
      let rangeStart: number;
      let rangeEnd: number;

      switch (rangeValue) {
        case "today":
          rangeStart = todayStart;
          rangeEnd = todayStart + 24 * 60 * 60 * 1000;
          break;
        case "yesterday": {
          rangeStart = todayStart - 24 * 60 * 60 * 1000;
          rangeEnd = todayStart;
          break;
        }
        case "tomorrow":
          rangeStart = todayStart + 24 * 60 * 60 * 1000;
          rangeEnd = todayStart + 48 * 60 * 60 * 1000;
          break;
        case "thisWeek": {
          const dayOfWeek = today.getDay();
          const weekStart = todayStart - dayOfWeek * 24 * 60 * 60 * 1000;
          rangeStart = weekStart;
          rangeEnd = weekStart + 7 * 24 * 60 * 60 * 1000;
          break;
        }
        case "lastWeek": {
          const dayOfWeek = today.getDay();
          const thisWeekStart = todayStart - dayOfWeek * 24 * 60 * 60 * 1000;
          rangeStart = thisWeekStart - 7 * 24 * 60 * 60 * 1000;
          rangeEnd = thisWeekStart;
          break;
        }
        case "nextWeek": {
          const dayOfWeek = today.getDay();
          const thisWeekStart = todayStart - dayOfWeek * 24 * 60 * 60 * 1000;
          rangeStart = thisWeekStart + 7 * 24 * 60 * 60 * 1000;
          rangeEnd = thisWeekStart + 14 * 24 * 60 * 60 * 1000;
          break;
        }
        case "thisMonth": {
          const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
          rangeStart = monthStart.getTime();
          const monthEnd = new Date(
            today.getFullYear(),
            today.getMonth() + 1,
            1,
          );
          rangeEnd = monthEnd.getTime();
          break;
        }
        case "lastMonth": {
          const lastMonthStart = new Date(
            today.getFullYear(),
            today.getMonth() - 1,
            1,
          );
          rangeStart = lastMonthStart.getTime();
          const thisMonthStart = new Date(
            today.getFullYear(),
            today.getMonth(),
            1,
          );
          rangeEnd = thisMonthStart.getTime();
          break;
        }
        case "nextMonth": {
          const nextMonthStart = new Date(
            today.getFullYear(),
            today.getMonth() + 1,
            1,
          );
          rangeStart = nextMonthStart.getTime();
          const nextMonthEnd = new Date(
            today.getFullYear(),
            today.getMonth() + 2,
            1,
          );
          rangeEnd = nextMonthEnd.getTime();
          break;
        }
        case "thisYear": {
          const yearStart = new Date(today.getFullYear(), 0, 1);
          rangeStart = yearStart.getTime();
          const yearEnd = new Date(today.getFullYear() + 1, 0, 1);
          rangeEnd = yearEnd.getTime();
          break;
        }
        default:
          if (Array.isArray(filterValue) && filterValue.length === 2) {
            rangeStart = getDateValue(filterValue[0]) || 0;
            rangeEnd = getDateValue(filterValue[1]) || 0;
          } else {
            return false;
          }
      }

      return dateVal >= rangeStart && dateVal < rangeEnd;
    }

    case FilterOperator.IS_ANY_OF: {
      const arrVal = getArrayValue(cellValue);
      const filterArr = Array.isArray(filterValue)
        ? filterValue.map((v) =>
            typeof v === "object" && v !== null
              ? (v as { id?: string }).id || String(v)
              : String(v),
          )
        : [
            typeof filterValue === "object" && filterValue !== null
              ? (filterValue as { id?: string }).id || String(filterValue)
              : String(filterValue),
          ];
      return arrVal.some((v) => filterArr.includes(v));
    }

    case FilterOperator.IS_NONE_OF: {
      const arrVal = getArrayValue(cellValue);
      const filterArr = Array.isArray(filterValue)
        ? filterValue.map((v) =>
            typeof v === "object" && v !== null
              ? (v as { id?: string }).id || String(v)
              : String(v),
          )
        : [
            typeof filterValue === "object" && filterValue !== null
              ? (filterValue as { id?: string }).id || String(filterValue)
              : String(filterValue),
          ];
      return !arrVal.some((v) => filterArr.includes(v));
    }

    default:
      return true;
  }
}

export function evaluateFilterGroup(
  record: RecordEntity,
  filterGroup: FilterGroup,
  fields: FieldEntity[],
): boolean {
  if (!filterGroup.conditions || filterGroup.conditions.length === 0) {
    return true;
  }

  const results = filterGroup.conditions.map((condition) =>
    evaluateCondition(record, condition, fields),
  );

  if (filterGroup.conjunction === "and") {
    return results.every(Boolean);
  } else {
    return results.some(Boolean);
  }
}

export function filterRecords(
  records: RecordEntity[],
  filterGroup: FilterGroup,
  fields: FieldEntity[],
): RecordEntity[] {
  return records.filter((record) =>
    evaluateFilterGroup(record, filterGroup, fields),
  );
}

export function createEmptyCondition(fieldId: string): FilterCondition {
  return {
    fieldId,
    operator: FilterOperator.EQUALS,
    value: null,
  };
}

export function isValidCondition(condition: FilterCondition): boolean {
  if (!condition.fieldId || !condition.operator) {
    return false;
  }

  if (operatorRequiresValue(condition.operator)) {
    return (
      condition.value !== undefined &&
      condition.value !== null &&
      condition.value !== ""
    );
  }

  return true;
}

export function getConditionDescription(
  condition: FilterCondition,
  fields: FieldEntity[],
): string {
  const field = fields.find((f) => f.id === condition.fieldId);
  if (!field) return "";

  const operatorLabel = getOperatorLabel(condition.operator);

  if (!operatorRequiresValue(condition.operator)) {
    return `${field.name} ${operatorLabel}`;
  }

  let valueStr = "";
  if (condition.value !== undefined && condition.value !== null) {
    if (Array.isArray(condition.value)) {
      valueStr = condition.value
        .map((v) =>
          typeof v === "object" && v !== null
            ? (v as { name?: string }).name || ""
            : String(v),
        )
        .join(", ");
    } else if (typeof condition.value === "object") {
      valueStr =
        (condition.value as { name?: string }).name || String(condition.value);
    } else {
      valueStr = String(condition.value);
    }
  }

  return `${field.name} ${operatorLabel} ${valueStr}`;
}

export function applyFilter(
  records: RecordEntity[],
  condition: FilterCondition,
  fields: FieldEntity[],
): RecordEntity[] {
  return records.filter((record) =>
    evaluateCondition(record, condition, fields),
  );
}

export function applyFilters(
  records: RecordEntity[],
  conditions: FilterCondition[],
  fields: FieldEntity[],
  conjunction: "and" | "or" = "and",
): RecordEntity[] {
  return records.filter((record) => {
    const results = conditions.map((condition) =>
      evaluateCondition(record, condition, fields),
    );
    return conjunction === "and"
      ? results.every(Boolean)
      : results.some(Boolean);
  });
}
