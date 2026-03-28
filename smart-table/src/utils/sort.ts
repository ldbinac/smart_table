import type { SortConfig, SortDirectionValue } from "../types";
import type { FieldEntity, RecordEntity } from "../db/schema";
import { SortDirection, FieldType } from "../types";

export function sortRecords(
  records: RecordEntity[],
  sorts: SortConfig[],
  fields: FieldEntity[],
): RecordEntity[] {
  if (!sorts || sorts.length === 0) {
    return [...records];
  }

  return [...records].sort((a, b) => {
    for (const sort of sorts) {
      const field = fields.find((f) => f.id === sort.fieldId);
      if (!field) continue;

      const comparison = compareValues(
        a.values[sort.fieldId],
        b.values[sort.fieldId],
        field,
        sort.direction,
      );

      if (comparison !== 0) {
        return comparison;
      }
    }
    return 0;
  });
}

function compareValues(
  aVal: unknown,
  bVal: unknown,
  field: FieldEntity,
  direction: SortDirectionValue,
): number {
  const nullComparison = compareNullValues(aVal, bVal, direction);
  if (nullComparison !== null) {
    return nullComparison;
  }

  let comparison = 0;

  switch (field.type) {
    case FieldType.NUMBER:
    case FieldType.RATING:
    case FieldType.PROGRESS:
    case FieldType.AUTO_NUMBER:
      comparison = compareNumbers(aVal, bVal);
      break;

    case FieldType.DATE:
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_TIME:
      comparison = compareDates(aVal, bVal);
      break;

    case FieldType.CHECKBOX:
      comparison = compareBooleans(aVal, bVal);
      break;

    case FieldType.SINGLE_SELECT:
      comparison = compareSingleSelect(aVal, bVal, field);
      break;

    case FieldType.MULTI_SELECT:
      comparison = compareMultiSelect(aVal, bVal);
      break;

    default:
      comparison = compareStrings(aVal, bVal);
  }

  return direction === SortDirection.ASC ? comparison : -comparison;
}

function compareNullValues(
  aVal: unknown,
  bVal: unknown,
  direction: SortDirectionValue,
): number | null {
  const aIsNull =
    aVal === null ||
    aVal === undefined ||
    aVal === "" ||
    (Array.isArray(aVal) && aVal.length === 0);
  const bIsNull =
    bVal === null ||
    bVal === undefined ||
    bVal === "" ||
    (Array.isArray(bVal) && bVal.length === 0);

  if (aIsNull && bIsNull) return 0;
  if (aIsNull) return direction === SortDirection.ASC ? 1 : -1;
  if (bIsNull) return direction === SortDirection.ASC ? -1 : 1;

  return null;
}

function compareNumbers(aVal: unknown, bVal: unknown): number {
  const aNum = toNumber(aVal);
  const bNum = toNumber(bVal);

  if (aNum === null && bNum === null) return 0;
  if (aNum === null) return 1;
  if (bNum === null) return -1;

  return aNum - bNum;
}

function compareDates(aVal: unknown, bVal: unknown): number {
  const aDate = toDate(aVal);
  const bDate = toDate(bVal);

  if (aDate === null && bDate === null) return 0;
  if (aDate === null) return 1;
  if (bDate === null) return -1;

  return aDate - bDate;
}

function compareStrings(aVal: unknown, bVal: unknown): number {
  const aStr = toString(aVal).toLowerCase();
  const bStr = toString(bVal).toLowerCase();

  return aStr.localeCompare(bStr, "zh-CN");
}

function compareBooleans(aVal: unknown, bVal: unknown): number {
  const aBool = !!aVal;
  const bBool = !!bVal;

  if (aBool === bBool) return 0;
  return aBool ? -1 : 1;
}

function compareSingleSelect(
  aVal: unknown,
  bVal: unknown,
  field: FieldEntity,
): number {
  const aName = getSelectName(aVal);
  const bName = getSelectName(bVal);

  const options = field.options?.options as
    | Array<{ id: string; name: string }>
    | undefined;
  if (options && options.length > 0) {
    const aIndex = options.findIndex(
      (opt) => opt.id === aVal || opt.name === aName,
    );
    const bIndex = options.findIndex(
      (opt) => opt.id === bVal || opt.name === bName,
    );

    if (aIndex !== -1 && bIndex !== -1) {
      return aIndex - bIndex;
    }
  }

  return aName.localeCompare(bName, "zh-CN");
}

