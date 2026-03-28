<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { FieldEntity } from "../../db/schema";
import type { FilterCondition, FilterOperatorValue } from "../../types";
import { FilterOperator } from "../../types";
import {
  getOperatorsForFieldType,
  OPERATOR_LABELS,
  operatorRequiresValue,
} from "../../utils/filter";
import FilterValueInput from "./FilterValueInput.vue";

interface Props {
  condition: FilterCondition;
  fields: FieldEntity[];
  removable: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "update:condition", value: FilterCondition): void;
  (e: "remove"): void;
}>();

const localCondition = ref<FilterCondition>({ ...props.condition });

watch(
  () => props.condition,
  (newVal) => {
    localCondition.value = { ...newVal };
  },
  { deep: true },
);

watch(
  localCondition,
  (newVal) => {
    emit("update:condition", newVal);
  },
  { deep: true },
);

const selectedField = computed(() => {
  return props.fields.find((f) => f.id === localCondition.value.fieldId);
});

const availableOperators = computed(() => {
  if (!selectedField.value) return [];
  return getOperatorsForFieldType(selectedField.value.type);
});

const operatorOptions = computed(() => {
  return availableOperators.value.map((op) => ({
    value: op,
    label: OPERATOR_LABELS[op],
  }));
});

const showValueInput = computed(() => {
  return (
    selectedField.value && operatorRequiresValue(localCondition.value.operator)
  );
});

function handleFieldChange(fieldId: string) {
  const field = props.fields.find((f) => f.id === fieldId);
  if (!field) return;

  const operators = getOperatorsForFieldType(field.type);
  const defaultOperator = operators[0] || FilterOperator.EQUALS;

  localCondition.value = {
    fieldId,
    operator: defaultOperator,
    value: undefined,
  };
}

function handleOperatorChange(operator: FilterOperatorValue) {
  localCondition.value.operator = operator;

  if (!operatorRequiresValue(operator)) {
    localCondition.value.value = undefined;
  }
}

function handleValueChange(value: unknown) {
  localCondition.value.value = value;
}

function handleRemove() {
  emit("remove");
}
</script>

<template>
  <div class="filter-condition">
    <el-select
      :model-value="localCondition.fieldId"
      placeholder="选择字段"
      class="field-select"
      @change="handleFieldChange">
      <el-option
        v-for="field in fields"
        :key="field.id"
        :label="field.name"
        :value="field.id" />
    </el-select>

    <el-select
      :model-value="localCondition.operator"
      placeholder="选择操作符"
      class="operator-select"
      :disabled="!selectedField"
      @change="handleOperatorChange">
      <el-option
        v-for="op in operatorOptions"
        :key="op.value"
        :label="op.label"
        :value="op.value" />
    </el-select>

    <FilterValueInput
      v-if="showValueInput && selectedField"
      :field="selectedField"
      :operator="localCondition.operator"
      :model-value="localCondition.value"
      @update:model-value="handleValueChange" />

    <el-button
      v-if="removable"
      type="danger"
      :icon="Delete"
      circle
      size="small"
      class="remove-btn"
      @click="handleRemove" />
  </div>
</template>

<script lang="ts">
import { Delete } from "@element-plus/icons-vue";
export default {
  name: "FilterCondition",
};
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.filter-condition {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm;
  background-color: $bg-color;
  border-radius: $border-radius-md;
  margin-bottom: $spacing-sm;

  &:last-child {
    margin-bottom: 0;
  }
}

.field-select {
  min-width: 140px;
}

.operator-select {
  min-width: 120px;
}

.remove-btn {
  flex-shrink: 0;
}
</style>
