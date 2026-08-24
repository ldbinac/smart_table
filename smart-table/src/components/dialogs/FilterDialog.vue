<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElDialog, ElButton, ElSelect, ElOption, ElInput, ElRadioGroup, ElRadioButton, ElDatePicker, ElInputNumber, ElTag } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { FilterOperator, type FilterCondition } from '@/types/filters'
import { FieldType } from '@/types/fields'
import type { FieldEntity } from '@/db/schema'

const { t } = useI18n()

const props = defineProps<{
  visible: boolean
  fields: FieldEntity[]
  initialFilters?: FilterCondition[]
  initialConjunction?: 'and' | 'or'
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'apply': [filters: FilterCondition[], conjunction: 'and' | 'or']
  'clear': []
}>()

interface FilterConditionExt extends FilterCondition {
  value?: any
}

const filters = ref<FilterConditionExt[]>([])
const conjunction = ref<'and' | 'or'>('and')

const textOperators = [
  { value: FilterOperator.EQUALS, label: t('filter.opEquals') },
  { value: FilterOperator.NOT_EQUALS, label: t('filter.opNotEquals') },
  { value: FilterOperator.CONTAINS, label: t('filter.opContains') },
  { value: FilterOperator.NOT_CONTAINS, label: t('filter.opNotContains') },
  { value: FilterOperator.STARTS_WITH, label: t('filter.opStartsWith') },
  { value: FilterOperator.ENDS_WITH, label: t('filter.opEndsWith') },
  { value: FilterOperator.IS_EMPTY, label: t('filter.opIsEmpty') },
  { value: FilterOperator.IS_NOT_EMPTY, label: t('filter.opIsNotEmpty') }
]

const numberOperators = [
  { value: FilterOperator.EQUALS, label: t('filter.opEquals') },
  { value: FilterOperator.NOT_EQUALS, label: t('filter.opNotEquals') },
  { value: FilterOperator.GREATER_THAN, label: t('filter.opGreaterThan') },
  { value: FilterOperator.LESS_THAN, label: t('filter.opLessThan') },
  { value: FilterOperator.GREATER_THAN_OR_EQUAL, label: t('filter.opGreaterThanOrEqual') },
  { value: FilterOperator.LESS_THAN_OR_EQUAL, label: t('filter.opLessThanOrEqual') },
  { value: FilterOperator.IS_EMPTY, label: t('filter.opIsEmpty') },
  { value: FilterOperator.IS_NOT_EMPTY, label: t('filter.opIsNotEmpty') }
]

const dateOperators = [
  { value: FilterOperator.EQUALS, label: t('filter.opEquals') },
  { value: FilterOperator.NOT_EQUALS, label: t('filter.opNotEquals') },
  { value: FilterOperator.GREATER_THAN, label: t('filter.opAfter') },
  { value: FilterOperator.LESS_THAN, label: t('filter.opBefore') },
  { value: FilterOperator.GREATER_THAN_OR_EQUAL, label: t('filter.opAfterOrEqual') },
  { value: FilterOperator.LESS_THAN_OR_EQUAL, label: t('filter.opBeforeOrEqual') },
  { value: FilterOperator.IS_EMPTY, label: t('filter.opIsEmpty') },
  { value: FilterOperator.IS_NOT_EMPTY, label: t('filter.opIsNotEmpty') }
]

const selectOperators = [
  { value: FilterOperator.EQUALS, label: t('filter.opEquals') },
  { value: FilterOperator.NOT_EQUALS, label: t('filter.opNotEquals') },
  { value: FilterOperator.IS_EMPTY, label: t('filter.opIsEmpty') },
  { value: FilterOperator.IS_NOT_EMPTY, label: t('filter.opIsNotEmpty') }
]

const checkboxOperators = [
  { value: FilterOperator.EQUALS, label: t('filter.opEquals') },
  { value: FilterOperator.IS_EMPTY, label: t('filter.opIsEmpty') }
]

