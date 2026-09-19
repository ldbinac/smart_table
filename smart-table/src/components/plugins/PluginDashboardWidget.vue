<script setup lang="ts">
/**
 * 仪表盘插件自定义组件（dashboard-widget 扩展点宿主）
 *
 * 包装 PluginSandbox，按插件 ID 在仪表盘网格单元内渲染对应插件 iframe。
 * 与 Base 作用域对齐（沿用当前仪表盘所属 Base 的安装与权限）。
 */
import PluginSandbox from "./PluginSandbox.vue";

defineProps<{
  pluginId: string;
  baseId: string;
  tableId?: string;
}>();
</script>

<template>
  <div class="plugin-dashboard-widget">
    <PluginSandbox
      :plugin-id="pluginId"
      :base-id="baseId"
      :table-id="tableId"
      extension-type="dashboard-widget" />
  </div>
</template>

<style scoped>
.plugin-dashboard-widget {
  width: 100%;
  height: 100%;
  overflow: hidden;
}
</style>
