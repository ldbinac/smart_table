<script setup lang="ts">
import { computed, ref } from "vue";
import type { FieldOptions } from "@/types/fields";

interface Props {
  modelValue: number | null;
  field?: {
    id: string;
    name: string;
    type: string;
    options?: FieldOptions;
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
  (e: "update:modelValue", value: number | null): void;
}>();

// 精度配置，默认0位小数
const precision = computed(() => {
  return props.field?.options?.precision ?? 0;
});

const format = computed(() => {
  return props.field?.options?.format ?? "number";
});

const currencySymbol = computed(() => {
  return props.field?.options?.currencySymbol ?? "¥";
});

const prefix = computed(() => {
  if (format.value === "currency") return currencySymbol.value;
  return props.field?.options?.prefix ?? "";
});

const suffix = computed(() => {
  if (format.value === "percent") return "%";
  return props.field?.options?.suffix ?? "";
});

const displayValue = computed(() => {
  if (props.modelValue === null || props.modelValue === undefined) return "-";

  let value = props.modelValue;

  if (format.value === "percent") {
    value = props.modelValue * 100;
  }

  return formatNumber(value, precision.value);
});

const formatNumber = (num: number, prec: number): string => {
  return num.toLocaleString("zh-CN", {
    minimumFractionDigits: prec,
    maximumFractionDigits: prec,
  });
};

const localValue = computed({
  get: () => props.modelValue,
  set: (val: number | null) => {
    if (val === null || val === undefined || isNaN(val)) {
      emit("update:modelValue", null);
    } else {
      let finalValue = val;
      if (format.value === "percent") {
        finalValue = val / 100;
      }
      // 根据精度存储原始值
      const multiplier = Math.pow(10, precision.value);
      emit(
        "update:modelValue",
        Math.round(finalValue * multiplier) / multiplier,
      );
    }
  },
});

const inputRef = ref();

const focus = () => {
  inputRef.value?.focus();
};

defineExpose({ focus });
</script>

<template>
  <div class="number-field" :class="{ 'is-readonly': readonly }">
    <template v-if="readonly">
      <div class="number-field-readonly">
        <span v-if="prefix" class="number-prefix">{{ prefix }}</span>
        <span class="number-value">{{ displayValue }}</span>
        <span v-if="suffix" class="number-suffix">{{ suffix }}</span>
      </div>
    </template>
    <template v-else>
      <el-input-number
        v-model="localValue"
        :placeholder="placeholder || '请输入数字'"
        :precision="precision"
        :controls="false"
        class="number-input"
        ref="inputRef" />
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.number-field {
  width: 100%;

  &.is-readonly {
    .number-field-readonly {
      padding: $spacing-sm;
      color: $text-primary;
      font-size: $font-size-base;
      font-family: "SF Mono", "Monaco", "Inconsolata", monospace;
    }

    .number-prefix,
    .number-suffix {
      color: $text-secondary;
      margin: 0 2px;
    }
  }

  .number-input {
    width: 100%;

    :deep(.el-input__wrapper) {
      border-radius: $border-radius-sm;
      padding-left: 8px;
      padding-right: 8px;
    }
  }
}
</style>
