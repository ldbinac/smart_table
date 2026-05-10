import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";
import { useAdminStore } from "@/stores/adminStore";

let pluginsInitialized = false;

export function initDayjsPlugins(): void {
  if (!pluginsInitialized) {
    dayjs.extend(utc);
    dayjs.extend(timezone);
    pluginsInitialized = true;
  }
}

export function getEffectiveTimezone(): string {
  initDayjsPlugins();

  let adminStore;
  try {
    adminStore = useAdminStore();
  } catch {
    return "UTC";
  }

  const mode = (adminStore.systemConfigs["timezone_mode"] as any)?.config_value;
  const name = (adminStore.systemConfigs["timezone_name"] as any)?.config_value;

  if (mode === "local" && name && typeof name === "string") {
    try {
      const test = dayjs().tz(name);
      if (test.isValid()) {
        return name;
      }
    } catch {
      // 无效时区，回退到 UTC
    }
  }
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
