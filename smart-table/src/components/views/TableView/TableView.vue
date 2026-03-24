<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useBaseStore } from '@/stores'
import { useViewStore } from '@/stores/viewStore'
import { recordService } from '@/db/services/recordService'
import type { RecordEntity, FieldEntity } from '@/db/schema'
import type { CellValue, SortConfig } from '@/types'
import TableCell from './TableCell.vue'
import TableHeader from './TableHeader.vue'
import TableRow from './TableRow.vue'
import ContextMenu from '@/components/common/ContextMenu.vue'

interface Props {
  tableId?: string
  viewId?: string
  readonly?: boolean
  records?: any[]
}

const props = withDefaults(defineProps<Props>(), {
  tableId: '',
  viewId: '',
  readonly: false,
  records: undefined
})

const emit = defineEmits<{
  (e: 'record-select', record: RecordEntity | null): void
  (e: 'records-select', records: RecordEntity[]): void
  (e: 'record-update', record: RecordEntity): void
  (e: 'record-create'): void
  (e: 'record-delete', recordIds: string[]): void
}>()

const baseStore = useBaseStore()
const viewStore = useViewStore()

const selectedRows = ref<string[]>([])
const hoveredRowId = ref<string | null>(null)
const editingCell = ref<{ recordId: string; fieldId: string } | null>(null)

const contextMenuVisible = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const contextMenuTarget = ref<'row' | 'header' | 'cell'>('row')
const contextMenuField = ref<FieldEntity | null>(null)
const contextMenuRecord = ref<RecordEntity | null>(null)

const columnWidths = ref<Record<string, number>>({})
const isDraggingRow = ref(false)
const draggedRowId = ref<string | null>(null)

const records = computed(() => props.records || baseStore.records)
const fields = computed(() => baseStore.sortedFields)
const visibleFields = computed(() => baseStore.visibleFields)
const frozenFields = computed(() => baseStore.frozenFields)
const currentView = computed(() => viewStore.currentView)

const rowHeight = computed(() => currentView.value?.rowHeight || 'medium')

const sortedRecords = computed(() => {
  const sorts = viewStore.currentSorts as SortConfig[]
  if (!sorts || sorts.length === 0) return records.value
  
  return [...records.value].sort((a, b) => {
    for (const sort of sorts) {
      const aVal = a.values[sort.fieldId]
      const bVal = b.values[sort.fieldId]
      
      let comparison = 0
      if (aVal === null || aVal === undefined) {
        comparison = bVal === null || bVal === undefined ? 0 : -1
      } else if (bVal === null || bVal === undefined) {
        comparison = 1
      } else if (typeof aVal === 'number' && typeof bVal === 'number') {
        comparison = aVal - bVal
      } else {
        comparison = String(aVal).localeCompare(String(bVal))
      }
      
      if (comparison !== 0) {
        return sort.direction === 'desc' ? -comparison : comparison
      }
    }
    return 0
  })
})

const contextMenuItems = computed(() => {
  const items: any[] = []
  
  if (contextMenuTarget.value === 'row') {
    items.push(
      { id: 'edit', label: '编辑', icon: 'edit' },
      { id: 'duplicate', label: '复制记录', icon: 'copy' },
      { divider: true, id: 'divider1' }
    )
    
    if (selectedRows.value.length > 1) {
      items.push(
        { id: 'delete-selected', label: `删除选中的 ${selectedRows.value.length} 条记录`, icon: 'delete', danger: true }
      )
    } else {
      items.push(
        { id: 'delete', label: '删除记录', icon: 'delete', danger: true }
      )
    }
  } else if (contextMenuTarget.value === 'header') {
    const field = contextMenuField.value
    if (field) {
      items.push(
        { id: 'sort-asc', label: '升序排列', icon: 'sort' },
        { id: 'sort-desc', label: '降序排列', icon: 'sort' },
        { divider: true, id: 'divider1' }
      )
      
      const isFrozen = frozenFields.value.some(f => f.id === field.id)
      if (isFrozen) {
        items.push({ id: 'unfreeze', label: '取消冻结' })
      } else {
        items.push({ id: 'freeze', label: '冻结列' })
      }
      
      items.push(
        { divider: true, id: 'divider2' },
        { id: 'hide-field', label: '隐藏字段' },
        { id: 'edit-field', label: '编辑字段属性' }
      )
    }
  }
  
  return items
})

const handleCellUpdate = async (record: RecordEntity, fieldId: string, value: CellValue) => {
  // 使用 JSON.parse(JSON.stringify()) 确保所有值都是纯 JavaScript 对象
  // 避免响应式对象导致的 IndexedDB 克隆错误
  const plainValues = JSON.parse(JSON.stringify(record.values))
  const plainValue = JSON.parse(JSON.stringify(value))
  const newValues = { ...plainValues, [fieldId]: plainValue }
  await recordService.updateRecord(record.id, { values: newValues })
  await baseStore.loadTable(record.tableId)
  editingCell.value = null
}

