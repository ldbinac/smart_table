<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { tableService } from '@/db/services/tableService'
import { fieldService } from '@/db/services/fieldService'
import { recordService } from '@/db/services/recordService'
import type { FieldEntity, RecordEntity, TableEntity } from '@/db/schema'
import type { CellValue } from '@/types'

interface Props {
  modelValue: CellValue
  field: FieldEntity
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: CellValue): void
}>()

const linkedTableId = ref<string>('')
const linkedFieldId = ref<string>('')
const linkedTables = ref<TableEntity[]>([])
const linkedFields = ref<FieldEntity[]>([])
const linkedRecords = ref<RecordEntity[]>([])
const selectedRecords = ref<RecordEntity[]>([])
const visible = ref(false)
const searchQuery = ref('')

const allowMultiple = computed(() => {
  return props.field.options?.allowMultiple !== false
})

const displayField = computed(() => {
  if (linkedFieldId.value) {
    return linkedFields.value.find(f => f.id === linkedFieldId.value)
  }
  return linkedFields.value.find(f => f.isPrimary) || linkedFields.value[0]
})

const filteredRecords = computed(() => {
  if (!searchQuery.value) return linkedRecords.value
  const query = searchQuery.value.toLowerCase()
  return linkedRecords.value.filter(record => {
    const displayValue = displayField.value ? record.values[displayField.value!.id] : ''
    return String(displayValue).toLowerCase().includes(query)
  })
})

watch(() => props.field.options, (options) => {
  if (options?.linkedTableId) {
    linkedTableId.value = options.linkedTableId as string
    loadLinkedTableData()
  }
  if (options?.linkedFieldId) {
    linkedFieldId.value = options.linkedFieldId as string
  }
}, { immediate: true })

watch(() => props.modelValue, (newVal) => {
  if (Array.isArray(newVal)) {
    const ids = newVal.map(v => typeof v === 'string' ? v : String(v))
    selectedRecords.value = linkedRecords.value.filter(r => ids.includes(r.id))
  } else if (newVal) {
    const id = typeof newVal === 'string' ? newVal : String(newVal)
    selectedRecords.value = linkedRecords.value.filter(r => r.id === id)
  } else {
    selectedRecords.value = []
  }
}, { immediate: true })

async function loadLinkedTables() {
  if (linkedTableId.value) {
    linkedTables.value = await tableService.getTablesByBase(linkedTableId.value)
  }
}

async function loadLinkedTableData() {
  if (!linkedTableId.value) return
  
  linkedFields.value = await fieldService.getFieldsByTable(linkedTableId.value)
  linkedRecords.value = await recordService.getRecordsByTable(linkedTableId.value)
}

function handleTableChange(tableId: string) {
  linkedTableId.value = tableId
  loadLinkedTableData()
}

function isSelected(record: RecordEntity): boolean {
  return selectedRecords.value.some(r => r.id === record.id)
}

function toggleRecord(record: RecordEntity) {
  if (props.readonly) return
  
  if (allowMultiple.value) {
    if (isSelected(record)) {
      selectedRecords.value = selectedRecords.value.filter(r => r.id !== record.id)
    } else {
      selectedRecords.value.push(record)
    }
    emit('update:modelValue', selectedRecords.value.map(r => r.id))
  } else {
    selectedRecords.value = [record]
    emit('update:modelValue', record.id)
    visible.value = false
  }
}

function removeRecord(recordId: string) {
  selectedRecords.value = selectedRecords.value.filter(r => r.id !== recordId)
  emit('update:modelValue', selectedRecords.value.map(r => r.id))
}

function getRecordDisplayValue(record: RecordEntity): string {
  if (!displayField.value) return record.id
  return String(record.values[displayField.value!.id] || '无标题')
}

onMounted(() => {
  loadLinkedTables()
})
</script>

<template>
  <div class="link-field">
    <div v-if="readonly" class="link-display">
      <el-tag
        v-for="record in selectedRecords"
        :key="record.id"
        size="small"
        class="link-tag"
      >
        {{ getRecordDisplayValue(record) }}
      </el-tag>
      <span v-if="selectedRecords.length === 0" class="empty-text">-</span>
    </div>
    
    <el-popover
      v-else
      v-model:visible="visible"
      trigger="click"
      placement="bottom-start"
      :width="360"
    >
      <template #reference>
        <div class="link-trigger">
          <el-tag
            v-for="record in selectedRecords"
            :key="record.id"
            size="small"
            closable
            class="link-tag"
            @close="removeRecord(record.id)"
          >
            {{ getRecordDisplayValue(record) }}
          </el-tag>
          <span v-if="selectedRecords.length === 0" class="placeholder">
            选择关联记录
          </span>
        </div>
      </template>
      
      <div class="link-dropdown">
        <div class="dropdown-header">
          <el-select
            v-model="linkedTableId"
            placeholder="选择关联表"
            size="small"
            @change="handleTableChange"
          >
            <el-option
              v-for="table in linkedTables"
              :key="table.id"
              :label="table.name"
              :value="table.id"
            />
          </el-select>
        </div>
        
        <el-input
          v-model="searchQuery"
          placeholder="搜索记录"
          prefix-icon="Search"
          size="small"
          clearable
          class="search-input"
        />
        
        <div class="record-list">
          <div
            v-for="record in filteredRecords"
            :key="record.id"
            class="record-option"
            :class="{ selected: isSelected(record) }"
            @click="toggleRecord(record)"
          >
            <span class="record-name">{{ getRecordDisplayValue(record) }}</span>
            <el-icon v-if="isSelected(record)" class="check-icon">
              <Check />
            </el-icon>
          </div>
          
          <div v-if="filteredRecords.length === 0" class="no-results">
            未找到记录
          </div>
        </div>
      </div>
    </el-popover>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.link-field {
  width: 100%;
}

.link-display {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
}

.link-trigger {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
  min-height: 32px;
  padding: $spacing-xs;
  border: 1px solid $border-color;
  border-radius: $border-radius-sm;
  cursor: pointer;
  
  &:hover {
    border-color: $primary-color;
  }
}

.link-tag {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.placeholder {
  color: $text-placeholder;
  font-size: $font-size-sm;
}

.empty-text {
  color: $text-disabled;
}

.link-dropdown {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.dropdown-header {
  display: flex;
  gap: $spacing-sm;
  
  .el-select {
    flex: 1;
  }
}

.search-input {
  width: 100%;
}

.record-list {
  max-height: 250px;
  overflow-y: auto;
}

.record-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-sm;
  border-radius: $border-radius-sm;
  cursor: pointer;
  
  &:hover {
    background-color: $bg-color;
  }
  
  &.selected {
    background-color: rgba($primary-color, 0.1);
  }
}

.record-name {
  font-size: $font-size-sm;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.check-icon {
  color: $primary-color;
}

.no-results {
  padding: $spacing-md;
  text-align: center;
  color: $text-disabled;
  font-size: $font-size-sm;
}
</style>
