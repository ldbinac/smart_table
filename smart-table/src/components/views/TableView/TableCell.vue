<script setup lang="ts">
import { computed, ref, nextTick } from "vue";
import type { FieldEntity, RecordEntity } from "@/db/schema";
import type { CellValue, FieldOptions } from "@/types";

interface Props {
  record: RecordEntity;
  field: FieldEntity;
  readonly?: boolean;
  selected?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
  selected: false,
});

const emit = defineEmits<{
  (e: "update", value: CellValue): void;
  (e: "edit", active: boolean): void;
}>();

const isEditing = ref(false);
const editValue = ref<string | number | boolean | string[] | null>(null);
const inputRef = ref<HTMLInputElement | HTMLTextAreaElement | null>(null);

const cellValue = computed(() => {
  return props.record.values[props.field.id] ?? null;
});

const displayValue = computed(() => {
  const value = cellValue.value;
  if (value === null || value === undefined) return "";

  const type = props.field.type;
  const options = props.field.options as FieldOptions | undefined;

  switch (type) {
    case "text":
    case "email":
    case "url":
    case "phone":
      return String(value);
    case "number":
      if (typeof value === "number") {
        const precision = options?.precision;
        const formatted =
          precision !== undefined ? value.toFixed(precision) : String(value);
        const prefix = options?.prefix || "";
        const suffix = options?.suffix || "";
        return `${prefix}${formatted}${suffix}`;
      }
      return String(value);
    case "singleSelect": {
      const opts = options?.options || [];
      const opt = opts.find((o) => o.id === value || o.name === value);
      return opt?.name || String(value);
    }
    case "multiSelect": {
      if (!Array.isArray(value)) return "";
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
    case "date":
      return value ? String(value) : "";
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
    default:
      return String(value);
  }
});

const fieldType = computed(() => props.field.type);

const isEditable = computed(() => {
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
  } else {
    editValue.value = cv as string | number | boolean | null;
  }
  emit("edit", true);

  await nextTick();
  inputRef.value?.focus();
};

const finishEdit = () => {
  if (!isEditing.value) return;

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

const handleDoubleClick = () => {
  startEdit();
};

const getSelectOptions = computed(() => {
  const options = props.field.options as FieldOptions | undefined;
  return options?.options || [];
});

const getOptionColor = (optionId: string) => {
  const options = props.field.options as FieldOptions | undefined;
  const opt = options?.options?.find(
    (o) => o.id === optionId || o.name === optionId,
  );
  return opt?.color || "#6B7280";
};

const isMultiSelectChecked = (optId: string): boolean => {
  if (!Array.isArray(editValue.value)) return false;
  return editValue.value.includes(optId);
};

const toggleMultiSelectOption = (optId: string) => {
  const currentValues = Array.isArray(editValue.value)
    ? [...editValue.value]
    : [];
  const idx = currentValues.indexOf(optId);
  if (idx > -1) {
    currentValues.splice(idx, 1);
  } else {
    currentValues.push(optId);
  }
  editValue.value = currentValues;
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
        <input
          ref="inputRef"
          :value="editValue as number"
          type="number"
          class="cell-input"
          @input="editValue = Number(($event.target as HTMLInputElement).value)"
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
        <div class="multi-select-editor">
          <label
            v-for="opt in getSelectOptions"
            :key="opt.id"
            class="multi-select-option">
            <input
              type="checkbox"
              :checked="isMultiSelectChecked(opt.id)"
              @change="toggleMultiSelectOption(opt.id)" />
            <span>{{ opt.name }}</span>
          </label>
          <button class="apply-btn" @click="finishEdit">应用</button>
        </div>
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
        <input
          ref="inputRef"
          :value="editValue as string"
          type="date"
          class="cell-input"
          @input="editValue = ($event.target as HTMLInputElement).value"
          @blur="finishEdit"
          @keydown="handleKeydown" />
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
          <span class="checkbox-display" :class="{ checked: cellValue }">
            {{ cellValue ? "✓" : "" }}
          </span>
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
