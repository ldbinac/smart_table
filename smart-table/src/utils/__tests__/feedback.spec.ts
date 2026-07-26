import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  APP_NAME,
  APP_VERSION,
  GITHUB_ISSUES_NEW_URL,
  GITEE_ISSUES_NEW_URL,
  FEEDBACK_EMAIL,
  WECHAT_QR_PATH,
  collectSystemInfo,
  buildIssueBody,
  buildEmailBody,
  buildGitHubIssueUrl,
  buildGiteeIssueUrl,
  buildMailtoLink,
  openInNewTab,
  copyToClipboard,
} from "../feedback";

// Mock adminStore，避免 formatDateTime 调用时缺少 Pinia
vi.mock("@/stores/adminStore", () => ({
  useAdminStore: () => ({ systemConfigs: {} }),
}));

describe("feedback 工具模块", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("常量", () => {
    it("应用名称应为 SmartTable", () => {
      expect(APP_NAME).toBe("SmartTable");
    });

    it("应用版本应为字符串", () => {
      expect(typeof APP_VERSION).toBe("string");
      expect(APP_VERSION.length).toBeGreaterThan(0);
    });

    it("GitHub Issues URL 应指向项目仓库", () => {
      expect(GITHUB_ISSUES_NEW_URL).toBe(
        "https://github.com/ldbinac/smart_table/issues/new",
      );
    });

    it("Gitee Issues URL 应指向项目仓库", () => {
      expect(GITEE_ISSUES_NEW_URL).toBe(
        "https://gitee.com/binac/smart_table/issues/new",
      );
    });

    it("反馈邮箱应为有效格式", () => {
      expect(FEEDBACK_EMAIL).toContain("@");
    });

    it("公众号二维码路径应为 /wechat_official_account.png", () => {
      expect(WECHAT_QR_PATH).toBe("/wechat_official_account.png");
    });
  });

  describe("collectSystemInfo", () => {
    it("应返回包含所有必需字段的对象", () => {
      const info = collectSystemInfo();
      expect(info).toHaveProperty("appName", APP_NAME);
      expect(info).toHaveProperty("appVersion", APP_VERSION);
      expect(info).toHaveProperty("userAgent");
      expect(info).toHaveProperty("os");
      expect(info).toHaveProperty("pageUrl");
      expect(info).toHaveProperty("screenResolution");
      expect(info).toHaveProperty("viewportSize");
      expect(info).toHaveProperty("devicePixelRatio");
      expect(info).toHaveProperty("language");
      expect(info).toHaveProperty("feedbackTime");
    });

    it("反馈时间应符合 yyyy-MM-dd HH:mm:ss 格式", () => {
      const info = collectSystemInfo();
      expect(info.feedbackTime).toMatch(
        /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/,
      );
    });

    it("应包含浏览器 UA 字符串", () => {
      const info = collectSystemInfo();
      expect(typeof info.userAgent).toBe("string");
      expect(info.userAgent.length).toBeGreaterThan(0);
    });
  });

  describe("buildIssueBody", () => {
    it("应包含系统环境信息标题", () => {
      const body = buildIssueBody();
      expect(body).toContain("## 系统环境信息");
    });

    it("应包含所有环境信息字段", () => {
      const body = buildIssueBody();
      expect(body).toContain(`- 应用名称：${APP_NAME}`);
      expect(body).toContain(`- 应用版本：${APP_VERSION}`);
      expect(body).toContain("- 浏览器 UA：");
      expect(body).toContain("- 操作系统：");
      expect(body).toContain("- 页面 URL：");
      expect(body).toContain("- 屏幕分辨率：");
      expect(body).toContain("- 视口大小：");
      expect(body).toContain("- 设备像素比：");
      expect(body).toContain("- 语言：");
      expect(body).toContain("- 反馈时间：");
    });

    it("应包含问题描述与复现步骤模板", () => {
      const body = buildIssueBody();
      expect(body).toContain("## 问题描述");
      expect(body).toContain("## 复现步骤");
      expect(body).toContain("## 期望结果");
      expect(body).toContain("## 实际结果");
    });
  });

  describe("buildEmailBody", () => {
    it("应包含提示语", () => {
      const body = buildEmailBody();
      expect(body).toContain("请在此描述您的问题或建议");
    });

    it("应包含系统环境信息", () => {
      const body = buildEmailBody();
      expect(body).toContain(`应用名称：${APP_NAME}`);
      expect(body).toContain(`应用版本：${APP_VERSION}`);
      expect(body).toContain("系统环境信息");
    });
  });

  describe("buildGitHubIssueUrl", () => {
    it("应以 GitHub Issues 创建 URL 开头", () => {
      const url = buildGitHubIssueUrl();
      expect(url.startsWith(GITHUB_ISSUES_NEW_URL)).toBe(true);
    });

    it("应包含 title 与 body 查询参数", () => {
      const url = buildGitHubIssueUrl();
      expect(url).toContain("title=");
      expect(url).toContain("body=");
    });

    it("应使用默认标题", () => {
      const url = buildGitHubIssueUrl();
      expect(url).toContain(encodeURIComponent("用户问题反馈"));
    });
  });

  describe("buildGiteeIssueUrl", () => {
    it("应返回 Gitee Issues 新建页 URL（无查询参数）", () => {
      const url = buildGiteeIssueUrl();
      // Gitee Web 表单不支持 URL 查询参数预填充，故直接返回新建页地址
      expect(url).toBe(GITEE_ISSUES_NEW_URL);
      expect(url).not.toContain("?");
    });
  });

  describe("buildMailtoLink", () => {
    it("应以 mailto: 与反馈邮箱开头", () => {
      const link = buildMailtoLink();
      expect(link.startsWith(`mailto:${FEEDBACK_EMAIL}`)).toBe(true);
    });

    it("应包含 subject 参数", () => {
      const link = buildMailtoLink();
      expect(link).toContain("subject=");
      // URLSearchParams 编码后 [SmartTable 反馈] 变为 %5BSmartTable+...
      expect(link).toContain("%5BSmartTable");
      expect(link).toContain("SmartTable");
    });

    it("应包含 body 参数", () => {
      const link = buildMailtoLink();
      expect(link).toContain("body=");
    });
  });

  describe("openInNewTab", () => {
    it("应使用 _blank 与 noopener,noreferrer 调用 window.open", () => {
      const spy = vi.spyOn(window, "open").mockImplementation(() => null);
      openInNewTab("https://example.com");
      expect(spy).toHaveBeenCalledWith(
        "https://example.com",
        "_blank",
        "noopener,noreferrer",
      );
      spy.mockRestore();
    });
  });

  describe("copyToClipboard", () => {
    it("应调用 navigator.clipboard.writeText 并返回 true", async () => {
      // jsdom 中 navigator.clipboard 默认不存在，需手动注入
      const writeText = vi.fn().mockResolvedValue(undefined);
      Object.defineProperty(navigator, "clipboard", {
        value: { writeText },
        configurable: true,
      });
      // jsdom 中 isSecureContext 默认为 false，需覆盖为 true 以走 clipboard API 路径
      Object.defineProperty(window, "isSecureContext", {
        value: true,
        configurable: true,
      });
      const result = await copyToClipboard("test content");
      expect(writeText).toHaveBeenCalledWith("test content");
      expect(result).toBe(true);
    });

    it("clipboard API 不可用时应返回 false", async () => {
      const writeText = vi.fn().mockRejectedValue(new Error("denied"));
      Object.defineProperty(navigator, "clipboard", {
        value: { writeText },
        configurable: true,
      });
      Object.defineProperty(window, "isSecureContext", {
        value: true,
        configurable: true,
      });
      const result = await copyToClipboard("test content");
      expect(result).toBe(false);
    });
  });
});
