<script setup lang="ts">
/**
 * 插件 UI 扩展点宿主组件（工具栏按钮 + 侧边面板）
 *
 * 挂载到数据表工具栏区域：渲染所有有效启用插件声明的 toolbar-button 扩展点，
 * 点击后在右侧 Drawer 中加载对应插件的 side-panel（iframe 沙箱）。
 */
import { ref, computed, watch } from "vue";
import { useRoute } from "vue-router";
import * as Icons from "@element-plus/icons-vue";
import {
  pluginRegistry,
  setContext,
  loadPluginsForBase,
} from "@/plugins/registry";
import PluginSandbox from "./PluginSandbox.vue";

const route = useRoute();

const panelVisible = ref(false);
const activePluginId = ref("");
const activeTitle = ref("");
const sandboxKey = ref(0); // 强制重建沙箱（切换插件/重试）

const baseId = computed(() => String(route.params.id || ""));
const tableId = computed(() => String(route.params.tableId || ""));

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
        :title="`${item.extension.title}（${item.plugin.name}）`"
        @click="openPanel(item.plugin.id, item.extension.title)">
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
