<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { RecordEntity, FieldEntity } from '@/db/schema'
import { FieldType, type CellValue, type FieldTypeValue } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'
import { generateId } from '@/utils/id'
import dayjs from 'dayjs'

interface Props {
  fields: FieldEntity[]
  record?: RecordEntity
  readonly?: boolean
  title?: string
  description?: string
  submitButtonText?: string
  visibleFieldIds?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
  title: '',
  description: '',
  submitButtonText: '提交'
})

const emit = defineEmits<{
  (e: 'submit', values: Record<string, CellValue>): void
  (e: 'cancel'): void
}>()

const formValues = ref<Record<string, CellValue>>({})
const formErrors = ref<Record<string, string>>({})
const isSubmitting = ref(false)
const submitSuccess = ref(false)

// 获取主键字段
const primaryField = computed(() => {
  return props.fields.find((f) => f.isPrimary) || props.fields[0]
})

// 检查字段是否为主键字段
function isPrimaryField(field: FieldEntity): boolean {
  return primaryField.value?.id === field.id
}

const visibleFields = computed(() => {
  let fields = props.fields.filter(f => !f.options?.hidden)
  
  // 如果指定了可见字段ID列表，则只显示这些字段
  if (props.visibleFieldIds && props.visibleFieldIds.length > 0) {
    fields = fields.filter(f => props.visibleFieldIds?.includes(f.id))
  }
  
  // 过滤掉系统字段（创建人、创建时间、修改人、修改时间、自动编号）
  if (!props.readonly) {
    const systemFieldTypes: FieldTypeValue[] = [
      FieldType.CREATED_BY,
      FieldType.CREATED_TIME,
      FieldType.UPDATED_BY,
      FieldType.UPDATED_TIME,
      FieldType.AUTO_NUMBER
    ]
    fields = fields.filter(f => !systemFieldTypes.includes(f.type as FieldTypeValue))
  }
  
  return fields
})

const isValid = computed(() => {
  return Object.keys(formErrors.value).length === 0
})

const formTitle = computed(() => {
  return props.title || '数据收集表单'
})

watch(() => props.record, (newRecord) => {
  if (newRecord) {
    formValues.value = { ...newRecord.values }
  } else {
    resetForm()
  }
}, { immediate: true })

function validateField(field: FieldEntity, value: CellValue): string | null {
  // 主键字段跳过验证（自动生成）
  if (isPrimaryField(field)) {
    return null
  }
  
  // 必填验证
  if (field.options?.required && (value === null || value === undefined || value === '' || value === false)) {
    return `${field.name}为必填项`
  }
  
  // 如果值为空且不是必填项，跳过其他验证
  if (value === null || value === undefined || value === '') {
    return null
  }
  
  // 字段类型特定验证
  switch (field.type) {
    case FieldType.EMAIL:
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value))) {
        return '请输入有效的邮箱地址'
      }
      break
    case FieldType.PHONE:
      if (!/^1[3-9]\d{9}$/.test(String(value))) {
        return '请输入有效的手机号码'
      }
      break
    case FieldType.URL:
      try {
        new URL(String(value))
      } catch {
        return '请输入有效的URL'
      }
      break
    case FieldType.NUMBER:
    case FieldType.RATING:
      if (typeof value === 'number' || !isNaN(Number(value))) {
        const numValue = Number(value)
        // 最小值验证
        if (field.options?.min !== undefined && numValue < Number(field.options.min)) {
          return `${field.name}不能小于${field.options.min}`
        }
        // 最大值验证
        if (field.options?.max !== undefined && numValue > Number(field.options.max)) {
          return `${field.name}不能大于${field.options.max}`
        }
      }
      break
    case FieldType.TEXT:
    case FieldType.MULTI_SELECT:
      const strValue = String(value)
      // 最小长度验证
      if (field.options?.minLength !== undefined && strValue.length < Number(field.options.minLength)) {
        return `${field.name}至少需要${field.options.minLength}个字符`
      }
      // 最大长度验证
      if (field.options?.maxLength !== undefined && strValue.length > Number(field.options.maxLength)) {
        return `${field.name}不能超过${field.options.maxLength}个字符`
      }
      break
  }
  
  // 自定义验证规则
  const validation = field.options?.validation as { pattern?: string; message?: string } | undefined
  if (validation?.pattern) {
    const pattern = new RegExp(validation.pattern)
    if (!pattern.test(String(value))) {
      return validation.message || `${field.name}格式不正确`
    }
  }
  
  return null
}

