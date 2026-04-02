<script setup lang="ts">
import { computed, ref, nextTick } from "vue";
import dayjs from "dayjs";
import type { FieldEntity, RecordEntity } from "@/db/schema";
import type { CellValue, FieldOptions } from "@/types";
import MultiSelectField from "@/components/fields/MultiSelectField.vue";
import { FormulaEngine } from "@/utils/formula/engine";
import { isFieldRequired, isValueEmpty } from "@/utils/validation";
import { ElMessage } from "element-plus";

interface Props {
  record: RecordEntity;
  field: FieldEntity;
  readonly?: boolean;
  selected?: boolean;
  fields?: FieldEntity[]; // 所有字段，用于公式计算
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
  selected: false,
});

const emit = defineEmits<{
  (e: "update", value: CellValue): void;
  (e: "edit", active: boolean): void;
  (e: "open-detail"): void;
}>();

const isEditing = ref(false);
const editValue = ref<string | number | boolean | string[] | null>(null);
const dateEditValue = ref<Date | null>(null);
const inputRef = ref<HTMLInputElement | HTMLTextAreaElement | null>(null);

const cellValue = computed(() => {
  return props.record.values[props.field.id] ?? null;
});

// 创建一个响应式的记录值引用，用于触发公式重新计算
const recordValuesHash = computed(() => {
  // 返回 values 对象的字符串表示，这样任何值的变化都会触发重新计算
  return JSON.stringify(props.record.values);
});

// 获取字段配置
const fieldOptions = computed(() => {
  return props.field.options as FieldOptions | undefined;
});

// 数值字段精度配置
const numberPrecision = computed(() => {
  return fieldOptions.value?.precision ?? 0;
});

// 日期字段时间显示配置
const dateShowTime = computed(() => {
  return fieldOptions.value?.showTime ?? false;
});

// 日期显示格式
const dateDisplayFormat = computed(() => {
  return dateShowTime.value ? "YYYY-MM-DD HH:mm:ss" : "YYYY-MM-DD";
});

// 日期选择器类型
const datePickerType = computed(() => {
  return dateShowTime.value ? "datetime" : "date";
});

// 公式字段计算结果 - 使用独立的 computed 来确保响应性
const formulaValue = computed(() => {
  // 依赖 recordValuesHash，确保任何字段值变化都会重新计算
  // 使用 hash 值作为依赖，当任何字段值变化时，hash 会改变，触发重新计算
  const hash = recordValuesHash.value;
  console.log("Formula recalculating, hash:", hash);
  return calculateFormula();
});

const displayValue = computed(() => {
  const value = cellValue.value;
  const type = props.field.type;
  const options = fieldOptions.value;

  switch (type) {
    case "text":
    case "email":
    case "url":
    case "phone":
      return value === null || value === undefined ? "" : String(value);
    case "number":
      if (typeof value === "number") {
        const precision = options?.precision ?? 0;
        const formatted = value.toFixed(precision);
        const prefix = options?.prefix || "";
        const suffix = options?.suffix || "";
        return `${prefix}${formatted}${suffix}`;
      }
      return value === null || value === undefined ? "" : String(value);
    case "singleSelect": {
      if (value === null || value === undefined) return "";
      const opts = options?.options || [];
      const opt = opts.find((o) => o.id === value || o.name === value);
      return opt?.name || String(value);
    }
    case "multiSelect": {
      if (!Array.isArray(value) || value.length === 0) return "";
      const opts = options?.options || [];
      return value
        .map((v) => {
          const opt = opts.find((o) => o.id === v || o.name === v);
          return opt?.name || String(v);
        })
        .join(", ");
    }
    case "checkbox":
      return value ? "✓" : "";
    case "date": {
      if (!value) return "";
      // 根据配置显示日期或日期时间
      const showTime = options?.showTime ?? false;
      const format = showTime ? "YYYY-MM-DD HH:mm:ss" : "YYYY-MM-DD";

      // 处理时间戳格式
      const timestamp = typeof value === "string" ? Number(value) : value;
      if (typeof timestamp === "number" && !isNaN(timestamp)) {
        return dayjs(timestamp).format(format);
      }
      // 处理字符串日期格式
      if (typeof value === "string") {
        return dayjs(value).format(format);
      }
      return String(value);
    }
    case "rating": {
      const maxRating = options?.maxRating || 5;
      const rating = Number(value) || 0;
      return "★".repeat(rating) + "☆".repeat(maxRating - rating);
    }
    case "progress": {
      const progress = Number(value) || 0;
      return `${progress}%`;
    }
    case "member": {
      if (!Array.isArray(value)) return "";
      return value
        .map((m) => {
          if (typeof m === "string") return m;
          return m.name || "";
        })
        .filter(Boolean)
        .join(", ");
    }
    case "attachment": {
      if (!Array.isArray(value)) return "";
      return `${value.length} 个文件`;
    }
    case "formula": {
      // 公式字段使用独立的 computed 属性
      return formulaValue.value;
    }
    default:
      return value === null || value === undefined ? "" : String(value);
  }
});

