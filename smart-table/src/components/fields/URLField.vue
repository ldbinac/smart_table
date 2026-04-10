<script setup lang="ts">
import { ref, computed, watch } from "vue";
import type { FieldEntity } from "@/db/schema";
import type { CellValue } from "@/types";
import { validateUrl } from "@/utils/validation";

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
  const result = validateUrl(localValue.value);
  validationError.value = result.error || "";
  return result.valid;
});

const displayUrl = computed(() => {
  if (!localValue.value) return "";
  try {
    const url = new URL(localValue.value);
    return url.hostname + url.pathname;
  } catch {
    return localValue.value;
  }
});

function handleInput(value: string) {
  localValue.value = value;
  // 实时校验
  const result = validateUrl(value);
  validationError.value = result.error || "";
  emit("update:modelValue", value);
}

function handleBlur() {
  let value = localValue.value.trim();
  // 失焦时进行校验
  const result = validateUrl(value);
  validationError.value = result.error || "";
  if (value && !value.match(/^https?:\/\//i)) {
    value = "https://" + value;
    localValue.value = value;
  }
  emit("update:modelValue", value);
}

function openUrl() {
  if (localValue.value) {
    const url = localValue.value.trim();
    if (!/^https?:\/\//i.test(url)) {
      return;
    }
    window.open(url, "_blank", "noopener,noreferrer");
  }
}
</script>

<template>
  <div class="url-field">
    <el-input
      v-if="!readonly"
      :model-value="localValue"
      placeholder="请输入链接地址"
      :class="{ 'is-error': !isValid }"
      @update:model-value="handleInput"
      @blur="handleBlur">
      <template #prefix>
        <el-icon><Link /></el-icon>
      </template>
    </el-input>
    <div v-else class="url-display">
      <el-icon><Link /></el-icon>
      <a
        v-if="localValue"
        class="url-link"
        :title="localValue"
        @click="openUrl">
        {{ displayUrl }}
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

.url-field {
  width: 100%;
}

.is-error {
  :deep(.el-input__wrapper) {
    border-color: $error-color;
  }
}

.url-display {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
}

.url-link {
  color: $primary-color;
  cursor: pointer;
  font-size: $font-size-sm;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

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
