<script setup lang="ts">
import { ref, computed } from 'vue'
import type { RecordEntity, FieldEntity } from '@/db/schema'
import KanbanCard from './KanbanCard.vue'
import Sortable from 'sortablejs'

interface Group {
  id: string
  name: string
  color?: string
  records: RecordEntity[]
}

interface Props {
  group: Group
  records: RecordEntity[]
  fields: FieldEntity[]
  cardFields: string[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'addRecord'): void
  (e: 'updateRecord', recordId: string, values: Record<string, unknown>): void
  (e: 'deleteRecord', recordId: string): void
  (e: 'moveRecord', recordId: string): void
}>()

const columnRef = ref<HTMLElement | null>(null)
const isAdding = ref(false)
let sortableInstance: Sortable | null = null

const cardFieldObjects = computed(() => {
  return props.cardFields
    .map(id => props.fields.find(f => f.id === id))
    .filter(Boolean) as FieldEntity[]
})

function handleAddClick() {
  isAdding.value = true
  emit('addRecord')
}

function initSortable() {
  if (!columnRef.value) return
  
  sortableInstance = new Sortable(columnRef.value, {
    group: 'kanban-cards',
    animation: 150,
    ghostClass: 'kanban-card-ghost',
    chosenClass: 'kanban-card-chosen',
    dragClass: 'kanban-card-drag',
    onEnd: (evt) => {
      const recordId = evt.item.dataset.recordId
      if (recordId && evt.from !== evt.to) {
        emit('moveRecord', recordId)
      }
    }
  })
}

function destroySortable() {
  if (sortableInstance) {
    sortableInstance.destroy()
    sortableInstance = null
  }
}

defineExpose({
  initSortable,
  destroySortable
})
</script>

<template>
  <div class="kanban-column" :style="{ borderTopColor: group.color || '#3370FF' }">
    <div class="column-header">
      <div class="column-title">
        <span
          v-if="group.color"
          class="column-color"
          :style="{ backgroundColor: group.color }"
        />
        <span class="column-name">{{ group.name }}</span>
        <span class="column-count">{{ records.length }}</span>
      </div>
      <el-dropdown trigger="click">
        <el-button link size="small">
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
        @update="(values) => $emit('updateRecord', record.id, values)"
        @delete="$emit('deleteRecord', record.id)"
      />
    </div>
    
    <div class="column-footer">
      <el-button link @click="handleAddClick">
        <el-icon><Plus /></el-icon>
        添加记录
      </el-button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.kanban-column {
  display: flex;
  flex-direction: column;
  width: 280px;
  min-width: 280px;
  max-height: 100%;
  background-color: $surface-color;
  border-radius: $border-radius-lg;
  border-top: 3px solid $primary-color;
  box-shadow: $shadow-sm;
}

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md;
  border-bottom: 1px solid $border-color;
}

.column-title {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
}

.column-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.column-name {
  font-weight: 500;
  color: $text-primary;
}

.column-count {
  padding: 2px 8px;
  font-size: $font-size-xs;
  color: $text-secondary;
  background-color: $bg-color;
  border-radius: $border-radius-sm;
}

.column-cards {
  flex: 1;
  padding: $spacing-sm;
  overflow-y: auto;
  min-height: 100px;
}

.column-footer {
  padding: $spacing-sm;
  border-top: 1px solid $border-color;
}

:deep(.kanban-card-ghost) {
  opacity: 0.5;
  background-color: $primary-color-light;
}

:deep(.kanban-card-chosen) {
  box-shadow: $shadow-lg;
}

:deep(.kanban-card-drag) {
  opacity: 0.8;
}
</style>