// 计算公式字段值
const calculateFormula = (): string => {
  const formula = fieldOptions.value?.formula as string;
  if (!formula) return "";

  try {
    // 获取所有字段（从父组件传入）
    const allFields = props.fields;
    if (!allFields || allFields.length === 0) {
      return "";
    }
    const engine = new FormulaEngine(allFields);
    const result = engine.calculate(props.record, formula);

    if (result === "#ERROR") {
      return "计算错误";
    }

    // 数字格式化
    if (typeof result === "number") {
      const precision = fieldOptions.value?.precision ?? 2;
      return result.toLocaleString("zh-CN", {
        minimumFractionDigits: precision,
        maximumFractionDigits: precision,
      });
    }

    return String(result);
  } catch (error) {
    console.error("Formula calculation error:", error);
    return "计算错误";
  }
};

const fieldType = computed(() => props.field.type);

const isEditable = computed(() => {
  // 主键字段不可编辑
  if (props.field.isPrimary) return false;

  return (
    !props.readonly &&
    ![
      "formula",
      "createdBy",
      "createdTime",
      "updatedBy",
      "updatedTime",
      "autoNumber",
    ].includes(props.field.type)
  );
});

const startEdit = async () => {
  if (!isEditable.value) return;

  isEditing.value = true;
  const cv = cellValue.value;
  if (fieldType.value === "multiSelect") {
    editValue.value = Array.isArray(cv)
      ? cv.map((v) => (typeof v === "string" ? v : v.id))
      : [];
  } else if (fieldType.value === "date") {
    // 日期字段特殊处理
    if (cv) {
      const timestamp = typeof cv === "string" ? Number(cv) : cv;
      if (typeof timestamp === "number" && !isNaN(timestamp)) {
        dateEditValue.value = new Date(timestamp);
      } else if (typeof cv === "string") {
        dateEditValue.value = new Date(cv);
      } else {
        dateEditValue.value = null;
      }
    } else {
      dateEditValue.value = null;
    }
  } else {
    editValue.value = cv as string | number | boolean | null;
  }
  emit("edit", true);

  await nextTick();
  inputRef.value?.focus();
};

const finishEdit = () => {
  if (!isEditing.value) return;

  // 检查必填字段
  if (isFieldRequired(props.field) && isValueEmpty(editValue.value)) {
    ElMessage.error(`请填写必填字段：${props.field.name}`);
    cancelEdit();
    return;
  }

  isEditing.value = false;
  emit("edit", false);

  if (editValue.value !== cellValue.value) {
    emit("update", editValue.value as CellValue);
  }
};

const cancelEdit = () => {
  isEditing.value = false;
  emit("edit", false);
  editValue.value = null;
};

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    finishEdit();
  } else if (event.key === "Escape") {
    cancelEdit();
  }
};

const handleDateChange = (val: Date | null) => {
  dateEditValue.value = val;
  if (val) {
    // 根据配置决定存储格式
    const showTime = dateShowTime.value;
    if (showTime) {
      // 存储为时间戳
      emit("update", val.getTime() as CellValue);
    } else {
      // 存储为日期字符串
      emit("update", dayjs(val).format("YYYY-MM-DD") as CellValue);
    }
  } else {
    emit("update", null);
  }
  finishEdit();
};

const handleDoubleClick = () => {
  // 附件字段双击时打开详情对话框
  if (fieldType.value === 'attachment') {
    emit("open-detail");
    return;
  }
  startEdit();
};

// 切换复选框状态
const toggleCheckbox = () => {
  if (!isEditable.value) return;
  const newValue = !cellValue.value;
  emit("update", newValue as CellValue);
};

const getSelectOptions = computed(() => {
  const options = fieldOptions.value;
  return options?.options || [];
});

const getOptionColor = (optionId: string) => {
  const options = fieldOptions.value;
  const opt = options?.options?.find(
    (o) => o.id === optionId || o.name === optionId,
  );
  return opt?.color || "#6B7280";
};

const multiSelectDisplayValues = computed(() => {
  if (!Array.isArray(cellValue.value)) return [];
  return cellValue.value.map((v) => (typeof v === "string" ? v : v.id));
});
</script>