const handleRowClick = (record: RecordEntity, event: MouseEvent) => {
  if (event.ctrlKey || event.metaKey) {
    const index = selectedRows.value.indexOf(record.id)
    if (index > -1) {
      selectedRows.value.splice(index, 1)
    } else {
      selectedRows.value.push(record.id)
    }
  } else if (event.shiftKey && selectedRows.value.length > 0) {
    const lastSelectedId = selectedRows.value[selectedRows.value.length - 1]
    const lastIndex = sortedRecords.value.findIndex(r => r.id === lastSelectedId)
    const currentIndex = sortedRecords.value.findIndex(r => r.id === record.id)
    
    const start = Math.min(lastIndex, currentIndex)
    const end = Math.max(lastIndex, currentIndex)
    
    const newSelection = sortedRecords.value.slice(start, end + 1).map(r => r.id)
    selectedRows.value = [...new Set([...selectedRows.value, ...newSelection])]
  } else {
    selectedRows.value = [record.id]
  }
  
  emit('record-select', record)
  emit('records-select', selectedRows.value.map(id => sortedRecords.value.find(r => r.id === id)!).filter(Boolean))
}

const handleRowContextMenu = (record: RecordEntity, event: MouseEvent) => {
  if (!selectedRows.value.includes(record.id)) {
    selectedRows.value = [record.id]
  }
  
  contextMenuTarget.value = 'row'
  contextMenuRecord.value = record
  contextMenuX.value = event.clientX
  contextMenuY.value = event.clientY
  contextMenuVisible.value = true
}

const handleHeaderContextMenu = (field: FieldEntity, event: MouseEvent) => {
  contextMenuTarget.value = 'header'
  contextMenuField.value = field
  contextMenuX.value = event.clientX
  contextMenuY.value = event.clientY
  contextMenuVisible.value = true
}

const handleContextMenuSelect = async (item: any) => {
  const { id } = item
  
  switch (id) {
    case 'edit':
      if (contextMenuRecord.value) {
        editingCell.value = {
          recordId: contextMenuRecord.value.id,
          fieldId: fields.value[0]?.id || ''
        }
      }
      break
      
    case 'duplicate':
      if (contextMenuRecord.value) {
        const newRecord = await recordService.createRecord({
          tableId: contextMenuRecord.value.tableId,
          values: { ...contextMenuRecord.value.values }
        })
        if (newRecord) {
          await baseStore.loadTable(contextMenuRecord.value.tableId)
        }
      }
      break
      
    case 'delete':
      if (contextMenuRecord.value) {
        await recordService.deleteRecord(contextMenuRecord.value.id)
        await baseStore.loadTable(contextMenuRecord.value.tableId)
        selectedRows.value = []
        emit('record-delete', [contextMenuRecord.value.id])
      }
      break
      
    case 'delete-selected':
      await recordService.batchDeleteRecords(selectedRows.value)
      if (baseStore.currentTable) {
        await baseStore.loadTable(baseStore.currentTable.id)
      }
      emit('record-delete', [...selectedRows.value])
      selectedRows.value = []
      break
      
    case 'sort-asc':
      if (contextMenuField.value && currentView.value) {
        await viewStore.updateSorts(currentView.value.id, [
          { fieldId: contextMenuField.value.id, direction: 'asc' }
        ])
      }
      break
      
    case 'sort-desc':
      if (contextMenuField.value && currentView.value) {
        await viewStore.updateSorts(currentView.value.id, [
          { fieldId: contextMenuField.value.id, direction: 'desc' }
        ])
      }
      break
      
    case 'freeze':
      if (contextMenuField.value && currentView.value) {
        const newFrozen = [...currentView.value.frozenFields, contextMenuField.value.id]
        await viewStore.updateFrozenFields(currentView.value.id, newFrozen)
      }
      break
      
    case 'unfreeze':
      if (contextMenuField.value && currentView.value) {
        const newFrozen = currentView.value.frozenFields.filter(fid => fid !== contextMenuField.value!.id)
        await viewStore.updateFrozenFields(currentView.value.id, newFrozen)
      }
      break
      
    case 'hide-field':
      if (contextMenuField.value && currentView.value) {
        const newHidden = [...currentView.value.hiddenFields, contextMenuField.value.id]
        await viewStore.updateHiddenFields(currentView.value.id, newHidden)
      }
      break
  }
  
  contextMenuVisible.value = false
}

