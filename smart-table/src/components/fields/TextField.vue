<script setup lang="ts">
import type { FieldOptions } from '@/types/fields'

interface Props {
  modelValue: string | null
  field?: {
    id: string
    name: string
    type: string
    options?: FieldOptions
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
  (e: 'update:modelValue', value: string | null): void
}>()

const localValue = computed({
  get: () => props.modelValue ?? '',
  set: (val: string) => emit('update:modelValue', val || null)
})

const isMultiline = computed(() => {
  return props.field?.options?.isRichText || false
})

const maxLength = computed(() => {
  return props.field?.options?.maxLength
})

const inputRef = ref<HTMLTextAreaElement | HTMLInputElement>()

const focus = () => {
  inputRef.value?.focus()
}

defineExpose({ focus })
</script>

<template>
  <div class="text-field" :class="{ 'is-readonly': readonly }">
    <template v-if="readonly">
      <div v-if="isMultiline" class="text-field-readonly text-field-multiline">
        {{ localValue || '-' }}
      </div>
      <div v-else class="text-field-readonly">
        {{ localValue || '-' }}
      </div>
    </template>
    <template v-else>
      <el-input
        v-if="isMultiline"
        v-model="localValue"
        type="textarea"
        :placeholder="placeholder || '请输入文本'"
        :maxlength="maxLength"
        :rows="3"
        resize="none"
        ref="inputRef"
      />
      <el-input
        v-else
        v-model="localValue"
        :placeholder="placeholder || '请输入文本'"
        :maxlength="maxLength"
        ref="inputRef"
        clearable
      />
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.text-field {
  width: 100%;

  &.is-readonly {
    .text-field-readonly {
      padding: $spacing-sm;
      color: $text-primary;
      font-size: $font-size-base;
      line-height: 1.5;
      @include text-ellipsis;
    }

    .text-field-multiline {
      white-space: pre-wrap;
      word-break: break-word;
    }
  }

  :deep(.el-input__wrapper),
  :deep(.el-textarea__inner) {
    border-radius: $border-radius-sm;
  }

  :deep(.el-textarea__inner) {
    font-family: inherit;
  }
}
</style>