function handleFieldChange(fieldId: string, value: CellValue) {
  formValues.value[fieldId] = value
  
  const field = props.fields.find(f => f.id === fieldId)
  if (field) {
    const error = validateField(field, value)
    if (error) {
      formErrors.value[fieldId] = error
    } else {
      delete formErrors.value[fieldId]
    }
  }
}

async function handleSubmit() {
  formErrors.value = {}
  
  // 只验证可见字段
  visibleFields.value.forEach(field => {
    const error = validateField(field, formValues.value[field.id])
    if (error) {
      formErrors.value[field.id] = error
    }
  })
  
  if (Object.keys(formErrors.value).length === 0) {
    isSubmitting.value = true
    try {
      emit('submit', { ...formValues.value })
      submitSuccess.value = true
      
      // 如果不是编辑模式，提交成功后重置表单
      if (!props.record) {
        setTimeout(() => {
          resetForm()
          submitSuccess.value = false
        }, 1500)
      }
    } finally {
      isSubmitting.value = false
    }
  } else {
    // 显示第一个错误
    const firstError = Object.values(formErrors.value)[0]
    ElMessage.error(firstError)
  }
}

async function handleCancel() {
  // 如果有填写内容，确认是否放弃
  const hasValues = Object.values(formValues.value).some(v => 
    v !== null && v !== undefined && v !== '' && v !== false
  )
  
  if (hasValues && !props.readonly) {
    try {
      await ElMessageBox.confirm(
        '确定要取消吗？已填写的内容将不会保存。',
        '确认取消',
        {
          confirmButtonText: '确定',
          cancelButtonText: '继续填写',
          type: 'warning'
        }
      )
      emit('cancel')
    } catch {
      // 用户选择继续填写
    }
  } else {
    emit('cancel')
  }
}

function resetForm() {
  formValues.value = {}
  formErrors.value = {}
  submitSuccess.value = false
  
  // 为主键字段自动生成唯一ID
  if (primaryField.value && !props.record) {
    formValues.value[primaryField.value.id] = generateId()
  }
  
  // 设置默认值
  visibleFields.value.forEach(field => {
    if (field.options?.defaultValue !== undefined && !isPrimaryField(field)) {
      formValues.value[field.id] = field.options.defaultValue as CellValue
    }
  })
}

// 获取字段类型对应的组件类型
function getFieldComponentType(field: FieldEntity): string {
  switch (field.type) {
    case FieldType.TEXT:
    case FieldType.URL:
    case FieldType.EMAIL:
    case FieldType.PHONE:
      return 'text'
    case FieldType.NUMBER:
    case FieldType.RATING:
      return 'number'
    case FieldType.SINGLE_SELECT:
      return 'singleSelect'
    case FieldType.MULTI_SELECT:
      return 'multiSelect'
    case FieldType.DATE:
      return 'date'
    case FieldType.CHECKBOX:
      return 'checkbox'
    default:
      return 'text'
  }
}

// 获取单选/多选选项
function getSelectOptions(field: FieldEntity) {
  return (
    (field.options?.options as Array<{
      id: string;
      name: string;
      color?: string;
    }>) || []
  )
}

// 获取数值字段精度
function getNumberPrecision(field: FieldEntity): number {
  return (field.options?.precision as number) ?? 0
}

// 获取日期字段是否显示时间
function getDateShowTime(field: FieldEntity): boolean {
  return (field.options?.showTime as boolean) ?? false
}

// 获取日期字段格式
function getDateFormat(field: FieldEntity): string {
  return getDateShowTime(field) ? 'YYYY-MM-DD HH:mm:ss' : 'YYYY-MM-DD'
}

// 获取日期选择器类型
function getDatePickerType(field: FieldEntity): 'date' | 'datetime' {
  return getDateShowTime(field) ? 'datetime' : 'date'
}

// 处理日期变更
function handleDateChange(fieldId: string, val: Date | null) {
  if (!val) {
    handleFieldChange(fieldId, null)
    return
  }
  
  const field = props.fields.find(f => f.id === fieldId)
  if (!field) return
  
  const showTime = getDateShowTime(field)
  if (showTime) {
    // 显示时间时存储为时间戳
    handleFieldChange(fieldId, val.getTime())
  } else {
    // 仅日期时存储为日期字符串
    handleFieldChange(fieldId, dayjs(val).format('YYYY-MM-DD'))
  }
}

