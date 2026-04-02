<script setup lang="ts">
import { ref, computed, watch } from "vue";
import type { FieldEntity } from "@/db/schema";
import type { CellValue } from "@/types";
import { validateEmail } from "@/utils/validation";

interface Props {
  modelValue: CellValue;
  field: FieldEntity;
  readonly?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
});

const emit = defineEmits<{
  (e: "update:modelValue", value: CellValue): void;
}>();

const localValue = ref("");
const validationError = ref("");

watch(
  () => props.modelValue,
  (newVal) => {
    localValue.value = String(newVal || "");
    // 清空校验错误
    validationError.value = "";
  },
  { immediate: true },
);

const isValid = computed(() => {
  if (!localValue.value) return true;
  const result = validateEmail(localValue.value);
  validationError.value = result.error || "";
  return result.valid;
});

function handleInput(value: string) {
  localValue.value = value;
  // 实时校验
  const result = validateEmail(value);
  validationError.value = result.error || "";
  emit("update:modelValue", value);
}

function handleBlur() {
  // 失焦时进行校验
  const result = validateEmail(localValue.value);
  validationError.value = result.error || "";
  emit("update:modelValue", localValue.value);
}
</script>

<template>
  <div class="email-field">
    <el-input
      v-if="!readonly"
      :model-value="localValue"
      placeholder="请输入邮箱地址"
      :class="{ 'is-error': !isValid }"
      @update:model-value="handleInput"
      @blur="handleBlur">
      <template #prefix>
        <el-icon><Message /></el-icon>
      </template>
    </el-input>
    <div v-else class="email-display">
      <el-icon><Message /></el-icon>
      <a v-if="localValue" :href="`mailto:${localValue}`" class="email-link">
        {{ localValue }}
      </a>
      <span v-else class="empty-text">-</span>
    </div>
    <div v-if="!isValid && !readonly && validationError" class="error-message">
      {{ validationError }}
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.email-field {
  width: 100%;
}

.is-error {
  :deep(.el-input__wrapper) {
    border-color: $error-color;
  }
}

.email-display {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
}

.email-link {
  color: $primary-color;
  text-decoration: none;
  font-size: $font-size-sm;

  &:hover {
    text-decoration: underline;
  }
}

.empty-text {
  color: $text-disabled;
}

.error-message {
  font-size: $font-size-xs;
  color: $error-color;
  margin-top: 2px;
}
</style>