<template>
  <div
    class="table-cell"
    :class="{
      'is-editing': isEditing,
      'is-selected': selected,
      'is-readonly': !isEditable,
    }"
    :data-field-type="fieldType"
    @dblclick="handleDoubleClick">
    <template v-if="isEditing">
      <template v-if="fieldType === 'text'">
        <textarea
          v-if="(field.options as FieldOptions)?.isRichText"
          ref="inputRef"
          :value="editValue as string"
          class="cell-input textarea"
          @input="editValue = ($event.target as HTMLTextAreaElement).value"
          @blur="finishEdit"
          @keydown="handleKeydown" />
        <input
          v-else
          ref="inputRef"
          :value="editValue as string"
          type="text"
          class="cell-input"
          @input="editValue = ($event.target as HTMLInputElement).value"
          @blur="finishEdit"
          @keydown="handleKeydown" />
      </template>

      <template v-else-if="fieldType === 'number'">
        <el-input-number
          ref="inputRef"
          v-model="editValue as number"
          :precision="numberPrecision"
          :controls="false"
          class="cell-number-input"
          @blur="finishEdit"
          @keydown="handleKeydown" />
      </template>

      <template v-else-if="fieldType === 'singleSelect'">
        <select
          ref="inputRef"
          :value="editValue as string"
          class="cell-select"
          @blur="finishEdit"
          @change="
            editValue = ($event.target as HTMLSelectElement).value;
            finishEdit();
          ">
          <option :value="null">无</option>
          <option v-for="opt in getSelectOptions" :key="opt.id" :value="opt.id">
            {{ opt.name }}
          </option>
        </select>
      </template>

      <template v-else-if="fieldType === 'multiSelect'">
        <MultiSelectField
          v-model="editValue as string[]"
          :field="field"
          @blur="finishEdit" />
      </template>

      <template v-else-if="fieldType === 'checkbox'">
        <input
          ref="inputRef"
          v-model="editValue"
          type="checkbox"
          class="cell-checkbox"
          @change="finishEdit" />
      </template>

      <template v-else-if="fieldType === 'date'">
        <el-date-picker
          ref="inputRef"
          v-model="dateEditValue"
          :type="datePickerType"
          :placeholder="dateShowTime ? '选择日期时间' : '选择日期'"
          :format="dateDisplayFormat"
          class="cell-date-picker"
          @change="handleDateChange" />
      </template>

      <template v-else-if="fieldType === 'rating'">
        <div class="rating-editor">
          <span
            v-for="i in (field.options as FieldOptions)?.maxRating || 5"
            :key="i"
            class="rating-star"
            :class="{ active: i <= ((editValue as number) || 0) }"
            @click="editValue = i"
            >★</span
          >
          <button class="clear-btn" @click="editValue = 0">清除</button>
        </div>
      </template>

      <template v-else-if="fieldType === 'progress'">
        <input
          ref="inputRef"
          :value="editValue as number"
          type="range"
          min="0"
          max="100"
          class="cell-range"
          @input="editValue = Number(($event.target as HTMLInputElement).value)"
          @blur="finishEdit" />
      </template>

      <template v-else>
        <input
          ref="inputRef"
          :value="editValue as string"
          type="text"
          class="cell-input"
          @input="editValue = ($event.target as HTMLInputElement).value"
          @blur="finishEdit"
          @keydown="handleKeydown" />
      </template>
    </template>

    <template v-else>
      <div class="cell-content">
        <template v-if="fieldType === 'singleSelect' && cellValue">
          <span
            class="select-tag"
            :style="{ backgroundColor: getOptionColor(cellValue as string) }">
            {{ displayValue }}
          </span>
        </template>

        <template
          v-else-if="
            fieldType === 'multiSelect' &&
            Array.isArray(cellValue) &&
            cellValue.length > 0
          ">
          <span
            v-for="(val, idx) in multiSelectDisplayValues"
            :key="`${field.id}-${idx}-${val}`"
            class="select-tag"
            :style="{ backgroundColor: getOptionColor(val) }">
            {{
              (field.options as FieldOptions)?.options?.find(
                (o) => o.id === val || o.name === val,
              )?.name || val
            }}
          </span>
        </template>

        <template v-else-if="fieldType === 'checkbox'">
          <div
            class="switch-display"
            :class="{ checked: cellValue }"
            @click.stop="toggleCheckbox">
            <div class="switch-slider"></div>
          </div>
        </template>

        <template v-else-if="fieldType === 'progress'">
          <div class="progress-display">
            <div class="progress-bar">
              <div
                class="progress-fill"
                :style="{ width: `${Number(cellValue) || 0}%` }" />
            </div>
            <span class="progress-text">{{ displayValue }}</span>
          </div>
        </template>

        <template v-else-if="fieldType === 'rating'">
          <span class="rating-display">{{ displayValue }}</span>
        </template>

        <template v-else-if="fieldType === 'url' && cellValue">
          <a
            :href="String(cellValue)"
            target="_blank"
            class="url-link"
            @click.stop>
            {{ displayValue }}
          </a>
        </template>

        <template v-else-if="fieldType === 'email' && cellValue">
          <a :href="`mailto:${cellValue}`" class="email-link" @click.stop>
            {{ displayValue }}
          </a>
        </template>

        <template v-else>
          <span class="text-display">{{ displayValue || "" }}</span>
        </template>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use "sass:color";
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.table-cell {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 32px;
  padding: 4px 8px;
  display: flex;
  align-items: center;
  cursor: default;
  overflow: hidden;

  &.is-selected {
    background-color: rgba($primary-color, 0.1);
  }

  &.is-editing {
    padding: 2px;

    .cell-input,
    .cell-select {
      width: 100%;
      height: 100%;
      min-height: 28px;
      padding: 4px 8px;
      border: 1px solid $primary-color;
      border-radius: $border-radius-sm;
      font-size: $font-size-sm;
      color: $text-primary;
      background: $surface-color;
      outline: none;

      &:focus {
        border-color: $primary-color;
        box-shadow: 0 0 0 2px rgba($primary-color, 0.2);
      }
    }

    .cell-input.textarea {
      min-height: 60px;
      resize: vertical;
    }

    .cell-checkbox {
      width: 16px;
      height: 16px;
      cursor: pointer;
    }

    .cell-range {
      width: 100%;
    }

    .cell-number-input,
    .cell-date-picker {
      width: 100%;

      :deep(.el-input__wrapper) {
        border-radius: $border-radius-sm;
      }
    }
  }
}

