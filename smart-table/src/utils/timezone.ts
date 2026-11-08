import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";
import relativeTime from "dayjs/plugin/relativeTime";
import "dayjs/locale/zh-cn";
import { useAdminStore } from "@/stores/adminStore";

let pluginsInitialized = false;

export function initDayjsPlugins(): void {
  if (!pluginsInitialized) {
    dayjs.extend(utc);
    dayjs.extend(timezone);
    dayjs.extend(relativeTime);
    dayjs.locale("zh-cn");
    pluginsInitialized = true;
  }
}

/**
 * 将后端返回的时间值（ISO 字符串 / 毫秒时间戳 / Date）统一转换为 UTC epoch 毫秒时间戳
 *
 * 后端 SQLite 读出 DateTime(timezone=True) 列时会丢失 tzinfo，
 * isoformat() 输出无时区后缀的字符串（如 "2026-11-08T07:32:04"）。
 * ES 规范规定 new Date() 对无时区 ISO 字符串按 **本地时间** 解析，
 * 会导致 8 小时偏差（东八区）。此函数检测这种情况，显式补 Z 后缀按 UTC 解析。
 */
export function toUtcTimestamp(
  value: string | number | Date | null | undefined,
): number {
  initDayjsPlugins();

  if (value === null || value === undefined || value === "") return 0;
  if (typeof value === "number") return value;
  if (value instanceof Date) return value.getTime();

  // 字符串：无时区后缀 → 后端 SQLite 读出的 UTC 时间，显式加 Z 解析
  const trimmed = value.trim();
  if (
    trimmed.length >= 19 &&
    !trimmed.endsWith("Z") &&
    !trimmed.match(/[+-]\d{2}:\d{2}$/)
  ) {
    // 无时区后缀，当作 UTC 解析
    const t = new Date(trimmed + "Z").getTime();
    return Number.isNaN(t) ? 0 : t;
  }
  // 已有时区后缀（Z 或 +08:00），new Date 能正确解析
  const t = new Date(trimmed).getTime();
  return Number.isNaN(t) ? 0 : t;
}

export function getEffectiveTimezone(): string {
  initDayjsPlugins();

  const adminStore = useAdminStore();
  const mode = adminStore.systemConfigs?.timezone_mode?.value;
  const configuredName = adminStore.systemConfigs?.timezone_name?.value;

  if (mode === "local" && configuredName) {
    return configuredName;
  }

  // 未配置时，使用浏览器本地时区
  if (mode === undefined || mode === null) {
    return dayjs.tz.guess();
  }

  // utc 模式返回 UTC
  return "UTC";
}

export function toConfiguredTimezone(
  value: string | number | Date | null | undefined,
): dayjs.Dayjs | null {
  initDayjsPlugins();

  if (value === null || value === undefined || value === "") {
    return null;
  }

  let d: dayjs.Dayjs;

  if (typeof value === "string") {
    // 后端返回的 UTC 时间字符串可能没有 Z 后缀（如 "2026-05-10 05:21:11"）
    // 这种情况下需要显式指定为 UTC 解析，避免被当作本地时间
    const trimmed = value.trim();
    if (
      trimmed.length >= 19 &&
      !trimmed.endsWith("Z") &&
      !trimmed.match(/[+-]\d{2}:\d{2}$/)
    ) {
      // 无时区信息的字符串，按 UTC 解析
      d = dayjs.utc(trimmed);
    } else {
      d = dayjs(value);
    }
  } else {
    d = dayjs(value);
  }

  if (!d.isValid()) {
    return null;
  }

  const tz = getEffectiveTimezone();
  if (tz === "UTC") {
    return d.utc();
  }
  return d.tz(tz);
}

export function formatDateTime(
  value: string | number | Date | null | undefined,
  format: string = "YYYY-MM-DD HH:mm:ss",
): string {
  const converted = toConfiguredTimezone(value);
  if (!converted) {
    return "-";
  }
  return converted.format(format);
}

export function formatDate(
  value: string | number | Date | null | undefined,
  format: string = "YYYY-MM-DD",
): string {
  return formatDateTime(value, format);
}

export function formatRelativeTime(
  value: string | number | Date | null | undefined,
): string {
  const converted = toConfiguredTimezone(value);
  if (!converted) {
    return "-";
  }
  return converted.fromNow();
}
