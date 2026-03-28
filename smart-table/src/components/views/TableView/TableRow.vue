<script setup lang="ts">
import { computed } from "vue";
import type { RecordEntity } from "@/db/schema";

interface Props {
  record: RecordEntity;
  index: number;
  isSelected?: boolean;
  isHovered?: boolean;
  rowHeight?: "short" | "medium" | "tall";
}

const props = withDefaults(defineProps<Props>(), {
  isSelected: false,
  isHovered: false,
  rowHeight: "medium",
});

const emit = defineEmits<{
  (e: "click", event: MouseEvent): void;
  (e: "dblclick", event: MouseEvent): void;
  (e: "contextmenu", event: MouseEvent): void;
  (e: "dragstart", event: DragEvent): void;
  (e: "dragend", event: DragEvent): void;
}>();

const rowHeightValue = computed(() => {
  const heights = {
    short: "28px",
    medium: "36px",
    tall: "48px",
  };
  return heights[props.rowHeight];
});

const handleClick = (event: MouseEvent) => {
  emit("click", event);
};

const handleDoubleClick = (event: MouseEvent) => {
  emit("dblclick", event);
};

const handleContextMenu = (event: MouseEvent) => {
  event.preventDefault();
  emit("contextmenu", event);
};

const handleDragStart = (event: DragEvent) => {
  emit("dragstart", event);
};

const handleDragEnd = (event: DragEvent) => {
  emit("dragend", event);
};
</script>

<template>
  <div
    class="table-row"
    :class="{
      'is-selected': isSelected,
      'is-hovered': isHovered,
      'is-even': index % 2 === 1,
    }"
    :style="{ height: rowHeightValue }"
    draggable="true"
    @click="handleClick"
    @dblclick="handleDoubleClick"
    @contextmenu="handleContextMenu"
    @dragstart="handleDragStart"
    @dragend="handleDragEnd">
    <slot />
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.table-row {
  display: flex;
  width: 100%;
  min-height: 28px;
  background-color: $surface-color;
  border-bottom: 1px solid $border-color;
  transition: background-color $transition-fast;

  &.is-even {
    background-color: rgba($bg-color, 0.5);
  }

  &.is-hovered {
    background-color: rgba($primary-color, 0.05);
  }

  &.is-selected {
    background-color: rgba($primary-color, 0.1);

    &.is-hovered {
      background-color: rgba($primary-color, 0.15);
    }
  }

  &:hover {
    .row-index {
      opacity: 1;
    }
  }
}
</style>
