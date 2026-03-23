<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { FieldEntity, RecordEntity } from '../../db/schema'
import type { GroupNode } from '../../utils/group'
import { FieldType } from '../../types'
import { groupRecords } from '../../utils/group'

interface Props {
  fields: FieldEntity[]
  records: RecordEntity[]
  groupBy: string[]
  rowHeight?: 'short' | 'medium' | 'tall'
}

const props = withDefaults(defineProps<Props>(), {
  groupBy: () => [],
  rowHeight: 'medium'
})

const emit = defineEmits<{
  (e: 'rowClick', record: RecordEntity): void
  (e: 'cellClick', record: RecordEntity, field: FieldEntity): void
  (e: 'update:groupBy', value: string[]): void
}>()

const groupNodes = ref<GroupNode[]>([])
const expandedKeys = ref<Set<string>>(new Set())

const rowHeightMap = {
  short: '32px',
  medium: '40px',
  tall: '56px'
}

const visibleFields = computed(() => {
  return props.fields.filter(f => !f.isSystem)
})

const flattenedData = computed(() => {
  const result: Array<{ type: 'group' | 'record'; node?: GroupNode; record?: RecordEntity; level: number }> = []

  const processNodes = (nodes: GroupNode[], level: number) => {
    for (const node of nodes) {
      result.push({ type: 'group', node, level })

      if (expandedKeys.value.has(node.key) && node.children) {
        processNodes(node.children, level + 1)
      } else if (!node.children && node.records.length > 0) {
        for (const record of node.records) {
          result.push({ type: 'record', record, level: level + 1 })
        }
      }
    }
  }

  if (groupNodes.value.length > 0) {
    processNodes(groupNodes.value, 0)
  } else {
    for (const record of props.records) {
      result.push({ type: 'record', record, level: 0 })
    }
  }

  return result
})

const isGrouped = computed(() => props.groupBy.length > 0)

function updateGroups() {
  if (props.groupBy.length === 0) {
    groupNodes.value = []
    expandedKeys.value.clear()
    return
  }

  groupNodes.value = groupRecords(
    props.records,
    { fieldIds: props.groupBy },
    props.fields
  )

  const collectKeys = (nodes: GroupNode[]) => {
    for (const node of nodes) {
      expandedKeys.value.add(node.key)
      if (node.children) {
        collectKeys(node.children)
      }
    }
  }
  collectKeys(groupNodes.value)
}

watch(() => [props.records, props.groupBy], () => {
  updateGroups()
}, { deep: true, immediate: true })

function toggleGroup(key: string) {
  if (expandedKeys.value.has(key)) {
    expandedKeys.value.delete(key)
  } else {
    expandedKeys.value.add(key)
  }
}

function expandAll() {
  const collectKeys = (nodes: GroupNode[]) => {
    for (const node of nodes) {
      expandedKeys.value.add(node.key)
      if (node.children) {
        collectKeys(node.children)
      }
    }
  }
  collectKeys(groupNodes.value)
}

function collapseAll() {
  expandedKeys.value.clear()
}

function getGroupStyle(level: number) {
  return {
    paddingLeft: `${level * 24}px`
  }
}

function getRecordStyle(level: number) {
  return {
    paddingLeft: `${level * 24}px`
  }
}

function getCellDisplayValue(value: unknown, field: FieldEntity): string {
  if (value === null || value === undefined) return ''

  switch (field.type) {
    case FieldType.CHECKBOX:
      return value ? '✓' : ''

    case FieldType.MULTI_SELECT:
      if (Array.isArray(value)) {
        return value.map(v => typeof v === 'object' ? (v as { name: string }).name : v).join(', ')
      }
      return String(value)

    case FieldType.SINGLE_SELECT:
      if (typeof value === 'object' && value !== null) {
        return (value as { name: string }).name
      }
      return String(value)

    case FieldType.DATE:
      if (typeof value === 'number') {
        const date = new Date(value)
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
      }
      return String(value)

    default:
      return String(value)
  }
}

