<script setup lang="ts">
import { ref, computed } from "vue";
import type { FieldOption } from "@/types/fields";
import MultiSelectDropdown from "@/components/common/MultiSelectDropdown.vue";

interface Props {
  modelValue: string[] | null;
  field?: {
    id: string;
    name: string;
    type: string;
    options?: {
      options?: FieldOption[];
      allowAddOptions?: boolean;
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
  (e: "update:modelValue", value: string[] | null): void;
  (e: "blur"): void;
}>();

const options = computed(() => {
  return props.field?.options?.choices ?? [];
});

const selectedOptions = computed(() => {
  if (!props.modelValue || props.modelValue.length === 0) return [];
  return options.value.filter((opt) => props.modelValue!.includes(opt.id));
});

const localValue = computed({
  get: () => props.modelValue ?? [],
  set: (val: string[]) =>
    emit("update:modelValue", val.length > 0 ? val : null),
});

const dropdownRef = ref<InstanceType<typeof MultiSelectDropdown>>();

const focus = () => {
  dropdownRef.value?.open();
};

const handleConfirm = () => {
  emit("blur");
};

const handleCancel = () => {
  emit("blur");
};

defineExpose({ focus });
</script>

<template>
  <div class="multi-select-field" :class="{ 'is-readonly': readonly }">
    <template v-if="readonly">
      <div class="multi-select-readonly">
        <template v-if="selectedOptions.length > 0">
          <span
            v-for="option in selectedOptions"
            :key="option.id"
            class="select-tag"
            :style="{
              backgroundColor: option.color + '20',
              color: option.color,
              borderColor: option.color + '40',
            }">
            {{ option.name }}
          </span>
        </template>
        <span v-else class="empty-value">-</span>
      </div>
    </template>
    <template v-else>
      <MultiSelectDropdown
        ref="dropdownRef"
        v-model="localValue"
        :options="options"
        :placeholder="placeholder || '请选择'"
        @confirm="handleConfirm"
        @cancel="handleCancel" />
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.multi-select-field {
  width: 100%;

  &.is-readonly {
    .multi-select-readonly {
      padding: $spacing-sm;
      min-height: 32px;
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      align-items: center;
    }

    .empty-value {
      color: $text-disabled;
    }
  }

  .select-tag {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: $font-size-sm;
    font-weight: 500;
    border: 1px solid;
    white-space: nowrap;
  }
}
</style>
