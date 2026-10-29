/**
 * 前端版本检测与强制刷新机制
 *
 * 设计思路：
 * 1. 应用启动时向服务器请求 /version.json（带时间戳绕过缓存）
 * 2. 对比服务器版本 vs localStorage 中存储的上次运行版本
 * 3. 若不一致 → 弹出确认对话框，用户确认后 window.location.reload(true) 强制刷新
 * 4. "稍后再说"选项写入 sessionStorage，同一 session 内不再重复弹窗
 *
 * 依赖：Vite 构建时由 generateVersionPlugin 生成 dist/version.json
 *       Nginx 对 /version.json 配置 no-cache 策略
 */

import { ElMessageBox } from "element-plus";
import { t } from "@/i18n";

/** 服务器返回的 version.json 结构（Vite 插件生成） */
export interface ServerVersion {
  version: string;
  buildTime: string;
  buildHash: string;
  buildNumber: number;
}

/** localStorage key */
const CLIENT_VERSION_KEY = "smarttable.appVersion";
const CLIENT_BUILD_HASH_KEY = "smarttable.buildHash";
/** sessionStorage key — 标记用户本次 session 内已点过"稍后再说" */
const UPDATE_SKIPPED_KEY = "smarttable.updateSkipped";
/** sessionStorage key — 标记本次启动是"刚刷新过"，防止刷新后仍检测到无版本导致死循环弹窗 */
const REFRESHING_FLAG_KEY = "smarttable.refreshing";

// ============================================================================
// 版本对比
// ============================================================================

/**
 * 比较服务器版本与本地缓存版本是否一致
 * - 优先精确匹配 buildHash（每次构建唯一）
 * - 再 fallback 到 semver 版本号比较
 * - 本地无版本记录（localStorage key 不存在）也视为不一致 —— 说明浏览器可能残留
 *   旧 index.html/JS/CSS（例如首次升级到带版本检测的版本时），需要强制刷新
 */
function isVersionMismatch(server: ServerVersion): boolean {
  const localHash = localStorage.getItem(CLIENT_BUILD_HASH_KEY);
  const localVersion = localStorage.getItem(CLIENT_VERSION_KEY);

  // 没有任何本地版本记录 → 视为旧版本，触发刷新（保护：sessionStorage 刚刷过标记）
  if (!localHash && !localVersion) {
    if (sessionStorage.getItem(REFRESHING_FLAG_KEY)) {
      // 刚刷过就退出，防止死循环
      sessionStorage.removeItem(REFRESHING_FLAG_KEY);
      return false;
    }
    return true;
  }

  // 精确匹配 buildHash（最可靠，每次构建都不同）
  if (localHash && server.buildHash !== localHash) return true;

  // fallback：semver 版本号比较
  if (localVersion && server.version !== localVersion) return true;

  return false;
}

// ============================================================================
// 存储读写
// ============================================================================

export function getClientVersion(): { version: string | null; buildHash: string | null } {
  return {
    version: localStorage.getItem(CLIENT_VERSION_KEY),
    buildHash: localStorage.getItem(CLIENT_BUILD_HASH_KEY),
  };
}

export function saveClientVersion(info: ServerVersion): void {
  localStorage.setItem(CLIENT_VERSION_KEY, info.version);
  localStorage.setItem(CLIENT_BUILD_HASH_KEY, info.buildHash);
  // 保存后清除"稍后再说"标记，下次启动重新检测
  sessionStorage.removeItem(UPDATE_SKIPPED_KEY);
}

/** 刷新前清理本地存储中的旧版本残留（可选） */
export function clearStaleCaches(): void {
  // 保留用户设置，只清理版本相关 key
  localStorage.removeItem(CLIENT_VERSION_KEY);
  localStorage.removeItem(CLIENT_BUILD_HASH_KEY);
  sessionStorage.removeItem(UPDATE_SKIPPED_KEY);
}

// ============================================================================
// 服务器版本请求
// ============================================================================

