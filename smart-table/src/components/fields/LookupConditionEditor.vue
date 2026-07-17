<script setup lang="ts">
import { computed } from "vue";
import { Delete } from "@element-plus/icons-vue";
import type { FieldEntity } from "@/db/schema";
import type {
  LookupFilterOperator,
  LookupFilterCondition,
} from "@/types/fields";
import { getLookupFilterOperatorLabel } from "@/types/fields";

interface Props {
  /** 过滤条件列表 */
  conditions: LookupFilterCondition[];
  /** 条件连接：and 或 or */
  conjunction: "and" | "or";
  /** 源表字段列表（用于条件中的 fieldId 选择） */
  sourceTableFields: FieldEntity[];
  /** 当前表字段列表（用于条件中 valueType=field 时的 valueFieldId 选择） */
  currentTableFields: FieldEntity[];
  /** 是否禁用 */
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
});

const emit = defineEmits<{
  (e: "update:conditions", value: LookupFilterCondition[]): void;
  (e: "update:conjunction", value: "and" | "or"): void;
}>();

const MAX_CONDITIONS = 5;

const numberLikeTypes = ["number", "currency", "percent", "rating"];
const dateLikeTypes = ["date", "date_time"];

/** 是否可以继续添加条件 */
const canAddCondition = computed(() => props.conditions.length < MAX_CONDITIONS);

/** 获取适用于指定字段类型的操作符列表 */
function getApplicableOperators(fieldType: string): LookupFilterOperator[] {
  const base: LookupFilterOperator[] = [
    "equal",
    "not_equal",
    "is_empty",
    "is_not_empty",
  ];
  const textLikeTypes = [
    "single_line_text",
    "long_text",
    "rich_text",
    "email",
    "phone",
    "url",
  ];
  const selectMemberLinkTypes = [
    "single_select",
    "multi_select",
    "collaborator",
    "member",
    "link",
    "link_to_record",
  ];
  const dateLikeOperatorTypes = [
    "date",
    "date_time",
    "created_time",
    "updated_time",
  ];

  if (
    textLikeTypes.includes(fieldType) ||
    selectMemberLinkTypes.includes(fieldType)
  ) {
    return [...base, "contains"];
  }
  if (dateLikeOperatorTypes.includes(fieldType)) {
    return [...base, "before", "after"];
  }
  return base;
}

/** 判断操作符是否为空值类型（无需值输入） */
function isEmptyOperator(operator: LookupFilterOperator): boolean {
  return operator === "is_empty" || operator === "is_not_empty";
}

/** 根据字段 ID 查找源表字段 */
function getSourceField(fieldId: string): FieldEntity | undefined {
  return props.sourceTableFields.find((f) => f.id === fieldId);
}

/** 获取源表字段的类型 */
function getSourceFieldType(fieldId: string): string {
  return getSourceField(fieldId)?.type || "";
}

/** 判断字段类型是否为数字类（需用 ElInputNumber） */
function isNumberLikeType(type: string): boolean {
  return numberLikeTypes.includes(type);
}

/** 判断字段类型是否为日期类（需用 ElDatePicker） */
function isDateLikeType(type: string): boolean {
  return dateLikeTypes.includes(type);
}

/** 添加新条件 */
function addCondition() {
  if (props.conditions.length >= MAX_CONDITIONS) return;
  const newCondition: LookupFilterCondition = {
    fieldId: props.sourceTableFields[0]?.id || "",
    operator: "equal",
    valueType: "custom",
    valueCustom: "",
  };
  emit("update:conditions", [...props.conditions, newCondition]);
}

/** 删除指定索引的条件 */
function removeCondition(index: number) {
  const newConditions = [...props.conditions];
  newConditions.splice(index, 1);
  emit("update:conditions", newConditions);
}

/** 更新单个条件 */
function updateCondition(index: number, updates: Partial<LookupFilterCondition>) {
  const newConditions = [...props.conditions];
  newConditions[index] = { ...newConditions[index], ...updates };
  emit("update:conditions", newConditions);
}

/** 当字段变更时，如果当前操作符不适用于新字段类型，重置为 equal */
function onFieldChange(index: number, newFieldId: string) {
  const field = props.sourceTableFields.find((f) => f.id === newFieldId);
  if (field) {
    const applicable = getApplicableOperators(field.type);
    const current = props.conditions[index];
    if (!applicable.includes(current.operator)) {
      updateCondition(index, { fieldId: newFieldId, operator: "equal" });
      return;
    }
  }
  updateCondition(index, { fieldId: newFieldId });
}

/** 当操作符变更时，如果是 is_empty/is_not_empty，清除 value */
function onOperatorChange(index: number, newOperator: LookupFilterOperator) {
  if (newOperator === "is_empty" || newOperator === "is_not_empty") {
    updateCondition(index, {
      operator: newOperator,
      valueCustom: undefined,
      valueFieldId: undefined,
    });
  } else {
    updateCondition(index, { operator: newOperator });
  }
}
</script>

