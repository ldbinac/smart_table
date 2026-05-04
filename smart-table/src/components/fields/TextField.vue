<script setup lang="ts">
import { computed } from "vue";
import type { FieldOptions } from "@/types/fields";

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

const maxLength = computed(() => {
  return props.field?.options?.maxLength;
});

const handleInput = (event: Event) => {
  const target = event.target as HTMLInputElement;
  emit("update:modelValue", target.value || null);
};

const displayValue = computed(() => {
  if (props.modelValue === null || props.modelValue === undefined) return "";
  return String(props.modelValue);
});
</script>

<template>
  <div class="text-field">
    <input
      type="text"
      :value="displayValue"
      :placeholder="placeholder || '请输入' + (field?.name || '文本')"
      :maxlength="maxLength"
      :readonly="readonly"
      @input="handleInput"
      class="text-input"
    />
  </div>
</template>

<style scoped>
.text-field {
  width: 100%;
}

.text-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
  line-height: 1.5;
  color: #606266;
  background-color: #fff;
  transition: border-color 0.2s;
  box-sizing: border-box;
  outline: none;
}

.text-input:hover {
  border-color: #c0c4cc;
}

.text-input:focus {
  border-color: #409eff;
}

.text-input:readonly {
  background-color: #f5f7fa;
  color: #c0c4cc;
  cursor: not-allowed;
}

.text-input::placeholder {
  color: #c0c4cc;
}
</style>
