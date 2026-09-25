<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElDialog, ElButton, ElSelect, ElOption, ElInput, ElRadioGroup, ElRadioButton, ElDatePicker, ElInputNumber, ElTag } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { FilterOperator, type FilterCondition } from '@/types/filters'
import { FieldType } from '@/types/fields'
import type { FieldEntity } from '@/db/schema'
import { FormulaEngine } from '@/utils/formula/engine'
import { linkApiService } from '@/services/api/linkApiService'
import { useUserCacheStore } from '@/stores/userCacheStore'
import MemberSelect from '@/components/common/MemberSelect.vue'

const { t } = useI18n()

const userCacheStore = useUserCacheStore()

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

// 成员字段：包含/不属于等集合语义
const memberOperators = [
  { value: FilterOperator.IS_ANY_OF, label: t('filter.opIsAnyOf') },
  { value: FilterOperator.IS_NONE_OF, label: t('filter.opIsNoneOf') },
  { value: FilterOperator.CONTAINS, label: t('filter.opContains') },
  { value: FilterOperator.NOT_CONTAINS, label: t('filter.opNotContains') },
  { value: FilterOperator.IS_EMPTY, label: t('filter.opIsEmpty') },
  { value: FilterOperator.IS_NOT_EMPTY, label: t('filter.opIsNotEmpty') }
]

// 关联字段：属于/不属于关联记录
const linkOperators = [
  { value: FilterOperator.IS_ANY_OF, label: t('filter.opIsAnyOf') },
  { value: FilterOperator.IS_NONE_OF, label: t('filter.opIsNoneOf') },
  { value: FilterOperator.IS_EMPTY, label: t('filter.opIsEmpty') },
  { value: FilterOperator.IS_NOT_EMPTY, label: t('filter.opIsNotEmpty') }
]

// 查找字段：原值模式为数组，聚合模式为标量（数字），文本与数值比较均开放
const lookupOperators = [
  { value: FilterOperator.EQUALS, label: t('filter.opEquals') },
  { value: FilterOperator.NOT_EQUALS, label: t('filter.opNotEquals') },
  { value: FilterOperator.CONTAINS, label: t('filter.opContains') },
  { value: FilterOperator.NOT_CONTAINS, label: t('filter.opNotContains') },
  { value: FilterOperator.GREATER_THAN, label: t('filter.opGreaterThan') },
  { value: FilterOperator.LESS_THAN, label: t('filter.opLessThan') },
  { value: FilterOperator.GREATER_THAN_OR_EQUAL, label: t('filter.opGreaterThanOrEqual') },
  { value: FilterOperator.LESS_THAN_OR_EQUAL, label: t('filter.opLessThanOrEqual') },
  { value: FilterOperator.IS_EMPTY, label: t('filter.opIsEmpty') },
  { value: FilterOperator.IS_NOT_EMPTY, label: t('filter.opIsNotEmpty') }
]

// 公式字段按公式结果类型分派操作符
const formulaDateOperators = [
  { value: FilterOperator.EQUALS, label: t('filter.opEquals') },
  { value: FilterOperator.NOT_EQUALS, label: t('filter.opNotEquals') },
  { value: FilterOperator.GREATER_THAN, label: t('filter.opAfter') },
  { value: FilterOperator.LESS_THAN, label: t('filter.opBefore') },
  { value: FilterOperator.IS_EMPTY, label: t('filter.opIsEmpty') },
  { value: FilterOperator.IS_NOT_EMPTY, label: t('filter.opIsNotEmpty') }
]

function getFormulaResultType(field: FieldEntity): 'datetime' | 'date' | 'number' | 'text' {
  const formula = String(field.options?.formula ?? field.config?.formula ?? '')
  return FormulaEngine.inferResultType(formula)
}

