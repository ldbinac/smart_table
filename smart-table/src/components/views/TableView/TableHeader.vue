<script setup lang="ts">
import { ref } from "vue";
import type { FieldEntity } from "@/db/schema";
import { getFieldTypeIconComponent } from "@/types/fields";
import { Sort, Lock } from "@element-plus/icons-vue";

interface Props {
  field: FieldEntity;
  sortDirection?: "asc" | "desc" | null;
  isFrozen?: boolean;
  resizable?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  sortDirection: null,
  isFrozen: false,
  resizable: true,
});

const emit = defineEmits<{
  (e: "sort", direction: "asc" | "desc"): void;
  (e: "resize", width: number): void;
  (e: "freeze"): void;
  (e: "unfreeze"): void;
  (e: "hide"): void;
  (e: "contextmenu", event: MouseEvent): void;
}>();

const headerRef = ref<HTMLElement | null>(null);
const isResizing = ref(false);
const resizeStartX = ref(0);
const resizeStartWidth = ref(0);

const handleSort = () => {
  if (props.sortDirection === "asc") {
    emit("sort", "desc");
  } else if (props.sortDirection === "desc") {
    emit("sort", "asc");
  } else {
    emit("sort", "asc");
  }
};

const startResize = (event: MouseEvent) => {
  if (!props.resizable) return;

  isResizing.value = true;
  resizeStartX.value = event.clientX;
  resizeStartWidth.value = headerRef.value?.offsetWidth || 0;

  document.addEventListener("mousemove", onResize);
  document.addEventListener("mouseup", stopResize);
};

const onResize = (event: MouseEvent) => {
  if (!isResizing.value) return;

  const diff = event.clientX - resizeStartX.value;
  const newWidth = Math.max(60, resizeStartWidth.value + diff);

  emit("resize", newWidth);
};

const stopResize = () => {
  isResizing.value = false;
  document.removeEventListener("mousemove", onResize);
  document.removeEventListener("mouseup", stopResize);
};

const handleContextMenu = (event: MouseEvent) => {
  event.preventDefault();
  emit("contextmenu", event);
};
</script>

<template>
  <div
    ref="headerRef"
    class="table-header-cell"
    :class="{
      'is-frozen': isFrozen,
      'is-sorting': sortDirection !== null,
    }"
    @contextmenu="handleContextMenu">
    <div class="header-content" @click="handleSort">
      <span class="field-icon">
        <el-icon>
          <component :is="getFieldTypeIconComponent(field.type)" />
        </el-icon>
      </span>
      <span class="field-name">{{ field.name }}</span>
      <span v-if="sortDirection" class="sort-indicator">
        <el-icon v-if="sortDirection === 'asc'">
          <Sort />
        </el-icon>
        <el-icon v-else>
          <Sort style="transform: rotate(180deg)" />
        </el-icon>
      </span>
    </div>

    <div v-if="resizable" class="resize-handle" @mousedown.stop="startResize" />

    <div v-if="isFrozen" class="frozen-indicator">
      <el-icon><Lock /></el-icon>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.table-header-cell {
  position: relative;
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 12px;
  background-color: $gray-50;
  border-right: 1px solid $gray-200;
  border-bottom: 1px solid $gray-200;
  font-size: $font-size-sm;
  font-weight: 600;
  color: $gray-700;
  user-select: none;
  transition: background-color $transition-fast;

  &:hover {
    background-color: $gray-100;
  }

  &.is-frozen {
    background-color: $gray-100;

    .frozen-indicator {
      position: absolute;
      right: 4px;
      top: 50%;
      transform: translateY(-50%);
      color: $primary-color;
      display: flex;
      align-items: center;
      gap: 2px;
      font-size: 10px;
      font-weight: 500;

      &::after {
        content: "冻结";
      }
    }
  }

  &.is-sorting {
    color: $primary-color;
    background-color: rgba($primary-color, 0.05);

    .field-icon {
      color: $primary-color;
    }
  }
}

.header-content {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  cursor: pointer;

  &:hover {
    color: $gray-900;
  }
}

.field-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  color: $gray-500;

  .el-icon {
    font-size: 16px;
  }
}

.field-name {
  @include text-ellipsis;
  flex: 1;
}

.sort-indicator {
  display: flex;
  align-items: center;
  color: $primary-color;
}

.resize-handle {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  cursor: col-resize;

  &:hover {
    background-color: $primary-color;
  }
}
</style>