<template>
  <div class="lookup-condition-editor">
    <!-- 顶部 conjunction 切换 -->
    <div class="conjunction-bar">
      <ElRadioGroup
        :model-value="conjunction"
        :disabled="disabled"
        size="small"
        @update:model-value="
          emit('update:conjunction', $event as 'and' | 'or')
        "
      >
        <ElRadioButton value="and">满足全部条件</ElRadioButton>
        <ElRadioButton value="or">满足任一条件</ElRadioButton>
      </ElRadioGroup>
    </div>

    <!-- 条件列表 -->
    <div class="condition-list">
      <div
        v-for="(condition, index) in conditions"
        :key="index"
        class="condition-row"
      >
        <!-- 1. 源表字段下拉 -->
        <ElSelect
          :model-value="condition.fieldId"
          :disabled="disabled"
          size="small"
          placeholder="选择字段"
          class="condition-field-select"
          @update:model-value="onFieldChange(index, $event as string)"
        >
          <ElOption
            v-for="field in sourceTableFields"
            :key="field.id"
            :label="field.name"
            :value="field.id"
          />
        </ElSelect>

        <!-- 2. 操作符下拉 -->
        <ElSelect
          :model-value="condition.operator"
          :disabled="disabled"
          size="small"
          placeholder="选择操作符"
          class="condition-operator-select"
          @update:model-value="
            onOperatorChange(index, $event as LookupFilterOperator)
          "
        >
          <ElOption
            v-for="op in getApplicableOperators(
              getSourceFieldType(condition.fieldId),
            )"
            :key="op"
            :label="getLookupFilterOperatorLabel(op)"
            :value="op"
          />
        </ElSelect>

        <!-- 3. 值类型切换 + 4. 值输入（is_empty/is_not_empty 时隐藏） -->
        <template v-if="!isEmptyOperator(condition.operator)">
          <ElSelect
            :model-value="condition.valueType"
            :disabled="disabled"
            size="small"
            class="condition-value-type-select"
            @update:model-value="
              updateCondition(index, {
                valueType: $event as 'field' | 'custom',
              })
            "
          >
            <ElOption label="当前表字段" value="field" />
            <ElOption label="自定义值" value="custom" />
          </ElSelect>

          <div class="condition-value-input">
            <!-- valueType === 'field'：当前表字段下拉 -->
            <ElSelect
              v-if="condition.valueType === 'field'"
              :model-value="condition.valueFieldId"
              :disabled="disabled"
              size="small"
              placeholder="选择当前表字段"
              class="value-field-select"
              @update:model-value="
                updateCondition(index, { valueFieldId: $event as string })
              "
            >
              <ElOption
                v-for="field in currentTableFields"
                :key="field.id"
                :label="field.name"
                :value="field.id"
              />
            </ElSelect>

            <!-- valueType === 'custom'：根据源表字段类型动态渲染 -->
            <template v-else>
              <ElInputNumber
                v-if="isNumberLikeType(getSourceFieldType(condition.fieldId))"
                :model-value="
                  typeof condition.valueCustom === 'number'
                    ? condition.valueCustom
                    : undefined
                "
                :disabled="disabled"
                size="small"
                placeholder="请输入数值"
                class="value-custom-input"
                @update:model-value="
                  updateCondition(index, {
                    valueCustom: $event as number | undefined,
                  })
                "
              />
              <ElDatePicker
                v-else-if="
                  isDateLikeType(getSourceFieldType(condition.fieldId))
                "
                :model-value="
                  typeof condition.valueCustom === 'string'
                    ? condition.valueCustom
                    : undefined
                "
                :disabled="disabled"
                size="small"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="请选择日期"
                class="value-custom-input"
                @update:model-value="
                  updateCondition(index, {
                    valueCustom: ($event as string | null) ?? undefined,
                  })
                "
              />
              <ElInput
                v-else
                :model-value="
                  typeof condition.valueCustom === 'string'
                    ? condition.valueCustom
                    : ''
                "
                :disabled="disabled"
                size="small"
                placeholder="请输入值"
                class="value-custom-input"
                @update:model-value="
                  updateCondition(index, { valueCustom: $event as string })
                "
              />
            </template>
          </div>
        </template>

        <!-- 删除条件按钮 -->
        <ElButton
          text
          size="small"
          :disabled="disabled"
          class="condition-delete-btn"
          @click="removeCondition(index)"
        >
          <ElIcon><Delete /></ElIcon>
        </ElButton>
      </div>
    </div>

    <!-- 添加条件按钮 -->
    <ElButton
      :disabled="!canAddCondition || disabled"
      size="small"
      class="add-button"
      @click="addCondition"
    >
      + 添加条件
    </ElButton>
  </div>
</template>

<style lang="scss" scoped>
.lookup-condition-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.conjunction-bar {
  display: flex;
  align-items: center;
}

.condition-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.condition-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.condition-field-select,
.condition-operator-select,
.condition-value-type-select,
.condition-value-input {
  flex: 1;
  min-width: 0;
}

// ElSelect 默认有固定宽度，需要强制撑满容器
.condition-field-select,
.condition-operator-select,
.condition-value-type-select,
.value-field-select {
  width: 100%;
}

.condition-value-input {
  display: flex;
  align-items: center;

  .value-custom-input {
    width: 100%;
  }
}

.condition-delete-btn {
  flex: none;
  padding: 4px;
}

.add-button {
  width: 100%;
  border-style: dashed;
}
</style>
