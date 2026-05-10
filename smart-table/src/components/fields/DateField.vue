<script setup lang="ts">
import { computed, ref } from "vue";
import { formatDate } from "@/utils/timezone";
import dayjs from "dayjs";

interface Props {
  modelValue: string | null;
  field?: {
    id: string;
    name: string;
    type: string;
    options?: {
      dateFormat?: string;
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

const displayFormat = "YYYY-MM-DD";

const displayValue = computed(() => {
  if (!props.modelValue) return "-";
  return formatDate(props.modelValue);
});

const localValue = computed({
  get: () => {
    if (!props.modelValue) return null;
    return dayjs(props.modelValue).toDate();
  },
  set: (val: Date | null) => {
    if (!val) {
      emit("update:modelValue", null);
    } else {
      emit("update:modelValue", dayjs(val).format(displayFormat));
    }
  },
});

const pickerRef = ref();

const focus = () => {
  pickerRef.value?.focus();
};

defineExpose({ focus });
</script>

<template>
  <div class="date-field" :class="{ 'is-readonly': readonly }">
    <template v-if="readonly">
      <div class="date-field-readonly">
        {{ displayValue }}
      </div>
    </template>
    <template v-else>
      <el-date-picker
        v-model="localValue"
        type="date"
        :placeholder="placeholder || '请选择日期'"
        :format="displayFormat"
        :value-format="displayFormat"
        clearable
        ref="pickerRef"
        class="date-picker" />
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.date-field {
  width: 100%;

  &.is-readonly {
    .date-field-readonly {
      padding: $spacing-sm;
      color: $text-primary;
      font-size: $font-size-base;
    }
  }

  .date-picker {
    width: 100%;

    :deep(.el-input__wrapper) {
      border-radius: $border-radius-sm;
    }
  }
}
</style>
