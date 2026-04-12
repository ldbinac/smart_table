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

const currentValue = ref(0);

const progressColor = computed(() => {
  const value = currentValue.value;
  if (value < 30) return "#EF4444";
  if (value < 60) return "#FBBF24";
  if (value < 90) return "#3370FF";
  return "#34D399";
});

watch(
  () => props.modelValue,
  (newVal) => {
    currentValue.value = Number(newVal) || 0;
  },
  { immediate: true },
);

function handleChange(value: number) {
  if (props.readonly) return;
  currentValue.value = value;
  emit("update:modelValue", value);
}
</script>

<template>
  <div class="progress-field">
    <div class="progress-wrapper">
      <template v-if="!readonly">
        <el-slider
          :model-value="currentValue"
          :max="100"
          :format-tooltip="(val: number) => `${val}%`"
          @update:model-value="handleChange" />
        <span class="progress-value">{{ currentValue }}%</span>
      </template>
      <template v-else>
        <el-progress
          :percentage="currentValue"
          :stroke-width="10"
          :color="progressColor"
          :show-text="false" />
        <span class="progress-value readonly">{{ currentValue }}%</span>
      </template>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.progress-field {
  width: 100%;
}

.progress-wrapper {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .el-slider {
    flex: 1;
  }
}

.progress-value {
  font-size: $font-size-sm;
  color: $text-secondary;
  min-width: 40px;
  text-align: right;

  &.readonly {
    margin-left: $spacing-sm;
  }
}
</style>