/**
 * 请求服务器的 version.json
 * URL 带 ?_t=时间戳 参数，强制绕过浏览器缓存和 Nginx 缓存
 */
async function fetchServerVersion(): Promise<ServerVersion | null> {
  try {
    const url = `/version.json?_t=${Date.now()}`;
    const response = await fetch(url, {
      method: "GET",
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      console.warn(`[versionCheck] version.json 请求失败: ${response.status}`);
      return null;
    }
    const data = (await response.json()) as ServerVersion;
    if (!data.version || !data.buildHash) {
      console.warn("[versionCheck] version.json 格式异常", data);
      return null;
    }
    return data;
  } catch (err) {
    // 网络错误 / offline — 静默跳过，不阻塞正常使用
    console.warn("[versionCheck] 无法连接服务器，跳过版本检测:", err);
    return null;
  }
}

// ============================================================================
// 主入口
// ============================================================================

/**
 * 检测版本并在需要时弹出升级对话框
 *
 * 触发刷新的条件（任一满足）：
 *   1. localStorage 中 smarttable.appVersion 不存在（升级到带版本检测的版本后首次运行）
 *   2. 本地 buildHash 与服务器不一致（每次构建唯一）
 *   3. 本地 version 与服务器不一致（fallback）
 *
 * 死循环保护：刷新前设置 sessionStorage 标记，刷新后首次进入会跳过一次检测
 *
 * 应该在 Vue app 挂载后尽快调用（非阻塞，版本检测在后台进行）
 */
export async function checkAndPromptUpdate(): Promise<void> {
  // 同一 session 内已经点过"稍后再说" → 跳过
  if (sessionStorage.getItem(UPDATE_SKIPPED_KEY)) return;

  const serverVersion = await fetchServerVersion();
  if (!serverVersion) return; // 请求失败，静默跳过（网络错误 / offline）

  const client = getClientVersion();

  if (!isVersionMismatch(serverVersion)) {
    // 版本一致 → 静默更新一下本地存储（服务器 buildHash 可能更精确）
    // （isVersionMismatch 返回 false 时如果是刚刷过，REFRESHING_FLAG_KEY 也已被清除）
    saveClientVersion(serverVersion);
    return;
  }

  // ── 触发刷新的两种场景 ──
  const hasNoLocalRecord = !client.version && !client.buildHash;
  const displayCurrentVersion = hasNoLocalRecord
    ? t("version.unknownVersion")
    : `v${client.version}`;

  console.info(
    `[versionCheck] 检测到需要刷新: ${displayCurrentVersion} → v${serverVersion.version}` +
      (hasNoLocalRecord ? " (本地无版本记录)" : ""),
  );

  try {
    await ElMessageBox.confirm(
      `<p>${t("version.updateMessage")}</p>
       <p style="margin-top:10px;font-size:13px;color:#909399;">
         ${t("version.currentVersion")}: <b>${displayCurrentVersion}</b><br>
         ${t("version.latestVersion")}: <b>v${serverVersion.version}</b>
       </p>`,
      t("version.updateAvailable"),
      {
        dangerouslyUseHTMLString: true,
        confirmButtonText: t("version.refreshNow"),
        cancelButtonText: t("version.later"),
        type: "warning",
        closeOnClickModal: false,
        closeOnPressEscape: false,
      },
    );

    // 用户确认 → 设置防死循环标记 + 保存版本 + 强制刷新
    // 先写 sessionStorage 标记，这样 reload 后 isVersionMismatch 会检测到并 return false，
    // 然后正常执行到 saveClientVersion 把版本写入 localStorage
    sessionStorage.setItem(REFRESHING_FLAG_KEY, "1");
    clearStaleCaches();
    saveClientVersion(serverVersion);
    window.location.reload();
  } catch {
    // 用户点"稍后再说" → sessionStorage 标记，同 session 不再弹窗
    sessionStorage.setItem(UPDATE_SKIPPED_KEY, "1");
    console.info("[versionCheck] 用户选择稍后再说，本次 session 不再提示");
  }
}
