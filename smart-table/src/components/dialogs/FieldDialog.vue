<script setup lang="ts">
import { ref } from 'vue'
import { ElDialog, ElButton, ElInput, ElSelect, ElOption, ElForm, ElFormItem, ElSwitch, ElColorPicker, ElTag, ElMessage } from 'element-plus'
import { fieldService } from '@/db/services/fieldService'
import { FieldType, getFieldTypeLabel, getFieldTypeIcon, type FieldTypeValue } from '@/types/fields'
import type { FieldEntity } from '@/db/schema'
import type { FieldOptions } from '@/types'

const props = defineProps<{
  visible: boolean
  tableId: string
  fields: FieldEntity[]
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'field-created': [field: FieldEntity]
  'field-updated': [field: FieldEntity]
  'field-deleted': [fieldId: string]
}>()

const activeTab = ref<'list' | 'create' | 'edit'>('list')
const editingField = ref<FieldEntity | null>(null)

const newField = ref<{
  name: string
  type: FieldTypeValue
  isRequired: boolean
  description: string
}>({
  name: '',
  type: FieldType.TEXT,
  isRequired: false,
  description: ''
})

const systemTypes = [FieldType.CREATED_BY, FieldType.CREATED_TIME, FieldType.UPDATED_BY, FieldType.UPDATED_TIME, FieldType.AUTO_NUMBER]
const fieldTypes = Object.values(FieldType).filter((type): type is FieldTypeValue => 
  !systemTypes.includes(type as typeof systemTypes[number])
)

const selectOptions = ref<{ id: string; name: string; color: string }[]>([])
const newOptionName = ref('')
const newOptionColor = ref('#3370FF')

function openCreateField() {
  activeTab.value = 'create'
  newField.value = {
    name: '',
    type: FieldType.TEXT,
    isRequired: false,
    description: ''
  }
  selectOptions.value = []
}

function openEditField(field: FieldEntity) {
  editingField.value = field
  activeTab.value = 'edit'
  newField.value = {
    name: field.name,
    type: field.type as FieldTypeValue,
    isRequired: field.isRequired ?? false,
    description: field.description || ''
  }
  if (field.type === FieldType.SINGLE_SELECT || field.type === FieldType.MULTI_SELECT) {
    selectOptions.value = (field.options?.options as { id: string; name: string; color: string }[]) || []
  } else {
    selectOptions.value = []
  }
}

function backToList() {
  activeTab.value = 'list'
  editingField.value = null
  newField.value = {
    name: '',
    type: FieldType.TEXT,
    isRequired: false,
    description: ''
  }
  selectOptions.value = []
}

async function createField() {
  if (!newField.value.name.trim()) {
    ElMessage.warning('请输入字段名称')
    return
  }

  try {
    const options: FieldOptions = {}
    if (newField.value.type === FieldType.SINGLE_SELECT || newField.value.type === FieldType.MULTI_SELECT) {
      options.options = selectOptions.value
    }

    const field = await fieldService.createField({
      tableId: props.tableId,
      name: newField.value.name.trim(),
      type: newField.value.type,
      isRequired: newField.value.isRequired,
      description: newField.value.description,
      options: Object.keys(options).length > 0 ? options : undefined
    })

    emit('field-created', field)
    ElMessage.success('字段创建成功')
    backToList()
  } catch (error) {
    ElMessage.error('字段创建失败: ' + (error instanceof Error ? error.message : '未知错误'))
  }
}

async function updateField() {
  if (!editingField.value) return
  if (!newField.value.name.trim()) {
    ElMessage.warning('请输入字段名称')
    return
  }

  try {
    const options: FieldOptions = { ...editingField.value.options }
    if (newField.value.type === FieldType.SINGLE_SELECT || newField.value.type === FieldType.MULTI_SELECT) {
      options.options = selectOptions.value
    }

    await fieldService.updateField(editingField.value.id, {
      name: newField.value.name.trim(),
      isRequired: newField.value.isRequired,
      description: newField.value.description,
      options: options as Record<string, unknown>
    })

    const updatedField = { ...editingField.value, ...newField.value, options: options as Record<string, unknown> }
    emit('field-updated', updatedField)
    ElMessage.success('字段更新成功')
    backToList()
  } catch (error) {
    ElMessage.error('字段更新失败: ' + (error instanceof Error ? error.message : '未知错误'))
  }
}

async function deleteField(field: FieldEntity) {
  if (field.isSystem) {
    ElMessage.warning('系统字段不能删除')
    return
  }

  try {
    await fieldService.deleteField(field.id)
    emit('field-deleted', field.id)
    ElMessage.success('字段删除成功')
  } catch (error) {
    ElMessage.error('字段删除失败: ' + (error instanceof Error ? error.message : '未知错误'))
  }
}

function addOption() {
  if (!newOptionName.value.trim()) return
  
  selectOptions.value.push({
    id: Date.now().toString(),
    name: newOptionName.value.trim(),
    color: newOptionColor.value
  })
  newOptionName.value = ''
}

function removeOption(index: number) {
  selectOptions.value.splice(index, 1)
}

function onTypeChange() {
  if (newField.value.type !== FieldType.SINGLE_SELECT && newField.value.type !== FieldType.MULTI_SELECT) {
    selectOptions.value = []
  }
}

