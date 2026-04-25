<script setup lang="ts">
import { computed, ref } from "vue";
import type { FieldOption } from "@/types/fields";

interface Props {
  modelValue: string | null;
  field?: {
    id: string;
    name: string;
    type: string;
    options?: {
      options?: FieldOption[];
      allowAddOptions?: boolean;
    };
  };
  readonly?: boolean;
  placeholder?: string;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  readonly: false,
  placeholder: "",
});

const emit = defineEmits<{
  (e: "update:modelValue", value: string | null): void;
}>();

const options = computed(() => {
  return props.field?.options?.choices ?? [];
});

const selectedOption = computed(() => {
  if (!props.modelValue) return null;
  return options.value.find((opt) => opt.id === props.modelValue);
});

const localValue = computed({
  get: () => props.modelValue,
  set: (val: string | null) => emit("update:modelValue", val),
});

const selectRef = ref();

const focus = () => {
  selectRef.value?.focus();
};

defineExpose({ focus });
</script>

<template>
  <div class="single-select-field" :class="{ 'is-readonly': readonly }">
    <template v-if="readonly">
      <div class="single-select-readonly">
        <span
          v-if="selectedOption"
          class="select-tag"
          :style="{
            backgroundColor: selectedOption.color + '20',
            color: selectedOption.color,
          }">
          {{ selectedOption.name }}
        </span>
        <span v-else class="empty-value">-</span>
      </div>
    </template>
    <template v-else>
      <el-select
        v-model="localValue"
        :placeholder="placeholder || '请选择'"
        clearable
        ref="selectRef"
        class="select-input">
        <el-option
          v-for="option in options"
          :key="option.id"
          :label="option.name"
          :value="option.id">
          <span
            class="option-tag"
            :style="{
              backgroundColor: option.color + '20',
              color: option.color,
            }">
            {{ option.name }}
          </span>
        </el-option>
      </el-select>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.single-select-field {
  width: 100%;

  &.is-readonly {
    .single-select-readonly {
      padding: $spacing-sm;
      min-height: 32px;
      display: flex;
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
  }
}
</style>
