<script setup lang="ts">
import { computed, ref } from "vue";
import type { FieldEntity } from "@/db/schema";
import { FieldType } from "@/types";

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

const fieldIcon = computed(() => {
  const icons: Record<string, string> = {
    [FieldType.TEXT]: "text",
    [FieldType.NUMBER]: "number",
    [FieldType.DATE]: "calendar",
    [FieldType.SINGLE_SELECT]: "select",
    [FieldType.MULTI_SELECT]: "multi-select",
    [FieldType.CHECKBOX]: "checkbox",
    [FieldType.ATTACHMENT]: "attachment",
    [FieldType.MEMBER]: "user",
    [FieldType.RATING]: "star",
    [FieldType.PROGRESS]: "progress",
    [FieldType.PHONE]: "phone",
    [FieldType.EMAIL]: "email",
    [FieldType.URL]: "link",
    [FieldType.FORMULA]: "formula",
    [FieldType.LINK]: "link",
    [FieldType.LOOKUP]: "lookup",
    [FieldType.CREATED_BY]: "user",
    [FieldType.CREATED_TIME]: "clock",
    [FieldType.UPDATED_BY]: "user",
    [FieldType.UPDATED_TIME]: "clock",
    [FieldType.AUTO_NUMBER]: "auto-number",
  };
  return icons[props.field.type] || "text";
});

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
        <svg
          v-if="fieldIcon === 'text'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <path d="M4 7V4h16v3M9 20h6M12 4v16" />
        </svg>
        <svg
          v-else-if="fieldIcon === 'number'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <path d="M4 17h6M10 7l-2 10M14 7l4 10M14 17h4" />
        </svg>
        <svg
          v-else-if="fieldIcon === 'calendar'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <rect x="3" y="4" width="18" height="18" rx="2" />
          <path d="M16 2v4M8 2v4M3 10h18" />
        </svg>
        <svg
          v-else-if="fieldIcon === 'select'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <circle cx="12" cy="12" r="8" />
        </svg>
        <svg
          v-else-if="fieldIcon === 'multi-select'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <circle cx="8" cy="8" r="4" />
          <circle cx="16" cy="16" r="4" />
        </svg>
        <svg
          v-else-if="fieldIcon === 'checkbox'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M9 12l2 2 4-4" />
        </svg>
        <svg
          v-else-if="fieldIcon === 'attachment'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <path
            d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
        </svg>
        <svg
          v-else-if="fieldIcon === 'user'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
        <svg
          v-else-if="fieldIcon === 'star'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <polygon
            points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
        <svg
          v-else-if="fieldIcon === 'progress'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <rect x="3" y="10" width="18" height="4" rx="2" />
          <path d="M3 12h10" />
        </svg>
        <svg
          v-else-if="fieldIcon === 'phone'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <path
            d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z" />
        </svg>
        <svg
          v-else-if="fieldIcon === 'email'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <path
            d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
          <polyline points="22,6 12,13 2,6" />
        </svg>
        <svg
          v-else-if="fieldIcon === 'link'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
          <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
        </svg>
        <svg
          v-else-if="fieldIcon === 'formula'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM17 14v6M14 17h6" />
        </svg>
        <svg
          v-else-if="fieldIcon === 'clock'"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
        <svg
          v-else
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2">
          <path d="M4 7V4h16v3M9 20h6M12 4v16" />
        </svg>
      </span>
      <span class="field-name">{{ field.name }}</span>
      <span v-if="sortDirection" class="sort-indicator">
        <svg
          v-if="sortDirection === 'asc'"
          viewBox="0 0 24 24"
          fill="currentColor"
          width="12"
          height="12">
          <path d="M12 4l-8 8h16z" />
        </svg>
        <svg
          v-else
          viewBox="0 0 24 24"
          fill="currentColor"
          width="12"
          height="12">
          <path d="M12 20l8-8H4z" />
        </svg>
      </span>
    </div>

    <div v-if="resizable" class="resize-handle" @mousedown.stop="startResize" />

    <div v-if="isFrozen" class="frozen-indicator">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        width="12"
        height="12">
        <path d="M12 2v20M2 12h20" />
      </svg>
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
        content: "已冻结";
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

  svg {
    width: 16px;
    height: 16px;
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
