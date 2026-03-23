<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { FieldEntity } from '@/db/schema'
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

const localValue = ref('')

watch(() => props.modelValue, (newVal) => {
  localValue.value = String(newVal || '')
}, { immediate: true })

const isValid = computed(() => {
  if (!localValue.value) return true
  const phoneRegex = /^1[3-9]\d{9}$/
  return phoneRegex.test(localValue.value)
})

function handleInput(value: string) {
  localValue.value = value
  emit('update:modelValue', value)
}

function formatPhone(value: string): string {
  const cleaned = value.replace(/\D/g, '')
  if (cleaned.length <= 3) return cleaned
  if (cleaned.length <= 7) return `${cleaned.slice(0, 3)} ${cleaned.slice(3)}`
  return `${cleaned.slice(0, 3)} ${cleaned.slice(3, 7)} ${cleaned.slice(7, 11)}`
}

function handleBlur() {
  const cleaned = localValue.value.replace(/\D/g, '')
  if (cleaned) {
    localValue.value = cleaned
    emit('update:modelValue', cleaned)
  }
}
</script>

<template>
  <div class="phone-field">
    <el-input
      v-if="!readonly"
      :model-value="localValue"
      placeholder="请输入手机号码"
      :class="{ 'is-error': !isValid }"
      @update:model-value="handleInput"
      @blur="handleBlur"
    >
      <template #prefix>
        <el-icon><Phone /></el-icon>
      </template>
    </el-input>
    <div v-else class="phone-display">
      <el-icon><Phone /></el-icon>
      <span v-if="localValue" class="phone-number">
        {{ formatPhone(localValue) }}
      </span>
      <span v-else class="empty-text">-</span>
    </div>
    <div v-if="!isValid && !readonly" class="error-message">
      请输入正确的手机号码
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.phone-field {
  width: 100%;
}

.is-error {
  :deep(.el-input__wrapper) {
    border-color: $error-color;
  }
}

.phone-display {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  color: $text-primary;
}

.phone-number {
  font-size: $font-size-sm;
}

.empty-text {
  color: $text-disabled;
}

.error-message {
  font-size: $font-size-xs;
  color: $error-color;
  margin-top: 2px;
}
</style>
