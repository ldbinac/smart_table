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
  try {
    new URL(localValue.value);
    return true;
  } catch {
    return false;
  }
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
  emit("update:modelValue", value);
}

function handleBlur() {
  let value = localValue.value.trim();
  if (value && !value.match(/^https?:\/\//i)) {
    value = "https://" + value;
    localValue.value = value;
  }
  emit("update:modelValue", value);
}

function openUrl() {
  if (localValue.value) {
    window.open(localValue.value, "_blank", "noopener,noreferrer");
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
    <div v-if="!isValid && !readonly" class="error-message">
      请输入正确的链接地址
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