const handleSort = async (fieldId: string, direction: 'asc' | 'desc') => {
  if (currentView.value) {
    const currentSorts = viewStore.currentSorts as SortConfig[]
    const existingSortIndex = currentSorts.findIndex(s => s.fieldId === fieldId)
    const newSorts = [...currentSorts]
    
    if (existingSortIndex > -1) {
      newSorts[existingSortIndex] = { fieldId, direction }
    } else {
      newSorts.push({ fieldId, direction })
    }
    
    await viewStore.updateSorts(currentView.value.id, newSorts as SortConfig[])
  }
}

const handleColumnResize = (fieldId: string, width: number) => {
  columnWidths.value[fieldId] = width
}

const handleRowDragStart = (event: DragEvent, record: RecordEntity) => {
  isDraggingRow.value = true
  draggedRowId.value = record.id
  
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', record.id)
  }
}

const handleRowDragEnd = () => {
  isDraggingRow.value = false
  draggedRowId.value = null
}

const handleKeyDown = (event: KeyboardEvent) => {
  if (editingCell.value) return
  
  const currentIndex = selectedRows.value.length > 0
    ? sortedRecords.value.findIndex(r => r.id === selectedRows.value[0])
    : -1
  
  switch (event.key) {
    case 'ArrowUp':
      event.preventDefault()
      if (currentIndex > 0) {
        const newRecord = sortedRecords.value[currentIndex - 1]
        selectedRows.value = [newRecord.id]
        emit('record-select', newRecord)
      }
      break
      
    case 'ArrowDown':
      event.preventDefault()
      if (currentIndex < sortedRecords.value.length - 1) {
        const newRecord = sortedRecords.value[currentIndex + 1]
        selectedRows.value = [newRecord.id]
        emit('record-select', newRecord)
      }
      break
      
    case 'Delete':
    case 'Backspace':
      if (selectedRows.value.length > 0) {
        event.preventDefault()
        recordService.batchDeleteRecords(selectedRows.value)
        if (baseStore.currentTable) {
          baseStore.loadTable(baseStore.currentTable.id)
        }
        emit('record-delete', [...selectedRows.value])
        selectedRows.value = []
      }
      break
      
    case 'a':
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault()
        selectedRows.value = sortedRecords.value.map(r => r.id)
        emit('records-select', sortedRecords.value)
      }
      break
      
    case 'Escape':
      selectedRows.value = []
      emit('record-select', null)
      break
      
    case 'Enter':
      if (selectedRows.value.length === 1) {
        const record = sortedRecords.value.find(r => r.id === selectedRows.value[0])
        if (record && visibleFields.value.length > 0) {
          editingCell.value = {
            recordId: record.id,
            fieldId: visibleFields.value[0].id
          }
        }
      }
      break
  }
}

const addNewRecord = async () => {
  if (!baseStore.currentTable) return
  
  const newRecord = await recordService.createRecord({
    tableId: baseStore.currentTable.id,
    values: {}
  })
  
  if (newRecord) {
    await baseStore.loadTable(baseStore.currentTable.id)
    selectedRows.value = [newRecord.id]
    emit('record-create')
    
    await nextTick()
    editingCell.value = {
      recordId: newRecord.id,
      fieldId: visibleFields.value[0]?.id || ''
    }
  }
}

const getColumnWidth = (fieldId: string): number => {
  return columnWidths.value[fieldId] || 150
}

const isFieldFrozen = (fieldId: string): boolean => {
  return frozenFields.value.some(f => f.id === fieldId)
}

const getFieldSortDirection = (fieldId: string): 'asc' | 'desc' | null => {
  const sorts = viewStore.currentSorts as SortConfig[]
  const sort = sorts.find(s => s.fieldId === fieldId)
  return sort?.direction || null
}

onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeyDown)
})

defineExpose({
  addNewRecord,
  selectedRows,
  refresh: () => baseStore.loadTable(baseStore.currentTable?.id || '')
})
</script>

