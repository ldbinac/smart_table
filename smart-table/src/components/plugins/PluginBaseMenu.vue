<script setup lang="ts">
/**
 * 插件 UI 扩展点宿主组件（base-menu）
 *
 * 在 Base 工具栏以下拉菜单聚合所有有效启用插件声明的 base-menu 扩展点，
 * 点击后在对话框中加载对应插件的 iframe 沙箱（extension-type=base-menu）。
 */
import { ref, computed } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { ArrowDown } from "@element-plus/icons-vue";
import * as Icons from "@element-plus/icons-vue";
import {
  pluginRegistry,
  setContext,
  loadPluginsForBase,
} from "@/plugins/registry";
import type {
  ExtensionPoint,
  PluginEntity,
} from "@/plugins/types";
import PluginSandbox from "./PluginSandbox.vue";

const route = useRoute();
const { t } = useI18n();

const baseId = computed(() => String(route.params.id || ""));
const tableId = computed(
  () => String(route.params.tableId || ""),
);

const items = computed(() => pluginRegistry.baseMenuItems.value);

function resolveIcon(name?: string) {
  if (!name) return Icons.Menu;
  return (Icons as Record<string, unknown>)[name] ?? Icons.Menu;
}

const dialogVisible = ref(false);
const activePluginId = ref("");
const activeTitle = ref("");
const sandboxKey = ref(0);

function ensureLoaded(): void {
  if (!baseId.value) return;
  setContext({ baseId: baseId.value, tableId: tableId.value });
  // 去重加载在 registry 内完成，重复调用不会重复请求
  void loadPluginsForBase(baseId.value);
}
ensureLoaded();

function open(item: {
  plugin: PluginEntity;
  extension: ExtensionPoint;
}): void {
  activePluginId.value = item.plugin.id;
  activeTitle.value = item.extension.title;
  sandboxKey.value += 1;
  dialogVisible.value = true;
}

function handleClosed(): void {
  activePluginId.value = "";
  dialogVisible.value = false;
}
</script>

<template>
  <el-dropdown
    v-if="items.length > 0"
    trigger="click"
    @command="open">
    <el-button size="default">
      <el-icon><component :is="resolveIcon('Menu')" /></el-icon>
      <span style="margin: 0 4px">{{ t("plugin.baseMenu") }}</span>
      <el-icon class="el-icon--right"><ArrowDown /></el-icon>
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="item in items"
          :key="`${item.plugin.id}:${item.extension.title}`"
          :command="item">
          <el-icon v-if="item.extension.icon">
            <component :is="resolveIcon(item.extension.icon)" />
          </el-icon>
          <span style="margin-left: 4px">{{ item.extension.title }}</span>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>

  <el-dialog
    v-model="dialogVisible"
    :title="activeTitle"
    width="60%"
    @closed="handleClosed">
    <!-- 显式高度：el-dialog body 高度由内容决定，iframe height:100% 无参照
         会退化为浏览器默认 150px，这里按视口 80% 给定 -->
    <div class="plugin-dialog-panel">
      <PluginSandbox
        v-if="dialogVisible && activePluginId"
        :key="sandboxKey"
        :plugin-id="activePluginId"
        :base-id="baseId"
        :table-id="tableId"
        extension-type="base-menu" />
    </div>
  </el-dialog>
</template>

<style scoped>
.plugin-dialog-panel {
  height: 80vh;
}
</style>