// 导出表单数据为 JSON
function exportFormData() {
  const data = {
    title: formTitle.value,
    description: props.description,
    fields: visibleFields.value.map(f => ({
      id: f.id,
      name: f.name,
      type: f.type,
      required: f.options?.required,
      options: f.options
    })),
    values: { ...formValues.value }
  }
  
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `form-data-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('表单数据已导出')
}

defineExpose({
  resetForm,
  validate: () => isValid.value,
  getValues: () => ({ ...formValues.value }),
  exportFormData
})
</script>

<template>
  <div class="form-view">
    <!-- 表单头部 -->
    <div class="form-header">
      <h2 class="form-title">{{ formTitle }}</h2>
      <p v-if="description" class="form-description">{{ description }}</p>
    </div>
    
    <!-- 提交成功提示 -->
    <el-result
      v-if="submitSuccess"
      icon="success"
      title="提交成功"
      sub-title="您的数据已成功保存"
    >
      <template #extra>
        <el-button type="primary" @click="resetForm">继续填写</el-button>
      </template>
    </el-result>
    
    <!-- 空状态 -->
    <el-empty
      v-else-if="visibleFields.length === 0"
      description="暂无可见字段"
    >
      <template #description>
        <p>当前没有可填写的字段</p>
        <p class="sub-text">请在字段管理中配置表单字段</p>
      </template>
    </el-empty>
    
    <!-- 表单内容 -->
    <el-form
      v-else
      label-position="top"
      class="form-container"
      @submit.prevent="handleSubmit"
    >
      <div
        v-for="field in visibleFields"
        :key="field.id"
        class="form-item"
        :class="{ 'has-error': formErrors[field.id], 'is-readonly': readonly || isPrimaryField(field) }"
      >
        <label class="form-label">
          {{ field.name }}
          <span v-if="field.options?.required && !readonly && !isPrimaryField(field)" class="required-mark">*</span>
        </label>
        
        <div class="form-control">
          <!-- 主键字段 - 自动生成ID且只读 -->
          <template v-if="isPrimaryField(field)">
            <el-input
              :model-value="String(formValues[field.id] || '')"
              disabled
              :placeholder="`自动生成${field.name}`"
              class="primary-field-input"
            />
            <span class="auto-filled-hint">系统自动生成唯一标识，不可修改</span>
          </template>
          
          <!-- 文本类型 -->
          <template v-else-if="getFieldComponentType(field) === 'text'">
            <el-input
              :model-value="String(formValues[field.id] || '')"
              :placeholder="`请输入${field.name}`"
              :disabled="readonly"
              @update:model-value="(val) => handleFieldChange(field.id, val)"
            />
          </template>
          
          <!-- 数字类型 - 与看板视图一致使用 ElInputNumber -->
          <template v-else-if="getFieldComponentType(field) === 'number'">
            <el-input-number
              :model-value="Number(formValues[field.id] || 0)"
              :placeholder="`请输入${field.name}`"
              :disabled="readonly"
              :precision="getNumberPrecision(field)"
              :min="field.options?.min !== undefined ? Number(field.options.min) : undefined"
              :max="field.options?.max !== undefined ? Number(field.options.max) : undefined"
              style="width: 100%"
              @update:model-value="(val) => handleFieldChange(field.id, val as CellValue)"
            />
          </template>
          
          <!-- 单选类型 -->
          <template v-else-if="getFieldComponentType(field) === 'singleSelect'">
            <el-select
              :model-value="formValues[field.id] as string | undefined"
              :placeholder="`请选择${field.name}`"
              :disabled="readonly"
              style="width: 100%"
              clearable
              @update:model-value="(val) => handleFieldChange(field.id, val)"
            >
              <el-option
                v-for="option in getSelectOptions(field)"
                :key="option.id"
                :label="option.name"
                :value="option.id"
              >
                <span
                  class="option-color"
                  :style="{ backgroundColor: option.color || '#3370FF' }"
                />
                <span>{{ option.name }}</span>
              </el-option>
            </el-select>
          </template>
          
          <!-- 多选类型 -->
          <template v-else-if="getFieldComponentType(field) === 'multiSelect'">
            <el-select
              :model-value="(formValues[field.id] as string[]) || []"
              :placeholder="`请选择${field.name}`"
              :disabled="readonly"
              style="width: 100%"
              multiple
              clearable
              @update:model-value="(val) => handleFieldChange(field.id, val)"
            >
              <el-option
                v-for="option in getSelectOptions(field)"
                :key="option.id"
                :label="option.name"
                :value="option.id"
              >
                <span
                  class="option-color"
                  :style="{ backgroundColor: option.color || '#3370FF' }"
                />
                <span>{{ option.name }}</span>
              </el-option>
            </el-select>
          </template>
          
          <!-- 日期类型 -->
          <template v-else-if="getFieldComponentType(field) === 'date'">
            <el-date-picker
              :model-value="formValues[field.id] as unknown as Date | undefined"
              :type="getDatePickerType(field)"
              :placeholder="`请选择${field.name}`"
              :format="getDateFormat(field)"
              :disabled="readonly"
              style="width: 100%"
              @update:model-value="(val) => handleDateChange(field.id, val as Date | null)"
            />
          </template>
          
          <!-- 复选框类型 - 与看板视图一致使用 ElSwitch -->
          <template v-else-if="getFieldComponentType(field) === 'checkbox'">
            <el-switch
              :model-value="Boolean(formValues[field.id])"
              :disabled="readonly"
              @update:model-value="(val) => handleFieldChange(field.id, val)"
            />
          </template>
        </div>
        
        <div v-if="formErrors[field.id]" class="form-error">
          <el-icon><Warning /></el-icon>
          {{ formErrors[field.id] }}
        </div>
        
        <div v-if="field.options?.description && !readonly && !isPrimaryField(field)" class="form-field-description">
          {{ field.options.description }}
        </div>
      </div>
      
      <div v-if="!readonly" class="form-actions">
        <el-button @click="handleCancel">取消</el-button>
        <el-button 
          type="primary" 
          native-type="submit" 
          :loading="isSubmitting"
          :disabled="!isValid && Object.keys(formErrors).length > 0"
        >
          {{ submitButtonText }}
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.form-view {
  width: 100%;
  max-width: 640px;
  margin: 0 auto;
  padding: $spacing-xl;
  background: $surface-color;
  border-radius: $border-radius-lg;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.form-header {
  text-align: center;
  margin-bottom: $spacing-xl;
  padding-bottom: $spacing-lg;
  border-bottom: 1px solid $border-color;
}

.form-title {
  font-size: $font-size-xl;
  font-weight: 600;
  color: $text-primary;
  margin: 0 0 $spacing-sm;
}

.form-description {
  font-size: $font-size-base;
  color: $text-secondary;
  margin: 0;
  line-height: 1.6;
}

.form-container {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
  
  &.has-error {
    .form-label {
      color: $error-color;
    }
    
    .form-control {
      :deep(.el-input__wrapper),
      :deep(.el-select__wrapper),
      :deep(.el-textarea__inner) {
        border-color: $error-color;
        box-shadow: 0 0 0 1px $error-color;
      }
    }
  }
  
  &.is-readonly {
    .form-control {
      :deep(.el-input__wrapper),
      :deep(.el-select__wrapper) {
        background-color: $bg-color;
      }
    }
  }
}

.form-label {
  font-size: $font-size-sm;
  font-weight: 500;
  color: $text-primary;
  display: flex;
  align-items: center;
}

.required-mark {
  color: $error-color;
  margin-left: 4px;
}

.form-control {
  width: 100%;
}

.form-error {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: $font-size-xs;
  color: $error-color;
}

.form-field-description {
  font-size: $font-size-xs;
  color: $text-secondary;
  line-height: 1.5;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: $spacing-md;
  margin-top: $spacing-xl;
  padding-top: $spacing-lg;
  border-top: 1px solid $border-color;
}

.sub-text {
  font-size: $font-size-sm;
  color: $text-secondary;
  margin-top: $spacing-xs;
}

// 主键字段样式
.primary-field-input {
  :deep(.el-input__wrapper) {
    background-color: $bg-color;
  }
}

.auto-filled-hint {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-top: 4px;
  display: block;
}

// 选项颜色标记
.option-color {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
  vertical-align: middle;
}

// 响应式适配
@media (max-width: 768px) {
  .form-view {
    padding: $spacing-lg;
    margin: $spacing-md;
    max-width: none;
  }
  
  .form-title {
    font-size: $font-size-lg;
  }
  
  .form-actions {
    flex-direction: column-reverse;
    
    .el-button {
      width: 100%;
    }
  }
}
</style>
