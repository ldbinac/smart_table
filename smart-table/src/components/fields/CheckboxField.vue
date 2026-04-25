<script setup lang="ts">
import { computed, ref } from 'vue'
import { Select, Close } from '@element-plus/icons-vue'

interface Props {
  modelValue: boolean | null
  field?: {
    id: string
    name: string
    type: string
    options?: Record<string, unknown>
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
  (e: 'update:modelValue', value: boolean | null): void
}>()

const localValue = computed({
  get: () => props.modelValue ?? false,
  set: (val: boolean) => emit('update:modelValue', val)
})

const checkboxRef = ref()

const focus = () => {
  checkboxRef.value?.$el?.focus()
}

defineExpose({ focus })
</script>

<template>
  <div class="checkbox-field" :class="{ 'is-readonly': readonly }">
    <template v-if="readonly">
      <div class="checkbox-readonly">
        <el-icon v-if="modelValue === true" class="checkbox-icon checked">
          <Select />
        </el-icon>
        <el-icon v-else-if="modelValue === false" class="checkbox-icon unchecked">
          <Close />
        </el-icon>
        <span v-else class="empty-value">-</span>
      </div>
    </template>
    <template v-else>
      <el-checkbox
        v-model="localValue"
        ref="checkboxRef"
        class="checkbox-input"
      />
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.checkbox-field {
  display: flex;
  align-items: center;
  width: 100%;

  &.is-readonly {
    .checkbox-readonly {
      padding: $spacing-sm;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .checkbox-icon {
      font-size: 18px;

      &.checked {
        color: $success-color;
      }

      &.unchecked {
        color: $text-disabled;
      }
    }

    .empty-value {
      color: $text-disabled;
    }
  }

  .checkbox-input {
    margin-left: $spacing-sm;
  }
}
</style>
