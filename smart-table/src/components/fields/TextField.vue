<script setup lang="ts">
import { TextFieldType, getTextFieldType, type FieldOptions } from "@/types/fields";
import RichTextField from "./RichTextField.vue";
import { sanitizeHtml } from "@/utils/helpers";

interface Props {
  modelValue: string | null;
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
  (e: "update:modelValue", value: string | null): void;
}>();

const localValue = computed({
  get: () => props.modelValue ?? "",
  set: (val: string) => emit("update:modelValue", val || null),
});

// 净化后的HTML（用于只读模式安全渲染）
const sanitizedHtml = computed(() => {
  if (!localValue.value) return '';
  return sanitizeHtml(localValue.value);
});

// 获取文本字段类型（向后兼容）
const textFieldType = computed(() => {
  return getTextFieldType(props.field?.options);
});

// 是否为单行文本
const isSingleLine = computed(() => {
  return textFieldType.value === TextFieldType.SINGLE_LINE_TEXT;
});

// 是否为多行文本
const isLongText = computed(() => {
  return textFieldType.value === TextFieldType.LONG_TEXT;
});

// 是否为富文本
const isRichText = computed(() => {
  return textFieldType.value === TextFieldType.RICH_TEXT;
});

const maxLength = computed(() => {
  return props.field?.options?.maxLength;
});

const inputRef = ref<HTMLTextAreaElement | HTMLInputElement>();
const richTextRef = ref<InstanceType<typeof RichTextField>>();

const focus = () => {
  if (isRichText.value) {
    richTextRef.value?.focus();
  } else {
    inputRef.value?.focus();
  }
};

defineExpose({ focus });
</script>

<template>
  <div class="text-field" :class="{ 'is-readonly': readonly }">
    <!-- 只读模式 -->
    <template v-if="readonly">
      <!-- 富文本只读显示 -->
      <div v-if="isRichText" class="text-field-readonly rich-text-readonly">
        <div v-if="localValue" v-html="sanitizedHtml"></div>
        <span v-else class="placeholder">-</span>
      </div>
      <!-- 多行文本只读显示 -->
      <div v-else-if="isLongText" class="text-field-readonly text-field-multiline">
        {{ localValue || "-" }}
      </div>
      <!-- 单行文本只读显示 -->
      <div v-else class="text-field-readonly">
        {{ localValue || "-" }}
      </div>
    </template>
    
    <!-- 编辑模式 -->
    <template v-else>
      <!-- 单行文本 -->
      <el-input
        v-if="isSingleLine"
        v-model="localValue"
        :placeholder="placeholder || '请输入文本'"
        :maxlength="maxLength"
        ref="inputRef"
        clearable />
      <!-- 多行文本 -->
      <el-input
        v-else-if="isLongText"
        v-model="localValue"
        type="textarea"
        :placeholder="placeholder || '请输入文本'"
        :maxlength="maxLength"
        :rows="3"
        resize="none"
        ref="inputRef" />
      <!-- 富文本 -->
      <RichTextField
        v-else-if="isRichText"
        ref="richTextRef"
        v-model="localValue"
        :placeholder="placeholder || '请输入文本'"
        :max-length="maxLength" />
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

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
      @include text-ellipsis;
    }

    .rich-text-readonly {
      white-space: normal;
      word-break: break-word;
      
      :deep(ul), :deep(ol) {
        margin: $spacing-sm 0;
        padding-left: $spacing-lg;
      }
      
      :deep(li) {
        margin: $spacing-xs 0;
      }
      
      .placeholder {
        color: $text-secondary;
      }
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
