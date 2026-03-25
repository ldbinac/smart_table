<script setup lang="ts">
import { Delete, Plus } from "@element-plus/icons-vue";
import { FieldType, type FieldOption, type FieldOptions } from "@/types/fields";
import { generateId } from "@/utils/id";

interface Field {
  id: string;
  name: string;
  type: string;
  options?: FieldOptions;
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
  { label: "文本", value: FieldType.TEXT },
  { label: "数字", value: FieldType.NUMBER },
  { label: "日期", value: FieldType.DATE },
  { label: "单选", value: FieldType.SINGLE_SELECT },
  { label: "多选", value: FieldType.MULTI_SELECT },
  { label: "复选框", value: FieldType.CHECKBOX },
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

const addOption = () => {
  ensureOptions();
  const options = localField.value.options?.options || [];
  const newOption: FieldOption = {
    id: generateId(),
    name: `选项 ${options.length + 1}`,
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
  key: "isRichText" | "includeTime",
  val: string | number | boolean,
) => {
  updateOption(key, Boolean(val));
};

const showTextOptions = computed(
  () => localField.value.type === FieldType.TEXT,
);
const showNumberOptions = computed(
  () => localField.value.type === FieldType.NUMBER,
);
const showDateOptions = computed(
  () => localField.value.type === FieldType.DATE,
);
const showSelectOptions = computed(
  () =>
    localField.value.type === FieldType.SINGLE_SELECT ||
    localField.value.type === FieldType.MULTI_SELECT,
);

const numberFormatOptions = [
  { label: "数字", value: "number" },
  { label: "货币", value: "currency" },
  { label: "百分比", value: "percent" },
];

const currencySymbolOptions = [
  { label: "¥ 人民币", value: "¥" },
  { label: "$ 美元", value: "$" },
  { label: "€ 欧元", value: "€" },
  { label: "£ 英镑", value: "£" },
];
</script>

<template>
  <div class="field-config-panel">
    <div class="config-section">
      <div class="config-label">字段名称</div>
      <el-input
        v-model="localField.name"
        placeholder="请输入字段名称"
        class="config-input" />
    </div>

    <div class="config-section">
      <div class="config-label">字段类型</div>
      <el-select v-model="localField.type" class="config-input" disabled>
        <el-option
          v-for="option in fieldTypeOptions"
          :key="option.value"
          :label="option.label"
          :value="option.value" />
      </el-select>
    </div>

    <template v-if="showTextOptions">
      <div class="config-section">
        <div class="config-label">多行文本</div>
        <el-switch
          :model-value="localField.options?.isRichText || false"
          @update:model-value="
            (val) => updateBooleanOption('isRichText', val)
          " />
      </div>
      <div class="config-section">
        <div class="config-label">最大长度</div>
        <el-input-number
          :model-value="localField.options?.maxLength"
          @update:model-value="
            (val: number | undefined) => updateOption('maxLength', val)
          "
          :min="1"
          :max="10000"
          :controls="false"
          placeholder="不限制"
          class="config-input" />
      </div>
    </template>

    <template v-if="showNumberOptions">
      <div class="config-section">
        <div class="config-label">数字格式</div>
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
        <div class="config-label">货币符号</div>
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
        <div class="config-label">小数位数</div>
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

    <template v-if="showDateOptions">
      <div class="config-section">
        <div class="config-label">包含时间</div>
        <el-switch
          :model-value="localField.options?.includeTime || false"
          @update:model-value="
            (val) => updateBooleanOption('includeTime', val)
          " />
      </div>
    </template>

    <template v-if="showSelectOptions">
      <div class="config-section">
        <div class="config-label">选项列表</div>
        <div class="options-list">
          <div
            v-for="option in localField.options?.options || []"
            :key="option.id"
            class="option-item">
            <el-color-picker
              :model-value="option.color"
              @update:model-value="
                (val: string) => updateOptionColor(option.id, val)
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
            添加选项
          </el-button>
        </div>
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
</style>