.cell-content {
  width: 100%;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  overflow: hidden;
  color: $text-primary;
}

.text-display {
  @include text-ellipsis;
  width: 100%;
}

.select-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: $font-size-xs;
  color: #fff;
  white-space: nowrap;
}

.checkbox-display {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border: 1px solid $border-color;
  border-radius: 3px;
  font-size: 12px;

  &.checked {
    background-color: $primary-color;
    border-color: $primary-color;
    color: #fff;
  }
}

// 开关按钮样式
.switch-display {
  position: relative;
  width: 36px;
  height: 20px;
  background-color: #dcdfe6;
  border-radius: 10px;
  cursor: pointer;
  transition: background-color 0.3s ease;
  flex-shrink: 0;

  &:hover {
    background-color: #c0c4cc;
  }

  &.checked {
    background-color: $primary-color;

    &:hover {
      background-color: color.adjust($primary-color, $lightness: -10%);
    }

    .switch-slider {
      transform: translateX(16px);
    }
  }

  &:active .switch-slider {
    width: 18px;
  }

  &.checked:active .switch-slider {
    transform: translateX(14px);
  }
}

.switch-slider {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  background-color: #fff;
  border-radius: 50%;
  transition:
    transform 0.3s ease,
    width 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.progress-display {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background-color: $bg-color;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: $primary-color;
  transition: width 0.2s ease;
}

.progress-text {
  font-size: $font-size-xs;
  color: $text-secondary;
  white-space: nowrap;
}

.rating-display {
  color: #fbbf24;
  letter-spacing: 1px;
}

.rating-editor {
  display: flex;
  align-items: center;
  gap: 2px;

  .rating-star {
    cursor: pointer;
    color: #d1d5db;
    font-size: 16px;
    transition: color 0.15s;

    &.active {
      color: #fbbf24;
    }

    &:hover {
      color: #fbbf24;
    }
  }

  .clear-btn {
    margin-left: 8px;
    padding: 2px 6px;
    font-size: $font-size-xs;
    border: 1px solid $border-color;
    border-radius: $border-radius-sm;
    background: $surface-color;
    cursor: pointer;
  }
}

.multi-select-editor {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px;
  background: $surface-color;
  border: 1px solid $border-color;
  border-radius: $border-radius-sm;
  box-shadow: $shadow-md;

  .multi-select-option {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px;
    cursor: pointer;

    &:hover {
      background-color: $bg-color;
    }
  }

  .apply-btn {
    margin-top: 4px;
    padding: 4px 8px;
    font-size: $font-size-xs;
    background: $primary-color;
    color: #fff;
    border: none;
    border-radius: $border-radius-sm;
    cursor: pointer;
  }
}

.url-link,
.email-link {
  color: $primary-color;
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}
</style>
