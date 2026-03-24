<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { RecordEntity, FieldEntity } from '@/db/schema'
import { FieldType } from '@/types'
import KanbanColumn from './KanbanColumn.vue'
import AddRecordDialog from '@/components/dialogs/AddRecordDialog.vue'

interface Props {
  fields: FieldEntity[]
  records: RecordEntity[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'updateRecord', recordId: string, values: Record<string, unknown>): void
  (e: 'addRecord', values: Record<string, unknown>): void
  (e: 'deleteRecord', recordId: string): void
  (e: 'editRecord', recordId: string): void
}>()

const groupFieldId = ref<string>('')
const cardFields = ref<string[]>([])

// 添加记录对话框状态
const addRecordDialogVisible = ref(false)
const currentGroupId = ref<string>('')
const currentGroupName = ref<string>('')

const groupField = computed(() => {
  return props.fields.find(f => f.id === groupFieldId.value)
})

const selectFields = computed(() => {
  return props.fields.filter(f => 
    f.type === FieldType.SINGLE_SELECT || f.type === FieldType.MULTI_SELECT
  )
})

const groups = computed(() => {
  if (!groupField.value) {
    return [{ id: 'default', name: '全部', records: props.records }]
  }

  const options = groupField.value.options?.options as Array<{ id: string; name: string; color?: string }> || []
  const grouped: Record<string, RecordEntity[]> = {}
  
  options.forEach(opt => {
    grouped[opt.id] = []
  })
  grouped['uncategorized'] = []

  props.records.forEach(record => {
    const value = record.values[groupFieldId.value]
    if (value && grouped[value as string]) {
      grouped[value as string].push(record)
    } else {
      grouped['uncategorized'].push(record)
    }
  })

  return [
    ...options.map(opt => ({
      id: opt.id,
      name: opt.name,
      color: opt.color,
      records: grouped[opt.id]
    })),
    { id: 'uncategorized', name: '未分组', records: grouped['uncategorized'] }
  ]
})

function handleAddRecord(groupId: string, groupName: string) {
  currentGroupId.value = groupId
  currentGroupName.value = groupName
  addRecordDialogVisible.value = true
}

function handleSaveNewRecord(values: Record<string, unknown>) {
  emit('addRecord', values)
}

function handleUpdateRecord(recordId: string, values: Record<string, unknown>) {
  emit('updateRecord', recordId, values)
}

function handleDeleteRecord(recordId: string) {
  emit('deleteRecord', recordId)
}

function handleEditRecord(recordId: string) {
  emit('editRecord', recordId)
}

function handleMoveRecord(recordId: string, targetGroupId: string) {
  if (groupFieldId.value) {
    const newGroupId = targetGroupId === 'uncategorized' ? null : targetGroupId
    emit('updateRecord', recordId, { [groupFieldId.value]: newGroupId })
  }
}

onMounted(() => {
  if (selectFields.value.length > 0) {
    groupFieldId.value = selectFields.value[0].id
  }
  if (props.fields.length > 0) {
    cardFields.value = props.fields.slice(0, 3).map(f => f.id)
  }
})
</script>

<template>
  <div class="kanban-view">
    <div class="kanban-toolbar">
      <el-select v-model="groupFieldId" placeholder="选择分组字段" class="group-select">
        <el-option
          v-for="field in selectFields"
          :key="field.id"
          :label="field.name"
          :value="field.id"
        />
      </el-select>
      <el-select
        v-model="cardFields"
        multiple
        collapse-tags
        collapse-tags-tooltip
        placeholder="选择卡片显示字段"
        class="card-fields-select"
      >
        <el-option
          v-for="field in fields"
          :key="field.id"
          :label="field.name"
          :value="field.id"
        />
      </el-select>
    </div>
    
    <div ref="kanbanRef" class="kanban-container">
      <KanbanColumn
        v-for="group in groups"
        :key="group.id"
        :group="group"
        :records="group.records"
        :fields="fields"
        :card-fields="cardFields"
        @add-record="handleAddRecord(group.id, group.name)"
        @edit-record="handleEditRecord"
        @update-record="handleUpdateRecord"
        @delete-record="handleDeleteRecord"
        @move-record="(recordId) => handleMoveRecord(recordId, group.id)"
      />
    
    <!-- 添加记录对话框 -->
    <AddRecordDialog
      v-model:visible="addRecordDialogVisible"
      :fields="fields"
      :group-field-id="groupFieldId"
      :group-id="currentGroupId"
      :group-name="currentGroupName"
      @save="handleSaveNewRecord"
    />
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.kanban-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: $bg-color;
}

.kanban-toolbar {
  display: flex;
  gap: $spacing-md;
  padding: $spacing-md;
  background-color: $surface-color;
  border-bottom: 1px solid $border-color;
  
  .group-select {
    width: 200px;
  }
  
  .card-fields-select {
    width: 300px;
  }
}

.kanban-container {
  display: flex;
  flex: 1;
  gap: $spacing-md;
  padding: $spacing-md;
  overflow-x: auto;
  overflow-y: hidden;
}
</style>
