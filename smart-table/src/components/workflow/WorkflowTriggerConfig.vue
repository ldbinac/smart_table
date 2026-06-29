<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import type { FieldEntity } from "@/db/schema";
import type { WorkflowTrigger, TriggerType, ScheduleConfig, ScheduleRepeatType, ScheduleCustomUnit, ScheduleEndType } from "@/types/workflow";
import { FilterOperator } from "@/types/filters";
import type { FilterOperatorValue } from "@/types/filters";
import {
  getOperatorsForFieldType,
  OPERATOR_LABELS,
  operatorRequiresValue,
} from "@/utils/filter";
import FieldValueInput from "@/components/fields/FieldValueInput.vue";
import { Delete, Plus } from "@element-plus/icons-vue";
import { isSpecifiedTimeTrigger, createDefaultScheduleConfig } from "@/utils/workflow";

interface Props {
  trigger: WorkflowTrigger;
  fields: FieldEntity[];
  readonly?: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "update:trigger", trigger: WorkflowTrigger): void;
}>();

function cloneTrigger(trigger: WorkflowTrigger): WorkflowTrigger {
  return JSON.parse(JSON.stringify(trigger));
}

const localTrigger = ref<WorkflowTrigger>(cloneTrigger(props.trigger));
let isUpdatingFromParent = false;

watch(
  () => props.trigger,
  (newTrigger) => {
    isUpdatingFromParent = true;
    localTrigger.value = cloneTrigger(newTrigger);
    nextTick(() => {
      isUpdatingFromParent = false;
    });
  },
  { deep: true },
);

watch(
  localTrigger,
  (newTrigger) => {
    if (isUpdatingFromParent) return;
    emit("update:trigger", { ...newTrigger });
  },
  { deep: true },
);

const triggerTypes: { value: TriggerType; label: string }[] = [
  { value: "record_created", label: "记录创建时" },
  { value: "record_updated", label: "记录更新时" },
  { value: "specified_time", label: "指定时间" },
  // { value: "field_changed", label: "字段变更时（暂不支持）" },
  // { value: "manual", label: "手动触发（暂不支持）" },
];

const triggerType = computed({
  get: () => localTrigger.value.trigger_type,
  set: (value) => {
    const prevType = localTrigger.value.trigger_type;
    localTrigger.value.trigger_type = value;

    // 清理旧配置：从事件触发切换到指定时间时
    if (!isSpecifiedTimeTrigger(prevType) && isSpecifiedTimeTrigger(value)) {
      localTrigger.value.field_ids = [];
      const config = ensureFilterConfig();
      config.conditions = [];
      config.schedule = createDefaultScheduleConfig();
    }

    // 从指定时间切换回事件触发时
    if (isSpecifiedTimeTrigger(prevType) && !isSpecifiedTimeTrigger(value)) {
      const config = ensureFilterConfig();
      delete config.schedule;
    }

    if (value !== "record_updated" && value !== "field_changed") {
      localTrigger.value.field_ids = [];
    }
  },
});

const showFieldIdsSelector = computed(
  () =>
    localTrigger.value.trigger_type === "record_updated" ||
    localTrigger.value.trigger_type === "field_changed",
);

const showFilterSection = computed(
  () => !isSpecifiedTimeTrigger(localTrigger.value.trigger_type),
);

const showScheduleSection = computed(
  () => isSpecifiedTimeTrigger(localTrigger.value.trigger_type),
);

const fieldIdsEmpty = computed(
  () =>
    showFieldIdsSelector.value &&
    (localTrigger.value.field_ids ?? []).length === 0,
);

const selectedFieldIds = computed({
  get: () => localTrigger.value.field_ids ?? [],
  set: (value) => {
    localTrigger.value.field_ids = value;
  },
});

// ==================== 过滤条件 ====================

interface TriggerFilterCondition {
  field_id: string;
  operator: FilterOperatorValue;
  value: unknown;
}

