<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import {
  ElInput,
  ElInputNumber,
  ElSelect,
  ElOption,
  ElSwitch,
  ElRate,
  ElSlider,
} from "element-plus";
import type { FieldEntity } from "@/db/schema";
import { FieldType } from "@/types/fields";
import DateInput from "@/components/fields/DateInput.vue";
import type { CellValue } from "@/types";

const { t } = useI18n();

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

function update(value: unknown) {
  emit("update:modelValue", value);
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
  if (Array.isArray(props.modelValue)) {
    return props.modelValue as string[];
  }
  if (typeof props.modelValue === "string" && props.modelValue) {
    return props.modelValue.split(",");
  }
  return [];
}

function getCheckboxValue() {
  return props.modelValue === true || props.modelValue === "true";
}

function getRatingValue() {
  return Number(props.modelValue) || 0;
}

function getProgressValue() {
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
    case FieldType.PROGRESS:
      return "progress";
    default:
      return "text";
  }
}

function isViewMode(_field: FieldEntity): boolean {
  return false
}
</script>

<template>
  <div class="field-value-input">
    <!-- 单行文本 / 邮箱 / 电话 / URL -->
    <template v-if="getComponentType() === 'text'">
      <ElInput
        :model-value="getTextValue()"
        :placeholder="placeholder || t('field.inputFieldName', { name: field.name })"
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
        :placeholder="placeholder || t('field.inputFieldName', { name: field.name })"
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
        :placeholder="placeholder || t('field.inputFieldName', { name: field.name })"
        :disabled="disabled"
        class="input-control"
        style="width: 100%"
        @update:model-value="update" />
    </template>

    <!-- 单选 -->
    <template v-else-if="getComponentType() === 'single_select'">
      <div class="select-wrap">
        <ElSelect
          :model-value="getSingleSelectValue()"
          :placeholder="placeholder || t('field.selectFieldName', { name: field.name })"
          :disabled="disabled"
          class="input-control"
          style="width: 100%"
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
      </div>
    </template>

    <!-- 多选 -->
    <template v-else-if="getComponentType() === 'multi_select'">
      <div class="select-wrap">
        <ElSelect
          :model-value="getMultiSelectValue()"
          :placeholder="placeholder || t('field.selectFieldName', { name: field.name })"
          :disabled="disabled"
          class="input-control"
          style="width: 100%"
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
      </div>
    </template>

    <!-- 日期 / 日期时间 -->
    <template v-else-if="getComponentType() === 'date'">
      <DateInput
        :field="field"
        :model-value="props.modelValue as CellValue"
        :placeholder="placeholder || t('field.selectFieldName', { name: field.name })"
        :disabled="disabled || isViewMode(field)"
        class="input-control"
        style="width: 100%"
        @update:model-value="update" />
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

    <!-- 进度 -->
    <template v-else-if="getComponentType() === 'progress'">
      <ElSlider
        :model-value="getProgressValue()"
        :min="(field.options?.min as number) ?? 0"
        :max="(field.options?.max as number) ?? 100"
        :disabled="disabled"
        class="input-control"
        @update:model-value="update" />
    </template>
  </div>
</template>

<style lang="scss" scoped>
.field-value-input {
  width: 100%;

  // Element Plus 2.x 的 .el-select 是 display:inline-block，
  // 其内部 .el-select__wrapper（flex 容器）作为 inline-block 的子元素
  // 不会自动撑满父级，会塌缩成内容宽度。
  // 强制 display:block + width:100% 让 wrapper 正常撑满，单选/多选等
  // 动态切换字段类型时保持稳定布局，避免出现极窄样式。
  :deep(.el-select) {
    display: block !important;
    width: 100% !important;
  }
  :deep(.el-select__wrapper) {
    display: flex !important;
    width: 100% !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
  }

  :deep(.el-input),
  :deep(.el-input-number),
  :deep(.el-date-editor) {
    width: 100%;
  }
}

// 单选/多选 ElSelect 的包裹层：保证 ElSelect 作为普通块级子元素渲染，
// 避免上层 flex 上下文 blockify 导致内部 .el-select__wrapper 塌缩为内容宽度
.select-wrap {
  display: block;
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
