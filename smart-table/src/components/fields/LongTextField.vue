<script setup lang="ts">
import { computed, ref } from "vue";

interface Props {
  modelValue: string | null;
  field?: {
    id: string;
    name: string;
    type: string;
    options?: {
      maxLength?: number;
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

const localValue = computed({
  get: () => props.modelValue ?? "",
  set: (val: string) => emit("update:modelValue", val || null),
});

const maxLength = computed(() => {
  return props.field?.options?.maxLength;
});

const textareaRef = ref<HTMLTextAreaElement>();

const focus = () => {
  textareaRef.value?.focus();
};

defineExpose({ focus });
</script>

<template>
  <div class="long-text-field" :class="{ 'is-readonly': readonly }">
    <!-- 只读模式 -->
    <template v-if="readonly">
      <div class="text-field-readonly text-field-multiline">
        {{ localValue || "-" }}
      </div>
    </template>

    <!-- 编辑模式 -->
    <template v-else>
      <el-input
        v-model="localValue"
        type="textarea"
        :placeholder="placeholder || '请输入文本'"
        :maxlength="maxLength"
        :rows="3"
        resize="none"
        ref="textareaRef"
      />
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.long-text-field {
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
  }

  :deep(.el-textarea__inner) {
    border-radius: $border-radius-sm;
    font-family: inherit;
  }
}
</style>
