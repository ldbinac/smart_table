<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { RecordEntity, FieldEntity } from '@/db/schema'
import { FieldType, type CellValue } from '@/types'
import FieldComponentFactory from '@/components/fields/FieldComponentFactory.vue'

interface Props {
  fields: FieldEntity[]
  record?: RecordEntity
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false
})

const emit = defineEmits<{
  (e: 'submit', values: Record<string, CellValue>): void
  (e: 'cancel'): void
}>()

const formValues = ref<Record<string, CellValue>>({})
const formErrors = ref<Record<string, string>>({})

const visibleFields = computed(() => {
  return props.fields.filter(f => !f.options?.hidden)
})

const isValid = computed(() => {
  return Object.keys(formErrors.value).length === 0
})

watch(() => props.record, (newRecord) => {
  if (newRecord) {
    formValues.value = { ...newRecord.values }
  } else {
    formValues.value = {}
    props.fields.forEach(field => {
      if (field.options?.defaultValue !== undefined) {
        formValues.value[field.id] = field.options.defaultValue as CellValue
      }
    })
  }
}, { immediate: true })

function validateField(field: FieldEntity, value: CellValue): string | null {
  if (field.options?.required && (value === null || value === undefined || value === '')) {
    return `${field.name}为必填项`
  }
  
  switch (field.type) {
    case FieldType.EMAIL:
      if (value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value))) {
        return '请输入有效的邮箱地址'
      }
      break
    case FieldType.PHONE:
      if (value && !/^1[3-9]\d{9}$/.test(String(value))) {
        return '请输入有效的手机号码'
      }
      break
    case FieldType.URL:
      if (value) {
        try {
          new URL(String(value))
        } catch {
          return '请输入有效的URL'
        }
      }
      break
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

function handleSubmit() {
  formErrors.value = {}
  
  props.fields.forEach(field => {
    const error = validateField(field, formValues.value[field.id])
    if (error) {
      formErrors.value[field.id] = error
    }
  })
  
  if (Object.keys(formErrors.value).length === 0) {
    emit('submit', { ...formValues.value })
  }
}

function handleCancel() {
  emit('cancel')
}

function resetForm() {
  formValues.value = {}
  formErrors.value = {}
  props.fields.forEach(field => {
    if (field.options?.defaultValue !== undefined) {
      formValues.value[field.id] = field.options.defaultValue as CellValue
    }
  })
}

defineExpose({
  resetForm,
  validate: () => isValid.value,
  getValues: () => ({ ...formValues.value })
})
</script>

<template>
  <div class="form-view">
    <el-form
      label-position="top"
      class="form-container"
      @submit.prevent="handleSubmit"
    >
      <div
        v-for="field in visibleFields"
        :key="field.id"
        class="form-item"
        :class="{ 'has-error': formErrors[field.id] }"
      >
        <label class="form-label">
          {{ field.name }}
          <span v-if="field.options?.required" class="required-mark">*</span>
        </label>
        
        <div class="form-control">
          <FieldComponentFactory
            :model-value="formValues[field.id]"
            :field="field"
            :readonly="readonly"
            @update:model-value="(val: CellValue) => handleFieldChange(field.id, val)"
          />
        </div>
        
        <div v-if="formErrors[field.id]" class="form-error">
          {{ formErrors[field.id] }}
        </div>
        
        <div v-if="field.options?.description" class="form-description">
          {{ field.options.description }}
        </div>
      </div>
      
      <div v-if="!readonly" class="form-actions">
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" native-type="submit" :disabled="!isValid">
          提交
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.form-view {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
  padding: $spacing-lg;
}

.form-container {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
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
      :deep(.el-select__wrapper) {
        border-color: $error-color;
      }
    }
  }
}

.form-label {
  font-size: $font-size-sm;
  font-weight: 500;
  color: $text-primary;
}

.required-mark {
  color: $error-color;
  margin-left: 2px;
}

.form-control {
  width: 100%;
}

.form-error {
  font-size: $font-size-xs;
  color: $error-color;
}

.form-description {
  font-size: $font-size-xs;
  color: $text-secondary;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: $spacing-sm;
  margin-top: $spacing-lg;
  padding-top: $spacing-lg;
  border-top: 1px solid $border-color;
}
</style>
