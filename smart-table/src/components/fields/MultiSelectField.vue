<script setup lang="ts">
import type { FieldOption } from '@/types/fields'

interface Props {
  modelValue: string[] | null
  field?: {
    id: string
    name: string
    type: string
    options?: {
      options?: FieldOption[]
      allowAddOptions?: boolean
    }
  }
  readonly?: boolean
  placeholder?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  readonly: false,
  placeholder: ''
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string[] | null): void
}>()

const options = computed(() => {
  return props.field?.options?.options ?? []
})

const selectedOptions = computed(() => {
  if (!props.modelValue || props.modelValue.length === 0) return []
  return options.value.filter(opt => props.modelValue!.includes(opt.id))
})

const localValue = computed({
  get: () => props.modelValue ?? [],
  set: (val: string[]) => emit('update:modelValue', val.length > 0 ? val : null)
})

const selectRef = ref()

const focus = () => {
  selectRef.value?.focus()
}

defineExpose({ focus })
</script>

<template>
  <div class="multi-select-field" :class="{ 'is-readonly': readonly }">
    <template v-if="readonly">
      <div class="multi-select-readonly">
        <template v-if="selectedOptions.length > 0">
          <span
            v-for="option in selectedOptions"
            :key="option.id"
            class="select-tag"
            :style="{ backgroundColor: option.color + '20', color: option.color }"
          >
            {{ option.name }}
          </span>
        </template>
        <span v-else class="empty-value">-</span>
      </div>
    </template>
    <template v-else>
      <el-select
        v-model="localValue"
        :placeholder="placeholder || '请选择'"
        multiple
        collapse-tags
        collapse-tags-tooltip
        clearable
        ref="selectRef"
        class="select-input"
      >
        <el-option
          v-for="option in options"
          :key="option.id"
          :label="option.name"
          :value="option.id"
        >
          <span
            class="option-tag"
            :style="{ backgroundColor: option.color + '20', color: option.color }"
          >
            {{ option.name }}
          </span>
        </el-option>
      </el-select>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.multi-select-field {
  width: 100%;

  &.is-readonly {
    .multi-select-readonly {
      padding: $spacing-sm;
      min-height: 32px;
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      align-items: center;
    }

    .empty-value {
      color: $text-disabled;
    }
  }

  .select-tag {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: $font-size-sm;
    font-weight: 500;
  }

  .option-tag {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: $font-size-sm;
  }

  .select-input {
    width: 100%;

    :deep(.el-input__wrapper) {
      border-radius: $border-radius-sm;
    }

    :deep(.el-tag) {
      margin: 2px;
    }
  }
}
</style>
