/**
 * 插件管理 REST API 客户端
 * 复用统一 apiClient（自动携带 JWT、401 续期、{success,message,data} 适配）
 */
import { apiClient } from "@/api/client";
import type {
  PluginEntity,
  PluginVersion,
  PluginInstallation,
  PluginRunLog,
  PluginStatus,
} from "@/plugins/types";

const BASE = "/plugins";

/** 获取插件列表（可选 base_id 附带 Base 级安装/生效状态） */
export const fetchPlugins = (baseId?: string): Promise<PluginEntity[]> =>
  apiClient.get<PluginEntity[]>(`${BASE}`, baseId ? { base_id: baseId } : undefined);

/** 获取插件详情（含版本历史） */
export const fetchPlugin = (
  pluginId: string,
): Promise<PluginEntity & { versions: PluginVersion[] }> =>
  apiClient.get(`${BASE}/${pluginId}`);

/** 上传安装/升级安装包（系统管理员） */
export const uploadPlugin = (
  file: File,
  onProgress?: (percent: number) => void,
): Promise<{ action: "installed" | "upgraded"; plugin: PluginEntity }> =>
  apiClient.upload(`${BASE}/upload`, (() => {
    const fd = new FormData();
    fd.append("package", file);
    return fd;
  })(), onProgress) as Promise<{ action: "installed" | "upgraded"; plugin: PluginEntity }>;

/** 设置全局状态（系统管理员） */
export const setPluginStatus = (
  pluginId: string,
  status: PluginStatus,
): Promise<PluginEntity> =>
  apiClient.put<PluginEntity>(`${BASE}/${pluginId}/status`, { status });

/** 回滚到历史版本（系统管理员） */
export const rollbackPlugin = (
  pluginId: string,
  version: string,
): Promise<PluginEntity> =>
  apiClient.post<PluginEntity>(`${BASE}/${pluginId}/rollback`, { version });

/** 卸载插件（系统管理员） */
export const uninstallPlugin = (pluginId: string): Promise<{ uninstalled: string }> =>
  apiClient.delete(`${BASE}/${pluginId}`);

/** 读取插件配置：缺省返回生效合并视图；传 scope 时返回该作用域存储值 */
export const fetchPluginConfig = (
  pluginId: string,
  baseId?: string,
  scope?: "global" | "base",
): Promise<Record<string, unknown>> =>
  apiClient.get(`${BASE}/${pluginId}/config`, {
    ...(baseId ? { base_id: baseId } : {}),
    ...(scope ? { scope } : {}),
  });

/** 写入配置（configSchema 校验） */
export const savePluginConfig = (
  pluginId: string,
  scope: "global" | "base",
  config: Record<string, unknown>,
  baseId?: string,
): Promise<unknown> =>
  apiClient.put(`${BASE}/${pluginId}/config`, { scope, base_id: baseId, config });

/** 在 Base 内安装并启用（Base 管理员） */
export const installPluginToBase = (
  pluginId: string,
  baseId: string,
): Promise<PluginInstallation> =>
  apiClient.post<PluginInstallation>(`${BASE}/${pluginId}/installations`, {
    base_id: baseId,
  });

/** 启停 Base 级插件（Base 管理员） */
export const setPluginInstallationEnabled = (
  pluginId: string,
  baseId: string,
  enabled: boolean,
): Promise<PluginInstallation> =>
  apiClient.put<PluginInstallation>(`${BASE}/${pluginId}/installations`, {
    base_id: baseId,
    enabled,
  });

/** 从 Base 移除插件（Base 管理员） */
export const uninstallPluginFromBase = (
  pluginId: string,
  baseId: string,
): Promise<{ removed: string }> =>
  apiClient.delete(`${BASE}/${pluginId}/installations`, { params: { base_id: baseId } });

/** 手动运行脚本插件（触发者身份） */
export const runScriptPlugin = (
  pluginId: string,
  baseId: string,
): Promise<{
  status: string;
  duration_ms: number;
  result: unknown;
  output: string;
  error?: string;
  run_log_id: string;
  base_id?: string;
}> =>
  // 脚本后端最长可跑 300s（MAX_TIMEOUT），覆盖全局 30s axios 超时，避免长任务被前端提前掐断
  apiClient.post(`${BASE}/${pluginId}/run`, { base_id: baseId }, { timeout: 320000 });

/** 查询运行日志（Base 管理员） */
export const fetchRunLogs = async (
  pluginId: string,
  baseId: string,
  page = 1,
  perPage = 20,
): Promise<PluginRunLog[]> => {
  // 后端为分页响应（带 meta），apiClient 对带 meta 的响应会返回整个 {data, meta} 包装对象
  const res = await apiClient.get<PluginRunLog[] | { data?: PluginRunLog[] }>(
    `${BASE}/${pluginId}/run-logs`,
    {
      base_id: baseId,
      page,
      per_page: perPage,
    },
  );
  if (Array.isArray(res)) return res;
  return res?.data ?? [];
};

/** 获取 UI 插件沙箱签名 URL */
export const fetchSandboxUrl = (
  pluginId: string,
  baseId: string,
): Promise<{ url: string; version: string }> =>
  apiClient.post(`${BASE}/${pluginId}/sandbox-url`, { base_id: baseId });