function ensureFilterConfig(): Record<string, unknown> {
  if (!localTrigger.value.filter_config) {
    localTrigger.value.filter_config = {};
  }
  return localTrigger.value.filter_config;
}

const filterConditions = computed<TriggerFilterCondition[]>({
  get: () => {
    const config = ensureFilterConfig();
    return (config.conditions as TriggerFilterCondition[] | undefined) ?? [];
  },
  set: (value) => {
    const config = ensureFilterConfig();
    config.conditions = value;
  },
});

const filterConjunction = computed<"and" | "or">({
  get: () => {
    const config = ensureFilterConfig();
    return (config.conjunction as "and" | "or" | undefined) ?? "and";
  },
  set: (value) => {
    const config = ensureFilterConfig();
    config.conjunction = value;
  },
});

function addFilterCondition() {
  const config = ensureFilterConfig();
  // 确保 conjunction 字段被显式设置（前端默认 "and"，
  // 避免后端收到缺失 conjunction 的 filter_config）
  if (!config.conjunction) {
    config.conjunction = "and";
  }
  const firstField = props.fields[0];
  const defaultOperator = firstField
    ? getOperatorsForFieldType(firstField.type)[0] ?? FilterOperator.EQUALS
    : FilterOperator.EQUALS;
  filterConditions.value = [
    ...filterConditions.value,
    {
      field_id: firstField?.id ?? "",
      operator: defaultOperator,
      value: undefined,
    },
  ];
}

function removeFilterCondition(index: number) {
  const list = [...filterConditions.value];
  list.splice(index, 1);
  filterConditions.value = list;
}

function getFieldById(fieldId: string) {
  return props.fields.find((f) => f.id === fieldId);
}

function getOperatorOptions(fieldType: string) {
  return getOperatorsForFieldType(fieldType).map((op) => ({
    value: op,
    label: OPERATOR_LABELS[op],
  }));
}

function onFilterFieldChange(index: number, fieldId: string) {
  const list = [...filterConditions.value];
  const field = getFieldById(fieldId);
  const operators = field ? getOperatorsForFieldType(field.type) : [];
  list[index] = {
    field_id: fieldId,
    operator: operators[0] ?? FilterOperator.EQUALS,
    value: undefined,
  };
  filterConditions.value = list;
}

function onFilterOperatorChange(index: number, operator: FilterOperatorValue) {
  const list = [...filterConditions.value];
  list[index] = { ...list[index], operator };
  if (!operatorRequiresValue(operator)) {
    list[index].value = undefined;
  }
  filterConditions.value = list;
}

function onFilterValueChange(index: number, value: unknown) {
  const list = [...filterConditions.value];
  list[index] = { ...list[index], value };
  filterConditions.value = list;
}

// ==================== 定时器配置 ====================

const repeatTypeOptions: { value: ScheduleRepeatType; label: string }[] = [
  { value: "no_repeat", label: "不重复" },
  { value: "daily", label: "每天重复" },
  { value: "weekly", label: "每周重复" },
  { value: "monthly", label: "每月重复" },
  { value: "yearly", label: "每年重复" },
  { value: "weekdays", label: "周一至周五重复" },
  { value: "custom", label: "自定义重复" },
];

const customUnitOptions: { value: ScheduleCustomUnit; label: string }[] = [
  { value: "day", label: "天" },
  { value: "week", label: "周" },
  { value: "month", label: "月" },
  { value: "year", label: "年" },
];

function ensureScheduleConfig(): ScheduleConfig {
  const config = ensureFilterConfig();
  if (!config.schedule) {
    config.schedule = createDefaultScheduleConfig();
  }
  return config.schedule as ScheduleConfig;
}

const scheduleConfig = computed<ScheduleConfig>({
  get: () => ensureScheduleConfig(),
  set: (value) => {
    const config = ensureFilterConfig();
    config.schedule = value;
  },
});

const showCustomRepeat = computed(
  () => scheduleConfig.value.repeat_type === "custom",
);