function getOperatorsForField(field: FieldEntity | undefined) {
  if (!field) return textOperators

  switch (field.type) {
    case FieldType.NUMBER:
    case FieldType.RATING:
    case FieldType.PROGRESS:
      return numberOperators
    case FieldType.DATE:
    case FieldType.DATE_TIME:
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_TIME:
      return dateOperators
    case FieldType.SINGLE_SELECT:
    case FieldType.MULTI_SELECT:
      return selectOperators
    case FieldType.MEMBER:
      return memberOperators
    case FieldType.LINK:
      return linkOperators
    case FieldType.LOOKUP:
      return lookupOperators
    case FieldType.FORMULA: {
      const resultType = getFormulaResultType(field)
      if (resultType === 'number') return numberOperators
      if (resultType === 'date' || resultType === 'datetime') return formulaDateOperators
      return textOperators
    }
    case FieldType.CHECKBOX:
      return checkboxOperators
    default:
      return textOperators
  }
}

function getValueInputType(field: FieldEntity | undefined): 'text' | 'number' | 'date' | 'datetime' | 'select' | 'checkbox' | 'member' | 'link' | 'none' {
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
    case FieldType.DATE_TIME:
      // 日期时间字段使用带时间选择的日期时间组件
      return 'datetime'
    case FieldType.SINGLE_SELECT:
    case FieldType.MULTI_SELECT:
      return 'select'
    case FieldType.MEMBER:
      return 'member'
    case FieldType.LINK:
      return 'link'
    case FieldType.FORMULA: {
      const resultType = getFormulaResultType(field)
      if (resultType === 'number') return 'number'
      if (resultType === 'date' || resultType === 'datetime') return 'date'
      return 'text'
    }
    case FieldType.LOOKUP: {
      // 聚合模式（求和/平均/最大/最小/计数）产出数字，其余按文本
      const aggregation = String((field.config?.aggregationType as string) ?? 'original')
      return aggregation !== 'original' ? 'number' : 'text'
    }
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
    operator: getOperatorsForField(firstField)[0]?.value || FilterOperator.EQUALS,
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

// ==================== 关联字段选项加载 ====================

interface LinkRecordOption {
  id: string
  label: string
}

const linkFieldRecords = ref<Record<string, LinkRecordOption[]>>({})
const linkRecordsLoading = ref<Record<string, boolean>>({})

/** 从记录值中提取展示文本 */
function pickDisplayText(value: unknown): string {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'object') {
    const name = (value as { name?: string }).name
    return name ? String(name) : ''
  }
  return String(value)
}

function getLinkRecordLabel(record: { id: string; values: Record<string, unknown> }, field: FieldEntity): string {
  const displayFieldId = field.config?.displayFieldId as string | undefined
  if (displayFieldId) {
    const text = pickDisplayText(record.values?.[displayFieldId])
    if (text) return text
  }
  const values = Object.values(record.values || {})
  for (const value of values) {
    const text = pickDisplayText(value)
    if (text) return text
  }
  return record.id
}

async function loadLinkFieldRecords(field: FieldEntity | undefined) {
  if (!field || field.type !== FieldType.LINK) return
  const linkedTableId = String(field.config?.linkedTableId ?? '')
  if (!linkedTableId || linkFieldRecords.value[field.id]) return

  linkRecordsLoading.value[field.id] = true
  try {
    const result = await linkApiService.searchLinkableRecords(linkedTableId, {
      page: 1,
      per_page: 100
    })
    linkFieldRecords.value[field.id] = result.items.map((r) => ({
      id: r.id,
      label: getLinkRecordLabel(r, field)
    }))
  } catch (error) {
    console.error('[FilterDialog] 加载关联记录失败:', error)
    linkFieldRecords.value[field.id] = []
  } finally {
    linkRecordsLoading.value[field.id] = false
  }
}

// ==================== 预览格式化 ====================

const memberNameMap = ref<Record<string, string>>({})

async function resolveMemberNames(ids: string[]) {
  const missing = ids.filter((id) => !memberNameMap.value[id])
  if (missing.length === 0) return
  try {
    const users = await userCacheStore.fetchUsers(missing)
    const map: Record<string, string> = { ...memberNameMap.value }
    for (const user of users) map[user.id] = user.name
    memberNameMap.value = map
  } catch (error) {
    console.error('[FilterDialog] 解析成员姓名失败:', error)
  }
}

