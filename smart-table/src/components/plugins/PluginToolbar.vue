<script setup lang="ts">
/**
 * 插件 UI 扩展点宿主组件（工具栏按钮 + 侧边面板）
 *
 * 挂载到数据表工具栏区域：渲染所有有效启用插件声明的 toolbar-button 扩展点，
 * 点击后在右侧 Drawer 中加载对应插件的 side-panel（iframe 沙箱）。
 */
import { ref, computed, watch } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import * as Icons from "@element-plus/icons-vue";
import {
  pluginRegistry,
  setContext,
  loadPluginsForBase,
} from "@/plugins/registry";
import { checkSelectionRequirement, getSelectionSummary } from "@/plugins/selection";
import type {
  ExtensionPoint,
  PluginEntity,
  SelectionSummary,
} from "@/plugins/types";
import { useTableStore } from "@/stores/tableStore";
import PluginSandbox from "./PluginSandbox.vue";

const route = useRoute();
const { t } = useI18n();
const tableStore = useTableStore();

const panelVisible = ref(false);
const activePluginId = ref("");
const activeTitle = ref("");
const sandboxKey = ref(0); // 强制重建沙箱（切换插件/重试）

const baseId = computed(() => String(route.params.id || ""));
// 路由为 /base/:id（无 tableId）时，Base.vue 会默认选中第一个表格但不改路由，
// 此时回退到 store 中当前选中的表格，避免插件上下文缺失 tableId
const tableId = computed(
  () => String(route.params.tableId || tableStore.currentTable?.id || ""),
);

const buttons = computed(() => pluginRegistry.toolbarButtons.value);

/** 图标名 → Element Plus 图标组件（未知名称回退为 Grid） */
function resolveIcon(name?: string) {
  if (!name) return Icons.Grid;
  return (Icons as Record<string, unknown>)[name] ?? Icons.Grid;
}

async function loadPlugins(): Promise<void> {
  if (!baseId.value) return;
  setContext({ baseId: baseId.value, tableId: tableId.value });
  // 去重加载在 registry 内完成：组件被条件渲染重复挂载/多实例时不会重复请求
  await loadPluginsForBase(baseId.value);
}

/** 扩展点声明的勾选约束 */
function requirementOf(extension: ExtensionPoint) {
  return {
    requiresSelection: extension.requiresSelection,
    maxSelection: extension.maxSelection,
  };
}

/** 依据当前勾选判断按钮可用性（声明了 requiresSelection/maxSelection 才约束） */
function buttonState(item: { plugin: PluginEntity; extension: ExtensionPoint }) {
  return checkSelectionRequirement(
    pluginRegistry.selection.value as SelectionSummary | null,
    requirementOf(item.extension),
  );
}

function isButtonAvailable(item: {
  plugin: PluginEntity;
  extension: ExtensionPoint;
}): boolean {
  return buttonState(item).ok;
}

/** 按钮悬浮提示：不满足时给出原因，满足且声明了依赖时显示已选条数 */
function buttonTitle(item: {
  plugin: PluginEntity;
  extension: ExtensionPoint;
}): string {
  const base = `${item.extension.title}（${item.plugin.name}）`;
  const state = buttonState(item);
  if (!state.ok) {
    return state.reason === "empty"
      ? t("plugin.selection.selectFirst")
      : t("plugin.selection.maxExceeded", {
          n: item.extension.maxSelection ?? 0,
        });
  }
  const declared = Boolean(
    item.extension.requiresSelection || item.extension.maxSelection,
  );
  return declared
    ? `${base} · ${t("plugin.selection.selectedCount", { n: state.count })}`
    : base;
}

/** 点击入口：按声明校验勾选（以打开瞬间的最新勾选为准），不满足则提示 */
function handleButtonClick(item: {
  plugin: PluginEntity;
  extension: ExtensionPoint;
}): void {
  const state = checkSelectionRequirement(
    getSelectionSummary(),
    requirementOf(item.extension),
  );
  if (!state.ok) {
    ElMessage.warning(
      state.reason === "empty"
        ? t("plugin.selection.selectFirst")
        : t("plugin.selection.maxExceeded", {
            n: item.extension.maxSelection ?? 0,
          }),
    );
    return;
  }
  openPanel(item.plugin.id, item.extension.title);
}

function openPanel(pluginId: string, title: string): void {
  activePluginId.value = pluginId;
  activeTitle.value = title;
  sandboxKey.value += 1;
  panelVisible.value = true;
}

function handlePanelClosed(): void {
  // 关闭时销毁 iframe，释放沙箱资源
  activePluginId.value = "";
  panelVisible.value = false;
}

// 插件列表只与 baseId 相关：仅 Base 变化时重新加载，
// 避免"进入 Base 先后解析出 tableId"导致接口被连续请求两次，
// 以及同一 Base 内切换表格时的重复请求
watch(
  () => baseId.value,
  () => {
    setContext({ baseId: baseId.value, tableId: tableId.value });
    loadPlugins();
  },
  { immediate: true },
);

// tableId 仅影响插件运行上下文（沙箱内 table.getRecord 等），变化时只更新 registry 上下文
watch(
  () => tableId.value,
  () => {
    setContext({ baseId: baseId.value, tableId: tableId.value });
  },
);
</script>

<template>
  <div v-if="buttons.length > 0" class="plugin-toolbar">
    <el-button-group>
      <el-button
        v-for="item in buttons"
        :key="item.plugin.id"
        size="default"
        :disabled="!isButtonAvailable(item)"
        :title="buttonTitle(item)"
        @click="handleButtonClick(item)">
        <el-icon>
          <component :is="resolveIcon(item.extension.icon)" />
        </el-icon>
        {{ item.extension.title }}
      </el-button>
    </el-button-group>

    <el-drawer
      v-model="panelVisible"
      :title="activeTitle"
      size="50%"
      @closed="handlePanelClosed">
      <PluginSandbox
        v-if="panelVisible && activePluginId"
        :key="sandboxKey"
        :plugin-id="activePluginId"
        :base-id="baseId"
        :table-id="tableId"
        extension-type="side-panel" />
    </el-drawer>
  </div>
</template>

<style scoped>
.plugin-toolbar {
  display: inline-flex;
  align-items: center;
}
</style>