const presetColors = [
  '#3370FF', '#34D399', '#FBBF24', '#EF4444', '#8B5CF6',
  '#EC4899', '#14B8A6', '#F59E0B', '#6366F1', '#10B981'
]
</script>

<template>
  <ElDialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="字段管理"
    width="600px"
    :close-on-click-modal="false"
  >
    <!-- 字段列表 -->
    <div v-if="activeTab === 'list'" class="field-list">
      <div class="field-list-header">
        <span class="field-count">共 {{ fields.length }} 个字段</span>
        <ElButton type="primary" size="small" @click="openCreateField">
          + 添加字段
        </ElButton>
      </div>
      
      <div class="field-items">
        <div
          v-for="field in fields"
          :key="field.id"
          class="field-item"
          :class="{ 'is-system': field.isSystem }"
        >
          <div class="field-info">
            <span class="field-icon">{{ getFieldTypeIcon(field.type) }}</span>
            <span class="field-name">{{ field.name }}</span>
            <span class="field-type">{{ getFieldTypeLabel(field.type) }}</span>
            <ElTag v-if="field.isSystem" size="small" type="info">系统</ElTag>
            <ElTag v-if="field.isRequired" size="small" type="warning">必填</ElTag>
          </div>
          <div class="field-actions">
            <ElButton
              v-if="!field.isSystem"
              link
              type="primary"
              size="small"
              @click="openEditField(field)"
            >
              编辑
            </ElButton>
            <ElButton
              v-if="!field.isSystem"
              link
              type="danger"
              size="small"
              @click="deleteField(field)"
            >
              删除
            </ElButton>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑字段 -->
    <div v-else class="field-form">
      <ElForm label-width="80px">
        <ElFormItem label="字段名称" required>
          <ElInput
            v-model="newField.name"
            placeholder="请输入字段名称"
            maxlength="50"
            show-word-limit
          />
        </ElFormItem>

        <ElFormItem label="字段类型" required>
          <ElSelect v-model="newField.type" style="width: 100%" @change="onTypeChange">
            <ElOption
              v-for="type in fieldTypes"
              :key="type"
              :label="getFieldTypeLabel(type)"
              :value="type"
            >
              <span class="type-option">
                <span class="type-icon">{{ getFieldTypeIcon(type) }}</span>
                <span>{{ getFieldTypeLabel(type) }}</span>
              </span>
            </ElOption>
          </ElSelect>
        </ElFormItem>

        <ElFormItem v-if="newField.type === FieldType.SINGLE_SELECT || newField.type === FieldType.MULTI_SELECT" label="选项">
          <div class="options-editor">
            <div class="options-list">
              <div
                v-for="(option, index) in selectOptions"
                :key="option.id"
                class="option-item"
              >
                <ElColorPicker v-model="option.color" size="small" :predefine="presetColors" />
                <ElInput v-model="option.name" size="small" placeholder="选项名称" />
                <ElButton link type="danger" size="small" @click="removeOption(index)">
                  删除
                </ElButton>
              </div>
            </div>
            <div class="add-option">
              <ElColorPicker v-model="newOptionColor" size="small" :predefine="presetColors" />
              <ElInput
                v-model="newOptionName"
                size="small"
                placeholder="输入选项名称，按回车添加"
                @keyup.enter="addOption"
              />
              <ElButton type="primary" size="small" @click="addOption">添加</ElButton>
            </div>
          </div>
        </ElFormItem>

        <ElFormItem label="必填">
          <ElSwitch v-model="newField.isRequired" />
        </ElFormItem>

        <ElFormItem label="字段描述">
          <ElInput
            v-model="newField.description"
            type="textarea"
            :rows="2"
            placeholder="请输入字段描述（可选）"
          />
        </ElFormItem>
      </ElForm>

      <div class="form-actions">
        <ElButton @click="backToList">返回</ElButton>
        <ElButton type="primary" @click="activeTab === 'create' ? createField() : updateField()">
          {{ activeTab === 'create' ? '创建' : '保存' }}
        </ElButton>
      </div>
    </div>
  </ElDialog>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.field-list {
  .field-list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid $border-color;

    .field-count {
      color: $text-secondary;
      font-size: $font-size-sm;
    }
  }

  .field-items {
    max-height: 400px;
    overflow-y: auto;
  }

  .field-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    border-radius: $border-radius-md;
    transition: background-color 0.2s;

    &:hover {
      background-color: $bg-color;
    }

    &.is-system {
      opacity: 0.7;
    }

    .field-info {
      display: flex;
      align-items: center;
      gap: 8px;

      .field-icon {
        font-size: 16px;
      }

      .field-name {
        font-weight: 500;
        color: $text-primary;
      }

      .field-type {
        font-size: $font-size-xs;
        color: $text-secondary;
        background: $bg-color;
        padding: 2px 6px;
        border-radius: $border-radius-sm;
      }
    }

    .field-actions {
      display: flex;
      gap: 8px;
    }
  }
}

.field-form {
  .type-option {
    display: flex;
    align-items: center;
    gap: 8px;

    .type-icon {
      font-size: 14px;
    }
  }

  .options-editor {
    .options-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 12px;
    }

    .option-item {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .add-option {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px solid $border-color;
  }
}
</style>
