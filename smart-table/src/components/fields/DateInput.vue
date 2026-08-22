<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import dayjs from "dayjs";
import { Calendar } from "@element-plus/icons-vue";
import { FieldType } from "@/types";
import type { CellValue } from "@/types";
import type { FieldOptions } from "@/types/fields";

const props = defineProps<{
  /** 结构化字段类型，兼容 FieldEntity 与配置面板的精简字段对象 */
  field?: {
    type?: string;
    options?: FieldOptions;
  };
  modelValue: CellValue;
  disabled?: boolean;
  placeholder?: string;
  clearable?: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: CellValue): void;
}>();

const { t } = useI18n();

const options = computed<FieldOptions>(
  () => props.field?.options ?? ({} as FieldOptions),
);

/** 用户配置的日期格式，默认 YYYY-MM-DD */
const dateFormat = computed<string>(() => options.value.dateFormat || "YYYY-MM-DD");

type Mode = "date" | "month" | "monthDay" | "datetime";

/** 根据字段类型与配置格式推导选择器模式 */
const mode = computed<Mode>(() => {
  if (props.field?.type === FieldType.DATE_TIME) return "datetime";
  const fmt = dateFormat.value;
  if (fmt === "YYYY-MM" || fmt === "YYYYMM") return "month";
  if (fmt === "MMDD" || fmt === "MM-DD") return "monthDay";
  return "date";
});

const placeholderText = computed(() => props.placeholder || t("field.selectDate"));

// ---- date / month 模式（使用 el-date-picker 的 value-format 直接输出存储字符串）----
// 选择器输入框展示格式（与存储格式保持一致即可）
const pickerFormat = computed<string>(() => {
  if (mode.value === "month") return "YYYY-MM";
  return dateFormat.value; // YYYY-MM-DD 或 YYYYMMDD
});
const pickerValueFormat = computed<string>(() => dateFormat.value);

const dateModel = computed<string | null>(() =>
  props.modelValue == null || props.modelValue === "" ? null : String(props.modelValue),
);

function onDateUpdate(val: string | null) {
  emit("update:modelValue", val ?? null);
}

// ---- datetime 模式（DATE_TIME，仍按 ISO 字符串存储，保持原有时区语义）----
const datetimeModel = computed<Date | null>(() => {
  if (!props.modelValue) return null;
  const d = dayjs(props.modelValue as string);
  return d.isValid() ? d.toDate() : null;
});

function onDatetimeUpdate(val: Date | null) {
  if (!val) {
    emit("update:modelValue", null);
    return;
  }
  emit("update:modelValue", dayjs(val).toISOString());
}

// ---- monthDay 模式（自定义月日选择器）----
const monthDayValue = computed<{ month: number | null; day: number | null }>(() => {
  const v = props.modelValue as string | null;
  if (!v) return { month: null, day: null };
  let m = "";
  let d = "";
  if (dateFormat.value === "MM-DD") {
    m = v.slice(0, 2);
    d = v.slice(3, 5);
  } else {
    m = v.slice(0, 2);
    d = v.slice(2, 4);
  }
  return {
    month: m ? Number(m) : null,
    day: d ? Number(d) : null,
  };
});

const monthOptions = Array.from({ length: 12 }, (_, i) => i + 1);
const dayOptions = Array.from({ length: 31 }, (_, i) => i + 1);

// 月日模式使用本地草稿，待月、日均选中后再提交
const draftMonth = ref<number | null>(null);
const draftDay = ref<number | null>(null);

function syncDraftFromValue() {
  draftMonth.value = monthDayValue.value.month;
  draftDay.value = monthDayValue.value.day;
}

function emitMonthDay(month: number | null, day: number | null) {
  if (!month || !day) {
    emit("update:modelValue", null);
    return;
  }
  const mm = String(month).padStart(2, "0");
  const dd = String(day).padStart(2, "0");
  emit("update:modelValue", dateFormat.value === "MM-DD" ? `${mm}-${dd}` : `${mm}${dd}`);
}

function onMonthChange(m: number | null) {
  draftMonth.value = m;
  if (m && draftDay.value) emitMonthDay(m, draftDay.value);
}

function onDayChange(d: number | null) {
  draftDay.value = d;
  if (d && draftMonth.value) emitMonthDay(draftMonth.value, d);
}
</script>

<template>
  <!-- 年月模式：只能选择年、月 -->
  <el-date-picker
    v-if="mode === 'month'"
    :model-value="dateModel"
    type="month"
    :format="pickerFormat"
    :value-format="pickerValueFormat"
    :placeholder="placeholderText"
    :disabled="disabled"
    :clearable="clearable !== false"
    style="width: 100%"
    @update:model-value="onDateUpdate" />

  <!-- 普通日期模式：YYYY-MM-DD / YYYYMMDD -->
  <el-date-picker
    v-else-if="mode === 'date'"
    :model-value="dateModel"
    type="date"
    :format="pickerFormat"
    :value-format="pickerValueFormat"
    :placeholder="placeholderText"
    :disabled="disabled"
    :clearable="clearable !== false"
    style="width: 100%"
    @update:model-value="onDateUpdate" />

  <!-- 日期时间模式：DATE_TIME -->
  <el-date-picker
    v-else-if="mode === 'datetime'"
    :model-value="datetimeModel"
    type="datetime"
    format="YYYY-MM-DD HH:mm:ss"
    :placeholder="placeholderText"
    :disabled="disabled"
    :clearable="clearable !== false"
    style="width: 100%"
    @update:model-value="onDatetimeUpdate" />

  <!-- 月日模式：只能选择月、日 -->
  <el-popover
    v-else
    :disabled="disabled"
    placement="bottom-start"
    trigger="click"
    :width="220"
    @show="syncDraftFromValue">
    <template #reference>
      <el-input
        :model-value="dateModel || ''"
        readonly
        :disabled="disabled"
        :placeholder="placeholderText"
        style="width: 100%; cursor: pointer">
        <template #suffix>
          <el-icon><Calendar /></el-icon>
        </template>
      </el-input>
    </template>
    <div class="month-day-picker">
      <el-select
        :model-value="draftMonth"
        :placeholder="t('field.month')"
        style="width: 90px"
        @update:model-value="onMonthChange">
        <el-option
          v-for="m in monthOptions"
          :key="m"
          :label="String(m).padStart(2, '0')"
          :value="m" />
      </el-select>
      <span class="month-day-sep">{{ dateFormat === "MM-DD" ? "-" : "" }}</span>
      <el-select
        :model-value="draftDay"
        :placeholder="t('field.day')"
        style="width: 90px"
        @update:model-value="onDayChange">
        <el-option
          v-for="d in dayOptions"
          :key="d"
          :label="String(d).padStart(2, '0')"
          :value="d" />
      </el-select>
      <div class="month-day-actions">
        <el-button
          text
          size="small"
          @click="emitMonthDay(null, null)">
          {{ t("field.clear") }}
        </el-button>
      </div>
    </div>
  </el-popover>
</template>

<style scoped>
.month-day-picker {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}
.month-day-sep {
  color: var(--el-text-color-secondary);
}
.month-day-actions {
  width: 100%;
  text-align: right;
}
</style>