function compareMultiSelect(aVal: unknown, bVal: unknown): number {
  const aArr = toArray(aVal);
  const bArr = toArray(bVal);

  if (aArr.length === 0 && bArr.length === 0) return 0;
  if (aArr.length === 0) return 1;
  if (bArr.length === 0) return -1;

  const aStr = aArr.join(",").toLowerCase();
  const bStr = bArr.join(",").toLowerCase();

  return aStr.localeCompare(bStr, "zh-CN");
}

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return value;
  if (typeof value === "string") {
    const num = parseFloat(value);
    return isNaN(num) ? null : num;
  }
  return null;
}

function toDate(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return value;
  if (typeof value === "string") {
    const timestamp = Date.parse(value);
    return isNaN(timestamp) ? null : timestamp;
  }
  return null;
}

function toString(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean")
    return String(value);
  if (Array.isArray(value)) {
    return value.map((v) => toString(v)).join(" ");
  }
  if (typeof value === "object") {
    return (value as { name?: string }).name || JSON.stringify(value);
  }
  return "";
}

function getSelectName(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "object" && value !== null) {
    return (value as { name?: string }).name || "";
  }
  return "";
}

function toArray(value: unknown): string[] {
  if (value === null || value === undefined) return [];
  if (Array.isArray(value)) {
    return value
      .map((v) => {
        if (typeof v === "object" && v !== null) {
          return (v as { name?: string }).name || "";
        }
        return String(v);
      })
      .filter(Boolean);
  }
  return [toString(value)];
}

export function createSortConfig(
  fieldId: string,
  direction: SortDirectionValue = SortDirection.ASC,
): SortConfig {
  return { fieldId, direction };
}

export function toggleSortDirection(
  direction: SortDirectionValue,
): SortDirectionValue {
  return direction === SortDirection.ASC
    ? SortDirection.DESC
    : SortDirection.ASC;
}

export function updateSorts(
  sorts: SortConfig[],
  fieldId: string,
  multiSort: boolean = false,
): SortConfig[] {
  const existingIndex = sorts.findIndex((s) => s.fieldId === fieldId);

  if (existingIndex === -1) {
    const newSort = createSortConfig(fieldId);
    return multiSort ? [...sorts, newSort] : [newSort];
  }

  const existingSort = sorts[existingIndex];

  if (existingSort.direction === SortDirection.ASC) {
    const updated = { ...existingSort, direction: SortDirection.DESC };
    const newSorts = [...sorts];
    newSorts[existingIndex] = updated;
    return newSorts;
  } else {
    const newSorts = sorts.filter((_, index) => index !== existingIndex);
    return multiSort ? newSorts : [];
  }
}

export function getSortDirection(
  sorts: SortConfig[],
  fieldId: string,
): SortDirectionValue | null {
  const sort = sorts.find((s) => s.fieldId === fieldId);
  return sort ? sort.direction : null;
}

export function getSortIndex(sorts: SortConfig[], fieldId: string): number {
  return sorts.findIndex((s) => s.fieldId === fieldId);
}

export function reorderSorts(
  sorts: SortConfig[],
  fromIndex: number,
  toIndex: number,
): SortConfig[] {
  const newSorts = [...sorts];
  const [removed] = newSorts.splice(fromIndex, 1);
  newSorts.splice(toIndex, 0, removed);
  return newSorts;
}

export function removeSort(sorts: SortConfig[], fieldId: string): SortConfig[] {
  return sorts.filter((s) => s.fieldId !== fieldId);
}

export function clearSorts(): SortConfig[] {
  return [];
}

export function getSortDescription(
  sort: SortConfig,
  fields: FieldEntity[],
): string {
  const field = fields.find((f) => f.id === sort.fieldId);
  if (!field) return "";

  const directionLabel = sort.direction === SortDirection.ASC ? "升序" : "降序";
  return `${field.name} ${directionLabel}`;
}

export function applySort(
  records: RecordEntity[],
  sort: SortConfig,
  fields: FieldEntity[],
): RecordEntity[] {
  return sortRecords(records, [sort], fields);
}

export function applySorts(
  records: RecordEntity[],
  sorts: SortConfig[],
  fields: FieldEntity[],
): RecordEntity[] {
  return sortRecords(records, sorts, fields);
}
