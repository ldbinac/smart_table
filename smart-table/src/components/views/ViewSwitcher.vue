<script setup lang="ts">
import { ref, computed } from "vue";
import { useViewStore } from "@/stores/viewStore";
import { ViewType, type ViewTypeValue } from "@/types";

interface Props {
  tableId?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "view-change", viewId: string): void;
  (e: "view-create", type: ViewTypeValue): void;
}>();

const viewStore = useViewStore();

const showCreateMenu = ref(false);
const newViewName = ref("");
const newViewType = ref<ViewTypeValue>(ViewType.TABLE);
const isCreating = ref(false);
const editingViewId = ref<string | null>(null);
const editingViewName = ref("");

const views = computed(() => viewStore.sortedViews);
const currentView = computed(() => viewStore.currentView);

const viewTypes = [
  { type: ViewType.TABLE, label: "表格", icon: "table" },
  { type: ViewType.KANBAN, label: "看板", icon: "kanban" },
  { type: ViewType.CALENDAR, label: "日历", icon: "calendar" },
  { type: ViewType.GANTT, label: "甘特图", icon: "gantt" },
  { type: ViewType.FORM, label: "表单", icon: "form" },
  { type: ViewType.GALLERY, label: "画册", icon: "gallery" },
];

const getViewIcon = (type: string) => {
  const icons: Record<string, string> = {
    [ViewType.TABLE]: "table",
    [ViewType.KANBAN]: "kanban",
    [ViewType.CALENDAR]: "calendar",
    [ViewType.GANTT]: "gantt",
    [ViewType.FORM]: "form",
    [ViewType.GALLERY]: "gallery",
  };
  return icons[type] || "table";
};

const selectView = async (viewId: string) => {
  await viewStore.selectView(viewId);
  emit("view-change", viewId);
};

const startCreateView = (type: ViewTypeValue) => {
  newViewType.value = type;
  newViewName.value = `${getViewLabel(type)}视图`;
  showCreateMenu.value = true;
};

const createView = async () => {
  if (!newViewName.value.trim() || !props.tableId) return;

  isCreating.value = true;
  try {
    const view = await viewStore.createView({
      tableId: props.tableId,
      name: newViewName.value.trim(),
      type: newViewType.value,
    });

    if (view) {
      emit("view-create", newViewType.value);
      await selectView(view.id);
    }
  } finally {
    isCreating.value = false;
    showCreateMenu.value = false;
    newViewName.value = "";
  }
};

const startRenameView = (view: any) => {
  editingViewId.value = view.id;
  editingViewName.value = view.name;
};

const finishRename = async () => {
  if (!editingViewId.value || !editingViewName.value.trim()) {
    editingViewId.value = null;
    return;
  }

  await viewStore.updateView(editingViewId.value, {
    name: editingViewName.value.trim(),
  });
  editingViewId.value = null;
};

const cancelRename = () => {
  editingViewId.value = null;
  editingViewName.value = "";
};

const duplicateView = async (view: any) => {
  const newName = `${view.name} 副本`;
  await viewStore.duplicateView(view.id, newName);
};

const deleteView = async (view: any) => {
  if (views.value.length <= 1) {
    alert("至少保留一个视图");
    return;
  }

  if (confirm(`确定要删除视图 "${view.name}" 吗？`)) {
    await viewStore.deleteView(view.id);
  }
};

const setDefaultView = async (view: any) => {
  await viewStore.setDefaultView(view.id);
};

function getViewLabel(type: string): string {
  const typeInfo = viewTypes.find((t) => t.type === type);
  return typeInfo?.label || "表格";
}
</script>