function getOperatorsForField(field: FieldEntity | undefined) {
  if (!field) return textOperators
  
  switch (field.type) {
    case FieldType.NUMBER:
    case FieldType.RATING:
    case FieldType.PROGRESS:
      return numberOperators
    case FieldType.DATE:
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_TIME:
      return dateOperators
    case FieldType.SINGLE_SELECT:
    case FieldType.MULTI_SELECT:
    case FieldType.MEMBER:
      return selectOperators
    case FieldType.CHECKBOX:
      return checkboxOperators
    default:
      return textOperators
  }
}

function getValueInputType(field: FieldEntity | undefined): 'text' | 'number' | 'date' | 'select' | 'checkbox' | 'none' {
  if (!field) return 'text'
  
  switch (field.type) {
    case FieldType.NUMBER:
    case FieldType.RATING:
    case FieldType.PROGRESS:
      return 'number'
    case FieldType.DATE:
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_TIME:
      return 'date'
    case FieldType.SINGLE_SELECT:
    case FieldType.MULTI_SELECT:
      return 'select'
    case FieldType.CHECKBOX:
      return 'checkbox'
    default:
      return 'text'
  }
}

function needsValue(operator: string): boolean {
  return operator !== FilterOperator.IS_EMPTY && operator !== FilterOperator.IS_NOT_EMPTY
}

function addFilter() {
  const firstField = props.fields[0]
  if (!firstField) return
  
  filters.value.push({
    fieldId: firstField.id,
    operator: FilterOperator.EQUALS,
    value: undefined
  } as FilterConditionExt)
}

function removeFilter(index: number) {
  filters.value.splice(index, 1)
}

function getFieldById(fieldId: string) {
  return props.fields.find(f => f.id === fieldId)
}

function getSelectOptions(field: FieldEntity) {
  return (field.options?.choices || field.options?.options) as { id: string; name: string; color: string }[] || []
}

function onFieldChange(index: number) {
  const filter = filters.value[index]
  const field = getFieldById(filter.fieldId)
  if (field) {
    filter.value = undefined
    const operators = getOperatorsForField(field)
    filter.operator = operators[0]?.value || FilterOperator.EQUALS
  }
}

function applyFilters() {
  const validFilters = filters.value.filter(f => {
    if (!needsValue(f.operator)) return true
    return f.value !== undefined && f.value !== ''
  }) as FilterCondition[]
  
  emit('apply', validFilters, conjunction.value)
  emit('update:visible', false)
}

function clearFilters() {
  filters.value = []
  conjunction.value = 'and'
  emit('clear')
  emit('update:visible', false)
}

watch(() => props.visible, (visible) => {
  if (visible) {
    // 确保 initialFilters 是数组
    const initialFiltersArray = Array.isArray(props.initialFilters) 
      ? props.initialFilters 
      : []
    filters.value = [...initialFiltersArray]
    conjunction.value = props.initialConjunction || 'and'
    if (filters.value.length === 0 && props.fields.length > 0) {
      addFilter()
    }
  }
})
</script>

