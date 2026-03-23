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

const currentValue = ref(0)

const progressColor = computed(() => {
  const value = currentValue.value
  if (value < 30) return '#EF4444'
  if (value < 60) return '#FBBF24'
  if (value < 90) return '#3370FF'
  return '#34D399'
})

watch(() => props.modelValue, (newVal) => {
  currentValue.value = Number(newVal) || 0
}, { immediate: true })

function handleChange(value: number) {
  if (props.readonly) return
  currentValue.value = value
  emit('update:modelValue', value)
}

function handleInputChange(value: number | undefined) {
  if (props.readonly) return
  const val = Math.min(100, Math.max(0, value || 0))
  handleChange(val)
}
</script>

<template>
  <div class="progress-field">
    <div class="progress-wrapper">
      <el-progress
        :percentage="currentValue"
        :stroke-width="10"
        :color="progressColor"
        :show-text="false"
      />
      <div v-if="!readonly" class="progress-input">
        <el-input-number
          :model-value="currentValue"
          :min="0"
          :max="100"
          :controls="false"
          size="small"
          @update:model-value="handleInputChange"
        />
        <span class="percent-sign">%</span>
      </div>
      <span v-else class="progress-value">
        {{ currentValue }}%
      </span>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.progress-field {
  width: 100%;
}

.progress-wrapper {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.progress-input {
  display: flex;
  align-items: center;
  gap: 2px;
  
  :deep(.el-input-number) {
    width: 60px;
    
    .el-input__inner {
      text-align: center;
      padding: 0 4px;
    }
  }
}

.percent-sign {
  font-size: $font-size-sm;
  color: $text-secondary;
}

.progress-value {
  font-size: $font-size-sm;
  color: $text-secondary;
  min-width: 40px;
  text-align: right;
}
</style>