function handleRowClick(record: RecordEntity) {
  emit('rowClick', record)
}

function handleCellClick(record: RecordEntity, field: FieldEntity) {
  emit('cellClick', record, field)
}
</script>

<template>
  <div class="grouped-table-view">
    <div v-if="isGrouped" class="group-toolbar">
      <el-button size="small" @click="expandAll">全部展开</el-button>
      <el-button size="small" @click="collapseAll">全部折叠</el-button>
    </div>

    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th class="column-header" :style="{ width: '40px' }"></th>
            <th
              v-for="field in visibleFields"
              :key="field.id"
              class="column-header"
              :style="{ minWidth: '120px' }"
            >
              {{ field.name }}
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(item, index) in flattenedData" :key="index">
            <tr
              v-if="item.type === 'group'"
              class="group-row"
              :style="{ height: rowHeightMap[rowHeight] }"
              @click="toggleGroup(item.node!.key)"
            >
              <td class="group-cell" :colspan="visibleFields.length + 1" :style="getGroupStyle(item.level)">
                <el-icon
                  class="expand-icon"
                  :class="{ expanded: expandedKeys.has(item.node!.key) }"
                >
                  <ArrowRight />
                </el-icon>
                <span class="group-value">{{ item.node!.value }}</span>
                <span class="group-count">{{ item.node!.count }}</span>
              </td>
            </tr>
            <tr
              v-else
              class="data-row"
              :style="{ height: rowHeightMap[rowHeight] }"
              @click="handleRowClick(item.record!)"
            >
              <td class="row-number">{{ index + 1 }}</td>
              <td
                v-for="field in visibleFields"
                :key="field.id"
                class="data-cell"
                :style="getRecordStyle(item.level)"
                @click.stop="handleCellClick(item.record!, field)"
              >
                {{ getCellDisplayValue(item.record!.values[field.id], field) }}
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <div v-if="flattenedData.length === 0" class="empty-table">
        <span>暂无数据</span>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { ArrowRight } from '@element-plus/icons-vue'
export default {
  name: 'GroupedTableView'
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.grouped-table-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.group-toolbar {
  display: flex;
  gap: $spacing-sm;
  padding: $spacing-sm;
  border-bottom: 1px solid $border-color;
  background-color: $surface-color;
}

.table-container {
  flex: 1;
  overflow: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.column-header {
  text-align: left;
  padding: $spacing-sm $spacing-md;
  background-color: $bg-color;
  border-bottom: 1px solid $border-color;
  font-size: $font-size-sm;
  font-weight: 500;
  color: $text-secondary;
  position: sticky;
  top: 0;
  z-index: 1;
}

.group-row {
  background-color: $bg-color;
  cursor: pointer;
  transition: background-color $transition-fast;

  &:hover {
    background-color: darken($bg-color, 3%);
  }
}

.group-cell {
  display: flex;
  align-items: center;
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-sm;
  font-weight: 500;
  color: $text-primary;
}

.expand-icon {
  font-size: 12px;
  color: $text-secondary;
  transition: transform $transition-fast;
  margin-right: $spacing-xs;

  &.expanded {
    transform: rotate(90deg);
  }
}

.group-value {
  flex: 1;
}

.group-count {
  font-size: $font-size-xs;
  color: $text-secondary;
  background-color: $surface-color;
  padding: 2px $spacing-sm;
  border-radius: $border-radius-sm;
}

.data-row {
  border-bottom: 1px solid $border-color;
  transition: background-color $transition-fast;

  &:hover {
    background-color: rgba($primary-color, 0.05);
  }
}

.row-number {
  text-align: center;
  padding: $spacing-sm;
  font-size: $font-size-xs;
  color: $text-disabled;
  background-color: $bg-color;
  border-right: 1px solid $border-color;
}

.data-cell {
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-sm;
  color: $text-primary;
  border-right: 1px solid $border-color;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  &:last-child {
    border-right: none;
  }
}

.empty-table {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: $text-secondary;
  font-size: $font-size-sm;
}
</style>
