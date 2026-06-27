<script setup lang="ts">
import { computed } from "vue";
import {
  ElInput,
  ElInputNumber,
  ElSelect,
  ElOption,
  ElDatePicker,
  ElSwitch,
  ElRate,
} from "element-plus";
import type { FieldEntity } from "@/db/schema";
import { FieldType } from "@/types/fields";
import dayjs from "dayjs";

interface Props {
  field: FieldEntity;
  modelValue: unknown;
  placeholder?: string;
  disabled?: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "update:modelValue", value: unknown): void;
}>();

const choices = computed(() => {
  const list = (props.field.options?.choices as Array<{
    id: string;
    name: string;
    color?: string;
  }>) || [];
  return list;
});

const precision = computed(() => {
  return (props.field.options?.precision as number) ?? 0;
});

const maxLength = computed(() => {
  return (props.field.options?.maxLength as number) || undefined;
});

const isDateTime = computed(() => props.field.type === FieldType.DATE_TIME);

const dateFormat = computed(() =>
  isDateTime.value ? "YYYY-MM-DD HH:mm:ss" : "YYYY-MM-DD",
);

function update(value: unknown) {
  emit("update:modelValue", value);
}

function handleDateChange(val: Date | null) {
  if (!val) {
    update(null);
    return;
  }
  if (isDateTime.value) {
    update(dayjs(val).toISOString());
  } else {
    update(dayjs(val).format("YYYY-MM-DD"));
  }
}

function getTextValue() {
  return props.modelValue === null || props.modelValue === undefined
    ? ""
    : String(props.modelValue);
}

function getNumberValue() {
  if (props.modelValue === null || props.modelValue === undefined) {
    return null;
  }
  const num = Number(props.modelValue);
  return Number.isNaN(num) ? null : num;
}

function getSingleSelectValue() {
  return (props.modelValue as string | undefined) || undefined;
}

function getMultiSelectValue() {
  return Array.isArray(props.modelValue) ? (props.modelValue as string[]) : [];
}

function getDateValue() {
  if (!props.modelValue) return null;
  const date = dayjs(props.modelValue as string);
  return date.isValid() ? date.toDate() : null;
}

function getCheckboxValue() {
  return Boolean(props.modelValue);
}

function getRatingValue() {
  return Number(props.modelValue) || 0;
}

function getComponentType() {
  switch (props.field.type) {
    case FieldType.SINGLE_LINE_TEXT:
    case FieldType.EMAIL:
    case FieldType.PHONE:
    case FieldType.URL:
      return "text";
    case FieldType.LONG_TEXT:
      return "textarea";
    case FieldType.NUMBER:
      return "number";
    case FieldType.SINGLE_SELECT:
      return "single_select";
    case FieldType.MULTI_SELECT:
      return "multi_select";
    case FieldType.DATE:
    case FieldType.DATE_TIME:
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_TIME:
      return "date";
    case FieldType.CHECKBOX:
      return "checkbox";
    case FieldType.RATING:
      return "rating";
    default:
      return "text";
  }
}
</script>

<template>
  <div class="field-value-input">
    <!-- 单行文本 / 邮箱 / 电话 / URL -->
    <template v-if="getComponentType() === 'text'">
      <ElInput
        :model-value="getTextValue()"
        :placeholder="placeholder || `请输入${field.name}`"
        :maxlength="maxLength"
        :disabled="disabled"
        class="input-control"
        @update:model-value="update" />
    </template>

    <!-- 多行文本 -->
    <template v-else-if="getComponentType() === 'textarea'">
      <ElInput
        :model-value="getTextValue()"
        type="textarea"
        :rows="2"
        resize="none"
        :placeholder="placeholder || `请输入${field.name}`"
        :maxlength="maxLength"
        :disabled="disabled"
        class="input-control"
        @update:model-value="update" />
    </template>

    <!-- 数字 -->
    <template v-else-if="getComponentType() === 'number'">
      <ElInputNumber
        :model-value="getNumberValue()"
        :precision="precision"
        :placeholder="placeholder || `请输入${field.name}`"
        :disabled="disabled"
        class="input-control"
        style="width: 100%"
        @update:model-value="update" />
    </template>

    <!-- 单选 -->
    <template v-else-if="getComponentType() === 'single_select'">
      <ElSelect
        :model-value="getSingleSelectValue()"
        :placeholder="placeholder || `请选择${field.name}`"
        :disabled="disabled"
        class="input-control"
        clearable
        @update:model-value="update">
        <ElOption
          v-for="option in choices"
          :key="option.id"
          :label="option.name"
          :value="option.id">
          <div class="select-option">
            <span
              class="option-color"
              :style="{ backgroundColor: option.color || '#3370FF' }" />
            <span>{{ option.name }}</span>
          </div>
        </ElOption>
      </ElSelect>
    </template>

    <!-- 多选 -->
    <template v-else-if="getComponentType() === 'multi_select'">
      <ElSelect
        :model-value="getMultiSelectValue()"
        :placeholder="placeholder || `请选择${field.name}`"
        :disabled="disabled"
        class="input-control"
        multiple
        clearable
        @update:model-value="update">
        <ElOption
          v-for="option in choices"
          :key="option.id"
          :label="option.name"
          :value="option.id">
          <div class="select-option">
            <span
              class="option-color"
              :style="{ backgroundColor: option.color || '#3370FF' }" />
            <span>{{ option.name }}</span>
          </div>
        </ElOption>
      </ElSelect>
    </template>

    <!-- 日期 / 日期时间 -->
    <template v-else-if="getComponentType() === 'date'">
      <ElDatePicker
        :model-value="getDateValue()"
        :type="isDateTime ? 'datetime' : 'date'"
        :placeholder="placeholder || `请选择${field.name}`"
        :format="dateFormat"
        :disabled="disabled"
        class="input-control"
        style="width: 100%"
        @update:model-value="handleDateChange" />
    </template>

    <!-- 复选框 -->
    <template v-else-if="getComponentType() === 'checkbox'">
      <ElSwitch
        :model-value="getCheckboxValue()"
        :disabled="disabled"
        class="input-control"
        @update:model-value="update" />
    </template>

    <!-- 评分 -->
    <template v-else-if="getComponentType() === 'rating'">
      <ElRate
        :model-value="getRatingValue()"
        :max="(field.options?.maxRating as number) ?? 5"
        :disabled="disabled"
        class="input-control"
        @update:model-value="update" />
    </template>
  </div>
</template>

<style lang="scss" scoped>
.field-value-input {
  width: 100%;
}

.input-control {
  width: 100%;
}

.select-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.option-color {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 2px;
}
</style>
