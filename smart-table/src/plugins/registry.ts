/**
 * 插件注册表（前端）
 *
 * 职责：
 * - 维护当前 Base 下「有效启用」的插件（全局 enabled 且 Base 级 enabled）
 * - 按 UI 扩展点类型归类插件，供宿主组件挂载
 * - 记录插件运行时错误（错误边界数据），单插件异常不影响其他插件与宿主
 */
import { ref, computed } from "vue";
import { fetchPlugins } from "@/api/plugins";
import type {
  PluginEntity,
  ExtensionPoint,
  ExtensionPointType,
  PluginStatus,
  SelectionSummary,
} from "./types";

/** 插件运行时错误记录 */
export interface PluginErrorRecord {
  pluginId: string;
  extensionType: ExtensionPointType;
  message: string;
  at: number;
}

const plugins = ref<PluginEntity[]>([]);
const errors = ref<PluginErrorRecord[]>([]);
const loading = ref(false);

/** 当前上下文（挂载扩展点需要知道 baseId/tableId） */
const context = ref<{ baseId: string; tableId: string }>({
  baseId: "",
  tableId: "",
});

/** 已加载插件列表的 baseId（按 Base 去重：宿主组件重复挂载/多实例不重复请求） */
const loadedBaseId = ref("");
/** 进行中的加载请求（单飞：并发调用合并为一次网络请求） */
let loadInFlight: Promise<void> | null = null;

/**
 * 加载某 Base 的插件列表进 registry。
 * - 同一 Base 已加载过则直接复用，不重复请求；
 * - 并发调用合并为同一次请求（首次打开 Base 时"挂载→路由解析出 tableId→重挂载"只发一次）；
 * - 插件管理页发生变更后应调用 invalidatePluginsCache() 失效缓存。
 */
export async function loadPluginsForBase(baseId: string): Promise<void> {
  if (!baseId) return;
  if (loadedBaseId.value === baseId) return;
  if (loadInFlight) return loadInFlight;
  setLoading(true);
  loadInFlight = fetchPlugins(baseId)
    .then((list) => {
      setPlugins(list);
      loadedBaseId.value = baseId;
    })
    .catch((error) => {
      console.warn("[registry] 插件列表加载失败（已降级为无插件）:", error);
      setPlugins([]);
      // 失败同样标记为已加载，避免宿主重复挂载时反复重试；切换 Base 或失效缓存后会重新加载
      loadedBaseId.value = baseId;
    })
    .finally(() => {
      setLoading(false);
      loadInFlight = null;
    });
  return loadInFlight;
}

/** 使插件列表缓存失效（插件管理页安装/启停/卸载等变更后调用，下次进入 Base 重新拉取） */
export function invalidatePluginsCache(): void {
  loadedBaseId.value = "";
}

/**
 * 当前表格的勾选状态（由页面/表格组件上报）
 * 仅含记录 ID 与计数，供工具栏按钮可用性判断；真正传给插件的快照在打开插件时生成。
 */
const selection = ref<SelectionSummary | null>(null);

/** 上报当前勾选状态（切换表格/清空勾选时传 null） */
export function setSelection(summary: SelectionSummary | null): void {
  selection.value = summary;
}

/** 当前勾选条数（未接入表格时为 0） */
export const selectionCount = computed(() => selection.value?.total ?? 0);

/** 有效启用：全局 enabled 且 Base 级 enabled */
export function isEffective(plugin: PluginEntity): boolean {
  const globalOk = plugin.status === "enabled";
  const baseOk = plugin.baseEnabled === true;
  return globalOk && baseOk;
}

/** 全局状态是否为异常（连续运行失败自动置入） */
export function isErrorState(status: PluginStatus): boolean {
  return status === "error";
}

export function setPlugins(list: PluginEntity[]): void {
  plugins.value = list || [];
}

export function setLoading(value: boolean): void {
  loading.value = value;
}

export function setContext(next: Partial<{ baseId: string; tableId: string }>): void {
  context.value = { ...context.value, ...next };
}

/** 记录插件运行时错误（错误隔离：仅影响该插件挂载点） */
export function reportPluginError(
  pluginId: string,
  extensionType: ExtensionPointType,
  message: string,
): void {
  errors.value = [
    ...errors.value.filter((e) => !(e.pluginId === pluginId && e.extensionType === extensionType)),
    { pluginId, extensionType, message, at: Date.now() },
  ];
}

export function clearPluginErrors(pluginId: string): void {
  errors.value = errors.value.filter((e) => e.pluginId !== pluginId);
}

/** 按扩展点类型取插件声明 */
function collectExtensionPoints(
  type: ExtensionPointType,
): Array<{ plugin: PluginEntity; extension: ExtensionPoint }> {
  const result: Array<{ plugin: PluginEntity; extension: ExtensionPoint }> = [];
  for (const plugin of plugins.value) {
    if (!isEffective(plugin)) continue;
    if (plugin.type !== "ui") continue;
    if (isErrorState(plugin.status)) continue;
    for (const ep of plugin.manifest?.extensionPoints || []) {
      if (ep.type === type) {
        result.push({ plugin, extension: ep });
      }
    }
  }
  return result;
}

/** 工具栏按钮扩展点 */
export const toolbarButtons = computed(() =>
  collectExtensionPoints("toolbar-button"),
);

/** 侧边面板扩展点（以插件 id 索引，工具栏按钮点击后打开对应面板） */
export const sidePanels = computed(() => {
  const map = new Map<string, ExtensionPoint>();
  for (const { plugin, extension } of collectExtensionPoints("side-panel")) {
    map.set(plugin.id, extension);
  }
  return map;
});

/** Base 级菜单扩展点 */
export const baseMenuItems = computed(() =>
  collectExtensionPoints("base-menu"),
);

/** 记录详情区块扩展点 */
export const recordDetailBlocks = computed(() =>
  collectExtensionPoints("record-detail-block"),
);

export const pluginRegistry = {
  plugins,
  errors,
  loading,
  context,
  selection,
  selectionCount,
  isEffective,
  setSelection,
  setPlugins,
  setLoading,
  setContext,
  reportPluginError,
  clearPluginErrors,
  toolbarButtons,
  sidePanels,
  baseMenuItems,
  recordDetailBlocks,
};

export default pluginRegistry;
