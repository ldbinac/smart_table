<script setup lang="ts">
import { computed, ref } from "vue";
import type { FieldOptions } from "@/types/fields";
import { FormulaEngine } from "@/utils/formula/engine";
import type { FieldEntity, RecordEntity } from "@/db/schema";

interface Props {
  modelValue: string | number | null;
  field?: {
    id: string;
    name: string;
    type: string;
    options?: FieldOptions;
  };
  readonly?: boolean;
  placeholder?: string;
  // 用于公式计算所需的上下文
  record?: RecordEntity;
  allFields?: FieldEntity[];
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  readonly: false,
  placeholder: "",
});

const emit = defineEmits<{
  (e: "update:modelValue", value: string | number | null): void;
}>();

// 计算结果
const calculatedValue = computed(() => {
  if (!props.record || !props.allFields || !props.field?.options?.formula) {
    return props.modelValue;
  }

  try {
    const engine = new FormulaEngine(props.allFields);
    const result = engine.calculate(
      props.record,
      props.field.options.formula as string,
    );

    // 处理错误结果
    if (result && typeof result === "object" && "code" in result) {
      return "#ERROR";
    }

    return result as string | number | null;
  } catch (error) {
    console.error("Formula calculation error:", error);
    return "#ERROR";
  }
});

// 显示值格式化
const displayValue = computed(() => {
  const value = calculatedValue.value;

  if (value === null || value === undefined) {
    return props.readonly ? "-" : "";
  }

  if (value === "#ERROR") {
    return "计算错误";
  }

  // 数字格式化
  if (typeof value === "number") {
    const precision = props.field?.options?.precision ?? 2;
    return value.toLocaleString("zh-CN", {
      minimumFractionDigits: precision,
      maximumFractionDigits: precision,
    });
  }

  return String(value);
});

// 公式显示文本
const formulaDisplay = computed(() => {
  return props.field?.options?.formula || "";
});

// 是否为错误状态
const isError = computed(() => {
  return calculatedValue.value === "#ERROR";
});

const inputRef = ref();

const focus = () => {
  inputRef.value?.focus?.();
};

defineExpose({ focus });
</script>

<template>
  <div
    class="formula-field"
    :class="{ 'is-readonly': readonly, 'is-error': isError }">
    <template v-if="readonly">
      <div class="formula-field-readonly" :title="formulaDisplay">
        {{ displayValue }}
      </div>
    </template>
    <template v-else>
      <div class="formula-field-input-wrapper">
        <el-input
          ref="inputRef"
          :model-value="displayValue"
          :placeholder="placeholder || '自动计算'"
          readonly
          class="formula-input">
          <template #prefix>
            <el-icon class="formula-icon"><Calculator /></el-icon>
          </template>
        </el-input>
        <div v-if="formulaDisplay" class="formula-hint" :title="formulaDisplay">
          公式: {{ formulaDisplay }}
        </div>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.formula-field {
  width: 100%;

  &.is-readonly {
    .formula-field-readonly {
      padding: $spacing-sm;
      color: $text-primary;
      font-size: $font-size-base;
      font-family: "SF Mono", "Monaco", "Inconsolata", monospace;
      @include text-ellipsis;
    }
  }

  &.is-error {
    .formula-field-readonly {
      color: $error-color;
    }

    :deep(.el-input__wrapper) {
      box-shadow: 0 0 0 1px $error-color inset;
    }
  }

  .formula-field-input-wrapper {
    position: relative;
  }

  .formula-input {
    width: 100%;

    :deep(.el-input__wrapper) {
      border-radius: $border-radius-sm;
      background-color: $gray-100;

      &.is-focus {
        box-shadow: 0 0 0 1px $primary-color inset;
      }
    }

    :deep(.el-input__inner) {
      cursor: default;
      font-family: "SF Mono", "Monaco", "Inconsolata", monospace;
    }
  }

  .formula-icon {
    color: $primary-color;
    font-size: 14px;
  }

  .formula-hint {
    margin-top: 4px;
    font-size: $font-size-sm;
    color: $text-secondary;
    @include text-ellipsis;

    &::before {
      content: "🔣";
      margin-right: 4px;
    }
  }
}
</style>
