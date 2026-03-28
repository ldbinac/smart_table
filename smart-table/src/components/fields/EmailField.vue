<script setup lang="ts">
import { ref, computed, watch } from "vue";
import type { FieldEntity } from "@/db/schema";
import type { CellValue } from "@/types";

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

watch(
  () => props.modelValue,
  (newVal) => {
    localValue.value = String(newVal || "");
  },
  { immediate: true },
);

const isValid = computed(() => {
  if (!localValue.value) return true;
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(localValue.value);
});

function handleInput(value: string) {
  localValue.value = value;
  emit("update:modelValue", value);
}

function handleBlur() {
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
    <div v-if="!isValid && !readonly" class="error-message">
      请输入正确的邮箱地址
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
