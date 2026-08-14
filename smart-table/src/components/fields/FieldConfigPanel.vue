<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { Delete, Plus } from "@element-plus/icons-vue";
import { FieldType, type FieldOption, type FieldOptions } from "@/types/fields";
import { generateId } from "@/utils/id";
import { PRESET_REGEX_OPTIONS } from "@/utils/validation";

const { t } = useI18n();

interface Field {
  id: string;
  name: string;
  type: string;
  options?: FieldOptions;
  defaultValue?: any;
}

interface Props {
  field: Field;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:field", field: Field): void;
}>();

const localField = computed({
  get: () => props.field,
  set: (val: Field) => emit("update:field", val),
});

const fieldTypeOptions = [
  { label: t('field.type.single_line_text'), value: FieldType.SINGLE_LINE_TEXT },
  { label: t('field.type.long_text'), value: FieldType.LONG_TEXT },
  { label: t('field.type.rich_text'), value: FieldType.RICH_TEXT },
  { label: t('field.type.number'), value: FieldType.NUMBER },
  { label: t('field.type.date'), value: FieldType.DATE },
  { label: t('field.type.date_time'), value: FieldType.DATE_TIME },
  { label: t('field.type.single_select'), value: FieldType.SINGLE_SELECT },
  { label: t('field.type.multi_select'), value: FieldType.MULTI_SELECT },
  { label: t('field.type.checkbox'), value: FieldType.CHECKBOX },
  { label: t('field.type.attachment'), value: FieldType.ATTACHMENT },
];

const defaultColors = [
  "#3370FF",
  "#34D399",
  "#FBBF24",
  "#EF4444",
  "#8B5CF6",
  "#EC4899",
  "#14B8A6",
  "#F97316",
  "#6366F1",
  "#84CC16",
];

const ensureOptions = () => {
  if (!localField.value.options) {
    localField.value = { ...localField.value, options: {} };
  }
};

const updateOption = <K extends keyof FieldOptions>(
  key: K,
  value: FieldOptions[K],
) => {
  ensureOptions();
  localField.value = {
    ...localField.value,
    options: { ...localField.value.options, [key]: value },
  };
};

// 应用预置正则：同时写入 regex 与对应的提示信息 regexMessage
const applyPresetRegex = (preset: {
  label: string;
  pattern: string;
  message: string;
}) => {
  ensureOptions();
  localField.value = {
    ...localField.value,
    options: {
      ...localField.value.options,
      regex: preset.pattern,
      regexMessage: preset.message,
    },
  };
};

const addOption = () => {
  ensureOptions();
  const options = localField.value.options?.options || [];
  const newOption: FieldOption = {
    id: generateId(),
    name: t('field.optionCount', { count: options.length + 1 }),
    color: defaultColors[options.length % defaultColors.length],
  };
  updateOption("options", [...options, newOption]);
};

const removeOption = (optionId: string) => {
  const options = localField.value.options?.options || [];
  updateOption(
    "options",
    options.filter((opt) => opt.id !== optionId),
  );
};

const updateOptionName = (optionId: string, name: string) => {
  const options = localField.value.options?.options || [];
  updateOption(
    "options",
    options.map((opt) => (opt.id === optionId ? { ...opt, name } : opt)),
  );
};

const updateOptionColor = (optionId: string, color: string) => {
  const options = localField.value.options?.options || [];
  updateOption(
    "options",
    options.map((opt) => (opt.id === optionId ? { ...opt, color } : opt)),
  );
};

const updateBooleanOption = (
  key: "isRichText",
  val: string | number | boolean,
) => {
  updateOption(key, Boolean(val));
};

const showTextOptions = computed(
  () => localField.value.type === FieldType.SINGLE_LINE_TEXT ||
       localField.value.type === FieldType.LONG_TEXT ||
       localField.value.type === FieldType.RICH_TEXT,
);
// 仅单行文本字段展示正则表达式配置
const showRegexOptions = computed(
  () => localField.value.type === FieldType.SINGLE_LINE_TEXT,
);
const showNumberOptions = computed(
  () => localField.value.type === FieldType.NUMBER,
);
const showDateOptions = computed(
  () => localField.value.type === FieldType.DATE || localField.value.type === FieldType.DATE_TIME,
);
const isDateTimeField = computed(
  () => localField.value.type === FieldType.DATE_TIME,
);
const showSelectOptions = computed(
  () =>
    localField.value.type === FieldType.SINGLE_SELECT ||
    localField.value.type === FieldType.MULTI_SELECT,
);
const showAttachmentOptions = computed(
  () => localField.value.type === FieldType.ATTACHMENT,
);

