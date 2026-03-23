<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { FieldEntity } from '../../db/schema'
import type { SortConfig } from '../../types'
import { SortDirection } from '../../types'
import { getSortDescription, reorderSorts } from '../../utils/sort'

interface Props {
  fields: FieldEntity[]
  modelValue: SortConfig[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: SortConfig[]): void
  (e: 'apply'): void
  (e: 'reset'): void
}>()

const localSorts = ref<SortConfig[]>([])

watch(() => props.modelValue, (newVal) => {
  localSorts.value = newVal.map(s => ({ ...s }))
}, { immediate: true, deep: true })

watch(localSorts, (newVal) => {
  emit('update:modelValue', newVal)
}, { deep: true })

const hasSorts = computed(() => {
  return localSorts.value.length > 0
})

const availableFields = computed(() => {
  const sortedFieldIds = localSorts.value.map(s => s.fieldId)
  return props.fields.filter(f => !sortedFieldIds.includes(f.id))
})

const sortDescriptions = computed(() => {
  return localSorts.value.map(s => ({
    sort: s,
    description: getSortDescription(s, props.fields)
  }))
})

function addSort(fieldId?: string) {
  const targetFieldId = fieldId || availableFields.value[0]?.id
  if (!targetFieldId) return

  localSorts.value.push({
    fieldId: targetFieldId,
    direction: SortDirection.ASC
  })
}

function updateSortField(index: number, fieldId: string) {
  localSorts.value[index].fieldId = fieldId
}

function removeSortByIndex(index: number) {
  localSorts.value.splice(index, 1)
}

function moveSortUp(index: number) {
  if (index <= 0) return
  localSorts.value = reorderSorts(localSorts.value, index, index - 1)
}

function moveSortDown(index: number) {
  if (index >= localSorts.value.length - 1) return
  localSorts.value = reorderSorts(localSorts.value, index, index + 1)
}

function clearAllSorts() {
  localSorts.value = []
}

function handleApply() {
  emit('apply')
}

function handleReset() {
  localSorts.value = []
  emit('reset')
}

function getFieldById(fieldId: string) {
  return props.fields.find(f => f.id === fieldId)
}

function toggleDirection(index: number) {
  const current = localSorts.value[index].direction
  localSorts.value[index].direction = current === SortDirection.ASC ? SortDirection.DESC : SortDirection.ASC
}
</script>

<template>
  <div class="sort-panel">
    <div class="panel-header">
      <div class="header-title">
        <span class="title">排序条件</span>
        <span v-if="hasSorts" class="sort-count">
          {{ localSorts.length }} 个排序
        </span>
      </div>
      <div class="header-actions">
        <el-button
          text
          size="small"
          type="danger"
          @click="clearAllSorts"
          :disabled="!hasSorts"
        >
          清空
        </el-button>
      </div>
    </div>

    <div class="sorts-list">
      <template v-if="hasSorts">
        <div
          v-for="(sort, index) in localSorts"
          :key="sort.fieldId"
          class="sort-item"
        >
          <div class="sort-index">{{ index + 1 }}</div>

          <el-select
            :model-value="sort.fieldId"
            placeholder="选择字段"
            class="field-select"
            @change="updateSortField(index, $event)"
          >
            <el-option
              :label="getFieldById(sort.fieldId)?.name"
              :value="sort.fieldId"
            />
            <el-option
              v-for="field in availableFields"
              :key="field.id"
              :label="field.name"
              :value="field.id"
            />
          </el-select>

          <el-tooltip
            :content="sort.direction === SortDirection.ASC ? '升序' : '降序'"
            placement="top"
          >
            <el-button
              :icon="sort.direction === SortDirection.ASC ? SortUp : SortDown"
              circle
              size="small"
              @click="toggleDirection(index)"
            />
          </el-tooltip>

          <div class="sort-actions">
            <el-button
              :icon="ArrowUp"
              circle
              size="small"
              :disabled="index === 0"
              @click="moveSortUp(index)"
            />
            <el-button
              :icon="ArrowDown"
              circle
              size="small"
              :disabled="index === localSorts.length - 1"
              @click="moveSortDown(index)"
            />
            <el-button
              type="danger"
              :icon="Delete"
              circle
              size="small"
              @click="removeSortByIndex(index)"
            />
          </div>
        </div>
      </template>
      <div v-else class="empty-state">
        <span>暂无排序条件</span>
      </div>
    </div>

    <div class="panel-footer">
      <el-dropdown
        trigger="click"
        :disabled="availableFields.length === 0"
        @command="addSort"
      >
        <el-button type="primary" plain size="small">
          添加排序
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="field in availableFields"
              :key="field.id"
              :command="field.id"
            >
              {{ field.name }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <div class="footer-actions">
        <el-button size="small" @click="handleReset">
          重置
        </el-button>
        <el-button
          type="primary"
          size="small"
          @click="handleApply"
          :disabled="!hasSorts"
        >
          应用
        </el-button>
      </div>
    </div>

    <div v-if="hasSorts" class="sort-summary">
      <div class="summary-title">排序顺序：</div>
      <div class="summary-content">
        <template v-for="(item, index) in sortDescriptions" :key="item.sort.fieldId">
          <span class="summary-text">{{ item.description }}</span>
          <span v-if="index < sortDescriptions.length - 1" class="summary-separator">→</span>
        </template>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { SortUp, SortDown, ArrowUp, ArrowDown, Delete } from '@element-plus/icons-vue'
export default {
  name: 'SortPanel'
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.sort-panel {
  background-color: $surface-color;
  border: 1px solid $border-color;
  border-radius: $border-radius-md;
  padding: $spacing-md;
  min-width: 400px;
  max-width: 500px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-md;
  padding-bottom: $spacing-sm;
  border-bottom: 1px solid $border-color;
}

.header-title {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.title {
  font-size: $font-size-base;
  font-weight: 500;
  color: $text-primary;
}

.sort-count {
  font-size: $font-size-xs;
  color: $text-secondary;
  background-color: $bg-color;
  padding: 2px $spacing-sm;
  border-radius: $border-radius-sm;
}

.header-actions {
  display: flex;
  gap: $spacing-xs;
}

.sorts-list {
  max-height: 250px;
  overflow-y: auto;
  margin-bottom: $spacing-md;
}

.sort-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm;
  background-color: $bg-color;
  border-radius: $border-radius-md;
  margin-bottom: $spacing-sm;

  &:last-child {
    margin-bottom: 0;
  }
}

.sort-index {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background-color: $primary-color;
  color: white;
  border-radius: 50%;
  font-size: $font-size-xs;
  font-weight: 500;
  flex-shrink: 0;
}

.field-select {
  flex: 1;
  min-width: 120px;
}

.sort-actions {
  display: flex;
  gap: $spacing-xs;
  margin-left: auto;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 80px;
  color: $text-secondary;
  font-size: $font-size-sm;
  background-color: $bg-color;
  border-radius: $border-radius-md;
}

.panel-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: $spacing-sm;
  border-top: 1px solid $border-color;
}

.footer-actions {
  display: flex;
  gap: $spacing-sm;
}

.sort-summary {
  margin-top: $spacing-md;
  padding-top: $spacing-md;
  border-top: 1px solid $border-color;
}

.summary-title {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-bottom: $spacing-sm;
}

.summary-content {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: $spacing-xs;
}

.summary-text {
  font-size: $font-size-sm;
  color: $text-primary;
}

.summary-separator {
  color: $text-secondary;
  font-size: $font-size-xs;
}
</style>
