import type {
  FilterCondition,
  FilterOperatorValue,
  FilterGroup,
} from "../types";
import type { FieldEntity, RecordEntity } from "../db/schema";
import { FilterOperator, FieldType } from "../types";

export const OPERATOR_LABELS: Record<FilterOperatorValue, string> = {
  [FilterOperator.EQUALS]: "等于",
  [FilterOperator.NOT_EQUALS]: "不等于",
  [FilterOperator.CONTAINS]: "包含",
  [FilterOperator.NOT_CONTAINS]: "不包含",
  [FilterOperator.STARTS_WITH]: "开头为",
  [FilterOperator.ENDS_WITH]: "结尾为",
  [FilterOperator.IS_EMPTY]: "为空",
  [FilterOperator.IS_NOT_EMPTY]: "不为空",
  [FilterOperator.GREATER_THAN]: "大于",
  [FilterOperator.LESS_THAN]: "小于",
  [FilterOperator.GREATER_THAN_OR_EQUAL]: "大于等于",
  [FilterOperator.LESS_THAN_OR_EQUAL]: "小于等于",
  [FilterOperator.IS_WITHIN]: "在范围内",
  [FilterOperator.IS_BEFORE]: "早于",
  [FilterOperator.IS_AFTER]: "晚于",
  [FilterOperator.IS_ANY_OF]: "属于",
  [FilterOperator.IS_NONE_OF]: "不属于",
};

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
};

export function getOperatorsForFieldType(
  fieldType: string,
): FilterOperatorValue[] {
  return (
    OPERATORS_BY_FIELD_TYPE[fieldType] ||
    OPERATORS_BY_FIELD_TYPE[FieldType.SINGLE_LINE_TEXT]
  );
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
    const num = parseFloat(value);
    return isNaN(num) ? null : num;
  }
  return null;
}

function getDateValue(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return value;
  if (typeof value === "string") {
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

export function evaluateCondition(
  record: RecordEntity,
  condition: FilterCondition,
  fields: FieldEntity[],
): boolean {
  const field = fields.find((f) => f.id === condition.fieldId);
  if (!field) return true;

  const cellValue = record.values[condition.fieldId];
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
      if (
        field.type === FieldType.NUMBER ||
        field.type === FieldType.RATING ||
        field.type === FieldType.PROGRESS
      ) {
        const numVal = getNumericValue(cellValue);
        const numFilter = getNumericValue(filterValue);
        return numVal !== null && numFilter !== null && numVal === numFilter;
      }
      if (
        field.type === FieldType.DATE ||
        field.type === FieldType.CREATED_TIME ||
        field.type === FieldType.UPDATED_TIME
      ) {
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
      if (
        field.type === FieldType.NUMBER ||
        field.type === FieldType.RATING ||
        field.type === FieldType.PROGRESS
      ) {
        const numVal = getNumericValue(cellValue);
        const numFilter = getNumericValue(filterValue);
        return numVal === null || numFilter === null || numVal !== numFilter;
      }
      if (
        field.type === FieldType.DATE ||
        field.type === FieldType.CREATED_TIME ||
        field.type === FieldType.UPDATED_TIME
      ) {
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
      const strVal = getStringValue(cellValue).toLowerCase();
      const filterStr = getStringValue(filterValue).toLowerCase();
      if (
        field.type === FieldType.MULTI_SELECT ||
        field.type === FieldType.MEMBER
      ) {
        const arrVal = getArrayValue(cellValue);
        const filterArr = getArrayValue(filterValue);
        return filterArr.some((fv) => arrVal.includes(fv));
      }
      return strVal.includes(filterStr);
    }

    case FilterOperator.NOT_CONTAINS: {
      const strVal = getStringValue(cellValue).toLowerCase();
      const filterStr = getStringValue(filterValue).toLowerCase();
      if (
        field.type === FieldType.MULTI_SELECT ||
        field.type === FieldType.MEMBER
      ) {
        const arrVal = getArrayValue(cellValue);
        const filterArr = getArrayValue(filterValue);
        return !filterArr.some((fv) => arrVal.includes(fv));
      }
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
      if (
        field.type === FieldType.NUMBER ||
        field.type === FieldType.RATING ||
        field.type === FieldType.PROGRESS ||
        field.type === FieldType.AUTO_NUMBER
      ) {
        const numVal = getNumericValue(cellValue);
        const numFilter = getNumericValue(filterValue);
        return numVal !== null && numFilter !== null && numVal > numFilter;
      }
      if (
        field.type === FieldType.DATE ||
        field.type === FieldType.CREATED_TIME ||
        field.type === FieldType.UPDATED_TIME
      ) {
        const dateVal = getDateValue(cellValue);
        const dateFilter = getDateValue(filterValue);
        return dateVal !== null && dateFilter !== null && dateVal > dateFilter;
      }
      return false;
    }

    case FilterOperator.LESS_THAN: {
      if (
        field.type === FieldType.NUMBER ||
        field.type === FieldType.RATING ||
        field.type === FieldType.PROGRESS ||
        field.type === FieldType.AUTO_NUMBER
      ) {
        const numVal = getNumericValue(cellValue);
        const numFilter = getNumericValue(filterValue);
        return numVal !== null && numFilter !== null && numVal < numFilter;
      }
      if (
        field.type === FieldType.DATE ||
        field.type === FieldType.CREATED_TIME ||
        field.type === FieldType.UPDATED_TIME
      ) {
        const dateVal = getDateValue(cellValue);
        const dateFilter = getDateValue(filterValue);
        return dateVal !== null && dateFilter !== null && dateVal < dateFilter;
      }
      return false;
    }

    case FilterOperator.GREATER_THAN_OR_EQUAL: {
      if (
        field.type === FieldType.NUMBER ||
        field.type === FieldType.RATING ||
        field.type === FieldType.PROGRESS ||
        field.type === FieldType.AUTO_NUMBER
      ) {
        const numVal = getNumericValue(cellValue);
        const numFilter = getNumericValue(filterValue);
        return numVal !== null && numFilter !== null && numVal >= numFilter;
      }
      if (
        field.type === FieldType.DATE ||
        field.type === FieldType.CREATED_TIME ||
        field.type === FieldType.UPDATED_TIME
      ) {
        const dateVal = getDateValue(cellValue);
        const dateFilter = getDateValue(filterValue);
        return dateVal !== null && dateFilter !== null && dateVal >= dateFilter;
      }
      return false;
    }

    case FilterOperator.LESS_THAN_OR_EQUAL: {
      if (
        field.type === FieldType.NUMBER ||
        field.type === FieldType.RATING ||
        field.type === FieldType.PROGRESS ||
        field.type === FieldType.AUTO_NUMBER
      ) {
        const numVal = getNumericValue(cellValue);
        const numFilter = getNumericValue(filterValue);
        return numVal !== null && numFilter !== null && numVal <= numFilter;
      }
      if (
        field.type === FieldType.DATE ||
        field.type === FieldType.CREATED_TIME ||
        field.type === FieldType.UPDATED_TIME
      ) {
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

  const operatorLabel =
    OPERATOR_LABELS[condition.operator] || condition.operator;

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