const showEndDate = computed(
  () => scheduleConfig.value.end_type === "end_date",
);

function updateScheduleField<K extends keyof ScheduleConfig>(
  field: K,
  value: ScheduleConfig[K],
) {
  scheduleConfig.value = {
    ...scheduleConfig.value,
    [field]: value,
  };
}

function validateFieldIds(): boolean {
  return !fieldIdsEmpty.value;
}

defineExpose({ validateFieldIds });
</script>

<template>
  <div class="workflow-trigger-config">
    <el-form label-position="top" class="config-form">
      <el-form-item label="触发类型">
        <el-select v-model="triggerType" class="full-width" :disabled="readonly">
          <el-option
            v-for="type in triggerTypes"
            :key="type.value"
            :label="type.label"
            :value="type.value" />
        </el-select>
      </el-form-item>

      <el-form-item v-if="showFieldIdsSelector" label="监听字段" :error="fieldIdsEmpty ? '请选择监听字段' : ''">
        <el-select
          v-model="selectedFieldIds"
          multiple
          placeholder="选择监听的字段"
          class="full-width"
          :class="{ 'field-ids-error': fieldIdsEmpty }"
          :disabled="readonly">
          <el-option
            v-for="field in fields"
            :key="field.id"
            :label="field.name"
            :value="field.id" />
        </el-select>
      </el-form-item>

      <el-divider />

      <div v-if="showFilterSection" class="filter-section">
        <div class="filter-header">
          <span class="filter-title">触发过滤条件</span>
          <el-radio-group v-model="filterConjunction" size="small" :disabled="readonly">
            <el-radio-button label="and">全部满足</el-radio-button>
            <el-radio-button label="or">任一满足</el-radio-button>
          </el-radio-group>
        </div>

        <div class="conditions-list">
          <div
            v-for="(condition, index) in filterConditions"
            :key="index"
            class="condition-row">
            <el-select
              :model-value="condition.field_id"
              placeholder="选择字段"
              class="field-select"
              :disabled="readonly"
              @change="(val) => onFilterFieldChange(index, val as string)">
              <el-option
                v-for="field in fields"
                :key="field.id"
                :label="field.name"
                :value="field.id" />
            </el-select>

            <el-select
              :model-value="condition.operator"
              placeholder="操作符"
              class="operator-select"
              :disabled="readonly"
              @change="(val) => onFilterOperatorChange(index, val as FilterOperatorValue)">
              <el-option
                v-for="op in getOperatorOptions(getFieldById(condition.field_id)?.type ?? '')"
                :key="op.value"
                :label="op.label"
                :value="op.value" />
            </el-select>

            <div class="value-cell">
              <FieldValueInput
                v-if="operatorRequiresValue(condition.operator) && getFieldById(condition.field_id)"
                :field="getFieldById(condition.field_id)!"
                :model-value="condition.value"
                placeholder="值"
                class="value-input"
                :disabled="readonly"
                @update:model-value="(val) => onFilterValueChange(index, val)" />

              <span v-else class="value-placeholder">无需值</span>

              <el-button
                v-if="!readonly"
                type="danger"
                :icon="Delete"
                circle
                size="small"
                @click="removeFilterCondition(index)" />
            </div>
          </div>

          <el-button v-if="!readonly" type="primary" :icon="Plus" text @click="addFilterCondition">
            添加过滤条件
          </el-button>
        </div>
      </div>

      <div v-if="showScheduleSection" class="schedule-section">
        <div class="schedule-header">
          <span class="schedule-title">定时器配置</span>
        </div>

        <div class="schedule-form">
          <div class="schedule-row">
            <el-form-item class="schedule-start-date" label="触发日期">
              <el-date-picker
                :model-value="scheduleConfig.start_date"
                value-format="YYYY-MM-DD"
                placeholder="选择日期"
                class="full-width"
                :disabled="readonly"
                @update:model-value="(val: string) => updateScheduleField('start_date', val)" />
            </el-form-item>

            <el-form-item class="schedule-start-time" label="触发时间">
              <el-time-picker
                :model-value="scheduleConfig.start_time"
                value-format="HH:mm"
                format="HH:mm"
                placeholder="选择时间"
                class="full-width"
                :disabled="readonly"
                @update:model-value="(val: string) => updateScheduleField('start_time', val)" />
            </el-form-item>
          </div>

          <el-form-item class="schedule-repeat-type" label="重复模式">
            <el-select
              :model-value="scheduleConfig.repeat_type"
              class="full-width"
              :disabled="readonly"
              @update:model-value="(val: ScheduleRepeatType) => updateScheduleField('repeat_type', val)">
              <el-option
                v-for="option in repeatTypeOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value" />
            </el-select>
          </el-form-item>

          <div v-if="showCustomRepeat" class="schedule-row schedule-custom-row">
            <span class="custom-repeat-label">每</span>
            <el-input-number
              :model-value="scheduleConfig.custom_interval"
              :min="1"
              :disabled="readonly"
              @update:model-value="(val: number | undefined) => updateScheduleField('custom_interval', val ?? 1)" />
            <el-select
              :model-value="scheduleConfig.custom_unit"
              class="schedule-custom-unit"
              :disabled="readonly"
              @update:model-value="(val: ScheduleCustomUnit) => updateScheduleField('custom_unit', val)">
              <el-option
                v-for="option in customUnitOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value" />
            </el-select>
            <span class="custom-repeat-label">重复一次</span>
          </div>

          <el-form-item class="schedule-end-type" label="截止日期">
            <el-radio-group
              :model-value="scheduleConfig.end_type"
              :disabled="readonly"
              @update:model-value="(val: string | number | boolean | undefined) => updateScheduleField('end_type', val as ScheduleEndType)">
              <el-radio value="never">永不结束</el-radio>
              <el-radio value="end_date">指定日期</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item v-if="showEndDate" class="schedule-end-date" label="结束日期">
            <el-date-picker
              :model-value="scheduleConfig.end_date"
              value-format="YYYY-MM-DD"
              placeholder="选择结束日期"
              class="full-width"
              :disabled="readonly"
              @update:model-value="(val: string) => updateScheduleField('end_date', val)" />
          </el-form-item>
        </div>
      </div>
    </el-form>
  </div>