<template>
  <div class="table-view">
    <div class="table-container" v-if="visibleFields.length > 0">
      <div class="table-header">
        <div class="header-row">
          <div class="row-selector-header">
            <input
              type="checkbox"
              :checked="selectedRows.length === sortedRecords.length && sortedRecords.length > 0"
              :indeterminate="selectedRows.length > 0 && selectedRows.length < sortedRecords.length"
              @change="(e) => {
                if ((e.target as HTMLInputElement).checked) {
                  selectedRows = sortedRecords.map(r => r.id)
                } else {
                  selectedRows = []
                }
              }"
            />
          </div>
          <div
            v-for="field in visibleFields"
            :key="field.id"
            class="header-cell"
            :class="{ 'is-frozen': isFieldFrozen(field.id) }"
            :style="{ width: `${getColumnWidth(field.id)}px` }"
          >
            <TableHeader
              :field="field"
              :sort-direction="getFieldSortDirection(field.id)"
              :is-frozen="isFieldFrozen(field.id)"
              @sort="(dir) => handleSort(field.id, dir)"
              @resize="(w) => handleColumnResize(field.id, w)"
              @contextmenu="(e) => handleHeaderContextMenu(field, e)"
            />
          </div>
        </div>
      </div>
      
      <div class="table-body">
        <TableRow
          v-for="(record, index) in sortedRecords"
          :key="record.id"
          :record="record"
          :index="index"
          :is-selected="selectedRows.includes(record.id)"
          :is-hovered="hoveredRowId === record.id"
          :row-height="rowHeight"
          @click="(e) => handleRowClick(record, e)"
          @contextmenu="(e) => handleRowContextMenu(record, e)"
          @dragstart="(e) => handleRowDragStart(e, record)"
          @dragend="handleRowDragEnd"
        >
          <div class="row-selector">
            <input
              type="checkbox"
              :checked="selectedRows.includes(record.id)"
              @click.stop
              @change="(e) => {
                const checked = (e.target as HTMLInputElement).checked
                if (checked) {
                  selectedRows.push(record.id)
                } else {
                  const idx = selectedRows.indexOf(record.id)
                  if (idx > -1) selectedRows.splice(idx, 1)
                }
              }"
            />
            <span class="row-number">{{ index + 1 }}</span>
          </div>
          
          <div
            v-for="field in visibleFields"
            :key="field.id"
            class="table-cell-wrapper"
            :class="{
              'is-frozen': isFieldFrozen(field.id),
              'is-editing': editingCell?.recordId === record.id && editingCell?.fieldId === field.id
            }"
            :style="{ width: `${getColumnWidth(field.id)}px` }"
          >
            <TableCell
              :record="record"
              :field="field"
              :readonly="readonly"
              :selected="editingCell?.recordId === record.id && editingCell?.fieldId === field.id"
              @update="(value) => handleCellUpdate(record, field.id, value)"
              @edit="(active) => {
                if (active) {
                  editingCell = { recordId: record.id, fieldId: field.id }
                } else if (editingCell?.recordId === record.id && editingCell?.fieldId === field.id) {
                  editingCell = null
                }
              }"
            />
          </div>
        </TableRow>
        
        <div class="add-row-button" @click="addNewRecord">
          <span class="add-icon">+</span>
          <span>添加记录</span>
        </div>
      </div>
    </div>
    
    <div v-else class="empty-state">
      <p>暂无字段，请先添加字段</p>
    </div>
    
    <ContextMenu
      :items="contextMenuItems"
      :x="contextMenuX"
      :y="contextMenuY"
      :visible="contextMenuVisible"
      @update:visible="contextMenuVisible = $event"
      @select="handleContextMenuSelect"
    />
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.table-view {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: auto;
  background-color: $surface-color;
}

.table-container {
  min-width: max-content;
}

.table-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: $bg-color;
}

.header-row {
  display: flex;
  border-bottom: 2px solid $border-color;
}

.header-cell {
  flex-shrink: 0;
  border-right: 1px solid $border-color;
  
  &.is-frozen {
    position: sticky;
    left: 40px;
    z-index: 5;
    background-color: $bg-color;
    box-shadow: 2px 0 4px rgba(0, 0, 0, 0.1);
  }
}

.row-selector-header {
  width: 40px;
  min-width: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid $border-color;
  background-color: $bg-color;
  
  input[type="checkbox"] {
    width: 14px;
    height: 14px;
    cursor: pointer;
  }
}

.table-body {
  position: relative;
}

.row-selector {
  width: 40px;
  min-width: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 0 4px;
  border-right: 1px solid $border-color;
  background-color: inherit;
  
  input[type="checkbox"] {
    width: 14px;
    height: 14px;
    cursor: pointer;
    opacity: 0;
    transition: opacity $transition-fast;
  }
  
  .row-number {
    font-size: $font-size-xs;
    color: $text-disabled;
  }
  
  &:hover {
    input[type="checkbox"] {
      opacity: 1;
    }
    
    .row-number {
      display: none;
    }
  }
}

.table-cell-wrapper {
  flex-shrink: 0;
  border-right: 1px solid $border-color;
  
  &.is-frozen {
    position: sticky;
    left: 40px;
    z-index: 2;
    background-color: inherit;
    box-shadow: 2px 0 4px rgba(0, 0, 0, 0.05);
  }
  
  &.is-editing {
    z-index: 10;
  }
}

.add-row-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  color: $text-secondary;
  cursor: pointer;
  transition: all $transition-fast;
  
  &:hover {
    background-color: rgba($primary-color, 0.05);
    color: $primary-color;
  }
  
  .add-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border: 1px dashed currentColor;
    border-radius: $border-radius-sm;
    font-size: 14px;
  }
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: $text-secondary;
}
</style>
