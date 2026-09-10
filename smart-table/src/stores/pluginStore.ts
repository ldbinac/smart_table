/**
 * 插件状态管理
 * 插件列表、生命周期操作（启用/禁用/升级/回滚/卸载）、配置与运行日志
 */
import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { ElMessage } from "element-plus";
import { useI18n } from "vue-i18n";
import {
  fetchPlugins,
  uploadPlugin,
  setPluginStatus,
  rollbackPlugin,
  uninstallPlugin,
  fetchPluginConfig,
  savePluginConfig,
  installPluginToBase,
  setPluginInstallationEnabled,
  uninstallPluginFromBase,
  runScriptPlugin,
  fetchRunLogs,
} from "@/api/plugins";
import type {
  PluginEntity,
  PluginVersion,
  PluginRunLog,
  PluginStatus,
  PluginType,
} from "@/plugins/types";

export const usePluginStore = defineStore("plugin", () => {
  const plugins = ref<PluginEntity[]>([]);
  const versions = ref<Record<string, PluginVersion[]>>({});
  const configs = ref<Record<string, Record<string, unknown>>>({});
  const runLogs = ref<PluginRunLog[]>([]);
  const loading = ref(false);
  const uploading = ref(false);
  const uploadProgress = ref(0);

  /** 按类型/关键词过滤 */
  const filterKeyword = ref("");
  const filterType = ref<PluginType | "">("");

  const filteredPlugins = computed(() => {
    const kw = filterKeyword.value.trim().toLowerCase();
    return plugins.value.filter((p) => {
      if (filterType.value && p.type !== filterType.value) return false;
      if (!kw) return true;
      return (
        p.name.toLowerCase().includes(kw) ||
        p.id.toLowerCase().includes(kw)
      );
    });
  });

  const uiPlugins = computed(() =>
    plugins.value.filter((p) => p.type === "ui"),
  );
  const scriptPlugins = computed(() =>
    plugins.value.filter((p) => p.type === "script"),
  );

  /** 最近一次列表查询使用的 base_id（操作后刷新列表时保持一致） */
  let lastListBaseId: string | undefined;

  /** 加载插件列表；传 base_id 时附带该 Base 的安装/生效状态 */
  async function loadPlugins(baseId?: string): Promise<void> {
    lastListBaseId = baseId;
    loading.value = true;
    try {
      plugins.value = await fetchPlugins(baseId);
    } catch (error) {
      console.error("[pluginStore] 插件列表加载失败:", error);
      plugins.value = [];
    } finally {
      loading.value = false;
    }
  }

  /** 上传安装/升级 */
  async function upload(file: File): Promise<{ action: string } | null> {
    uploading.value = true;
    uploadProgress.value = 0;
    try {
      const result = await uploadPlugin(file, (p) => {
        uploadProgress.value = p;
      });
      await loadPlugins(lastListBaseId);
      return { action: result.action };
    } catch (error) {
      console.error("[pluginStore] 插件上传失败:", error);
      throw error;
    } finally {
      uploading.value = false;
      uploadProgress.value = 0;
    }
  }

  /** 全局启用/禁用/恢复 */
  async function setStatus(
    pluginId: string,
    status: PluginStatus,
  ): Promise<void> {
    await setPluginStatus(pluginId, status);
    await loadPlugins(lastListBaseId);
  }

  /** 回滚版本 */
  async function rollback(pluginId: string, version: string): Promise<void> {
    await rollbackPlugin(pluginId, version);
    await loadPlugins(lastListBaseId);
  }

  /** 卸载 */
  async function uninstall(pluginId: string): Promise<void> {
    await uninstallPlugin(pluginId);
    await loadPlugins(lastListBaseId);
  }

  /** 加载版本历史 */
  async function loadVersions(pluginId: string): Promise<PluginVersion[]> {
    const { fetchPlugin } = await import("@/api/plugins");
    const detail = await fetchPlugin(pluginId);
    versions.value[pluginId] = detail.versions || [];
    return versions.value[pluginId];
  }

  /** 配置读写 */
  async function loadConfig(
    pluginId: string,
    baseId?: string,
    scope?: "global" | "base",
  ): Promise<Record<string, unknown>> {
    const cfg = await fetchPluginConfig(pluginId, baseId, scope);
    configs.value[`${pluginId}:${baseId || "global"}`] = cfg || {};
    return cfg || {};
  }

  async function saveConfig(
    pluginId: string,
    scope: "global" | "base",
    config: Record<string, unknown>,
    baseId?: string,
  ): Promise<void> {
    await savePluginConfig(pluginId, scope, config, baseId);
  }

  /** Base 级安装/启停/移除 */
  async function installToBase(
    pluginId: string,
    baseId: string,
  ): Promise<void> {
    await installPluginToBase(pluginId, baseId);
    await loadPlugins(baseId);
  }

  async function setBaseEnabled(
    pluginId: string,
    baseId: string,
    enabled: boolean,
  ): Promise<void> {
    await setPluginInstallationEnabled(pluginId, baseId, enabled);
    await loadPlugins(baseId);
  }

  async function removeFromBase(
    pluginId: string,
    baseId: string,
  ): Promise<void> {
    await uninstallPluginFromBase(pluginId, baseId);
    await loadPlugins(baseId);
  }

  /** 运行脚本插件 */
  /** 是否有脚本正在运行（用于按钮 loading） */
  const running = ref(false);

  async function run(
    pluginId: string,
    baseId: string,
  ): Promise<{
    status: string;
    output: string;
    result?: unknown;
    error?: string;
    duration_ms?: number;
    base_id?: string;
  }> {
    running.value = true;
    try {
      const result = await runScriptPlugin(pluginId, baseId);
      return {
        status: result.status,
        output: result.output,
        result: result.result,
        error: result.error,
        duration_ms: result.duration_ms,
        base_id: result.base_id,
      };
    } finally {
      running.value = false;
    }
  }

  /** 运行日志 */
  async function loadRunLogs(
    pluginId: string,
    baseId: string,
  ): Promise<PluginRunLog[]> {
    const list = await fetchRunLogs(pluginId, baseId);
    // 兜底：保证始终是数组，避免 el-table 收到非数组导致渲染崩溃
    runLogs.value = Array.isArray(list) ? list : [];
    return runLogs.value;
  }

  return {
    plugins,
    versions,
    configs,
    runLogs,
    loading,
    uploading,
    uploadProgress,
    filterKeyword,
    filterType,
    filteredPlugins,
    uiPlugins,
    scriptPlugins,
    loadPlugins,
    upload,
    setStatus,
    rollback,
    uninstall,
    loadVersions,
    loadConfig,
    saveConfig,
    installToBase,
    setBaseEnabled,
    removeFromBase,
    run,
    running,
    loadRunLogs,
  };
});

/**
 * 插件操作提示（组件内使用，需 i18n 上下文）
 */
export function usePluginMessages() {
  const { t } = useI18n();
  return {
    success: (msg: string) => ElMessage.success(msg),
    error: (msg: string) => ElMessage.error(msg),
    t,
  };
}

export type { PluginEntity, PluginStatus };
