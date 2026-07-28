/**
 * 用户问题反馈工具模块
 * 集中管理反馈渠道常量、系统环境信息收集与各渠道跳转/调用构建函数
 */
import { formatDateTime } from "./timezone";

// ============================================
// 反馈渠道常量
// ============================================

/** 应用名称 */
export const APP_NAME = "SmartTable";

/** 应用版本（与 package.json 保持一致） */
export const APP_VERSION = "1.6.2";

/** GitHub 仓库地址 */
export const GITHUB_REPO_URL = "https://github.com/ldbinac/smart_table";

/** GitHub Issues 创建地址 */
export const GITHUB_ISSUES_NEW_URL = "https://github.com/ldbinac/smart_table/issues/new";

/** Gitee 仓库地址 */
export const GITEE_REPO_URL = "https://gitee.com/binac/smart_table";

/** Gitee Issues 创建地址 */
export const GITEE_ISSUES_NEW_URL = "https://gitee.com/binac/smart_table/issues/new";

/** 反馈收件邮箱 */
export const FEEDBACK_EMAIL = "ldengbin@126.com";

/** 公众号二维码图片路径（public 目录下） */
export const WECHAT_QR_PATH = "/wechat_official_account.png";

// ============================================
// 系统环境信息收集
// ============================================

/** 系统环境信息接口 */
export interface SystemInfo {
  appName: string;
  appVersion: string;
  userAgent: string;
  os: string;
  pageUrl: string;
  screenResolution: string;
  viewportSize: string;
  devicePixelRatio: string;
  language: string;
  feedbackTime: string;
}

/**
 * 从 userAgent 简易解析操作系统名称
 */
function parseOS(userAgent: string): string {
  const ua = userAgent.toLowerCase();
  if (ua.includes("windows")) return "Windows";
  if (ua.includes("mac os") || ua.includes("macos")) return "macOS";
  if (ua.includes("linux")) return "Linux";
  if (ua.includes("android")) return "Android";
  if (ua.includes("iphone") || ua.includes("ipad") || ua.includes("ios")) return "iOS";
  // navigator.platform 兜底
  if (typeof navigator !== "undefined" && navigator.platform) {
    return navigator.platform;
  }
  return "Unknown";
}

/**
 * 收集当前系统环境信息
 */
export function collectSystemInfo(): SystemInfo {
  const now = new Date();
  return {
    appName: APP_NAME,
    appVersion: APP_VERSION,
    userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "Unknown",
    os: parseOS(typeof navigator !== "undefined" ? navigator.userAgent : ""),
    pageUrl: typeof window !== "undefined" ? window.location.href : "Unknown",
    screenResolution:
      typeof window !== "undefined" && window.screen
        ? `${window.screen.width} × ${window.screen.height}`
        : "Unknown",
    viewportSize:
      typeof window !== "undefined"
        ? `${window.innerWidth} × ${window.innerHeight}`
        : "Unknown",
    devicePixelRatio:
      typeof window !== "undefined" && window.devicePixelRatio
        ? String(window.devicePixelRatio)
        : "Unknown",
    language: typeof navigator !== "undefined" ? navigator.language : "Unknown",
    feedbackTime: formatDateTime(now),
  };
}

// ============================================
// 反馈内容模板构建
// ============================================

/**
 * 生成包含系统环境信息的 Markdown 反馈正文模板
 */
export function buildIssueBody(info: SystemInfo = collectSystemInfo()): string {
  return [
    "## 问题描述",
    "",
    "<!-- 请在此描述您遇到的问题或建议 -->",
    "",
    "## 复现步骤",
    "",
    "1. ",
    "2. ",
    "3. ",
    "",
    "## 期望结果",
    "",
    "<!-- 您期望发生什么 -->",
    "",
    "## 实际结果",
    "",
    "<!-- 实际发生了什么 -->",
    "",
    "## 系统环境信息",
    "",
    `- 应用名称：${info.appName}`,
    `- 应用版本：${info.appVersion}`,
    `- 浏览器 UA：${info.userAgent}`,
    `- 操作系统：${info.os}`,
    `- 页面 URL：${info.pageUrl}`,
    `- 屏幕分辨率：${info.screenResolution}`,
    `- 视口大小：${info.viewportSize}`,
    `- 设备像素比：${info.devicePixelRatio}`,
    `- 语言：${info.language}`,
    `- 反馈时间：${info.feedbackTime}`,
    "",
  ].join("\n");
}

/**
 * 生成邮件正文模板（纯文本，适用于 mailto）
 */
export function buildEmailBody(info: SystemInfo = collectSystemInfo()): string {
  return [
    "请在此描述您的问题或建议：",
    "",
    "",
    "----------------------------------------",
    "系统环境信息",
    `应用名称：${info.appName}`,
    `应用版本：${info.appVersion}`,
    `浏览器 UA：${info.userAgent}`,
    `操作系统：${info.os}`,
    `页面 URL：${info.pageUrl}`,
    `屏幕分辨率：${info.screenResolution}`,
    `视口大小：${info.viewportSize}`,
    `设备像素比：${info.devicePixelRatio}`,
    `语言：${info.language}`,
    `反馈时间：${info.feedbackTime}`,
  ].join("\n");
}

// ============================================
// 各渠道链接构建
// ============================================

/** Issue 默认标题 */
export const DEFAULT_ISSUE_TITLE = "用户问题反馈";

/**
 * 构建 GitHub Issues 创建 URL（带预填充标题与正文）
 */
export function buildGitHubIssueUrl(
  title: string = DEFAULT_ISSUE_TITLE,
  body: string = buildIssueBody(),
): string {
  const params = new URLSearchParams({
    title,
    body,
  });
  return `${GITHUB_ISSUES_NEW_URL}?${params.toString()}`;
}

/**
 * 构建 Gitee Issues 新建页 URL
 *
 * 注意：与 GitHub 不同，Gitee Web 表单不支持通过 URL 查询参数
 * （如 ?title=&body=）预填充 Issue 表单。Gitee 官方仅支持通过
 * 仓库内 .gitee/ISSUE_TEMPLATE 配置静态模板，或通过 API v5 创建。
 *
 * 因此本函数直接返回新建页地址，由调用方配合 copyToClipboard()
 * 将模板复制到剪贴板，引导用户手动粘贴。
 */
export function buildGiteeIssueUrl(): string {
  return GITEE_ISSUES_NEW_URL;
}

/**
 * 构建 mailto 链接（含收件人、主题、正文）
 */
export function buildMailtoLink(
  info: SystemInfo = collectSystemInfo(),
): string {
  const subject = `[${APP_NAME} 反馈] 用户问题反馈 - ${info.feedbackTime}`;
  const body = buildEmailBody(info);
  const params = new URLSearchParams({
    subject,
    body,
  });
  return `mailto:${FEEDBACK_EMAIL}?${params.toString()}`;
}

// ============================================
// 跳转/调用工具
// ============================================

/**
 * 在新标签页打开指定 URL（带 noopener/noreferrer 安全属性）
 */
export function openInNewTab(url: string): void {
  window.open(url, "_blank", "noopener,noreferrer");
}

/**
 * 将文本复制到剪贴板
 * @returns 是否复制成功
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
    // 回退方案：使用临时 textarea + execCommand
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(textarea);
    return ok;
  } catch {
    return false;
  }
}
