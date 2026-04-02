<script setup lang="ts">
import { ref, computed, watch } from "vue";
import type { FieldEntity } from "@/db/schema";
import type { CellValue } from "@/types";
import { validatePhone } from "@/utils/validation";

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
  const result = validatePhone(localValue.value);
  validationError.value = result.error || "";
  return result.valid;
});

function handleInput(value: string) {
  localValue.value = value;
  // 实时校验
  const result = validatePhone(value);
  validationError.value = result.error || "";
  emit("update:modelValue", value);
}

function formatPhone(value: string): string {
  const cleaned = value.replace(/\D/g, "");
  if (cleaned.length <= 3) return cleaned;
  if (cleaned.length <= 7) return `${cleaned.slice(0, 3)} ${cleaned.slice(3)}`;
  return `${cleaned.slice(0, 3)} ${cleaned.slice(3, 7)} ${cleaned.slice(7, 11)}`;
}

function handleBlur() {
  const cleaned = localValue.value.replace(/\D/g, "");
  // 失焦时进行校验
  const result = validatePhone(cleaned);
  validationError.value = result.error || "";
  if (cleaned) {
    localValue.value = cleaned;
    emit("update:modelValue", cleaned);
  }
}
</script>

<template>
  <div class="phone-field">
    <el-input
      v-if="!readonly"
      :model-value="localValue"
      placeholder="请输入手机号码"
      :class="{ 'is-error': !isValid }"
      @update:model-value="handleInput"
      @blur="handleBlur">
      <template #prefix>
        <el-icon><Phone /></el-icon>
      </template>
    </el-input>
    <div v-else class="phone-display">
      <el-icon><Phone /></el-icon>
      <span v-if="localValue" class="phone-number">
        {{ formatPhone(localValue) }}
      </span>
      <span v-else class="empty-text">-</span>
    </div>
    <div v-if="!isValid && !readonly && validationError" class="error-message">
      {{ validationError }}
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.phone-field {
  width: 100%;
}

.is-error {
  :deep(.el-input__wrapper) {
    border-color: $error-color;
  }
}

.phone-display {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  color: $text-primary;
}

.phone-number {
  font-size: $font-size-sm;
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
