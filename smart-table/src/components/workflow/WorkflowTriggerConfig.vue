<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import type { FieldEntity } from "@/db/schema";
import type { WorkflowTrigger, TriggerType } from "@/types/workflow";
import { FilterOperator } from "@/types/filters";
import type { FilterOperatorValue } from "@/types/filters";
import {
  getOperatorsForFieldType,
  OPERATOR_LABELS,
  operatorRequiresValue,
} from "@/utils/filter";
import FieldValueInput from "@/components/fields/FieldValueInput.vue";
import { Delete, Plus } from "@element-plus/icons-vue";

interface Props {
  trigger: WorkflowTrigger;
  fields: FieldEntity[];
  readonly?: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "update:trigger", trigger: WorkflowTrigger): void;
}>();

const localTrigger = ref<WorkflowTrigger>({ ...props.trigger });
let isUpdatingFromParent = false;

watch(
  () => props.trigger,
  (newTrigger) => {
    isUpdatingFromParent = true;
    localTrigger.value = { ...newTrigger };
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
  { value: "field_changed", label: "字段变更时" },
  { value: "manual", label: "手动触发" },
];

const triggerType = computed({
  get: () => localTrigger.value.trigger_type,
  set: (value) => {
    localTrigger.value.trigger_type = value;
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

      <el-form-item v-if="showFieldIdsSelector" label="监听字段">
        <el-select
          v-model="selectedFieldIds"
          multiple
          placeholder="选择监听的字段"
          class="full-width"
          :disabled="readonly">
          <el-option
            v-for="field in fields"
            :key="field.id"
            :label="field.name"
            :value="field.id" />
        </el-select>
      </el-form-item>

      <el-divider />

      <div class="filter-section">
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

.filter-section {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.filter-title {
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
</style>
