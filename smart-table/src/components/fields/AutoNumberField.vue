<script setup lang="ts">
import { computed } from 'vue'
import type { FieldEntity } from '@/db/schema'
import type { CellValue } from '@/types'

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
  return String(props.modelValue)
})
</script>

<template>
  <div class="auto-number-field">
    <span class="number-value">{{ displayValue }}</span>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.auto-number-field {
  width: 100%;
}

.number-value {
  font-size: $font-size-sm;
  color: $text-secondary;
  font-family: monospace;
}
</style>