<template>
  <ElDialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="t('filter.title')"
    width="700px"
    :close-on-click-modal="false"
  >
    <div class="filter-dialog">
      <!-- 条件组合方式 -->
      <div class="conjunction-row">
        <span class="label">{{ t('filter.satisfyFollowing') }}</span>
        <ElRadioGroup v-model="conjunction" size="small">
          <ElRadioButton label="and">{{ t('filter.allConditions') }}</ElRadioButton>
          <ElRadioButton label="or">{{ t('filter.anyCondition') }}</ElRadioButton>
        </ElRadioGroup>
      </div>

      <!-- 筛选条件列表 -->
      <div class="filters-list">
        <div
          v-for="(filter, index) in filters"
          :key="index"
          class="filter-row"
        >
          <!-- 字段选择 -->
          <ElSelect
            v-model="filter.fieldId"
            :placeholder="t('filter.selectField')"
            style="width: 150px"
            @change="onFieldChange(index)"
          >
            <ElOption
              v-for="field in fields"
              :key="field.id"
              :label="field.name"
              :value="field.id"
            />
          </ElSelect>

          <!-- 操作符选择 -->
          <ElSelect
            v-model="filter.operator"
            :placeholder="t('filter.operator')"
            style="width: 130px"
          >
            <ElOption
              v-for="op in getOperatorsForField(getFieldById(filter.fieldId))"
              :key="op.value"
              :label="op.label"
              :value="op.value"
            />
          </ElSelect>

          <!-- 值输入 -->
          <template v-if="needsValue(filter.operator)">
            <!-- 文本输入 -->
            <ElInput
              v-if="getValueInputType(getFieldById(filter.fieldId)) === 'text'"
              v-model="filter.value"
              :placeholder="t('filter.inputValue')"
              style="width: 180px"
            />

            <!-- 数字输入 -->
            <ElInputNumber
              v-else-if="getValueInputType(getFieldById(filter.fieldId)) === 'number'"
              v-model="filter.value"
              :placeholder="t('filter.inputNumber')"
              style="width: 180px"
            />

            <!-- 日期输入 -->
            <ElDatePicker
              v-else-if="getValueInputType(getFieldById(filter.fieldId)) === 'date'"
              v-model="filter.value"
              type="date"
              :placeholder="t('filter.selectDate')"
              style="width: 180px"
              value-format="YYYY-MM-DD"
            />

            <!-- 选项选择 -->
            <ElSelect
              v-else-if="getValueInputType(getFieldById(filter.fieldId)) === 'select'"
              v-model="filter.value"
              :placeholder="t('filter.selectOption')"
              style="width: 180px"
            >
              <ElOption
                v-for="option in getSelectOptions(getFieldById(filter.fieldId)!)"
                :key="option.id"
                :label="option.name"
                :value="option.id"
              />
            </ElSelect>

            <!-- 复选框 -->
            <ElSelect
              v-else-if="getValueInputType(getFieldById(filter.fieldId)) === 'checkbox'"
              v-model="filter.value"
              :placeholder="t('filter.checkboxSelect')"
              style="width: 180px"
            >
              <ElOption :label="t('filter.checked')" :value="true" />
              <ElOption :label="t('filter.unchecked')" :value="false" />
            </ElSelect>
          </template>

          <!-- 删除按钮 -->
          <ElButton
            link
            type="danger"
            @click="removeFilter(index)"
          >
            {{ t('filter.delete') }}
          </ElButton>
        </div>
      </div>

      <!-- 添加条件按钮 -->
      <ElButton
        link
        type="primary"
        class="add-filter-btn"
        @click="addFilter"
      >
        + {{ t('filter.addCondition') }}
      </ElButton>

      <!-- 已选条件预览 -->
      <div v-if="filters.length > 0" class="filter-preview">
        <div class="preview-label">{{ t('filter.currentFilter') }}</div>
        <div class="preview-tags">
          <ElTag
            v-for="(filter, index) in filters"
            :key="index"
            size="small"
            closable
            @close="removeFilter(index)"
          >
            {{ getFieldById(filter.fieldId)?.name }}
            {{ getOperatorsForField(getFieldById(filter.fieldId)).find(o => o.value === filter.operator)?.label }}
            <template v-if="needsValue(filter.operator) && filter.value !== undefined">
              {{ filter.value }}
            </template>
          </ElTag>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <ElButton @click="$emit('update:visible', false)">{{ t('common.cancel') }}</ElButton>
        <ElButton link type="danger" @click="clearFilters">{{ t('filter.clear') }}</ElButton>
        <ElButton type="primary" @click="applyFilters">{{ t('filter.apply') }}</ElButton>
      </div>
    </template>
  </ElDialog>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.filter-dialog {
  .conjunction-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid $border-color;

    .label {
      color: $text-secondary;
      font-size: $font-size-sm;
    }
  }

  .filters-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 16px;
  }

  .filter-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .add-filter-btn {
    margin-bottom: 16px;
  }

  .filter-preview {
    padding-top: 12px;
    border-top: 1px solid $border-color;

    .preview-label {
      font-size: $font-size-sm;
      color: $text-secondary;
      margin-bottom: 8px;
    }

    .preview-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
