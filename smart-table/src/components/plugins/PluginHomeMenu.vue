<script setup lang="ts">
/**
 * 插件 UI 扩展点宿主组件（home-menu）
 *
 * 在首页（Home）操作区以下拉菜单聚合所有全局启用的 home-menu 扩展点，
 * 点击后在对话框中加载对应插件的 iframe 沙箱。该扩展点为全局作用域，
 * 无 Base 上下文（baseId 为空），仅可使用 config/storage/backend/network 等无状态能力。
 */
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { ArrowDown } from "@element-plus/icons-vue";
import * as Icons from "@element-plus/icons-vue";
import {
  pluginRegistry,
  loadPluginsForHome,
} from "@/plugins/registry";
import type {
  ExtensionPoint,
  PluginEntity,
} from "@/plugins/types";
import PluginSandbox from "./PluginSandbox.vue";

const { t } = useI18n();

const items = computed(() => pluginRegistry.homeMenuItems.value);

function resolveIcon(name?: string) {
  if (!name) return Icons.Menu;
  return (Icons as Record<string, unknown>)[name] ?? Icons.Menu;
}

const dialogVisible = ref(false);
const activePluginId = ref("");
const activeTitle = ref("");
const sandboxKey = ref(0);

function ensureLoaded(): void {
  // 首页菜单为全局作用域，独立于任何 Base 加载插件注册表
  void loadPluginsForHome();
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
      <span style="margin: 0 4px">{{ t("plugin.homeMenu") }}</span>
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
        base-id=""
        extension-type="home-menu" />
    </div>
  </el-dialog>
</template>

<style scoped>
.plugin-dialog-panel {
  height: 80vh;
}
</style>
