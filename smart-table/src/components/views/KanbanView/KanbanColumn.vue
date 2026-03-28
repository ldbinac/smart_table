<script setup lang="ts">
import { ref, computed } from "vue";
import type { RecordEntity, FieldEntity } from "@/db/schema";
import KanbanCard from "./KanbanCard.vue";
import Sortable from "sortablejs";

interface Group {
  id: string;
  name: string;
  color?: string;
  records: RecordEntity[];
}

interface Props {
  group: Group;
  records: RecordEntity[];
  fields: FieldEntity[];
  cardFields: string[];
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "addRecord"): void;
  (e: "editRecord", recordId: string): void;
  (e: "updateRecord", recordId: string, values: Record<string, unknown>): void;
  (e: "deleteRecord", recordId: string): void;
  (e: "moveRecord", recordId: string): void;
}>();

const columnRef = ref<HTMLElement | null>(null);
const isAdding = ref(false);
let sortableInstance: Sortable | null = null;

const cardFieldObjects = computed(() => {
  return props.cardFields
    .map((id) => props.fields.find((f) => f.id === id))
    .filter(Boolean) as FieldEntity[];
});

function handleAddClick() {
  isAdding.value = true;
  emit("addRecord");
}

function initSortable() {
  if (!columnRef.value) return;

  sortableInstance = new Sortable(columnRef.value, {
    group: "kanban-cards",
    animation: 200,
    ghostClass: "kanban-card-ghost",
    chosenClass: "kanban-card-chosen",
    dragClass: "kanban-card-drag",
    onEnd: (evt) => {
      const recordId = evt.item.dataset.recordId;
      if (recordId && evt.from !== evt.to) {
        emit("moveRecord", recordId);
      }
    },
  });
}

function destroySortable() {
  if (sortableInstance) {
    sortableInstance.destroy();
    sortableInstance = null;
  }
}

defineExpose({
  initSortable,
  destroySortable,
});
</script>

<template>
  <div
    class="kanban-column"
    :style="{ borderTopColor: group.color || '#3B82F6' }">
    <div class="column-header">
      <div class="column-title">
        <span
          v-if="group.color"
          class="column-color"
          :style="{ backgroundColor: group.color }" />
        <span class="column-name">{{ group.name }}</span>
        <span class="column-count">{{ records.length }}</span>
      </div>
      <el-dropdown trigger="click">
        <el-button link size="small" class="column-menu-btn">
          <el-icon><MoreFilled /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="handleAddClick">
              <el-icon><Plus /></el-icon>
              添加记录
            </el-dropdown-item>
            <el-dropdown-item divided @click="$emit('deleteRecord', group.id)">
              <el-icon><Delete /></el-icon>
              删除分组
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <div ref="columnRef" class="column-cards">
      <KanbanCard
        v-for="record in records"
        :key="record.id"
        :record="record"
        :fields="cardFieldObjects"
        :data-record-id="record.id"
        @edit="$emit('editRecord', record.id)"
        @delete="$emit('deleteRecord', record.id)" />
    </div>

    <div class="column-footer">
      <button class="add-card-btn" @click="handleAddClick">
        <el-icon class="add-icon"><Plus /></el-icon>
        <span>添加卡片</span>
      </button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.kanban-column {
  display: flex;
  flex-direction: column;
  width: 300px;
  min-width: 300px;
  max-height: 100%;
  background-color: $gray-100;
  border-radius: $border-radius-xl;
  border-top: 3px solid $primary-color;
  box-shadow: $shadow-sm;
  transition: box-shadow 0.3s $ease-out-cubic;

  &:hover {
    box-shadow: $shadow-md;
  }
}

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md $spacing-lg;
  background-color: $surface-color;
  border-radius: $border-radius-xl $border-radius-xl 0 0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.column-title {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.column-color {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.column-name {
  font-weight: 600;
  font-size: $font-size-base;
  color: $text-primary;
}

.column-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 20px;
  padding: 0 8px;
  font-size: $font-size-xs;
  font-weight: 500;
  color: $text-secondary;
  background-color: $gray-100;
  border-radius: $border-radius-full;
}

.column-menu-btn {
  opacity: 0.6;
  transition: opacity 0.2s ease;

  &:hover {
    opacity: 1;
  }
}

.column-cards {
  flex: 1;
  padding: $spacing-md;
  overflow-y: auto;
  min-height: 100px;

  // 放置区域高亮样式
  &:global(.sortable-drag-over) {
    background-color: rgba($primary-color, 0.05);
    border-radius: $border-radius-lg;
  }
}

.column-footer {
  padding: $spacing-sm $spacing-md $spacing-md;
}

// 添加卡片按钮 - 虚线边框样式
.add-card-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $spacing-xs;
  width: 100%;
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-sm;
  color: $text-secondary;
  background-color: transparent;
  border: 1.5px dashed $gray-300;
  border-radius: $border-radius-lg;
  cursor: pointer;
  transition: all 0.25s $ease-out-cubic;

  .add-icon {
    font-size: 14px;
    transition: transform 0.25s $ease-spring;
  }

  &:hover {
    color: $primary-color;
    border-style: solid;
    border-color: $primary-color;
    background-color: rgba($primary-color, 0.05);

    .add-icon {
      transform: scale(1.15);
    }
  }

  &:active {
    transform: scale(0.98);
  }
}

// 拖拽相关样式
:deep(.kanban-card-ghost) {
  opacity: 0.6;
  background: linear-gradient(135deg, rgba($primary-color, 0.08) 0%, rgba($primary-color, 0.04) 100%);
  border: 2px dashed rgba($primary-color, 0.4);
  border-radius: $border-radius-xl;
  box-shadow: none;

  * {
    opacity: 0;
  }
}

:deep(.kanban-card-chosen) {
  opacity: 0.9;
  transform: rotate(2deg) scale(1.02);
  box-shadow: $shadow-xl;
  cursor: grabbing;
}

:deep(.kanban-card-drag) {
  opacity: 0.85;
  transform: rotate(2deg);
  box-shadow: $shadow-xl;
  cursor: grabbing;
}

// 滚动条样式
.column-cards::-webkit-scrollbar {
  width: 4px;
}

.column-cards::-webkit-scrollbar-track {
  background: transparent;
}

.column-cards::-webkit-scrollbar-thumb {
  background: $gray-300;
  border-radius: $border-radius-full;
}

.column-cards::-webkit-scrollbar-thumb:hover {
  background: $gray-400;
}
</style>