function collectMemberIds(): string[] {
  const ids = new Set<string>()
  for (const filter of filters.value) {
    const field = getFieldById(filter.fieldId)
    if (field?.type === FieldType.MEMBER && Array.isArray(filter.value)) {
      for (const id of filter.value) ids.add(String(id))
    }
  }
  return [...ids]
}

function asIdArray(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String)
  return value !== undefined && value !== null && value !== '' ? [String(value)] : []
}

/** 关联字段选项：已选值中不在选项列表的 ID 兜底显示，避免回显丢失 */
function getLinkOptions(filter: FilterConditionExt): LinkRecordOption[] {
  const loaded = linkFieldRecords.value[filter.fieldId] || []
  if (!Array.isArray(filter.value) || filter.value.length === 0) return loaded
  const knownIds = new Set(loaded.map((o) => o.id))
  const extras = filter.value
    .map((id) => String(id))
    .filter((id) => !knownIds.has(id))
    .map((id) => ({ id, label: id }))
  return [...extras, ...loaded]
}

function formatFilterValue(filter: FilterConditionExt): string {
  const field = getFieldById(filter.fieldId)
  const value = filter.value
  if (value === undefined || value === null || value === '') return ''
  if (Array.isArray(value)) {
    if (field?.type === FieldType.MEMBER) {
      return value.map((id) => memberNameMap.value[String(id)] || String(id)).join(', ')
    }
    if (field?.type === FieldType.LINK) {
      const options = linkFieldRecords.value[filter.fieldId] || []
      const labelMap = Object.fromEntries(options.map((o) => [o.id, o.label]))
      return value.map((id) => labelMap[String(id)] || String(id)).join(', ')
    }
    return value.map((v) => String(v)).join(', ')
  }
  return String(value)
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
    // 回显：解析成员姓名、预加载关联字段选项，保证预览与下拉可显示
    resolveMemberNames(collectMemberIds())
    for (const filter of filters.value) {
      const field = getFieldById(filter.fieldId)
      if (field?.type === FieldType.LINK) {
        loadLinkFieldRecords(field)
      }
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
            <!-- 成员选择 -->
            <MemberSelect
              v-if="getValueInputType(getFieldById(filter.fieldId)) === 'member'"
              :model-value="asIdArray(filter.value)"
              allow-multiple
              :placeholder="t('filter.selectMember')"
              class="filter-member-select"
              @update:model-value="filter.value = $event"
            />

            <!-- 关联记录选择 -->
            <ElSelect
              v-else-if="getValueInputType(getFieldById(filter.fieldId)) === 'link'"
              :model-value="asIdArray(filter.value)"
              multiple
              filterable
              collapse-tags
              collapse-tags-tooltip
              :loading="linkRecordsLoading[filter.fieldId]"
              :placeholder="t('filter.selectLinkedRecord')"
              style="width: 180px"
              @update:model-value="filter.value = $event"
              @visible-change="(v: boolean) => v && loadLinkFieldRecords(getFieldById(filter.fieldId))"
            >
              <ElOption
                v-for="option in getLinkOptions(filter)"
                :key="option.id"
                :label="option.label"
                :value="option.id"
              />
            </ElSelect>

            <!-- 文本输入 -->
            <ElInput
              v-else-if="getValueInputType(getFieldById(filter.fieldId)) === 'text'"
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

            <!-- 日期/日期时间输入 -->
            <ElDatePicker
              v-else-if="['date', 'datetime'].includes(getValueInputType(getFieldById(filter.fieldId)))"
              v-model="filter.value"
              :type="getValueInputType(getFieldById(filter.fieldId)) === 'datetime' ? 'datetime' : 'date'"
              :placeholder="t('filter.selectDate')"
              style="width: 180px"
              value-format="x"
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
            <template v-if="needsValue(filter.operator) && formatFilterValue(filter)">
              {{ formatFilterValue(filter) }}
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

    .filter-member-select {
      width: 180px;
      flex-shrink: 0;
    }
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
