import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";

let pluginsInitialized = false;

export function initDayjsPlugins(): void {
  if (!pluginsInitialized) {
    dayjs.extend(utc);
    dayjs.extend(timezone);
    pluginsInitialized = true;
  }
}

function getBrowserLocalTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

export function getEffectiveTimezone(): string {
  initDayjsPlugins();

  // 默认总是使用浏览器本地时区
  return getBrowserLocalTimezone();
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
