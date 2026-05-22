import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  initDayjsPlugins,
  getEffectiveTimezone,
  formatDateTime,
  formatDate,
  toConfiguredTimezone,
} from "../timezone";

const mockStore = {
  systemConfigs: {} as Record<string, any>,
};

vi.mock("@/stores/adminStore", () => ({
  useAdminStore: () => mockStore,
}));

describe("timezone", () => {
  beforeEach(() => {
    initDayjsPlugins();
    mockStore.systemConfigs = {};
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("getEffectiveTimezone", () => {
    it("默认返回 UTC", () => {
      expect(getEffectiveTimezone()).toBe("UTC");
    });

    it("当 timezone_mode 为 local 时返回配置的时区名称", () => {
      mockStore.systemConfigs = {
        timezone_mode: { config_value: "local" },
        timezone_name: { config_value: "Asia/Shanghai" },
      };
      expect(getEffectiveTimezone()).toBe("Asia/Shanghai");
    });

    it("当 timezone_mode 为 utc 时返回 UTC", () => {
      mockStore.systemConfigs = {
        timezone_mode: { config_value: "utc" },
        timezone_name: { config_value: "Asia/Shanghai" },
      };
      expect(getEffectiveTimezone()).toBe("UTC");
    });
  });

  describe("formatDateTime", () => {
    it("UTC 模式下格式化 UTC 时间", () => {
      mockStore.systemConfigs = {
        timezone_mode: { config_value: "utc" },
      };
      const result = formatDateTime("2024-06-15T08:30:00Z");
      expect(result).toBe("2024-06-15 08:30:00");
    });

    it("本地时区模式下将 UTC 转换为本地时区", () => {
      mockStore.systemConfigs = {
        timezone_mode: { config_value: "local" },
        timezone_name: { config_value: "Asia/Shanghai" },
      };
      const result = formatDateTime("2024-06-15T08:30:00Z");
      expect(result).toBe("2024-06-15 16:30:00");
    });

    it("无效时间戳返回 '-'", () => {
      expect(formatDateTime(null)).toBe("-");
      expect(formatDateTime(undefined)).toBe("-");
      expect(formatDateTime("")).toBe("-");
      expect(formatDateTime("invalid")).toBe("-");
    });

    it("支持自定义格式", () => {
      mockStore.systemConfigs = {
        timezone_mode: { config_value: "utc" },
      };
      const result = formatDateTime("2024-06-15T08:30:00Z", "YYYY-MM-DD");
      expect(result).toBe("2024-06-15");
    });

    it("支持时间戳数字输入", () => {
      mockStore.systemConfigs = {
        timezone_mode: { config_value: "utc" },
      };
      const ts = new Date("2024-06-15T08:30:00Z").getTime();
      const result = formatDateTime(ts);
      expect(result).toBe("2024-06-15 08:30:00");
    });
  });

  describe("formatDate", () => {
    it("使用日期格式", () => {
      mockStore.systemConfigs = {
        timezone_mode: { config_value: "utc" },
      };
      const result = formatDate("2024-06-15T08:30:00Z");
      expect(result).toBe("2024-06-15");
    });
  });

  describe("toConfiguredTimezone", () => {
    it("返回配置时区的 dayjs 对象", () => {
      mockStore.systemConfigs = {
        timezone_mode: { config_value: "local" },
        timezone_name: { config_value: "Asia/Shanghai" },
      };
      const result = toConfiguredTimezone("2024-06-15T08:30:00Z");
      expect(result).not.toBeNull();
      expect(result!.format("YYYY-MM-DD HH:mm:ss")).toBe("2024-06-15 16:30:00");
    });

    it("无效输入返回 null", () => {
      expect(toConfiguredTimezone(null)).toBeNull();
      expect(toConfiguredTimezone("invalid")).toBeNull();
      expect(toConfiguredTimezone("")).toBeNull();
    });

    it("Date 对象输入正常处理", () => {
      mockStore.systemConfigs = {
        timezone_mode: { config_value: "utc" },
      };
      const date = new Date("2024-06-15T08:30:00Z");
      const result = toConfiguredTimezone(date);
      expect(result).not.toBeNull();
      expect(result!.format("YYYY-MM-DD HH:mm:ss")).toBe("2024-06-15 08:30:00");
    });

    it("无时区后缀的 UTC 字符串按 UTC 解析", () => {
      mockStore.systemConfigs = {
        timezone_mode: { config_value: "local" },
        timezone_name: { config_value: "Asia/Shanghai" },
      };
      // 后端返回的无 Z 后缀 UTC 时间
      const result = toConfiguredTimezone("2024-06-15 08:30:00");
      expect(result).not.toBeNull();
      expect(result!.format("YYYY-MM-DD HH:mm:ss")).toBe("2024-06-15 16:30:00");
    });

    it("带 Z 后缀的 ISO 字符串正常解析", () => {
      mockStore.systemConfigs = {
        timezone_mode: { config_value: "local" },
        timezone_name: { config_value: "Asia/Shanghai" },
      };
      const result = toConfiguredTimezone("2024-06-15T08:30:00Z");
      expect(result).not.toBeNull();
      expect(result!.format("YYYY-MM-DD HH:mm:ss")).toBe("2024-06-15 16:30:00");
    });
  });
});
