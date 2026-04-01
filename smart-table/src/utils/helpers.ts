import type { CellValue } from "../types";
import type { FieldEntity } from "../db/schema";

export function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

export function isEqual(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function pick<T extends object, K extends keyof T>(
  obj: T,
  keys: K[],
): Pick<T, K> {
  const result = {} as Pick<T, K>;
  for (const key of keys) {
    if (key in obj) {
      result[key] = obj[key];
    }
  }
  return result;
}

export function omit<T extends object, K extends keyof T>(
  obj: T,
  keys: K[],
): Omit<T, K> {
  const result = { ...obj };
  for (const key of keys) {
    delete result[key];
  }
  return result;
}

export function groupBy<T>(
  array: T[],
  keyFn: (item: T) => string,
): Record<string, T[]> {
  return array.reduce(
    (groups, item) => {
      const key = keyFn(item);
      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(item);
      return groups;
    },
    {} as Record<string, T[]>,
  );
}

export function sortBy<T>(
  array: T[],
  keyFn: (item: T) => unknown,
  order: "asc" | "desc" = "asc",
): T[] {
  return [...array].sort((a, b) => {
    const aVal = keyFn(a);
    const bVal = keyFn(b);

    if (aVal === bVal) return 0;
    if (aVal === null || aVal === undefined) return 1;
    if (bVal === null || bVal === undefined) return -1;

    const comparison = aVal < bVal ? -1 : 1;
    return order === "asc" ? comparison : -comparison;
  });
}

export function uniqBy<T>(array: T[], keyFn: (item: T) => unknown): T[] {
  const seen = new Set<unknown>();
  return array.filter((item) => {
    const key = keyFn(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function chunk<T>(array: T[], size: number): T[][] {
  const result: T[][] = [];
  for (let i = 0; i < array.length; i += size) {
    result.push(array.slice(i, i + size));
  }
  return result;
}

export function getValueByPath(
  obj: Record<string, unknown>,
  path: string,
): unknown {
  return path.split(".").reduce((current: unknown, key) => {
    if (current && typeof current === "object") {
      return (current as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}

export function setValueByPath(
  obj: Record<string, unknown>,
  path: string,
  value: unknown,
): void {
  const keys = path.split(".");
  const lastKey = keys.pop()!;
  const target = keys.reduce((current, key) => {
    if (!(key in current)) {
      current[key] = {} as Record<string, unknown>;
    }
    return current[key] as Record<string, unknown>;
  }, obj);
  target[lastKey] = value;
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

export function formatDate(
  timestamp: number,
  format: string = "YYYY-MM-DD",
): string {
  const date = new Date(timestamp);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");

  return format
    .replace("YYYY", String(year))
    .replace("MM", month)
    .replace("DD", day)
    .replace("HH", hours)
    .replace("mm", minutes)
    .replace("ss", seconds);
}

export function generateColor(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = seed.charCodeAt(i) + ((hash << 5) - hash);
  }

  const hue = hash % 360;
  return `hsl(${hue}, 65%, 50%)`;
}

export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.substring(0, maxLength - 3) + "...";
}

export function getCellDisplayValue(
  value: CellValue,
  field: FieldEntity,
): string {
  if (value === null || value === undefined) return "";

  switch (field.type) {
    case "checkbox":
      return value ? "是" : "否";

    case "multiSelect":
      if (Array.isArray(value)) {
        return value
          .map((v) =>
            typeof v === "object" ? (v as { name: string }).name : v,
          )
          .join(", ");
      }
      return String(value);

    case "date":
      return formatDate(Number(value), "YYYY-MM-DD");

    case "attachment":
      if (Array.isArray(value)) {
        return `${value.length} 个附件`;
      }
      return "";

    case "singleSelect":
      if (
        typeof value === "object" &&
        value !== null &&
        !Array.isArray(value)
      ) {
        return (value as { name: string }).name;
      }
      return String(value);

    default:
      return String(value);
  }
}

// 清新配色方案 - 用于仪表盘等组件
export const freshColors = {
  primary: "#3B82F6",
  primaryLight: "#EFF6FF",
  success: "#10B981",
  warning: "#F59E0B",
  danger: "#EF4444",
  gray50: "#F9FAFB",
  gray100: "#F3F4F6",
  gray200: "#E5E7EB",
  gray300: "#D1D5DB",
  gray400: "#9CA3AF",
  gray500: "#6B7280",
  gray600: "#4B5563",
  gray700: "#374151",
  gray800: "#1F2937",
};
