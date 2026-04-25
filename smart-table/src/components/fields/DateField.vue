<script setup lang="ts">
import { computed, ref } from "vue";
import dayjs from "dayjs";

interface Props {
  modelValue: string | null;
  field?: {
    id: string;
    name: string;
    type: string;
    options?: {
      showTime?: boolean;
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

// 时间显示配置，默认不显示时间
const showTime = computed(() => {
  return props.field?.options?.showTime ?? false;
});

const displayFormat = computed(() => {
  return showTime.value ? "YYYY-MM-DD HH:mm:ss" : "YYYY-MM-DD";
});

const pickerType = computed(() => {
  return showTime.value ? "datetime" : "date";
});

const displayValue = computed(() => {
  if (!props.modelValue) return "-";
  return dayjs(props.modelValue).format(displayFormat.value);
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
      emit("update:modelValue", dayjs(val).format(displayFormat.value));
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
        :type="pickerType"
        :placeholder="
          placeholder || (showTime ? '请选择日期时间' : '请选择日期')
        "
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