<template>
  <div class="view-switcher">
    <div class="views-list">
      <div
        v-for="view in views"
        :key="view.id"
        class="view-item"
        :class="{ 'is-active': currentView?.id === view.id }"
        @click="selectView(view.id)">
        <span class="view-icon">
          <svg
            v-if="getViewIcon(view.type) === 'table'"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            width="14"
            height="14">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M3 9h18M3 15h18M9 3v18M15 3v18" />
          </svg>
          <svg
            v-else-if="getViewIcon(view.type) === 'kanban'"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            width="14"
            height="14">
            <rect x="3" y="3" width="5" height="18" rx="1" />
            <rect x="10" y="3" width="5" height="12" rx="1" />
            <rect x="17" y="3" width="5" height="15" rx="1" />
          </svg>
          <svg
            v-else-if="getViewIcon(view.type) === 'calendar'"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            width="14"
            height="14">
            <rect x="3" y="4" width="18" height="18" rx="2" />
            <path d="M16 2v4M8 2v4M3 10h18" />
          </svg>
          <svg
            v-else-if="getViewIcon(view.type) === 'gantt'"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            width="14"
            height="14">
            <path d="M3 6h8M3 12h12M3 18h6" />
            <rect x="11" y="4" width="10" height="4" rx="1" />
            <rect x="7" y="10" width="14" height="4" rx="1" />
            <rect x="9" y="16" width="12" height="4" rx="1" />
          </svg>
          <svg
            v-else-if="getViewIcon(view.type) === 'form'"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            width="14"
            height="14">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
          </svg>
          <svg
            v-else-if="getViewIcon(view.type) === 'gallery'"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            width="14"
            height="14">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <path d="M21 15l-5-5L5 21" />
          </svg>
        </span>

        <template v-if="editingViewId === view.id">
          <input
            v-model="editingViewName"
            class="view-name-input"
            @click.stop
            @keyup.enter="finishRename"
            @keyup.escape="cancelRename"
            @blur="finishRename"
            autofocus />
        </template>
        <template v-else>
          <span class="view-name">{{ view.name }}</span>
        </template>

        <span v-if="view.isDefault" class="default-badge">默认</span>

        <el-dropdown
          trigger="click"
          @command="
            (cmd: string) => {
              if (cmd === 'rename') startRenameView(view);
              else if (cmd === 'duplicate') duplicateView(view);
              else if (cmd === 'delete') deleteView(view);
              else if (cmd === 'default') setDefaultView(view);
            }
          ">
          <span class="view-menu-trigger" @click.stop>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              width="12"
              height="12">
              <circle cx="12" cy="12" r="1" />
              <circle cx="12" cy="5" r="1" />
              <circle cx="12" cy="19" r="1" />
            </svg>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="rename">重命名</el-dropdown-item>
              <el-dropdown-item command="duplicate">复制视图</el-dropdown-item>
              <el-dropdown-item v-if="!view.isDefault" command="default"
                >设为默认</el-dropdown-item
              >
              <el-dropdown-item command="delete" divided class="danger"
                >删除视图</el-dropdown-item
              >
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <el-dropdown
      trigger="click"
      @command="(type: ViewTypeValue) => startCreateView(type)">
      <button class="add-view-btn">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          width="14"
          height="14">
          <path d="M12 5v14M5 12h14" />
        </svg>
        <span>添加视图</span>
      </button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item
            v-for="vt in viewTypes"
            :key="vt.type"
            :command="vt.type">
            <span class="dropdown-icon">
              <svg
                v-if="vt.icon === 'table'"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                width="14"
                height="14">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <path d="M3 9h18M3 15h18M9 3v18M15 3v18" />
              </svg>
              <svg
                v-else-if="vt.icon === 'kanban'"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                width="14"
                height="14">
                <rect x="3" y="3" width="5" height="18" rx="1" />
                <rect x="10" y="3" width="5" height="12" rx="1" />
                <rect x="17" y="3" width="5" height="15" rx="1" />
              </svg>
              <svg
                v-else-if="vt.icon === 'calendar'"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                width="14"
                height="14">
                <rect x="3" y="4" width="18" height="18" rx="2" />
                <path d="M16 2v4M8 2v4M3 10h18" />
              </svg>
              <svg
                v-else-if="vt.icon === 'gantt'"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                width="14"
                height="14">
                <path d="M3 6h8M3 12h12M3 18h6" />
                <rect x="11" y="4" width="10" height="4" rx="1" />
                <rect x="7" y="10" width="14" height="4" rx="1" />
                <rect x="9" y="16" width="12" height="4" rx="1" />
              </svg>
              <svg
                v-else-if="vt.icon === 'form'"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                width="14"
                height="14">
                <path
                  d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
              </svg>
              <svg
                v-else-if="vt.icon === 'gallery'"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                width="14"
                height="14">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <path d="M21 15l-5-5L5 21" />
              </svg>
            </span>
            {{ vt.label }}
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>

    <el-dialog
      v-model="showCreateMenu"
      title="创建新视图"
      width="400px"
      :close-on-click-modal="false"
      :append-to-body="true"
      align-center>
      <el-form @submit.prevent="createView">
        <el-form-item label="视图名称">
          <el-input
            v-model="newViewName"
            placeholder="请输入视图名称"
            autofocus />
        </el-form-item>
        <el-form-item label="视图类型">
          <el-select v-model="newViewType" disabled>
            <el-option
              v-for="vt in viewTypes"
              :key="vt.type"
              :label="vt.label"
              :value="vt.type" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateMenu = false">取消</el-button>
        <el-button type="primary" :loading="isCreating" @click="createView">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.view-switcher {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-sm $spacing-lg;
  @include glass-effect;
  border-bottom: 1px solid $gray-200;
  position: sticky;
  top: 0;
  z-index: 100;
}

