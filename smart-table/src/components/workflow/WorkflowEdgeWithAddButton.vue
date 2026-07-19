<script setup lang="ts">
import { computed, ref } from "vue";
import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath } from "@vue-flow/core";
import { Plus, Delete } from "@element-plus/icons-vue";
import type { EdgeProps } from "@vue-flow/core";
import { ADDABLE_NODE_TYPES } from "@/utils/workflowNodeType";

interface EdgeData {
  readonly?: boolean;
  sourceNodeType?: string;
  branchId?: string;
  branchName?: string;
}

const props = defineProps<EdgeProps<EdgeData>>();
const emit = defineEmits<{
  (
    e: "edge-insert",
    payload: { sourceId: string; targetId: string; nodeType: string },
  ): void;
  (
    e: "edge-delete",
    payload: { sourceId: string; targetId: string; branchId?: string },
  ): void;
}>();

const path = computed(() => getSmoothStepPath(props));
const menuVisible = ref(false);

const nodeTypeMenu = ADDABLE_NODE_TYPES;

const isConditionSource = computed(
  () => props.data?.sourceNodeType === "condition",
);

const branchName = computed(() => props.data?.branchName ?? "满足条件");

const sourceLabelPosition = computed(() => {
  const [, labelX, labelY] = path.value;
  const ratio = 0.25;
  return {
    x: props.sourceX + (labelX - props.sourceX) * ratio,
    y: props.sourceY + (labelY - props.sourceY) * ratio,
  };
});

function handleSelect(nodeType: string) {
  menuVisible.value = false;
  emit("edge-insert", {
    sourceId: props.source,
    targetId: props.target,
    nodeType,
  });
}

function handleDelete() {
  emit("edge-delete", {
    sourceId: props.source,
    targetId: props.target,
    branchId: props.data?.branchId,
  });
}
</script>

<template>
  <BaseEdge :path="path[0]" />

  <EdgeLabelRenderer>
    <div
      v-if="!data?.readonly && !isConditionSource"
      class="edge-add-button-wrapper nodrag nopan"
      :style="{
        position: 'absolute',
        transform: `translate(-50%, -50%) translate(${path[1]}px, ${path[2]}px)`,
        pointerEvents: 'all',
      }"
    >
      <button class="edge-add-button" @click="menuVisible = !menuVisible">
        <Plus />
      </button>

      <div v-if="menuVisible" class="edge-add-menu">
        <div
          v-for="item in nodeTypeMenu"
          :key="item.type"
          class="edge-add-menu-item"
          @click="handleSelect(item.type)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
      </div>
    </div>

    <div
      v-if="!data?.readonly && isConditionSource"
      class="edge-delete-button-wrapper nodrag nopan"
      :style="{
        position: 'absolute',
        transform: `translate(-50%, -50%) translate(${path[1]}px, ${path[2]}px)`,
        pointerEvents: 'all',
      }"
    >
      <button class="edge-delete-button" title="删除连线" @click="handleDelete">
        <Delete />
      </button>
    </div>

    <div
      v-if="isConditionSource"
      class="edge-source-label nodrag nopan"
      :style="{
        position: 'absolute',
        transform: `translate(-50%, -50%) translate(${sourceLabelPosition.x}px, ${sourceLabelPosition.y}px)`,
        pointerEvents: 'none',
      }"
    >
      {{ branchName }}
    </div>
  </EdgeLabelRenderer>
</template>

<style lang="scss" scoped>
.edge-add-button-wrapper {
  z-index: 10;
}

.edge-add-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  padding: 0;
  color: white;
  cursor: pointer;
  background-color: $primary-color;
  border: none;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
  transition: background-color 0.2s, transform 0.2s;

  &:hover {
    background-color: rgba($primary-color, 0.85);
    transform: scale(1.15);
  }

  svg {
    width: 12px;
    height: 12px;
  }
}

.edge-add-menu {
  position: absolute;
  top: 22px;
  left: 50%;
  min-width: 120px;
  padding: 4px 0;
  background-color: white;
  border: 1px solid $border-color;
  border-radius: $border-radius-md;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateX(-50%);
}

.edge-add-menu-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: $font-size-sm;
  color: $text-primary;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.2s;

  .el-icon {
    font-size: 16px;
    color: $primary-color;
  }

  &:hover {
    background-color: rgba($primary-color, 0.08);
  }
}

.edge-delete-button-wrapper {
  z-index: 10;
}

.edge-delete-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  padding: 0;
  color: white;
  cursor: pointer;
  background-color: $error-color;
  border: none;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
  transition: background-color 0.2s, transform 0.2s;

  &:hover {
    background-color: rgba($error-color, 0.85);
    transform: scale(1.15);
  }

  svg {
    width: 10px;
    height: 10px;
  }
}

.edge-source-label {
  padding: 2px 6px;
  font-size: 12px;
  color: $text-secondary;
  background-color: white;
  border: 1px solid $border-color;
  border-radius: $border-radius-sm;
}

:deep(.vue-flow__edge-path) {
  stroke-width: 2.5px;
}
</style>
