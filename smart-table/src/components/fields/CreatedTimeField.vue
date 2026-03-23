<script setup lang="ts">
import { computed } from 'vue'
import type { FieldEntity } from '@/db/schema'
import type { CellValue } from '@/types'
import dayjs from 'dayjs'

interface Props {
  modelValue: CellValue
  field: FieldEntity
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: true
})

const displayValue = computed(() => {
  if (props.modelValue === null || props.modelValue === undefined) {
    return '-'
  }
  
  const timestamp = Number(props.modelValue)
  if (isNaN(timestamp)) {
    return String(props.modelValue)
  }
  
  const format = (props.field.options?.format as string) || 'YYYY-MM-DD HH:mm'
  return dayjs(timestamp).format(format)
})
</script>

<template>
  <div class="created-time-field">
    <span class="time-value">{{ displayValue }}</span>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.created-time-field {
  width: 100%;
}

.time-value {
  font-size: $font-size-sm;
  color: $text-secondary;
}
</style>
