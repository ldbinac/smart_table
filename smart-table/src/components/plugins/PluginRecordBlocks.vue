<script setup lang="ts">
/**
 * 插件 UI 扩展点宿主组件（record-detail-block）
 *
 * 在记录详情抽屉底部聚合所有有效启用插件声明的 record-detail-block 扩展点，
 * 每个区块加载一个 iframe 沙箱（携带 recordId，供插件读取当前记录上下文）。
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

const props = defineProps<{
  /** 当前记录 ID（来自记录详情抽屉） */
  recordId?: string;
  /** 当前记录所属表 ID（可选，缺省时由路由推断） */
  tableId?: string;
}>();

const route = useRoute();
const baseId = computed(() => String(route.params.id || ""));
const resolvedTableId = computed(
  () => props.tableId || String(route.params.tableId || ""),
);

const blocks = computed(() => pluginRegistry.recordDetailBlocks.value);

function resolveIcon(name?: string) {
  if (!name) return Icons.Grid;
  return (Icons as Record<string, unknown>)[name] ?? Icons.Grid;
}

// 各区块独立 key，确保切换记录时沙箱重建并刷新上下文
const sandboxKey = ref(0);
watch(
  () => props.recordId,
  (v) => {
    if (v) sandboxKey.value += 1;
  },
);

function ensureLoaded(): void {
  if (!baseId.value) return;
  setContext({ baseId: baseId.value, tableId: resolvedTableId.value });
  void loadPluginsForBase(baseId.value);
}
ensureLoaded();
</script>

<template>
  <div v-if="blocks.length > 0" class="plugin-record-blocks">
    <section
      v-for="item in blocks"
      :key="`${item.plugin.id}:${item.extension.title}`"
      class="plugin-record-block">
      <div class="plugin-record-block__title">
        <el-icon v-if="item.extension.icon">
          <component :is="resolveIcon(item.extension.icon)" />
        </el-icon>
        <span>{{ item.extension.title }}</span>
      </div>
      <div class="plugin-record-block__body">
        <PluginSandbox
          :key="`${sandboxKey}:${item.plugin.id}`"
          :plugin-id="item.plugin.id"
          :base-id="baseId"
          :table-id="resolvedTableId"
          :record-id="recordId"
          extension-type="record-detail-block" />
      </div>
    </section>
  </div>
</template>

<style scoped>
.plugin-record-blocks {
  margin-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 12px;
}
.plugin-record-block {
  margin-bottom: 16px;
}
.plugin-record-block__title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 8px;
}
.plugin-record-block__body {
  height: 320px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  overflow: hidden;
}
</style>