</template>

<style lang="scss" scoped>
.workflow-trigger-config {
  padding: $spacing-md;
}

.config-form {
  .el-form-item {
    margin-bottom: $spacing-md;
  }
}

.full-width {
  width: 100%;
}

.field-ids-error {
  :deep(.el-select__wrapper) {
    box-shadow: 0 0 0 1px var(--el-color-danger) inset;
  }
}

.filter-section,
.schedule-section {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.filter-header,
.schedule-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.filter-title,
.schedule-title {
  font-weight: 600;
  color: $text-primary;
}

.conditions-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.condition-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm;
  background-color: $bg-color;
  border-radius: $border-radius-md;
}

.field-select,
.operator-select {
  flex: 1;
  min-width: 100px;
}

.value-cell {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  width: 100%;
  flex-basis: 100%;
}

.value-input,
.value-placeholder {
  flex: 1;
}

.value-placeholder {
  color: $text-secondary;
  font-size: $font-size-sm;
}

.schedule-form {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.schedule-row {
  display: flex;
  gap: $spacing-md;

  .el-form-item {
    flex: 1;
    margin-bottom: 0;
  }
}

.schedule-custom-row {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm;
  background-color: $bg-color;
  border-radius: $border-radius-md;

  .custom-repeat-label {
    color: $text-primary;
    font-size: $font-size-sm;
  }

  .el-input-number {
    width: 120px;
  }

  .schedule-custom-unit {
    width: 120px;
  }
}

.schedule-end-type {
  :deep(.el-radio) {
    margin-right: $spacing-md;
  }
}
</style>
