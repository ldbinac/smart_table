<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { formatDate } from "@/utils/timezone";
import DateInput from "./DateInput.vue";
import type { CellValue } from "@/types";
import type { FieldOptions } from "@/types/fields";

const { t } = useI18n();

interface Props {
  modelValue: CellValue;
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
  (e: "update:modelValue", value: CellValue): void;
}>();

const dateFormat = computed<string>(() => props.field?.options?.dateFormat || "YYYY-MM-DD");

const displayValue = computed(() => {
  if (props.modelValue == null || props.modelValue === "") return "-";
  // 默认 YYYY-MM-DD 维持原有（带时区）显示；其余格式字符串本身即展示样式
  if (dateFormat.value === "YYYY-MM-DD") {
    return formatDate(props.modelValue as string);
  }
  return props.modelValue as string;
});

function onInputUpdate(val: CellValue) {
  emit("update:modelValue", val == null ? null : val);
}
</script>

<template>
  <div class="date-field" :class="{ 'is-readonly': readonly }">
    <template v-if="readonly">
      <div class="date-field-readonly">
        {{ displayValue }}
      </div>
    </template>
    <template v-else>
      <DateInput
        :field="field"
        :model-value="modelValue"
        :placeholder="placeholder || t('field.placeholderDate')"
        @update:model-value="onInputUpdate" />
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.date-field {
  width: 100%;

  &.is-readonly {
    .date-field-readonly {
      padding: $spacing-sm;
      color: $text-primary;
      font-size: $font-size-base;
    }
  }
}
</style>
