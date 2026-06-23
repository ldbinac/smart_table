<script setup lang="ts">
import { computed, ref } from "vue";
import { FieldType, type FieldOptions, type CellValue } from "@/types/fields";
import { useMemberStore } from "@/stores/memberStore";
import SingleLineTextField from "./SingleLineTextField.vue";
import LongTextField from "./LongTextField.vue";
import RichTextField from "./RichTextField.vue";
import NumberField from "./NumberField.vue";
import DateField from "./DateField.vue";
import DateTimeField from "./DateTimeField.vue";
import SingleSelectField from "./SingleSelectField.vue";
import MultiSelectField from "./MultiSelectField.vue";
import CheckboxField from "./CheckboxField.vue";
import AttachmentField from "./AttachmentField.vue";
import MemberField from "./MemberField.vue";
import RatingField from "./RatingField.vue";
import ProgressField from "./ProgressField.vue";
import PhoneField from "./PhoneField.vue";
import EmailField from "./EmailField.vue";
import URLField from "./URLField.vue";
import LinkField from "./LinkField.vue";
import LookupField from "./LookupField.vue";
import CreatedByField from "./CreatedByField.vue";
import CreatedTimeField from "./CreatedTimeField.vue";
import UpdatedByField from "./UpdatedByField.vue";
import UpdatedTimeField from "./UpdatedTimeField.vue";
import AutoNumberField from "./AutoNumberField.vue";
import FormulaField from "./FormulaField.vue";
import type { FieldEntity, RecordEntity } from "@/db/schema";

interface Field {
  id: string;
  name: string;
  type: string;
  options?: FieldOptions;
}

interface Props {
  modelValue: CellValue;
  field?: Field | null;
  readonly?: boolean;
  placeholder?: string;
  // 公式字段需要的上下文
  record?: RecordEntity;
  allFields?: FieldEntity[];
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
  placeholder: "",
  field: undefined,
});

const emit = defineEmits<{
  (e: "update:modelValue", value: CellValue): void;
}>();

// 权限相关
const memberStore = useMemberStore();

/** 当前字段的权限级别 */
const fieldPermission = computed(() => {
  return memberStore.getFieldPermission(props.field?.id || "");
});

/** 是否无读权限（需要显示占位） */
const isNoPermission = computed(() => fieldPermission.value === "none");

/** 最终的只读状态：props.readonly 或权限为 read 时强制禁用 */
const effectiveReadonly = computed(() => {
  return props.readonly || fieldPermission.value === "read";
});

const componentMap: Record<string, unknown> = {
  [FieldType.SINGLE_LINE_TEXT]: SingleLineTextField,
  [FieldType.LONG_TEXT]: LongTextField,
  [FieldType.RICH_TEXT]: RichTextField,
  [FieldType.NUMBER]: NumberField,
  [FieldType.DATE]: DateField,
  [FieldType.DATE_TIME]: DateTimeField,
  [FieldType.SINGLE_SELECT]: SingleSelectField,
  [FieldType.MULTI_SELECT]: MultiSelectField,
  [FieldType.CHECKBOX]: CheckboxField,
  [FieldType.ATTACHMENT]: AttachmentField,
  [FieldType.MEMBER]: MemberField,
  [FieldType.RATING]: RatingField,
  [FieldType.PROGRESS]: ProgressField,
  [FieldType.PHONE]: PhoneField,
  [FieldType.EMAIL]: EmailField,
  [FieldType.URL]: URLField,
  [FieldType.LINK]: LinkField,
  [FieldType.LOOKUP]: LookupField,
  [FieldType.CREATED_BY]: CreatedByField,
  [FieldType.CREATED_TIME]: CreatedTimeField,
  [FieldType.UPDATED_BY]: UpdatedByField,
  [FieldType.UPDATED_TIME]: UpdatedTimeField,
  [FieldType.AUTO_NUMBER]: AutoNumberField,
  [FieldType.FORMULA]: FormulaField,
};

const currentComponent = computed(() => {
  if (!props.field || !props.field.type) {
    return SingleLineTextField;
  }
  return componentMap[props.field.type] || SingleLineTextField;
});

const isSupported = computed(() => {
  if (!props.field || !props.field.type) {
    return false;
  }
  return props.field.type in componentMap;
});

const localValue = computed({
  get: () => props.modelValue,
  set: (val: CellValue) => emit("update:modelValue", val),
});

const fieldRef = ref();

const focus = () => {
  fieldRef.value?.focus?.();
};

defineExpose({ focus });
</script>

<template>
  <div class="field-component-factory">
    <!-- 无读权限：返回占位组件 -->
    <div v-if="isNoPermission" class="field-placeholder">
      <span class="placeholder-text">***</span>
    </div>

    <!-- 有读权限：正常渲染，但 read 权限时禁用编辑 -->
    <template v-else-if="field && field.type && isSupported">
      <component
        :is="currentComponent"
        v-model="localValue"
        :field="field"
        :readonly="effectiveReadonly"
        :placeholder="placeholder"
        :record="record"
        :all-fields="allFields"
        ref="fieldRef" />
    </template>

    <template v-else>
      <div class="unsupported-field">
        <span class="unsupported-text">{{ field?.type ? '不支持的字段类型：' + field.type : '字段信息不完整' }}</span>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.field-component-factory {
  width: 100%;
}

// 无读权限时的占位样式
.field-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 32px;
  background: #f5f7fa;
  color: #c0c4cc;
  font-size: 12px;

  .placeholder-text {
    letter-spacing: 2px;
  }
}

.unsupported-field {
  padding: $spacing-sm;
  background-color: rgba($error-color, 0.1);
  border-radius: $border-radius-sm;
}

.unsupported-text {
  color: $error-color;
  font-size: $font-size-sm;
}
</style>