// 默认值相关方法
const updateDefaultValue = (value: any) => {
  localField.value = {
    ...localField.value,
    defaultValue: value,
  };
};

const clearDefaultValue = () => {
  localField.value = {
    ...localField.value,
    defaultValue: undefined,
  };
};

// 获取单选/多选的选项列表用于默认值选择
const getSelectOptions = computed(() => {
  return localField.value.options?.options || [];
});

const numberFormatOptions = [
  { label: t('field.numFormat'), value: "number" },
  { label: t('field.currencyFormat'), value: "currency" },
  { label: t('field.percentFormat'), value: "percent" },
];

const currencySymbolOptions = [
  { label: t('field.currencySymbolCny'), value: "¥" },
  { label: t('field.currencySymbolUsd'), value: "$" },
  { label: t('field.currencySymbolEur'), value: "€" },
  { label: t('field.currencySymbolGbp'), value: "£" },
];
</script>

<template>
  <div class="field-config-panel">
    <div class="config-section">
      <div class="config-label">{{ t('field.fieldName') }}</div>
      <el-input
        v-model="localField.name"
        :placeholder="t('field.nameRequired')"
        class="config-input" />
    </div>

    <div class="config-section">
      <div class="config-label">{{ t('field.fieldType') }}</div>
      <el-select v-model="localField.type" class="config-input" disabled>
        <el-option
          v-for="option in fieldTypeOptions"
          :key="option.value"
          :label="option.label"
          :value="option.value" />
      </el-select>
    </div>

    <!-- 默认值配置区域 -->
    <div class="config-section default-value-section">
      <div class="config-label">
        <span>{{ t('field.defaultValue') }}</span>
        <el-button
          v-if="localField.defaultValue !== undefined"
          type="danger"
          size="small"
          @click="clearDefaultValue"
          class="clear-btn">
          {{ t('field.clear') }}
        </el-button>
      </div>

      <!-- 文本类型默认值 -->
      <el-input
        v-if="showTextOptions"
        v-model="localField.defaultValue"
        @update:model-value="updateDefaultValue"
        :placeholder="t('field.defaultTextPlaceholder')"
        class="config-input" />

      <!-- 数字类型默认值 -->
      <el-input-number
        v-if="showNumberOptions"
        :model-value="localField.defaultValue"
        @update:model-value="updateDefaultValue"
        :precision="localField.options?.precision"
        :placeholder="t('field.defaultNumberPlaceholder')"
        class="config-input" />

      <!-- 日期类型默认值 -->
      <div v-if="showDateOptions" class="date-default-wrapper">
        <el-radio-group
          :model-value="
            localField.defaultValue === 'now' ? 'dynamic' : 'static'
          "
          @update:model-value="
            (val: string | number | boolean | undefined) => updateDefaultValue(val === 'dynamic' ? 'now' : (val as string))
          "
          size="small"
          class="date-radio-group">
          <el-radio-button label="static">{{ t('field.specifyDate') }}</el-radio-button>
          <el-radio-button label="dynamic">当前{{ isDateTimeField ? t('field.currentDateTime') : t('field.currentDate') }}</el-radio-button>
        </el-radio-group>
        <el-date-picker
          v-if="localField.defaultValue !== 'now'"
          v-model="localField.defaultValue"
          @update:model-value="updateDefaultValue"
          :type="isDateTimeField ? 'datetime' : 'date'"
          :format="isDateTimeField ? 'YYYY-MM-DD HH:mm:ss' : 'YYYY-MM-DD'"
          :placeholder="isDateTimeField ? t('field.defaultDateTimePlaceholder') : t('field.defaultDatePlaceholder')"
          class="config-input date-picker" />
      </div>

      <!-- 单选类型默认值 -->
      <el-select
        v-if="localField.type === FieldType.SINGLE_SELECT"
        :model-value="localField.defaultValue"
        @update:model-value="updateDefaultValue"
        :placeholder="t('field.defaultOptionPlaceholder')"
        clearable
        class="config-input">
        <el-option
          v-for="option in getSelectOptions"
          :key="option.id"
          :label="option.name"
          :value="option.id" />
      </el-select>

      <!-- 多选类型默认值 -->
      <el-select
        v-if="localField.type === FieldType.MULTI_SELECT"
        :model-value="localField.defaultValue"
        @update:model-value="updateDefaultValue"
        :placeholder="t('field.defaultOptionPlaceholder')"
        multiple
        collapse-tags
        collapse-tags-tooltip
        class="config-input">
        <el-option
          v-for="option in getSelectOptions"
          :key="option.id"
          :label="option.name"
          :value="option.id" />
      </el-select>

      <!-- 复选框类型默认值 -->
      <el-switch
        v-if="localField.type === FieldType.CHECKBOX"
        :model-value="localField.defaultValue"
        @update:model-value="updateDefaultValue"
        :active-text="t('field.checked')"
        :inactive-text="t('field.unchecked')" />
    </div>

    <template v-if="showTextOptions">
      <div class="config-section">
        <div class="config-label">{{ t('field.multiLineText') }}</div>
        <el-switch
          :model-value="localField.options?.isRichText || false"
          @update:model-value="
            (val) => updateBooleanOption('isRichText', val)
          " />
      </div>
      <div class="config-section">
        <div class="config-label">{{ t('field.maxLength') }}</div>
        <el-input-number
          :model-value="localField.options?.maxLength"
          @update:model-value="
            (val: number | undefined) => updateOption('maxLength', val)
          "
          :min="1"
          :max="10000"
          :controls="false"
          :placeholder="t('field.noLimit')"
          class="config-input" />
      </div>
    </template>

    <!-- 正则表达式配置区块（仅单行文本字段） -->
    <template v-if="showRegexOptions">
      <div class="config-section">
        <div class="config-label">{{ t('field.regexPreset') }}</div>
        <div class="regex-preset-list">
          <el-tag
            v-for="preset in PRESET_REGEX_OPTIONS"
            :key="preset.label"
            size="small"
            type="info"
            effect="plain"
            class="regex-preset-tag"
            style="cursor: pointer"
            @click="applyPresetRegex(preset)">
            {{ preset.label }}
          </el-tag>
        </div>
      </div>
      <div class="config-section">
        <div class="config-label">{{ t('field.regex') }}</div>
        <el-input
          :model-value="localField.options?.regex || ''"
          @update:model-value="(val: string) => updateOption('regex', val)"
          :placeholder="t('field.regexPlaceholder')"
          class="config-input"
          clearable />
      </div>
      <div v-if="localField.options?.regex" class="config-section">
        <div class="config-label">{{ t('field.regexMessage') }}</div>
        <el-input
          :model-value="localField.options?.regexMessage || ''"
          @update:model-value="(val: string) => updateOption('regexMessage', val)"
          :placeholder="t('field.regexMessagePlaceholder')"
          class="config-input"
          clearable />
      </div>
    </template>

    <template v-if="showNumberOptions">
      <div class="config-section">
        <div class="config-label">{{ t('field.numberFormat') }}</div>
        <el-select
          :model-value="localField.options?.format || 'number'"
          @update:model-value="
            (val: 'number' | 'currency' | 'percent') =>
              updateOption('format', val)
          "
          class="config-input">
          <el-option
            v-for="option in numberFormatOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value" />
        </el-select>
      </div>
      <div
        v-if="localField.options?.format === 'currency'"
        class="config-section">
        <div class="config-label">{{ t('field.currencySymbolLabel') }}</div>
        <el-select
          :model-value="localField.options?.currencySymbol || '¥'"
          @update:model-value="
            (val: string) => updateOption('currencySymbol', val)
          "
          class="config-input">
          <el-option
            v-for="option in currencySymbolOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value" />
        </el-select>
      </div>
      <div class="config-section">
        <div class="config-label">{{ t('field.precision') }}</div>
        <el-input-number
          :model-value="localField.options?.precision ?? 2"
          @update:model-value="
            (val: number | undefined) => updateOption('precision', val)
          "
          :min="0"
          :max="10"
          :controls="false"
          class="config-input" />
      </div>
    </template>

    <template v-if="showSelectOptions">
      <div class="config-section">
        <div class="config-label">{{ t('field.optionList') }}</div>
        <div class="options-list">
          <div
            v-for="option in localField.options?.options || []"
            :key="option.id"
            class="option-item">
            <el-color-picker
              :model-value="option.color"
              @update:model-value="
                (val: string | null) => updateOptionColor(option.id, val || '')
              "
              size="small" />
            <el-input
              :model-value="option.name"
              @update:model-value="
                (val: string) => updateOptionName(option.id, val)
              "
              size="small"
              class="option-input" />
            <el-button
              type="danger"
              size="small"
              :icon="Delete"
              circle
              @click="removeOption(option.id)" />
          </div>
          <el-button
            type="primary"
            size="small"
            :icon="Plus"
            @click="addOption"
            class="add-option-btn">
            {{ t('field.addOption') }}
          </el-button>
        </div>
      </div>
    </template>

    <template v-if="showAttachmentOptions">
      <div class="config-section">
        <div class="config-label">{{ t('field.fileTypeLimit') }}</div>
        <el-select
          :model-value="localField.options?.acceptTypes || []"
          @update:model-value="
            (val: string[]) => updateOption('acceptTypes', val)
          "
          multiple
          :placeholder="t('field.fileTypeLimitPlaceholder')"
          class="config-input">
          <el-option :label="t('field.fileTypeImage')" value="image/*" />
          <el-option :label="t('field.fileTypePdf')" value="application/pdf" />
          <el-option :label="t('field.fileTypeWordDoc')" value="application/msword" />
          <el-option
            :label="t('field.fileTypeWordDocx')"
            value="application/vnd.openxmlformats-officedocument.wordprocessingml.document" />
          <el-option
            :label="t('field.fileTypeExcelXls')"
            value="application/vnd.ms-excel" />
          <el-option
            :label="t('field.fileTypeExcelXlsx')"
            value="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" />
          <el-option :label="t('field.fileTypeVideo')" value="video/*" />
          <el-option :label="t('field.fileTypeAudio')" value="audio/*" />
        </el-select>
      </div>

      <div class="config-section">
        <div class="config-label">{{ t('field.singleFileSizeMb') }}</div>
        <el-input-number
          :model-value="
            Math.floor(
              (localField.options?.maxSize || 10 * 1024 * 1024) / 1024 / 1024,
            )
          "
          @update:model-value="
            (val: number | undefined) => updateOption('maxSize', (val || 0) * 1024 * 1024)
          "
          :min="1"
          :max="100"
          :step="1"
          class="config-input" />
      </div>

      <div class="config-section">
        <div class="config-label">{{ t('field.maxFileCount') }}</div>
        <el-input-number
          :model-value="localField.options?.maxCount || 20"
          @update:model-value="
            (val: number | undefined) => updateOption('maxCount', val)
          "
          :min="1"
          :max="50"
          class="config-input" />
      </div>

      <div class="config-section">
        <div class="config-label">{{ t('field.generateThumbnail') }}</div>
        <el-switch
          :model-value="localField.options?.enableThumbnail !== false"
          @update:model-value="(val: string | number | boolean) => updateOption('enableThumbnail', !!val)" />
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.field-config-panel {
  @include flex-column;
  gap: $spacing-md;
}

.config-section {
  @include flex-column;
  gap: $spacing-xs;
}

.config-label {
  font-size: $font-size-sm;
  font-weight: 500;
  color: $text-secondary;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.clear-btn {
  padding: 2px 8px;
  font-size: 12px;
}

.default-value-section {
  border-top: 1px solid $border-color;
  padding-top: $spacing-md;
  margin-top: $spacing-sm;
}

.date-default-wrapper {
  @include flex-column;
  gap: $spacing-sm;
}

.date-radio-group {
  margin-bottom: $spacing-xs;
}

.date-picker {
  width: 100%;
}

.config-input {
  width: 100%;
}

.options-list {
  @include flex-column;
  gap: $spacing-sm;
}

.option-item {
  @include flex-start;
  gap: $spacing-sm;
}

.option-input {
  flex: 1;
}

.add-option-btn {
  width: fit-content;
}

.regex-preset-list {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
}

.regex-preset-tag {
  cursor: pointer;
  user-select: none;
}
</style>
