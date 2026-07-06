<script setup lang="ts">
import { computed, ref } from "vue";
import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath } from "@vue-flow/core";
import { Plus } from "@element-plus/icons-vue";
import type { EdgeProps } from "@vue-flow/core";

interface EdgeData {
  readonly?: boolean;
  sourceNodeType?: string;
}

const props = defineProps<EdgeProps<EdgeData>>();
const emit = defineEmits<{
  (
    e: "edge-insert",
    payload: { sourceId: string; targetId: string; nodeType: string },
  ): void;
}>();

const path = computed(() => getSmoothStepPath(props));
const menuVisible = ref(false);

const nodeTypeMenu = [
  { type: "update_record", label: "更新记录" },
  { type: "create_record", label: "创建记录" },
  { type: "webhook", label: "Webhook" },
  { type: "condition", label: "条件节点" },
];

const isConditionSource = computed(
  () => props.data?.sourceNodeType === "condition",
);

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
</script>

<template>
  <BaseEdge :path="path[0]" />

  <EdgeLabelRenderer>
    <div
      v-if="!data?.readonly"
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
          {{ item.label }}
        </div>
      </div>
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
      满足条件
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
  width: 24px;
  height: 24px;
  padding: 0;
  color: white;
  cursor: pointer;
  background-color: $primary-color;
  border: none;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
  transition: background-color 0.2s, transform 0.2s;

  &:hover {
    background-color: rgba($primary-color, 0.85);
    transform: scale(1.1);
  }

  svg {
    width: 14px;
    height: 14px;
  }
}

.edge-add-menu {
  position: absolute;
  top: 28px;
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
  padding: 8px 12px;
  font-size: $font-size-sm;
  color: $text-primary;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.2s;

  &:hover {
    background-color: rgba($primary-color, 0.08);
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
</style>
