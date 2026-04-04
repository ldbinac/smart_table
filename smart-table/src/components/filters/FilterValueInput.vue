<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { FieldEntity } from "../../db/schema";
import type { FilterOperatorValue, FieldTypeValue } from "../../types";
import { FieldType, FilterOperator } from "../../types";

interface Props {
  field: FieldEntity;
  operator: FilterOperatorValue;
  modelValue: unknown;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "update:modelValue", value: unknown): void;
}>();

const localValue = ref<string | number | boolean | string[] | undefined>(
  undefined,
);

watch(
  () => props.modelValue,
  (newVal) => {
    if (
      typeof newVal === "string" ||
      typeof newVal === "number" ||
      typeof newVal === "boolean" ||
      Array.isArray(newVal)
    ) {
      localValue.value = newVal as string | number | boolean | string[];
    } else {
      localValue.value = newVal ? String(newVal) : undefined;
    }
  },
  { immediate: true },
);

watch(localValue, (newVal) => {
  emit("update:modelValue", newVal);
});

const noValueOperators: FilterOperatorValue[] = [
  FilterOperator.IS_EMPTY,
  FilterOperator.IS_NOT_EMPTY,
];

const showInput = computed(() => {
  return !noValueOperators.includes(props.operator);
});

const multiSelectOperators: FilterOperatorValue[] = [
  FilterOperator.IS_ANY_OF,
  FilterOperator.IS_NONE_OF,
];

const multiSelectFieldTypes: FieldTypeValue[] = [
  FieldType.SINGLE_SELECT,
  FieldType.MULTI_SELECT,
  FieldType.MEMBER,
];

const showMultiSelect = computed(() => {
  return (
    multiSelectOperators.includes(props.operator) &&
    multiSelectFieldTypes.includes(props.field.type as FieldTypeValue)
  );
});

const showDateRange = computed(() => {
  return props.operator === FilterOperator.IS_WITHIN;
});

const selectOptions = computed(() => {
  const options = props.field.options?.choices as
    | Array<{ id: string; name: string; color?: string }>
    | undefined;
  return options || [];
});

const dateRangeOptions = [
  { value: "today", label: "今天" },
  { value: "yesterday", label: "昨天" },
  { value: "tomorrow", label: "明天" },
  { value: "thisWeek", label: "本周" },
  { value: "lastWeek", label: "上周" },
  { value: "nextWeek", label: "下周" },
  { value: "thisMonth", label: "本月" },
  { value: "lastMonth", label: "上月" },
  { value: "nextMonth", label: "下月" },
  { value: "thisYear", label: "今年" },
  { value: "custom", label: "自定义范围" },
];

const showCustomDateRange = ref(false);

watch(
  () => props.operator,
  (newOp) => {
    if (newOp === FilterOperator.IS_WITHIN) {
      if (!localValue.value) {
        localValue.value = "today";
      }
    }
  },
);

const selectedOptions = computed({
  get: () => {
    if (!localValue.value) return [];
    if (Array.isArray(localValue.value)) {
      return localValue.value;
    }
    return [String(localValue.value)];
  },
  set: (ids: string[]) => {
    localValue.value = ids;
  },
});

const customDateRange = ref<[Date, Date] | null>(null);

function handleDateRangeChange(value: string) {
  if (value === "custom") {
    showCustomDateRange.value = true;
    if (customDateRange.value) {
      localValue.value = [
        customDateRange.value[0].getTime(),
        customDateRange.value[1].getTime(),
      ].join(",");
    }
  } else {
    showCustomDateRange.value = false;
    localValue.value = value;
  }
}

function handleCustomDateRangeChange(dates: [Date, Date] | null) {
  if (dates) {
    customDateRange.value = dates;
    localValue.value = [dates[0].getTime(), dates[1].getTime()].join(",");
  }
}

const singleSelectValue = computed({
  get: () => String(localValue.value || ""),
  set: (val: string) => {
    localValue.value = val;
  },
});

const numberValue = computed({
  get: () =>
    typeof localValue.value === "number" ? localValue.value : undefined,
  set: (val: number | undefined) => {
    localValue.value = val;
  },
});

const textValue = computed({
  get: () => String(localValue.value || ""),
  set: (val: string) => {
    localValue.value = val;
  },
});

const dateValue = computed({
  get: () =>
    typeof localValue.value === "number" ? localValue.value : undefined,
  set: (val: number | undefined) => {
    localValue.value = val;
  },
});

const dateRangeSelectValue = computed(() => {
  if (typeof localValue.value === "string" && !localValue.value.includes(",")) {
    return localValue.value;
  }
  return "custom";
});

const switchValue = computed({
  get: () => Boolean(localValue.value),
  set: (val: boolean) => {
    localValue.value = val;
  },
});
</script>

<template>
  <div class="filter-value-input">
    <template v-if="showInput">
      <template v-if="field.type === FieldType.CHECKBOX">
        <el-switch v-model="switchValue" />
      </template>

      <template v-else-if="showMultiSelect">
        <el-select
          v-model="selectedOptions"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="选择选项"
          class="full-width">
          <el-option
            v-for="option in selectOptions"
            :key="option.id"
            :label="option.name"
            :value="option.id">
            <span
              v-if="option.color"
              class="option-color"
              :style="{ backgroundColor: option.color }" />
            {{ option.name }}
          </el-option>
        </el-select>
      </template>

      <template v-else-if="field.type === FieldType.SINGLE_SELECT">
        <el-select
          v-model="singleSelectValue"
          placeholder="选择选项"
          class="full-width">
          <el-option
            v-for="option in selectOptions"
            :key="option.id"
            :label="option.name"
            :value="option.id">
            <span
              v-if="option.color"
              class="option-color"
              :style="{ backgroundColor: option.color }" />
            {{ option.name }}
          </el-option>
        </el-select>
      </template>

      <template v-else-if="showDateRange">
        <el-select
          :model-value="dateRangeSelectValue"
          placeholder="选择日期范围"
          class="full-width"
          @change="handleDateRangeChange">
          <el-option
            v-for="option in dateRangeOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value" />
        </el-select>
        <el-date-picker
          v-if="showCustomDateRange"
          v-model="customDateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          class="full-width mt-sm"
          @change="handleCustomDateRangeChange" />
      </template>

      <template
        v-else-if="
          field.type === FieldType.DATE ||
          field.type === FieldType.CREATED_TIME ||
          field.type === FieldType.UPDATED_TIME
        ">
        <el-date-picker
          v-model="dateValue"
          type="date"
          placeholder="选择日期"
          class="full-width"
          value-format="x" />
      </template>

      <template
        v-else-if="
          field.type === FieldType.NUMBER ||
          field.type === FieldType.RATING ||
          field.type === FieldType.PROGRESS ||
          field.type === FieldType.AUTO_NUMBER
        ">
        <el-input-number
          v-model="numberValue"
          :controls="false"
          placeholder="输入数值"
          class="full-width" />
      </template>

      <template v-else>
        <el-input v-model="textValue" placeholder="输入值" clearable />
      </template>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.filter-value-input {
  min-width: 180px;
}

.full-width {
  width: 100%;
}

.mt-sm {
  margin-top: $spacing-sm;
}

.option-color {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 2px;
  margin-right: $spacing-sm;
}
</style>