.views-list {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  flex: 1;
  overflow-x: auto;
  padding: $spacing-xs 0;

  &::-webkit-scrollbar {
    height: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background-color: $gray-300;
    border-radius: 2px;
  }
}

.view-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  border-radius: $border-radius-md;
  font-size: $font-size-sm;
  color: $text-secondary;
  cursor: pointer;
  transition: all $transition-fast;
  white-space: nowrap;
  position: relative;

  &:hover {
    background-color: $gray-100;
    color: $text-primary;
  }

  &.is-active {
    background-color: rgba($primary-color, 0.08);
    color: $primary-color;
    font-weight: 500;
    @include tab-indicator;

    .view-icon {
      color: $primary-color;
    }
  }

  // 拖拽排序时的视觉反馈
  &.sortable-ghost {
    opacity: 0.4;
    background-color: $gray-100;
  }

  &.sortable-drag {
    background-color: $surface-color;
    box-shadow: $shadow-lg;
    border-radius: $border-radius-md;
  }
}

.view-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: $text-disabled;
}

.view-name {
  max-width: 120px;
  @include text-ellipsis;
  font-weight: 600;
}

.view-name-input {
  width: 100px;
  padding: 2px 6px;
  border: 1px solid $primary-color;
  border-radius: $border-radius-sm;
  font-size: $font-size-sm;
  outline: none;
}

.default-badge {
  padding: 1px 4px;
  font-size: 10px;
  background-color: rgba($primary-color, 0.1);
  color: $primary-color;
  border-radius: 2px;
}

.view-menu-trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
  border-radius: $border-radius-sm;
  opacity: 0;
  transition: opacity $transition-fast;

  &:hover {
    background-color: $bg-color;
  }

  .view-item:hover &,
  .view-item.is-active & {
    opacity: 1;
  }
}

.add-view-btn {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  border: 1px dashed $gray-300;
  border-radius: $border-radius-md;
  background: transparent;
  font-size: $font-size-sm;
  color: $text-secondary;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    border-color: $primary-color;
    color: $primary-color;
    background-color: rgba($primary-color, 0.04);
  }

  &:active {
    transform: scale(0.98);
  }
}

.dropdown-icon {
  display: inline-flex;
  align-items: center;
  margin-right: 8px;
}

:deep(.el-dropdown-menu__item.danger) {
  color: $error-color;
}
</style>
